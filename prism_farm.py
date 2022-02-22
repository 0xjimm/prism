import requests
import streamlit as st
import pandas as pd


@st.cache
def get_prices():
    """
    Parse json data from ET into a DataFrame
    """

    url = "https://api.extraterrestrial.money/v1/api/prices"

    response = requests.get(url).json()

    df = pd.json_normalize(pd.DataFrame.from_dict(response)["prices"]).set_index(
        "symbol"
    )

    luna_price = df.loc["LUNA", "price"]
    yluna_price = df.loc["yLUNA"]["price"]
    prism_price = df.loc["PRISM"]["price"]

    return luna_price, yluna_price, prism_price


@st.cache
def get_oracle_rewards(luna_price):

    # oracle address
    response = requests.get(
        " https://lcd.terra.dev/bank/balances/terra1jgp27m8fykex4e4jtt0l7ze8q528ux2lh4zh0f",
    ).json()

    # convert to dataframe
    df = pd.DataFrame.from_dict(response["result"]).set_index("denom")

    # parse for ust and luna rewards
    ust_rewards = int(df.loc["uusd", "amount"]) / 1e6
    luna_rewards = int(df.loc["uluna", "amount"]) / 1e6

    # add ust and value of luna
    oracle_rewards = ust_rewards + luna_rewards * luna_price

    return oracle_rewards


@st.cache
def get_staked_luna():

    # staking pool
    response = requests.get(
        " https://lcd.terra.dev/cosmos/staking/v1beta1/pool",
    ).json()

    # convert to dataframe
    df = pd.DataFrame.from_dict(response)

    # parse number of staked luna
    staked_luna = round(int(df.loc["bonded_tokens", "pool"]) / 1e6, -6)

    return staked_luna


@st.cache
def get_staking_yield(luna_price, staked_luna):

    # amount of oracle rewards in UST
    oracle_rewards = get_oracle_rewards(luna_price)

    avg_validator_commission = 0.05

    # oracle rewards paid over two years, distributed to staked luna, divided my current luna price, minus validator commissions
    staking_yield = (
        oracle_rewards / 2 / staked_luna / luna_price * (1 - avg_validator_commission)
    )

    return staking_yield


# initial parameters
luna_price, yluna_price, prism_price = get_prices()
staked_luna = get_staked_luna()
staking_yield = get_staking_yield(luna_price, staked_luna) * 100
yluna_yield = (luna_price / yluna_price) * staking_yield

st.markdown("# PRISM Farm Calculator")

# sidebar assumptions
st.sidebar.header("Assumptions")
st.sidebar.write("Exand the following sections to change your assumptions.")

with st.sidebar.expander("Prices", expanded=True):

    luna_price_input = st.number_input(
        "Luna Price",
        min_value=0.0,
        value=luna_price,
        step=0.5,
        format="%0.1f",
    )

    yluna_price = st.number_input(
        "yLuna Price", min_value=0.0, value=yluna_price, step=0.25, format="%0.1f"
    )

    prism_price = st.number_input(
        "Prism Price", min_value=0.0, value=prism_price, step=0.01, format="%0.2f"
    )

with st.sidebar.expander("PRISM Farm", expanded=True):

    yluna_staked = st.number_input(
        "yLuna Staked", min_value=0, value=2000000, step=250000
    )
