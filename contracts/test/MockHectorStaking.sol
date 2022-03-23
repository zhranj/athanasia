// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";

interface IMERC20 is IERC20 {
    function mint(address account_, uint256 amount_) external;
}

// Heavily stripped down and mocked Hector staking contract. For local testing only.
contract MockHectorStaking is Ownable {
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    address public immutable HEC;
    address public immutable sHEC;

    uint256 internal _index;
    mapping(address => uint256) public stakedBalances;
    mapping(address => bool) public warmupActive; // mock warmups, just track warmup amount for address

    address[] public stakers;

    constructor(address _HEC, address _sHEC) {
        require(_HEC != address(0));
        HEC = _HEC;
        require(_sHEC != address(0));
        sHEC = _sHEC;
        _index = 10**9;
    }

    function stake(uint256 _amount, address _recipient)
        external
        returns (bool)
    {
        if (stakedBalances[_recipient] == 0) {
            stakers.push(_recipient);
        }

        stakedBalances[_recipient] = stakedBalances[_recipient].add(_amount);

        IERC20(HEC).safeTransferFrom(msg.sender, address(this), _amount);

        warmupActive[_recipient] = true;
        return true;
    }

    function claim(address _recipient) public {
        require(!warmupActive[_recipient], "Balance still in warmup period.");
        IERC20(sHEC).safeTransfer(_recipient, stakedBalances[_recipient]);
        delete warmupActive[_recipient];
        delete stakedBalances[_recipient];
    }

    function unstake(uint256 _amount, bool _trigger) external {
        IERC20(sHEC).safeTransferFrom(msg.sender, address(this), _amount);
        IERC20(HEC).safeTransfer(msg.sender, _amount);
    }

    function index() public view returns (uint256) {
        return _index;
    }

    function setWarmupState(address _to, bool _state) public {
        warmupActive[_to] = _state;
    }

    function setIndex(uint256 _newIndex) public {
        _index = _newIndex;
    }

    // Simulate rebase, mint tokens
    function rebase(uint256 factor) public {
        require(factor > 10**9);
        _index = _index.mul(factor).div(10**9);
        uint256 hecMinted = 0;
        for (uint256 i = 0; i < stakers.length; ++i) {
            // mint SHEC to stakers
            uint256 currentBalance = IERC20(sHEC).balanceOf(stakers[i]);
            uint256 newBalance = currentBalance.mul(factor).div(10**9);
            IMERC20(sHEC).mint(stakers[i], newBalance - currentBalance);
            hecMinted += newBalance - currentBalance;

            // mint SHEC to those in warmup
            currentBalance = stakedBalances[stakers[i]];
            newBalance = currentBalance.mul(factor).div(10**9);
            stakedBalances[stakers[i]] = newBalance;
            IMERC20(sHEC).mint(address(this), newBalance - currentBalance);
            hecMinted += newBalance - currentBalance;
        }

        // HEC balance we have is the amount of HEC deposited - i.e this one gets the rebase benefit
        IMERC20(HEC).mint(address(this), hecMinted);
    }

    function muller(uint256 a, uint256 b) public view returns (uint256) {
        return a * b;
    }

    function divver(uint256 a, uint256 b) public view returns (uint256) {
        return a / b;
    }
}
