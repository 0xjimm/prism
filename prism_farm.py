import base64
import json
import requests
import streamlit as st
import pandas as pd
import plotly.express as px


@st.cache(show_spinner=False)
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
    yluna_price = df.loc["yLUNA", "price"]
    prism_price = df.loc["PRISM", "price"]

    return luna_price, yluna_price, prism_price


@st.cache(show_spinner=False)
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


@st.cache(show_spinner=False)
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


@st.cache(show_spinner=False)
def get_staking_yield(luna_price, staked_luna):

    # amount of oracle rewards in UST
    oracle_rewards = get_oracle_rewards(luna_price)

    avg_validator_commission = 0.05

    # oracle rewards paid over two years, distributed to staked luna, divided my current luna price, minus validator commissions
    staking_yield = (
        oracle_rewards / 2 / staked_luna / luna_price * (1 - avg_validator_commission)
    )

    return staking_yield


def dict_to_b64(data: dict) -> str:
    """Converts dict to ASCII-encoded base64 encoded string."""
    return base64.b64encode(bytes(json.dumps(data), "ascii")).decode()


# query xPRISM balance in AMPS vault
@st.cache(show_spinner=False)
def get_amps_vault_xprism():

    query_message = dict_to_b64(
        {"balance": {"address": "terra1pa4amk66q8punljptzmmftf6ylq3ezyzx6kl9m"}}
    )

    response = requests.get(
        f"https://lcd.terra.dev/terra/wasm/v1beta1/contracts/terra1042wzrwg2uk6jqxjm34ysqquyr9esdgm5qyswz/store?query_msg={query_message}",
    ).json()

    xprism_balance = float(response["query_result"]["balance"]) / 1e6

    return xprism_balance


# query user's pledged pledged xPRISM
@st.cache(show_spinner=False)
def get_user_amps(user_address):

    query_message = dict_to_b64({"get_boost": {"user": user_address}})

    response = requests.get(
        f"https://lcd.terra.dev/terra/wasm/v1beta1/contracts/terra1pa4amk66q8punljptzmmftf6ylq3ezyzx6kl9m/store?query_msg={query_message}",
    ).json()

    user_xprism = float(response["query_result"]["amt_bonded"]) / 1e6
    user_amps = float(response["query_result"]["total_boost"]) / 1e6

    return user_xprism, user_amps


# query user's AMPS amount
@st.cache(show_spinner=False)
def get_user_prism_farm(user_address):

    query_message = dict_to_b64({"reward_info": {"staker_addr": user_address}})

    response = requests.get(
        f"https://lcd.terra.dev/terra/wasm/v1beta1/contracts/terra1ns5nsvtdxu53dwdthy3yxs6x3w2hf3fclhzllc/store?query_msg={query_message}",
    ).json()

    user_yluna = float(response["query_result"]["bond_amount"]) / 1e6
    user_weight = float(response["query_result"]["boost_weight"]) / 1e6

    return user_yluna, user_weight


# query amount of yLUNA in PRISM Farm
@st.cache(show_spinner=False)
def get_yluna_staked():

    query_message = dict_to_b64(
        {"reward_info": {"staker_addr": "terra1ns5nsvtdxu53dwdthy3yxs6x3w2hf3fclhzllc"}}
    )

    response = requests.get(
        f"https://lcd.terra.dev/terra/wasm/v1beta1/contracts/terra1p7jp8vlt57cf8qwazjg58qngwvarmszsamzaru/store?query_msg={query_message}",
    ).json()

    yluna_staked = float(response["query_result"]["staked_amount"]) / 1e6

    return yluna_staked


# query user's AMPS weight
@st.cache(show_spinner=False)
def get_total_boost_weight():

    query_message = dict_to_b64({"distribution_status": {}})

    response = requests.get(
        f"https://lcd.terra.dev/terra/wasm/v1beta1/contracts/terra1ns5nsvtdxu53dwdthy3yxs6x3w2hf3fclhzllc/store?query_msg={query_message}",
    ).json()

    total_boost_weight = float(response["query_result"]["boost"]["total_weight"]) / 1e6

    return total_boost_weight


# initial parameters
luna_price, yluna_price, prism_price = get_prices()
staked_luna = get_staked_luna()
staking_yield = get_staking_yield(luna_price, staked_luna) * 100
yluna_yield = (luna_price / yluna_price) * staking_yield

st.sidebar.header("User Inputs")

# sidebar assumptions
user_address = st.sidebar.text_input(
    "Wallet Address", value="terra1376ghe2yntgxdct36chx83lrrva9jrrfym2j2p"
)


# asset prices
with st.sidebar.expander("Asset Prices", expanded=False):

    luna_price_input = st.number_input(
        "Luna",
        min_value=0.0,
        value=luna_price,
        step=luna_price * 0.01,
        format="%0.2f",
    )

    yluna_price = st.number_input(
        "yLUNA",
        min_value=0.0,
        value=yluna_price,
        step=yluna_price * 0.01,
        format="%0.2f",
    )

    prism_price = st.number_input(
        "Prism",
        min_value=0.0,
        value=prism_price,
        step=prism_price * 0.01,
        format="%0.3f",
    )


# updated parameters
staking_yield = get_staking_yield(luna_price_input, staked_luna) * 100
yluna_yield = (luna_price_input / yluna_price) * staking_yield

st.markdown("# PRISM Farm Calculator")
st.info("Mobile users, click the arrow on the upper left to change your assumptions.")
st.markdown(
    """
    This calculator is designed to help you better understand how much $PRISM you can earn from staking your yLUNA and pledging your xPRISM to earn AMPS.
    
    **In general, the more yLUNA you stake, the more xPRISM you pledge, and the longer you pledge, the more $PRISM you earn.**
    """
)

# pool parameters
total_rewards = 130_000_000
ratio = 0.8
base_rewards = total_rewards * ratio
boost_rewards = total_rewards * (1 - ratio)

st.subheader("PRISM Farm Allocation")
st.markdown(
    "130m \$PRISM allocated to the PRISM Farm over the course of 12 months.  26m $PRISM is allocated to particpants who have earned AMPS."
)

col1, col2 = st.columns(2)

col1.metric(label="PRISM Base Pool", value=f"{base_rewards:,.0f}")

col2.metric(label="PRISM Boost Pool", value=f"{boost_rewards:,.0f}")

# user input
st.subheader("User's Current Position")

# protocol queries
xprism_pledged = get_amps_vault_xprism()
total_boost_weight = get_total_boost_weight()
yluna_staked = get_yluna_staked()
total_amps = total_boost_weight**2 / yluna_staked

# user queries
user_xprism, user_amps = get_user_amps(user_address)
user_yluna, user_weight = get_user_prism_farm(user_address)

col3, col4, col5 = st.columns(3)

col3.metric(label="yLUNA Staked", value=f"{user_yluna:,.0f}")
col4.metric(label="xPRISM Pledged", value=f"{user_xprism:,.0f}")
col5.metric(label="AMPS Accrued", value=f"{user_amps:,.0f}")

# intial rewards
base_rewards = 104_000_000 * user_yluna / yluna_staked
base_apr = (base_rewards * prism_price) / (user_yluna * yluna_price) * 100
boost_rewards = 26_000_000 * user_weight / total_boost_weight
boost_apr = (boost_rewards * prism_price) / (user_yluna * yluna_price) * 100
total_apr = base_apr + boost_apr

col6, col7, col8 = st.columns(3)

col6.metric(label="Base APR", value=f"{base_apr:,.2f}%")
col7.metric(label="Boost APR", value=f"{boost_apr:,.2f}%")
col8.metric(label="Total APR", value=f"{total_apr:,.2f}%")

# user's new position
st.sidebar.subheader("User's New Position")

new_user_yluna = st.sidebar.number_input(
    "yLUNA Staked",
    min_value=0.0,
    value=user_yluna,
    step=user_yluna * 0.01,
    format="%.0f",
)

new_user_xprism = st.sidebar.number_input(
    "xPRISM Pledged",
    min_value=0.0,
    value=user_xprism,
    step=user_xprism * 0.01,
    format="%.0f",
)

# reset user amps if they decrease
if new_user_xprism < user_xprism:
    user_amps = 0
    st.sidebar.warning("Reducing xPRISM pledged will reset your accrued AMPS.")

new_yluna_staked = yluna_staked + new_user_yluna - user_yluna

# projected rewards over x days
df = pd.DataFrame(range(1, 61), columns=["days"])

# calculate APRs over time
df["new_user_amps"] = new_user_xprism * 0.49992 * df["days"] + user_amps
df["new_user_weight"] = (new_user_yluna * df["new_user_amps"]) ** (1 / 2)
df["new_total_amps"] = (xprism_pledged + new_user_xprism) * 0.49992 * df[
    "days"
] + total_amps
df["new_total_weight"] = (new_yluna_staked * df["new_total_amps"]) ** (1 / 2)

df["new_base_rewards"] = 104_000_000 * new_user_yluna / yluna_staked
df["new_base_apr"] = (
    df["new_base_rewards"] * prism_price / (new_user_yluna * yluna_price) * 100
)
df["new_boost_rewards"] = 26_000_000 * df["new_user_weight"] / df["new_total_weight"]
df["new_boost_apr"] = (
    df["new_boost_rewards"] * prism_price / (new_user_yluna * yluna_price)
) * 100
df["new_total_apr"] = df["new_base_apr"] + df["new_boost_apr"]
df["daily_rewards"] = (df["new_base_rewards"] + df["new_boost_rewards"]) / 365
df["daily_rewards_usd"] = df["daily_rewards"] * prism_price
df["rewards_sum"] = df["daily_rewards_usd"].cumsum()

# plot APRs
st.subheader("Projected APRs")
st.write("User's projected APR over the next 60 days, given all else equal.")
chart = px.line(
    data_frame=df,
    x="days",
    y=["new_base_apr", "new_boost_apr", "new_total_apr"],
    labels={"days": "Days", "value": "APR %", "variable": "Legend"},
    template="plotly_dark",
)

# show chart
st.plotly_chart(chart, use_container_width=True)

st.subheader("Projected Rewards")
st.write("User's cumulative rewards over the next 60 days, given all else equal.")

chart = px.line(
    data_frame=df,
    x="days",
    y=["daily_rewards_usd"],
    labels={"days": "Days", "value": "Rewards (USD)", "variable": "Legend"},
    template="plotly_dark",
)

st.plotly_chart(chart, use_container_width=True)
