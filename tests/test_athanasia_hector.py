import pytest
import brownie
from brownie import AthanasiaHector, accounts
from web3 import Web3
from scripts.deploy import deploy_athanasia
from scripts.utilities import get_deployer_account, get_user_account

ONE_HECTOR = 10 ** 9
ONE_FTM = 10 ** 18
ONE_TOR = 10 ** 18


@pytest.fixture(scope="function", autouse=True)
def user():
    return get_user_account()


@pytest.fixture(scope="function", autouse=True)
def deployer():
    return get_deployer_account()


@pytest.fixture(scope="function", autouse=True)
def hec(MockHEC, deployer):
    yield MockHEC.deploy({"from": deployer})


@pytest.fixture(scope="function", autouse=True)
def shec(MockSHEC, deployer):
    yield MockSHEC.deploy({"from": deployer})


@pytest.fixture(scope="function", autouse=True)
def otc(MockHecOtc, shec, deployer):
    yield MockHecOtc.deploy(False, shec.address, {"from": deployer})


@pytest.fixture(scope="function", autouse=True)
def tor(MockTOR, deployer):
    yield MockTOR.deploy({"from": deployer})


@pytest.fixture(scope="function", autouse=True)
def hec_staking(hec, shec, MockHectorStaking, deployer):
    hs = MockHectorStaking.deploy(
        hec.address, shec.address, {"from": deployer}
    )
    hec.mint(hs.address, 1000 * ONE_HECTOR)
    hs.setIndex(ONE_HECTOR)
    yield hs


@pytest.fixture(scope="function", autouse=True)
def nft(MockNFTContract, deployer, user):
    x = MockNFTContract.deploy({"from": deployer})
    x.mint(user, 1)
    x.mint(user, 18)
    x.mint(user, 9272)
    x.mint(deployer, 1337)
    yield x


def test_deploy_athanasia():
    contract = deploy_athanasia()
    assert contract is not None


@pytest.fixture(scope="function", autouse=True)
def athanasia(hec, shec, hec_staking, tor, otc, deployer, user):
    # Mint 1000 HEC to deployer/user account
    hec.mint(deployer, 1000 * ONE_HECTOR, {"from": deployer})
    hec.mint(user, 100 * ONE_HECTOR, {"from": deployer})
    # Mint 1000 sHEC to HectorStaking account
    shec.mint(hec_staking.address, 100 * ONE_HECTOR, {"from": deployer})
    athanasia_contract = deploy_athanasia()
    # Approve AthanasiaHector to spend the HEC from deployer/user
    hec.approve(athanasia_contract.address, 1000 * ONE_HECTOR, {"from": deployer})
    tor.approve(athanasia_contract.address, 1000 * ONE_HECTOR, {"from": user})
    # Set rebase index for hec staking
    yield athanasia_contract


def test_initialize_not_callable_by_non_owner(athanasia, user):
    with brownie.reverts("Ownable: caller is not the owner"):
        athanasia.initialize("0xfB7849f6Bfd365e5a3966048EF865A146cf15F24", {"from": user})


def test_initialize_callable_by_owner(athanasia, deployer):
    athanasia.initialize("0xfB7849f6Bfd365e5a3966048EF865A146cf15F24", {"from": deployer})
    assert athanasia.hectorOtcContract() == "0xfB7849f6Bfd365e5a3966048EF865A146cf15F24"


@pytest.fixture(scope="function", autouse=True)
def hec_otc(athanasia, otc, deployer):
    athanasia.initialize(otc.address, {"from": deployer})


def test_register_with_otc_fails_for_unauthorized_caller(athanasia, nft, user):
    with brownie.reverts("Athanasia: Only collection owner may register the collection"):
        athanasia.registerCollectionWithOtc(
            nft.address,
            "0x0000000000000000000000000000000000000000",
            10 * ONE_FTM,
            ONE_HECTOR,
            {"from": user})


def test_register_with_otc_fails_for_invalid_deposit_amount(athanasia, nft, deployer):
    with brownie.reverts("Athanasia: Invalid deposit amount"):
        athanasia.registerCollectionWithOtc(
            nft.address,
            "0x0000000000000000000000000000000000000000",
            10 * ONE_FTM,
            0,
            {"from": deployer})


def test_register_with_otc_fails_for_invalid_otc_price(athanasia, nft, deployer):
    with brownie.reverts("Athanasia: Invalid OTC price"):
        athanasia.registerCollectionWithOtc(
            nft.address,
            "0x0000000000000000000000000000000000000000",
            0,
            ONE_HECTOR,
            {"from": deployer})


def test_register_with_otc_fails_for_otc_unvalidated_collection(athanasia, otc, nft, deployer):
    otc.setFailAlways(True, {"from": deployer});

    with brownie.reverts("Athanasia: Collection not registered with OTC contract"):
        athanasia.registerCollectionWithOtc(
            nft.address,
            "0x0000000000000000000000001002000030000000",
            10 * ONE_FTM,
            ONE_HECTOR,
            {"from": deployer})

    otc.setFailAlways(False, {"from": deployer});


def test_register_with_otc_succeeds_for_deployer_when_everything_ok(athanasia, otc, nft, deployer):
    otc_token = "0x0000000000000000000000000000000000000000"
    otc.registerCollection(
        nft.address,
        otc_token,
        10 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        nft.address,
        otc_token,
        10 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})


def test_register_with_otc_succeeds_for_nft_collection_when_everything_ok(athanasia, otc, nft, deployer):
    otc_token = "0x0000000000000000000000000000000000000000"
    otc.registerCollection(
        deployer.address,
        otc_token,
        10 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        deployer.address,
        otc_token,
        10 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})


def test_register_with_otc_succeeds_reregister_before_deposit(athanasia, otc, nft, deployer):
    otc_token = "0x0000000000000000000000000000000000000000"
    otc.registerCollection(
        deployer.address,
        otc_token,
        10 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        deployer.address,
        otc_token,
        10 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})
    otc.registerCollection(
        deployer.address,
        otc_token,
        20 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        deployer.address,
        otc_token,
        20 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})
    # Check if otcPrice was updated
    assert athanasia.collections(deployer.address)[2] == 20 * ONE_FTM


def test_register_with_otc_fail_reregister_after_deposit(athanasia, otc, nft, deployer, user):
    otc_token = "0x0000000000000000000000000000000000000000"
    otc.registerCollection(
        nft.address,
        otc_token,
        5 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        nft.address,
        otc_token,
        5 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})
    athanasia.depositWithOtc(nft.address, [1], {"from": user, "amount": 5 * ONE_FTM})
    otc.registerCollection(
        nft.address,
        otc_token,
        10 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})

    with brownie.reverts("Athanasia: Update not possible after deposit have been made"):
        athanasia.registerCollectionWithOtc(
            nft.address,
            otc_token,
            10 * ONE_FTM,
            ONE_HECTOR,
            {"from": deployer})


def test_register_collection_fails_for_unauthorized_owner(athanasia, nft, user):
    with brownie.reverts("Athanasia: Only collection owner may register the collection"):
        athanasia.registerCollection(nft.address, ONE_HECTOR, {"from": user})


def test_register_collection_fails_for_invalid_deposit_amount(athanasia, nft, deployer):
    with brownie.reverts("Athanasia: Invalid deposit amount"):
        athanasia.registerCollection(nft.address, 0, {"from": deployer})


def test_register_collection_succeeds_for_nft_owner(athanasia, nft, deployer):
    athanasia.registerCollection(nft.address, ONE_HECTOR, {"from": deployer})


def test_register_collection_succeeds_for_nft_collection(athanasia, nft, deployer):
    athanasia.registerCollection(deployer.address, ONE_HECTOR, {"from": deployer})


def test_register_collection_succeeds_reregistration(athanasia, nft, deployer):
    athanasia.registerCollection(deployer.address, ONE_HECTOR, {"from": deployer})
    athanasia.registerCollection(deployer.address, 2 * ONE_HECTOR, {"from": deployer})

    assert athanasia.collections(deployer.address)[0] == 2 * ONE_HECTOR


def test_register_collection_fails_reregistration_after_deposit(athanasia, nft, shec, deployer, user):
    shec.approve(athanasia.address, 1000*ONE_HECTOR, {"from": user})
    shec.mint(user, ONE_HECTOR)
    athanasia.registerCollection(nft.address, ONE_HECTOR, {"from": deployer})
    athanasia.deposit(nft.address, [1], {"from": user})

    with brownie.reverts("Athanasia: Update not possible after deposit have been made"):
        athanasia.registerCollection(nft.address, 2 * ONE_HECTOR, {"from": deployer})


def test_deposit_fails_when_collection_not_registered(athanasia, nft, user):
    with brownie.reverts("Athanasia: Collection not registered"):
        athanasia.deposit(nft.address, [1], {"from": user})


@pytest.fixture(scope="function", autouse=False)
def athanasiaReg(athanasia, otc, nft, shec, deployer, user):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        5 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollection(nft.address, ONE_HECTOR, {"from": deployer})
    shec.approve(athanasia.address, 100 * ONE_HECTOR, {"from": user})
    yield athanasia


def test_deposit_fails_when_caller_does_not_have_shec(athanasiaReg, nft, user):
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        athanasiaReg.deposit(nft.address, [1], {"from": user})


def test_deposit_succeeds_single_nft(athanasiaReg, nft, shec, deployer, user):
    shec.mint(user, ONE_HECTOR, {"from": deployer})

    athanasiaReg.deposit(nft.address, [1], {"from": user})
    assert shec.balanceOf(athanasiaReg.address) == ONE_HECTOR


def test_deposit_succeeds_multiple_nft(athanasiaReg, nft, shec, deployer, user):
    shec.mint(user, 3 * ONE_HECTOR, {"from": deployer})

    athanasiaReg.deposit(nft.address, [1, 18, 9272], {"from": user})
    assert shec.balanceOf(athanasiaReg.address) == 3 * ONE_HECTOR


def test_deposit_withdraws_correct_amount(athanasiaReg, nft, shec, deployer, user):
    shec.mint(user, 3 * ONE_HECTOR, {"from": deployer})

    athanasiaReg.deposit(nft.address, [1, 18, 9272], {"from": user})
    assert shec.balanceOf(user) == 0


def test_deposit_fails_multideposit(athanasiaReg, nft, shec, deployer, user):
    shec.mint(user, 3 * ONE_HECTOR, {"from": deployer})

    athanasiaReg.deposit(nft.address, [18], {"from": user})

    with brownie.reverts("Athanasia: Token already deposited"):
        athanasiaReg.deposit(nft.address, [18, 9272], {"from": user})


def test_deposit_fails_invalid_nft(athanasiaReg, nft, shec, user):
    with brownie.reverts("ERC721: owner query for nonexistent token"):
        athanasiaReg.deposit(nft.address, [100], {"from": user})


def test_deposit_with_otc_when_not_registered(athanasia, nft, user):
    with brownie.reverts("Athanasia: Collection not registered"):
        athanasia.depositWithOtc(nft.address, [1], {"from": user})


@pytest.fixture(scope="function", autouse=False)
def athanasia_otc_ftm(athanasia, otc, nft, shec, deployer):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        5 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        5 * ONE_FTM,
        ONE_HECTOR,
        {"from": deployer})
    yield athanasia


def test_deposit_with_otc_fails_when_caller_does_not_send_ftm(athanasia_otc_ftm, nft, user):
    with brownie.reverts("Athanasia: Insufficient FTM funds for OTC"):
        athanasia_otc_ftm.depositWithOtc(nft.address, [1], {"from": user})


def test_deposit_with_otc_succeeds_single_nft_ftm(athanasia_otc_ftm, nft, shec, user):
    athanasia_otc_ftm.depositWithOtc(nft.address, [1], {"from": user, "amount": 5 * ONE_FTM})
    assert shec.balanceOf(athanasia_otc_ftm.address) == ONE_HECTOR


def test_deposit_with_otc_succeeds_multiple_nft_ftm(athanasia_otc_ftm, nft, shec, user):
    athanasia_otc_ftm.depositWithOtc(nft.address, [1, 18, 9272], {"from": user, "amount": 15 * ONE_FTM})
    assert shec.balanceOf(athanasia_otc_ftm.address) == 3 * ONE_HECTOR


def test_deposit_with_otc_fails_multideposit_ftm(athanasia_otc_ftm, nft, shec, user):
    athanasia_otc_ftm.depositWithOtc(nft.address, [18], {"from": user, "amount": 5 * ONE_FTM})

    with brownie.reverts("Athanasia: Token already deposited"):
        athanasia_otc_ftm.depositWithOtc(nft.address, [18, 9272], {"from": user, "amount": 10 * ONE_FTM})


@pytest.fixture(scope="function", autouse=False)
def athanasia_otc_tor(athanasia, otc, nft, shec, tor, deployer, user):
    otc.registerCollection(
        nft.address,
        tor.address,
        30 * ONE_TOR,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    athanasia.registerCollectionWithOtc(
        nft.address,
        tor.address,
        30 * ONE_TOR,
        ONE_HECTOR,
        {"from": deployer})
    tor.approve(athanasia.address, 1000 * ONE_TOR, {"from": user})
    yield athanasia


def test_deposit_with_otc_fails_when_caller_has_no_tor(athanasia_otc_tor, nft, user):
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        athanasia_otc_tor.depositWithOtc(nft.address, [1], {"from": user})


def test_deposit_with_otc_succeeds_single_nft_tor(athanasia_otc_tor, nft, shec, tor, user):
    tor.mint(user, 30 * ONE_TOR, {"from": user})

    athanasia_otc_tor.depositWithOtc(nft.address, [1], {"from": user})
    assert shec.balanceOf(athanasia_otc_tor.address) == ONE_HECTOR


def test_deposit_with_otc_succeeds_multiple_nft_tor(athanasia_otc_tor, nft, shec, tor, user):
    tor.mint(user, 90 * ONE_TOR, {"from": user})

    athanasia_otc_tor.depositWithOtc(nft.address, [1, 18, 9272], {"from": user})
    assert shec.balanceOf(athanasia_otc_tor.address) == 3 * ONE_HECTOR


def test_deposit_with_otc_withdraws_correct_tor(athanasia_otc_tor, nft, shec, tor, user):
    tor.mint(user, 1000 * ONE_TOR, {"from": user})

    athanasia_otc_tor.depositWithOtc(nft.address, [1, 18, 9272], {"from": user})
    assert tor.balanceOf(user) == (1000 - 90) * ONE_TOR


def test_deposit_with_otc_fails_multideposit_tor(athanasia_otc_tor, nft, shec, tor, user):
    tor.mint(user, 90 * ONE_TOR, {"from": user})

    athanasia_otc_tor.depositWithOtc(nft.address, [18], {"from": user})

    with brownie.reverts("Athanasia: Token already deposited"):
        athanasia_otc_tor.depositWithOtc(nft.address, [18, 9272], {"from": user})


@pytest.fixture(scope="function", autouse=False)
def athanasia_deposited(athanasia_otc_ftm, nft, shec, user, hec_staking):
    # Borrow some ETH/FTM from other test account
    accounts[-1].transfer(user, accounts[-1].balance())
    accounts[-2].transfer(user, accounts[-2].balance())
    athanasia_otc_ftm.depositWithOtc(nft.address, [1, 18, 9272], {"from": user, "amount": 15 * ONE_FTM})
    hec_staking.setIndex(ONE_HECTOR)
    yield athanasia_otc_ftm


def test_claimable_balance_zero_with_no_rebases(athanasia_deposited, nft):
    assert athanasia_deposited.claimableBalance(nft.address, 1) == 0


def test_claimable_balance_zero_for_invalid_collection(athanasia_deposited, nft):
    assert athanasia_deposited.claimableBalance(athanasia_deposited.address, 1) == 0


def test_claimable_balance_zero_for_invalid_nft(athanasia_deposited, nft):
    assert athanasia_deposited.claimableBalance(nft.address, 1337) == 0


def test_claimable_balance_correct_after_rebase(athanasia_deposited, nft, hec_staking):
    hec_staking.setIndex(1.2 * ONE_HECTOR)
    assert athanasia_deposited.claimableBalance(nft.address, 18) == 0.2 * ONE_HECTOR


def test_claim_fails_when_token_not_minted(athanasia_deposited, nft, user):
    with brownie.reverts("ERC721: owner query for nonexistent token"):
        athanasia_deposited.claim(nft.address, [100], {"from": user})


def test_claim_fails_when_caller_not_owner(athanasia_deposited, nft, user):
    with brownie.reverts("Athanasia: Not owner"):
        athanasia_deposited.claim(nft.address, [1337], {"from": user})


def test_claim_zero_when_no_rebases(athanasia_deposited, nft, hec, user):
    balance_before = hec.balanceOf(user)

    athanasia_deposited.claim(nft.address, [1], {"from": user})

    assert hec.balanceOf(user) == balance_before


def test_claim_single_after_one_rebase(athanasia_deposited, nft, hec, hec_staking, user):
    hec_staking.rebase(1.2 * ONE_HECTOR)
    balance_before = hec.balanceOf(user)

    athanasia_deposited.claim(nft.address, [1], {"from": user})

    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR


def test_claim_double_claim_does_nothing(athanasia_deposited, nft, hec, hec_staking, user):
    hec_staking.rebase(1.2 * ONE_HECTOR)
    balance_before = hec.balanceOf(user)

    athanasia_deposited.claim(nft.address, [1], {"from": user})
    athanasia_deposited.claim(nft.address, [1], {"from": user})

    # (1.2/1.0 - 1)
    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR


def test_claim_twice_rebase_between(athanasia_deposited, nft, hec, hec_staking, user):
    balance_before = hec.balanceOf(user)

    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_deposited.claim(nft.address, [1], {"from": user})
    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_deposited.claim(nft.address, [1], {"from": user})

    # (1.2/1.0 - 1) + (1.2*1.2/1.2 - 1)
    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR * 2


def test_claim_twice_rebase_between_two_nfts(athanasia_deposited, nft, hec, hec_staking, user):
    balance_before = hec.balanceOf(user)

    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_deposited.claim(nft.address, [1], {"from": user})
    hec_staking.rebase(1.3 * ONE_HECTOR)
    athanasia_deposited.claim(nft.address, [1, 18], {"from": user})

    # (1.2/1.0 - 1) + (1.3*1.2/1.2 - 1) + (1.2*1.3/1.0 - 1)
    assert hec.balanceOf(user) == balance_before + 0.5 * ONE_HECTOR + 560000000


def test_claim_thrice_rebase_between_three_nfts(athanasia_deposited, nft, hec, shec, hec_staking, user, deployer):
    balance_before = hec.balanceOf(user)
    # NOTE that rebase does not actually update the balance of athanasia, as it should.
    # If needed in the future, perhaps it would be wise to implement properly in the mock.
    hec_staking.rebase(1200000000)
    athanasia_deposited.claim(nft.address, [1], {"from": user})
    hec_staking.rebase(1100000000)
    athanasia_deposited.claim(nft.address, [1, 18], {"from": user})
    hec_staking.rebase(1571617000)
    athanasia_deposited.claim(nft.address, [1, 18, 9272], {"from": user})

    # NFT #1   : (1.2/1.0 - 1) + (1.2*1.1/1.2 - 1) + (1.2*1.1*1.571617/(1.2*1.1) - 1) = 0.2 + 0.1 + 0.571617
    # NFT #18  : (1.2*1.1/1.0 - 1) + (1.2*1.1*1.571617/(1.2*1.1) - 1) = 0.32 + 0.571617
    # NFT #9272: (1.2*1.1*1.571617/1.0 - 1) = 1.07453444
    assert hec.balanceOf(user) == balance_before +\
        871617000 +\
        891617000 +\
        1074534440


def test_register_and_deposit_fails_for_invalid_caller(athanasia, nft, user, deployer):
    with brownie.reverts("Athanasia: Only collection owner may register the collection"):
        athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 1000, {"from": user})


def test_register_and_deposit_fails_for_invalid_deposit_amount(athanasia, nft, deployer):
    with brownie.reverts("Athanasia: Invalid deposit amount"):
        athanasia.registerCollectionAndDeposit(nft.address, 0, 1000, {"from": deployer})


def test_register_and_deposit_fails_for_zero_collection_size(athanasia, nft, deployer):
    with brownie.reverts("Athanasia: Invalid collection size"):
        athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 0, {"from": deployer})


def test_register_and_deposit_succeeds_for_nft_owner(athanasia, nft, deployer, shec, hec_staking):
    shec.approve(athanasia.address, 1000 * ONE_HECTOR, {"from": deployer})
    shec.mint(deployer, 1000 * ONE_HECTOR, {"from": deployer})
    athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 1000, {"from": deployer})
    assert athanasia.collections(nft.address)[0] == ONE_HECTOR
    assert athanasia.collections(nft.address)[1] == "0x0000000000000000000000000000000000000000"
    assert athanasia.collections(nft.address)[2] == 0
    assert athanasia.collections(nft.address)[3] == hec_staking.index()
    assert athanasia.collections(nft.address)[4] == 1000


def test_register_and_deposit_succeeds_for_nft_collection(athanasia, nft, deployer, shec, hec_staking):
    shec.approve(athanasia.address, 1000 * ONE_HECTOR, {"from": deployer})
    shec.mint(deployer, 1000 * ONE_HECTOR, {"from": deployer})
    athanasia.registerCollectionAndDeposit(deployer, ONE_HECTOR, 1000, {"from": deployer})
    assert athanasia.collections(deployer)[0] == ONE_HECTOR
    assert athanasia.collections(deployer)[1] == "0x0000000000000000000000000000000000000000"
    assert athanasia.collections(deployer)[2] == 0
    assert athanasia.collections(deployer)[3] == hec_staking.index()
    assert athanasia.collections(deployer)[4] == 1000


def test_register_and_deposit_fails_reregistration(athanasia, nft, deployer, shec):
    shec.approve(athanasia.address, 1000 * ONE_HECTOR, {"from": deployer})
    shec.mint(deployer, 1000 * ONE_HECTOR, {"from": deployer})
    athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 1000, {"from": deployer})
    with brownie.reverts("Athanasia: Collection already registered"):
        athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 1000, {"from": deployer})


@pytest.fixture(scope="function", autouse=False)
def athanasia_rd(athanasia, nft, deployer, shec):
    shec.approve(athanasia.address, 10000 * ONE_HECTOR, {"from": deployer})
    shec.mint(deployer, 10000 * ONE_HECTOR, {"from": deployer})
    athanasia.registerCollectionAndDeposit(nft.address, ONE_HECTOR, 10000, {"from": deployer})
    yield athanasia


def test_rd_claim_returns_based_on_deposited_supply(athanasia_rd, nft, user, hec, hec_staking):
    hec_staking.rebase(1.1 * ONE_HECTOR)
    balance_before = hec.balanceOf(user)

    athanasia_rd.claim(nft.address, [1], {"from": user})

    assert hec.balanceOf(user) == balance_before + ONE_HECTOR * 0.1


@pytest.mark.parametrize("nft_id", [0, 10001])
def test_rd_claimable_balance_return_zero_token_out_of_range(athanasia_rd, nft, user, hec, hec_staking, nft_id):
    hec_staking.rebase(1.1 * ONE_HECTOR)
    assert athanasia_rd.claimableBalance(nft.address, nft_id, {"from": user}) == 0


def test_rd_claim_fails_when_token_not_minted(athanasia_rd, nft, user):
    with brownie.reverts("ERC721: owner query for nonexistent token"):
        athanasia_rd.claim(nft.address, [100], {"from": user})


def test_rd_claim_fails_when_caller_not_owner(athanasia_rd, nft, user):
    with brownie.reverts("Athanasia: Not owner"):
        athanasia_rd.claim(nft.address, [1337], {"from": user})


def test_rd_claim_zero_when_no_rebases(athanasia_rd, nft, hec, user):
    balance_before = hec.balanceOf(user)

    athanasia_rd.claim(nft.address, [1], {"from": user})

    assert hec.balanceOf(user) == balance_before


def test_rd_claim_single_after_one_rebase(athanasia_rd, nft, hec, hec_staking, user):
    hec_staking.rebase(1.2 * ONE_HECTOR)
    balance_before = hec.balanceOf(user)

    athanasia_rd.claim(nft.address, [1], {"from": user})

    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR


def test_rd_claim_double_claim_does_nothing(athanasia_rd, nft, hec, hec_staking, user):
    hec_staking.rebase(1.2 * ONE_HECTOR)
    balance_before = hec.balanceOf(user)

    athanasia_rd.claim(nft.address, [1], {"from": user})
    athanasia_rd.claim(nft.address, [1], {"from": user})

    # (1.2/1.0 - 1)
    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR


def test_rd_claim_twice_rebase_between(athanasia_rd, nft, hec, hec_staking, user):
    balance_before = hec.balanceOf(user)

    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_rd.claim(nft.address, [1], {"from": user})
    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_rd.claim(nft.address, [1], {"from": user})

    # (1.2/1.0 - 1) + (1.2*1.2/1.2 - 1)
    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR * 2


def test_rd_claim_twice_rebase_between_two_nfts(athanasia_rd, nft, hec, hec_staking, user):
    balance_before = hec.balanceOf(user)

    hec_staking.rebase(1.2 * ONE_HECTOR)
    athanasia_rd.claim(nft.address, [1], {"from": user})
    hec_staking.rebase(1.3 * ONE_HECTOR)
    athanasia_rd.claim(nft.address, [1, 18], {"from": user})

    # (1.2/1.0 - 1) + (1.3*1.2/1.2 - 1) + (1.2*1.3/1.0 - 1)
    assert hec.balanceOf(user) == balance_before + 0.5 * ONE_HECTOR + 560000000


def test_rd_claim_thrice_rebase_between_three_nfts(athanasia_rd, nft, hec, shec, hec_staking, user, deployer):
    # NOTE that rebase does not actually update the balance of athanasia, as it should.
    # If needed in the future, perhaps it would be wise to implement properly in the mock.
    # athanasia_rd.claim(nft.address, [1, 18, 9272], {"from": user})

    balance_before = hec.balanceOf(user)

    hec_staking.rebase(1200000000)
    athanasia_rd.claim(nft.address, [1], {"from": user})
    assert hec.balanceOf(user) == balance_before + 0.2 * ONE_HECTOR

    hec_staking.rebase(1100000000)
    athanasia_rd.claim(nft.address, [1, 18], {"from": user})
    assert hec.balanceOf(user) == balance_before + 0.3 * ONE_HECTOR + 0.32 * ONE_HECTOR

    hec_staking.rebase(1571617000)
    athanasia_rd.claim(nft.address, [1, 18], {"from": user})
    assert hec.balanceOf(user) == balance_before + 0.62 * ONE_HECTOR + 2 * 0.571617000 * ONE_HECTOR

    athanasia_rd.claim(nft.address, [9272], {"from": user})
    # NFT #1   : (1.2/1.0 - 1) + (1.2*1.1/1.2 - 1) + (1.2*1.1*1.571617/(1.2*1.1) - 1) = 0.2 + 0.1 + 0.571617
    # NFT #18  : (1.2*1.1/1.0 - 1) + (1.2*1.1*1.571617/(1.2*1.1) - 1) = 0.32 + 0.571617
    # NFT #9272: (1.2*1.1*1.571617/1.0 - 1) = 1.07453444
    assert hec.balanceOf(user) == balance_before + 871617000 + 891617000 + 1074534440


@pytest.fixture(scope="function", autouse=False)
def v2(MockV2, deployer):
    yield MockV2.deploy({"from": deployer})


def test_set_upgrade_address_not_callable_by_non_owner(athanasia_rd, v2, user):
    with brownie.reverts("Ownable: caller is not the owner"):
        athanasia_rd.setUpgradeAddress(v2.address, {"from": user})


def test_set_upgrade_address_sets_contract_address(athanasia_rd, v2, deployer):
    athanasia_rd.setUpgradeAddress(v2.address, {"from": deployer})
    assert athanasia_rd.v2contract() == v2.address


@pytest.fixture(scope="function", autouse=False)
def upgradable_athanasia(athanasia_rd, v2, deployer):
    athanasia_rd.setUpgradeAddress(v2.address, {"from": deployer})
    yield athanasia_rd


@pytest.mark.parametrize("tokens", [[1], [1, 1337], [1337, 9272], [1, 18, 9272]])
def test_upgrade_not_callable_by_nonowners(upgradable_athanasia, nft, deployer, tokens):
    with brownie.reverts("Athanasia: Only NFT owner can upgrade"):
        upgradable_athanasia.upgrade(nft.address, tokens, {"from": deployer})


@pytest.mark.parametrize("tokens", [[1], [1, 18]])
def test_upgrade_fails_when_upgrade_contract_not_set(athanasia_rd, nft, user, tokens):
    with brownie.reverts("Athanasia: Upgrade unavailable"):
        athanasia_rd.upgrade(nft.address, tokens, {"from": user})


@pytest.mark.parametrize("tokens", [[1], [9272, 1], [18, 9272, 1]])
def test_upgrade_callable_by_owner_and_sets_upgrade_status(upgradable_athanasia, nft, user, tokens):
    upgradable_athanasia.upgrade(nft.address, tokens, {"from": user})
    for token_id in tokens:
        assert upgradable_athanasia.upgradeStatus(nft.address, token_id) == True


def test_claimable_balance_returns_zero_when_upgraded(upgradable_athanasia, nft, hec_staking, user):
    tokens = [1, 18, 9272]
    upgradable_athanasia.upgrade(nft.address, tokens, {"from": user})
    hec_staking.rebase(1100000000)

    for token_id in tokens:
        assert upgradable_athanasia.claimableBalance(nft.address, token_id) == 0

@pytest.mark.parametrize("tokens", [[1], [9272, 1], [18, 9272, 1]])
def test_upgrade_fails_if_claim_possible(upgradable_athanasia, nft, hec_staking, user, tokens):
    hec_staking.rebase(1100000000)
    with brownie.reverts("Athanasia: Must claim before upgrade"):
        upgradable_athanasia.upgrade(nft.address, tokens, {"from": user})


@pytest.mark.parametrize("tokens", [[1], [9272, 1], [18, 9272, 1]])
def test_upgrade_reverts_if_already_upgraded(upgradable_athanasia, nft, user, tokens):
    upgradable_athanasia.upgrade(nft.address, [1], {"from": user})

    with brownie.reverts("Athanasia: Some already upgraded"):
        upgradable_athanasia.upgrade(nft.address, tokens, {"from": user})


@pytest.mark.parametrize("tokens", [[1], [9272, 1], [18, 9272, 1]])
def test_claim_reverts_when_upgraded(upgradable_athanasia, nft, user, hec_staking, tokens):
    upgradable_athanasia.upgrade(nft.address, [1], {"from": user})

    with brownie.reverts("Athanasia: Some already upgraded"):
        upgradable_athanasia.claim(nft.address, tokens, {"from": user})


@pytest.mark.parametrize("tokens", [[1], [9272, 1], [18, 9272, 1]])
def test_upgrade_transfers_deposit_amount_to_v2_contract(upgradable_athanasia, v2, nft, user, shec, tokens):
    v1_before = shec.balanceOf(upgradable_athanasia.address)
    v2_before = shec.balanceOf(v2.address)

    upgradable_athanasia.upgrade(nft.address, tokens, {"from": user})

    assert shec.balanceOf(upgradable_athanasia.address) == v1_before - len(tokens) * ONE_HECTOR
    assert shec.balanceOf(v2.address) == v2_before + len(tokens) * ONE_HECTOR


def test_register_and_deposit_otc_ftm_fails_non_owner(athanasia, otc, nft, deployer, user):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        5 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    with brownie.reverts("Athanasia: Only collection owner may register the collection"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            "0x0000000000000000000000000000000000000000",
            5 * ONE_FTM,
            {"from": user}
        )


def test_register_and_deposit_otc_ftm_fails_otc_mismatch(athanasia, otc, nft, deployer):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        6 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    otc.setFailAlways(True)

    with brownie.reverts("Athanasia: Collection not registered with OTC contract"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            "0x0000000000000000000000000000000000000000",
            5 * ONE_FTM * 10_000,
            {"from": deployer}
        )


def test_register_and_deposit_otc_ftm_fails_ftm_not_sent(athanasia, otc, nft, deployer):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        0.005 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})

    with brownie.reverts("Athanasia: Insufficient FTM funds for OTC"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            "0x0000000000000000000000000000000000000000",
            0.005 * ONE_FTM,
            {"from": deployer, "amount": 0.00499 * ONE_FTM * 10_000}
        )


def test_register_and_deposit_otc_ftm_succeeds_when_all_good(athanasia, hec_staking, otc, nft, deployer):
    otc.registerCollection(
        nft.address,
        "0x0000000000000000000000000000000000000000",
        0.005 * ONE_FTM,
        10_000 * ONE_HECTOR,
        {"from": deployer})

    athanasia.registerCollectionAndDepositWithOtc(
        nft.address,
        ONE_HECTOR,
        10_000,
        "0x0000000000000000000000000000000000000000",
        0.005 * ONE_FTM,
        {"from": deployer, "amount": 0.005 * ONE_FTM * 10_000}
    )

    collection = athanasia.collections(nft.address)
    assert collection[0] == ONE_HECTOR
    assert collection[1] == "0x0000000000000000000000000000000000000000"
    assert collection[2] == 0.005 * ONE_FTM
    assert collection[3] == hec_staking.index()
    assert collection[4] == 10_000


def test_register_and_deposit_otc_tor_otc_mismatch(athanasia, otc, tor, nft, shec, deployer):
    otc.registerCollection(
        nft.address,
        tor.address,
        15 * ONE_TOR,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    with brownie.reverts("Athanasia: Collection not registered with OTC contract"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            tor.address,
            14 * ONE_TOR,
            {"from": deployer}
        )


def test_register_and_deposit_otc_tor_fails_insufficient_funds(athanasia, otc, tor, nft, deployer):
    otc.registerCollection(
        nft.address,
        tor.address,
        15 * ONE_TOR,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    tor.approve(athanasia.address, 150000 * ONE_TOR, {"from": deployer})
    tor.mint(deployer, 140000 * ONE_TOR, {"from": deployer})

    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            tor.address,
            15 * ONE_TOR,
            {"from": deployer}
        )


def test_register_and_deposit_otc_tor_succeeds_when_all_good(athanasia, hec_staking, otc, tor, nft, deployer):
    otc.registerCollection(
        nft.address,
        tor.address,
        15 * ONE_TOR,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    tor.approve(athanasia.address, 150000 * ONE_TOR, {"from": deployer})
    tor.mint(deployer, 150000 * ONE_TOR, {"from": deployer})

    athanasia.registerCollectionAndDepositWithOtc(
        nft.address,
        ONE_HECTOR,
        10_000,
        tor.address,
        15 * ONE_TOR,
        {"from": deployer}
    )

    collection = athanasia.collections(nft.address)
    assert collection[0] == ONE_HECTOR
    assert collection[1] == tor.address
    assert collection[2] == 15 * ONE_TOR
    assert collection[3] == hec_staking.index()
    assert collection[4] == 10_000


def test_register_and_deposit_otc_tor_fails_on_reregistration(athanasia, otc, tor, nft, deployer):
    otc.registerCollection(
        nft.address,
        tor.address,
        15 * ONE_TOR,
        10_000 * ONE_HECTOR,
        {"from": deployer})
    tor.approve(athanasia.address, 150000 * ONE_TOR, {"from": deployer})
    tor.mint(deployer, 150000 * ONE_TOR, {"from": deployer})


    athanasia.registerCollectionAndDepositWithOtc(
        nft.address,
        ONE_HECTOR,
        10_000,
        tor.address,
        15 * ONE_TOR,
        {"from": deployer}
    )

    with brownie.reverts("Athanasia: Collection already registered"):
        athanasia.registerCollectionAndDepositWithOtc(
            nft.address,
            ONE_HECTOR,
            10_000,
            tor.address,
            15 * ONE_TOR,
            {"from": deployer}
        )