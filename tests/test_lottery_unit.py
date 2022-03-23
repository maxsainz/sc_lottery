# Example of expected result: 0.019
# Result to wei: 0.019 * 10**18 = 19_00000_00000_000_000

from asyncio import exceptions
import time
from brownie import Lottery, accounts, config, network, exceptions
import pytest
from scripts.deploy_lottery import deploy_lottery
from web3 import Web3
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    fund_with_link,
    get_account,
    get_contract,
)


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    # Act
    # If the price is 2,000 ETH/USD
    # usdEntryFee = 50
    # 2000/1 == 50/x == 0.025
    expected_entrance_fee = Web3.toWei(
        0.025, "ether"
    )  # We convert this amount of Ether to Wei
    entrance_fee = lottery.getEntranceFee()
    # Assert
    assert expected_entrance_fee == entrance_fee


def test_cant_enter_unless_started():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})


def test_can_start_and_enter_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    entrance_fee = lottery.getEntranceFee()
    # Act
    lottery.enter({"from": account, "value": entrance_fee})
    # Assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    entrance_fee = lottery.getEntranceFee()
    lottery.enter({"from": account, "value": entrance_fee})
    fund_with_link(lottery.address)  # fund_with_link(lottery) would also be correct
    # Act
    lottery.endLottery({"from": account})
    # Assert
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1), "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2), "value": lottery.getEntranceFee()})
    fund_with_link(lottery.address)
    transaction = lottery.endLottery(
        {"from": account}
    )  # Inside this transaction element there is an attribute that stores all of our events
    requestId = transaction.events["RequestedRandomness"][
        "requestId"
    ]  # Out of all the events look for the RequestedRandomness event
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        requestId, STATIC_RNG, lottery.address, {"from": account}
    )  # Pretend to be the Chainlink node and use the callBackWithRandomness function to dummy getting a random number back from the Chainlink node
    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    # 777 % 3 = 0
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0  # We transfer to the winner account all the money
    assert account.balance() == (starting_balance_of_account + balance_of_lottery)
