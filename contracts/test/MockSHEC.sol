// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockSHEC is ERC20 {
    constructor() ERC20("MockSHector", "msHEC") {}

    function mint(address account_, uint256 amount_) external {
        _mint(account_, amount_);
    }
}
