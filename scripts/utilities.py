from brownie import accounts, config, network
from brownie import MockHEC, MockSHEC, MockHectorStaking, MockHecOtc, MockNFTContract, MockTOR

LOCAL_ENVIRONMENTS = ["development", "ganache", "mainnet-fork"]


def get_deployer_account(id=None):
    if network.show_active() in LOCAL_ENVIRONMENTS:
        return accounts[0]
    if id:
        return accounts.load(id)
    return accounts.add(config["wallets"]["deployer"])


def get_user_account(id=None):
    if network.show_active() in LOCAL_ENVIRONMENTS:
        return accounts[1]
    if id:
        return accounts.load(id)
    return accounts.add(config["wallets"]["user"])


def get_hector_contracts():
    if network.show_active() not in LOCAL_ENVIRONMENTS:
        return (
            MockHEC(config["networks"][network.show_active()]["hec_token"]),
            MockSHEC(config["networks"][network.show_active()]["shec_token"]),
            MockHectorStaking(config["networks"][network.show_active()]["hector_staking"]),
        )

    deployer = get_deployer_account()
    if len(MockHEC) == 0:
        hecToken = MockHEC.deploy({"from": deployer})
    if len(MockSHEC) == 0:
        shecToken = MockSHEC.deploy({"from": deployer})
    if len(MockHectorStaking) == 0:
        hecStaking = MockHectorStaking.deploy(hecToken.address, shecToken.address, {"from": deployer})
    return (MockHEC[-1], MockSHEC[-1], MockHectorStaking[-1])
