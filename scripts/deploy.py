from brownie import AthanasiaHector
from brownie import network, config
from scripts.utilities import get_deployer_account, get_hector_contracts


def deploy_athanasia():
    (hec, shec, hecStaking) = get_hector_contracts()
    deployer = get_deployer_account()
    contract = AthanasiaHector.deploy(
        hec.address,
        shec.address,
        hecStaking.address,
        {"from": deployer},
        publish_source=config["networks"][network.show_active()]["verify_code"],
    )
    print(f"Contract deployed to {contract.address}")
    return contract


def main():
    print(f"Running on {network.show_active()}")
    deploy_athanasia()
