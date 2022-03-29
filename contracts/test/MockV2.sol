// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MockV2 {
    constructor() {}

    function upgradeTo(address, address, uint256[] memory) external pure returns (bool) {
        return true;
    }
}
