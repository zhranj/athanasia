// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/IERC721Enumerable.sol";
import "../interfaces/IAthanasia.sol";
import "../interfaces/IAthanasiaOtc.sol";

interface IHectorStaking {
    function unstake(uint256 _amount, bool _trigger) external;

    function index() external view returns (uint256);
}

/**
 * @dev Implementation of the IAthanasia interface for the Hector Finance (HEC) underlying token.
 *
 * Athanasia enables NFT collection owners to lock in a portion of the mint sale price in form of a secondary underlying token.
 *
 * Typically during an NFT mint, configured value is deposited into this smart contract and an OTC purchase of the
 * underlying token. This is done to avoid price spikes during minting.
 * Alternatively, one may also choose to directly deposit the underlying tokens.
 *
 * The best fit tokens are those that can be staked to earn rewards. The reward part can then be withdrawn by the NFT owner.
 */
contract AthanasiaHector is IAthanasia, Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ERC20 token address for $HEC token
    IERC20 public immutable hecToken;

    // ERC20 token address for $sHEC token
    IERC20 public immutable shecToken;

    // Hector Staking contract address
    IHectorStaking public immutable hecStakingContract;

    // Hector contract for selling over-the-counter HEC/sHEC token.
    address public hectorOtcContract;

    // Number of tokens in 1 HEC / sHEC
    uint256 public immutable ONE_HECTOR = 10**9;

    struct CollectionInfo {
        // The amount of HEC which will be deposited for each NFT minted.
        // This is the total amount purchased for each NFT via OTC contract.
        // In case of registerDeposit, this denotes the total deposit amount for the entire collection
        uint256 depositAmount;
        // ERC20 token which will be used to purchase HEC in the OTC contract.
        address otcPurchaseToken;
        // OTC price for purchase of 1 HEC.
        uint256 otcPrice;
        // If deposit on register is used, this value will be set to the current index at the time of deposit.
        uint256 stakingIndexOnDeposit;
    }

    // Contains all registered collections.
    mapping(address => CollectionInfo) public collections;

    // Tracks the staking indexes for each NFT in each collection at last withdrawal.
    mapping(address => mapping(uint256 => uint256)) stakingIndexes;

    /**
     * @dev Initializes the contract by setting `hecToken` and `shecToken` token addresses and the `hecStakingContract` address.
     */
    constructor(address _hecToken, address _sHecToken, address _hecStakingContract) {
        require(_hecStakingContract != address(0), "staking contract");
        hecStakingContract = IHectorStaking(_hecStakingContract);
        require(_hecToken != address(0), "HEC");
        hecToken = IERC20(_hecToken);
        require(_sHecToken != address(0), "sHEC");
        shecToken = IERC20(_sHecToken);
    }

    /**
     * @dev See {IAthanasia-initialize}.
     */
    function initialize(address _otcContract) external onlyOwner {
        require(_otcContract != address(0), "initialize: OTC contract");
        hectorOtcContract = _otcContract;
        shecToken.approve(address(hecStakingContract), ~uint256(0));
    }

    /**
     * @dev See {IAthanasia-registerCollectionWithOtc}.
     */
    function registerCollectionWithOtc(address _collection, address _otcToken, uint256 _otcPrice, uint256 _depositAmount) external {
        require(msg.sender == _collection || msg.sender == Ownable(_collection).owner(), "Athanasia: Only collection owner may register the collection");
        require(_depositAmount > 0, "Athanasia: Invalid deposit amount");
        require(_otcPrice > 0, "Athanasia: Invalid OTC price");

        // Make sure the OTC was allowed by Hector team
        require(IAthanasiaOtc(hectorOtcContract).validateCollection(_collection, _otcToken, _otcPrice), "Athanasia: Collection not registered with OTC contract");

        collections[_collection] = CollectionInfo(_depositAmount, _otcToken, _otcPrice, 0);

        // Approve HEctor OTC contract so it can transfer OTC tokens over and give us sHEC
        if (_otcToken != address(0)) {  // if null address, use FTM
            IERC20(_otcToken).approve(hectorOtcContract, ~uint256(0));
        }
    }

    /**
     * @dev See {IAthanasia-registerCollection}.
     */
    function registerCollection(address _collection, uint256 _depositAmount) external {
        require(msg.sender == _collection || msg.sender == Ownable(_collection).owner(), "Athanasia: Only collection owner may register the collection");
        require(_depositAmount > 0, "Athanasia: Invalid deposit amount");
        collections[_collection] = CollectionInfo(_depositAmount, address(0), 0, 0);
    }

    /**
     * @dev See {IAthanasia-registerCollectionAndDeposit}.
     */
    function registerCollectionAndDeposit(address _collection, uint256 _depositAmount, uint256 _collectionSize) external {
        require(msg.sender == _collection || msg.sender == Ownable(_collection).owner(), "Athanasia: Only collection owner may register the collection");
        require(_depositAmount > 0, "Athanasia: Invalid deposit amount");
        require(IERC721Enumerable(_collection).totalSupply() <= _collectionSize, "Athanasia: Invalid collection size");
        require(collections[_collection].depositAmount == 0, "Athanasia: Collection already registered");

        collections[_collection] = CollectionInfo(_depositAmount * _collectionSize, address(0), 0, hecStakingContract.index());

        shecToken.safeTransferFrom(msg.sender, address(this), _depositAmount * _collectionSize);
    }

    function _claimableBalance(address _collection, uint256 _tokenId) internal view returns (uint256 withdrawable) {
        // Check that the collection exists
        CollectionInfo memory collection = collections[_collection];
        if (collections[_collection].depositAmount == 0) {
            // Collection not registered
            return 0;
        }

        uint256 hecDepositPerNft = collection.depositAmount;

        // For collections where underlying tokens were not deposited during registration,
        // the deposit must be made explicitly, during which the staking index is recorded.
        if (collection.stakingIndexOnDeposit == 0) {
            if(stakingIndexes[_collection][_tokenId] == 0) {
                // No deposits were made
                return 0;
            }
        } else {
            hecDepositPerNft /= IERC721Enumerable(_collection).totalSupply();
        }

        uint256 currentIndex = hecStakingContract.index();
        uint256 indexAtLastWithdrawal = stakingIndexes[_collection][_tokenId];
        if (indexAtLastWithdrawal == 0) {
            indexAtLastWithdrawal = collection.stakingIndexOnDeposit;
        }

        if (indexAtLastWithdrawal >= currentIndex) {
            // No rebases happened
            return 0;
        }

        return (currentIndex - indexAtLastWithdrawal) * hecDepositPerNft / indexAtLastWithdrawal;
    }

    /**
     * @dev See {IAthanasia-claimableBalance}.
     */
    function claimableBalance(address _collection, uint256 _tokenId) external view returns (uint256 withdrawable) {
        return _claimableBalance(_collection, _tokenId);
    }

    /**
     * @dev See {IAthanasia-claim}.
     */
    function claim(address _collection, uint256[] memory _tokenIds) external {
        uint256 totalClaimable = 0;
        uint256 currentIndex = hecStakingContract.index();
        for (uint256 i = 0; i < _tokenIds.length; ++i) {
            require(IERC721Enumerable(_collection).ownerOf(_tokenIds[i]) == msg.sender, "Athanasia: Not owner");
            totalClaimable += _claimableBalance(_collection, _tokenIds[i]);
            stakingIndexes[_collection][_tokenIds[i]] = currentIndex;
        }

        if (totalClaimable > 0) {
            // Unstake the amount being claimed.
            hecStakingContract.unstake(totalClaimable, false);

            // Send the HEC to the caller
            hecToken.safeTransfer(msg.sender, totalClaimable);
        }
    }

    function _updateStakingIndexes(address _collection, uint256[] memory _tokenIds) internal {
        // Check that the collection exists
        uint256 hecAmountPerNft = collections[_collection].depositAmount;
        require(hecAmountPerNft > 0, "Athanasia: Collection not registered");

        uint256 currentIndex = hecStakingContract.index();
        for (uint256 i = 0; i < _tokenIds.length; ++i) {
            // Token must exist
            require(IERC721Enumerable(_collection).ownerOf(_tokenIds[i]) != address(0), "Athanasia: nonexistent token");
            // Token must not already be deposited
            require(stakingIndexes[_collection][_tokenIds[i]] == 0, "Athanasia: Token already deposited");
            stakingIndexes[_collection][_tokenIds[i]] = currentIndex;
        }
    }

    /**
     * @dev See {IAthanasia-deposit}.
     */
    function deposit(address _collection, uint256[] memory _tokenIds) external {
        _updateStakingIndexes(_collection, _tokenIds);
        shecToken.safeTransferFrom(msg.sender, address(this), _tokenIds.length * collections[_collection].depositAmount);
    }

    /**
     * @dev See {IAthanasia-depositWithOtc}.
     */
    function depositWithOtc(address _collection, uint256[] memory _tokenIds) external payable nonReentrant {
        _updateStakingIndexes(_collection, _tokenIds);

        uint256 hecAmountPerNft = collections[_collection].depositAmount;
        uint256 totalAmountForOtc = _tokenIds.length * collections[_collection].otcPrice * hecAmountPerNft / ONE_HECTOR;

        // First, transfer the tokens to this smart contract
        address otcTokenAddress = collections[_collection].otcPurchaseToken;
        if (otcTokenAddress == address(0)) {
            // OTC done in native FTM
            require(msg.value >= totalAmountForOtc, "Athanasia: Insufficient FTM funds for OTC");
            // Call OTC contract to perfomr OTC buy and send the needed FTM value over
            IAthanasiaOtc(hectorOtcContract).otc{value: totalAmountForOtc}(_collection, _tokenIds.length * hecAmountPerNft, totalAmountForOtc);
        }
        else {
            // OTC done in custom ERC20 token
            IERC20(collections[_collection].otcPurchaseToken).safeTransferFrom(msg.sender, address(this), totalAmountForOtc);
            // Call OTC contract to perform OTC buy
            IAthanasiaOtc(hectorOtcContract).otc(_collection, _tokenIds.length * hecAmountPerNft, totalAmountForOtc);
        }
    }
}
