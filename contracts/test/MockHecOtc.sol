// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "../../interfaces/IAthanasiaOtc.sol";

interface IMERC20 is IERC20 {
    function mint(address account_, uint256 amount_) external;
}

contract MockHecOtc is IAthanasiaOtc {
    using SafeERC20 for IERC20;

    bool public failAlways;
    address public immutable shec;

    constructor(bool _fail, address _shec) {
        failAlways = _fail;
        shec = _shec;
    }

    function setFailAlways(bool _fail) public {
        failAlways = _fail;
    }

    struct Collection {
        address otcToken;
        uint256 otcPrice;
        uint256 totalAmount;
    }

    mapping(address => Collection) public collections;

    function registerCollection(address collection, address otcToken, uint256 otcPrice, uint256 totalAmount) external {
        require(!failAlways, "OTC Register");
        collections[collection] = Collection(otcToken, otcPrice, totalAmount);
    }

    function validateCollection(address collection, address otcToken, uint256 otcPrice) external view returns(bool) {
        return !failAlways && collections[collection].otcToken == otcToken && collections[collection].otcPrice == otcPrice;
    }

    function otc(address collection, uint256 amountToPurchase, uint256 expectedCost) external payable {
        require(!failAlways, "OTC");
        Collection memory coll = collections[collection];
        uint256 cost = (amountToPurchase * coll.otcPrice) / 10**9;
        require(cost == expectedCost, 'OTC: Mismatch to the expected cost');
        if (coll.otcToken == address(0)) {
            require(msg.value == cost, 'OTC: Mismatch to the ETH value');
        } else {
            IERC20(coll.otcToken).safeTransferFrom(
                msg.sender,
                address(this),
                cost
            );
        }

        // Dont bother minting HEC and staking it, just mint the sHEC for the caller
        IMERC20(shec).mint(msg.sender, amountToPurchase);
    }
}