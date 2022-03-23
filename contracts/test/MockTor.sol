// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockTOR is ERC20 {
    constructor() ERC20("MockTOR", "TOR") {}

    function mint(address account_, uint256 amount_) external {
        _mint(account_, amount_);
    }

    function burn(uint256 _amount) public {
        _burn(msg.sender, _amount);
    }
}
