// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";

contract MockNFTContract is ERC721Enumerable, Ownable {
    constructor() ERC721("", "") {}

    function mint(address _to, uint256 _tokenId) public {
        _safeMint(_to, _tokenId);
    }
}
