// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @dev Required interface for an Athanasia passive yield capable NFTs.
 *
 * Athanasia enables NFT collection owners to lock in a portion of the mint sale price in form of a secondary underlying token.
 *
 * Typically during an NFT mint, configured value is deposited into this smart contract and an OTC purchase of the
 * underlying token. This is done to avoid price spikes during minting.
 * Alternatively, one may also choose to directly deposit the underlying tokens.
 *
 * The best fit tokens are those that can be staked to earn rewards. The reward part can then be withdrawn by the NFT owner.
 */
interface IAthanasia {
    /**
     * @dev Emitted when initial balance is deposited for an NFT.
     */
    event Deposit(address indexed depositor, address indexed collection, uint256 indexed tokenId, uint256 despositAmount);

    /**
     * @dev Emitted when the NFT owner claims the staking reward.
     */
    event Claim(address indexed owner, address indexed collection, uint256 indexed tokenId, uint256 withdrawAmount);

    /**
     * @dev Initialize this contract with the OTC address of the contract the sells OTC underlying token.
     *
     * Requirements:
     *  - can only be called by the owner.
     */
    function initialize(address otcContract) external;

    /**
     * @dev Registers or updates a collection with Athanasia, with the intent to purchase underlying tokens via OTC contract.
     *
     * Requirements:
     *  - caller must be the collection itself, or the owner of the collection (collection must inherit Ownable contract).
     *  - `otcPrice` must not be zero, represents the amount of underlying tokens deposited per NFT
     *  - `otcToken` may be null address, in which case native FTM token is used
     */
    function registerCollectionWithOtc(address collection, address otcToken, uint256 otcPrice, uint256 depositAmount) external;

    /**
     * @dev Registers or updates a collection with Athanasia, with the intent to purchase underlying tokens via OTC contract.
     *
     * Requirements:
     *  - caller must be the collection itself, or the owner of the collection (collection must inherit Ownable contract).
     *  - `depositAmount` must be positive, represents the amount of underlying tokens deposited per NFT
     */
    function registerCollection(address collection, uint256 depositAmount) external;

    /**
     * @dev Registers collection and immediately deposit all underlying tokens for the entire collection.
     *
     * This function allows already minted collections to onboard to Athanasia.
     * Requirements:
     *  - caller must be the collection itself, or the owner of the collection (collection must inherit Ownable contract).
     *  - `depositAmount` must be positive, represents the amount of underlying tokens deposited per NFT
     *  - `collectionSize` is the total collection size (or totalSupply if minting is complete)
     *  - caller must have depositAmount * collectionSize of underlying tokens on balance
     */
    function registerCollectionAndDeposit(address collection, uint256 depositAmount, uint256 collectionSize) external;

    /**
     * @dev Registers collection and immediately perform an OTC purchase for all underlying tokens for the entire collection
     *  using the specified otcToken and otcPrice.
     *
     * This function allows already minted collections to onboard to Athanasia.
     * Requirements:
     *  - caller must be the collection itself, or the owner of the collection (collection must inherit Ownable contract).
     *  - collection must be registered with OTC contract with exact same OTC token and OTC price, and the OTC amount
     *  - `depositAmount` must be positive, represents the amount of underlying tokens deposited per NFT
     *  - `collectionSize` is the total collection size (or totalSupply if minting is complete)
     *  - caller must have depositAmount * collectionSize * otcPrice / 10^9 of OTC tokens on balance and must have approved
     *       the athanasia contract to transfer the tokens
     */
    function registerCollectionAndDepositWithOtc(address collection, uint256 depositAmount, uint256 collectionSize, address otcToken, uint256 otcPrice) external payable;

    /**
     * @dev Returns the number of tokens the owner of the `tokenId` from collection `collection` may withdraw.
     *
     * Requirements:
     *  - `collection` must be registered with Athanasia.
     *  - `tokenId` must have had its initial balance deposited for.
     */
    function claimableBalance(address collection, uint256 tokenId) external view returns (uint256 withdrawable);

    /**
     * @dev Withdraws all the claimable tokens to the sender's wallet.
     *
     * Requirements:
     *  - `collection` must be registered with Athanasia.
     *  - `tokenIds` must have had its initial balance deposited for.
     *  - caller must be the owner of all the tokens
     */
    function claim(address collection, uint256[] memory tokenIds) external;

    /**
     * @dev Deposit the inital value for multiple NFTs and perform an OTC purchase of the underlying token.
     *
     * Requirements:
     *  - transaction initiator must be the owner of the NFTs
     *  - `collection` must be registered with Athanasia.
     *  - `tokenId` must have had its initial balance deposited for.
     *  - caller must be the owner of the token
     */
    function depositWithOtc(address collection, uint256[] memory tokenIds) external payable;

    /**
     * @dev Deposit the initial value for multiple NFTs by depositing the underlying token directly.
     *
     * Requirements:
     *  - `collection` must be registered with Athanasia.
     *  - `tokenId` must not have had its initial balance deposited for.
     *  - caller must be the owner of the token
     */
    function deposit(address collection, uint256[] memory tokenIds) external;

    /**
     * @dev Set the address of the upgraded contract. NFT holders may choose to stay on the
     * current version or to upgrade.
     */
    function setUpgradeAddress(address contractAddress) external;

    /**
     * @dev Upgrade NFTs from specific collection to the new smart contract version.
     *
     * Requirements:
     *  - callably only by the NFT owner.
     *  - upgrade contract must have been set.
     *
     * Consequences:
     *  - earning state is transfered to the new smart contract.
     *  - upon success, will not allow NFT owner to claim on this smart contract any more.
     *  - depending on implementation, may also claim any available earnings for the caller.
     *  - upgrade is not reversible.
     */
    function upgrade(address collection, uint256[] memory tokenIds) external;

    /**
     * @dev Onboard NFTs from specific collection from previous contract version to this one.
     *
     * Requirements:
     *  - callable only by previous contract version, on behalf of the token owner
     *  - needs to be implemented only by the V2+ contracts.
     *
     * Flow:
     *  User calls V1.upgrade() which in turns calls V2.upgradeTo(). From then on, V2 is the active
     *  Athanasia contract for the tokens passed.
     */
    function upgradeTo(address tokenOwner, address collection, uint256[] memory tokenIds) external returns (bool);
}
