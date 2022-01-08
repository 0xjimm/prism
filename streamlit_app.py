import requests
import numpy as np
import pandas as pd
import streamlit as st

risk_free_rate = 0.195
luna_ust_address = "terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552"
beth_ust_address = "terra1c0afrdc5253tkp5wt7rxhuj42xwyf2lcre0s7c"


@st.cache
def get_price(pair_address):

    # requests headers
    headers = {
        "authority": "api.coinhall.org",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        "accept": "*/*",
        "sec-gpc": "1",
        "origin": "https://coinhall.org",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://coinhall.org/",
        "accept-language": "en-US,en;q=0.9",
    }

    # coinhall api
    response = requests.get(
        "https://api.coinhall.org/api/v1/charts/terra/pairs", headers=headers
    ).json()

    # convert to dataframe
    df = (
        pd.DataFrame.from_dict(response, orient="index")
        .reset_index(drop=False)
        .rename(columns={"index": "address"})
        .drop(labels=["timestamp", "unofficial", "startAt", "endAt"], axis=1)
    )

    # filter for astroport pair
    df = df[df["address"] == pair_address].reset_index()

    # parse json data
    df = pd.concat(
        [
            df,
            df["asset0"].apply(pd.Series).add_prefix("asset0_"),
            df["asset1"].apply(pd.Series).add_prefix("asset1_"),
        ],
        axis=1,
    )

    # price
    if df["asset0_symbol"][0] == "UST":
        price = float(df["asset0_poolAmount"] / df["asset1_poolAmount"])
    else:
        price = float(df["asset1_poolAmount"] / df["asset0_poolAmount"])

    return price


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
luna_price = get_price(luna_ust_address)
staked_luna = get_staked_luna()
staking_yield = get_staking_yield(luna_price, staked_luna) * 100

eth_price = get_price(beth_ust_address)

# sidebar assumptions

st.sidebar.header("Assumptions")
st.sidebar.write("Exand the following sections to change your assumptions.")

with st.sidebar.expander("LUNA", expanded=True):

    staked_luna = st.number_input(
        label="Total Staked",
        min_value=100.0,
        step=100_000.0,
        value=staked_luna,
        format="%.2d",
        help="Total amount of LUNA Staked.",
    )

    luna_price = st.number_input(
        label="Price",
        min_value=1.0,
        step=1.0,
        value=luna_price,
        format="%.0d",
    )

    luna_yield = st.slider(
        label="Staking Yield",
        min_value=1.0,
        max_value=20.0,
        value=staking_yield + 1,
        format="%.1f%%",
        help="Yield after validator commissions, including airdrops.",
    )

    luna_market_share = st.slider(
        label="Staked Market Share",
        min_value=1,
        max_value=100,
        value=10,
        format="%d%%",
        help="Percent share of all staked LUNA.",
    )

    yluna_staked = st.slider(
        label="yLUNA Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="yLUNA used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )

with st.sidebar.expander("bETH"):

    staked_eth = st.number_input(
        label="Total Staked",
        min_value=100.0,
        step=1_000.0,
        value=148_000.0,
        format="%.2d",
        help="Total amount of ETH Staked.",
    )

    eth_price = st.number_input(
        label="Price",
        min_value=1.0,
        step=10.0,
        value=eth_price,
        format="%.2d",
    )

    eth_yield = st.slider(
        label="Staking Yield",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        format="%.1f%%",
        help="Since most of staked LUNA yield is denominated in UST, as price of LUNA increases, yield decreases.",
    )

    eth_market_share = st.slider(
        label="Staked ETH Market Share",
        min_value=1,
        max_value=100,
        value=10,
        format="%d%%",
        help="Percent share of all staked ETH.",
    )

    yeth_staked = st.slider(
        label="yETH Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="ETH used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )

with st.sidebar.expander("aUST"):

    staked_aust = st.number_input(
        label="Total Staked",
        min_value=100.0,
        step=1_000_000.0,
        value=4562000000.0,
        format="%.2d",
        help="Total amount of aUST.",
    )

    aust_price = st.number_input(
        label="Price",
        min_value=1.0,
        step=0.1,
        value=1.169,
        format="%.3f",
        help="Conversion ratio from aUST to UST.",
    )

    aust_yield = st.slider(
        label="Staking Yield",
        min_value=10.0,
        max_value=30.0,
        value=19.5,
        format="%.1f%%",
        help="Since most of staked LUNA yield is denominated in UST, as price of LUNA increases, yield decreases.",
    )

    aust_market_share = st.slider(
        label="aUST Market Share",
        min_value=1,
        max_value=100,
        value=10,
        format="%d%%",
        help="Percent share of all aUST.",
    )

    yaust_staked = st.slider(
        label="yaUST Staked",
        min_value=1,
        max_value=100,
        value=90,
        format="%d%%",
        help="aUST used for LP farms will receive swap fees and PRISM incentives but not receive staking rewards.",
    )


st.header("PRISM Protocol Valuation Calculator")

# luna calculations
prism_luna = staked_luna * luna_market_share / 100
prism_luna_rewards = prism_luna * luna_yield / 100
staked_yluna_revenue = prism_luna_rewards * yluna_staked / 100 * 0.1
unstaked_yluna_revenue = prism_luna_rewards * (1 - yluna_staked / 100)
total_yluna_revenue_usd = (staked_yluna_revenue + unstaked_yluna_revenue) * luna_price

# eth calculations
prism_eth = staked_eth * eth_market_share / 100
prism_eth_rewards = prism_eth * eth_yield / 100
staked_yeth_revenue = prism_eth_rewards * yeth_staked / 100 * 0.1
unstaked_yeth_revenue = prism_eth_rewards * (1 - yeth_staked / 100)
total_yeth_revenue_usd = (staked_yeth_revenue + unstaked_yeth_revenue) * eth_price

# aust calculations
prism_aust = staked_aust * aust_market_share / 100
prism_aust_rewards = prism_aust * aust_yield / 100
staked_yaust_revenue = prism_aust_rewards * yaust_staked / 100 * 0.1
unstaked_yaust_revenue = prism_aust_rewards * (1 - yaust_staked / 100)
total_yaust_revenue_usd = (staked_yaust_revenue + unstaked_yaust_revenue) * aust_price

st.subheader("LUNA Calculations")
st.write(f"Total Staked LUNA: {staked_luna:,.0f}")
st.write(f"LUNA Staked with PRISM: {prism_luna:,.0f}")
st.write(f"LUNA rewards per year: {prism_luna_rewards:,.0f}")
st.write(f"Staked yLUNA Revenue: {staked_yluna_revenue:,.0f}")
st.write(f"Unstaked yLUNA Revenue: {unstaked_yluna_revenue:,.0f}")
st.write(f"Total yLUNA Revenue: ${total_yluna_revenue_usd:,.0f}")

st.subheader("ETH Calculations")
st.write(f"Total Staked ETH: {staked_eth:,.0f}")
st.write(f"ETH Staked with PRISM: {prism_eth:,.0f}")
st.write(f"ETH rewards per year: {prism_eth_rewards:,.0f}")
st.write(f"Staked yETH Revenue: {staked_yeth_revenue:,.0f}")
st.write(f"Unstaked yETH Revenue: {unstaked_yeth_revenue:,.0f}")
st.write(f"Total yETH Revenue: ${total_yeth_revenue_usd:,.0f}")

st.subheader("aUST Calculations")
st.write(f"Total Staked aUST: {staked_aust:,.0f}")
st.write(f"aUST Staked with PRISM: {prism_aust:,.0f}")
st.write(f"aUST rewards per year: {prism_aust_rewards:,.0f}")
st.write(f"Staked aUST Revenue: {staked_yaust_revenue:,.0f}")
st.write(f"Unstaked yaUST Revenue: {unstaked_yaust_revenue:,.0f}")
st.write(f"Total yaUST Revenue: ${total_yaust_revenue_usd:,.0f}")
