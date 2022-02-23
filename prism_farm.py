import math
import requests
import streamlit as st
import pandas as pd


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


# initial parameters
luna_price, yluna_price, prism_price = get_prices()
staked_luna = get_staked_luna()
staking_yield = get_staking_yield(luna_price, staked_luna) * 100
yluna_yield = (luna_price / yluna_price) * staking_yield

# sidebar assumptions
st.sidebar.header("Assumptions")
st.sidebar.write("Exand the following sections to change your assumptions.")

with st.sidebar.expander("Asset Prices", expanded=True):

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

with st.sidebar.expander("PRISM Farm", expanded=True):

    yluna_staked = (
        st.number_input(
            "Total yLUNA Staked (Million)",
            min_value=0.0,
            value=2.0,
            step=0.5,
            max_value=25.0,
            format="%.1f",
        )
        * 1e6
    )

    num_users = st.number_input(
        "Number of Users",
        min_value=0,
        value=3500,
        step=100,
        max_value=15000,
    )

with st.sidebar.expander("PRISM AMPS Vault", expanded=True):

    avg_xprism = st.number_input(
        "Avg xPRISM Pledged",
        min_value=0,
        value=10000,
        step=1000,
    )

    avg_time = st.number_input(
        "Avg xPRISM Pledge Duration (Days)",
        min_value=0,
        value=30,
        step=1,
        max_value=200,
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
st.subheader("User's Position Input")
st.markdown(
    """
    Input the number of yLUNA staked.  AMPS are calculated based on the amount of xPRISM pledged, and pledge duration.
    """
)


col3, col4, col5 = st.columns(3)

user_yluna = col3.number_input(
    "yLUNA Staked",
    min_value=1,
    value=500,
    step=100,
)

user_xprism = col4.number_input(
    "xPRISM Pledged",
    min_value=0,
    value=500,
    step=100,
)

user_amps_duration = col5.number_input(
    "Pledge Duration (Days)", min_value=0, value=30, step=1, max_value=200
)

st.error("Unpledging any amount of xPRISM will reset all AMPS earned to zero.")


st.subheader("AMPS Vault")
st.markdown(
    """
    Each xPRISM accumulates 0.5 AMPS per day, up to a maximum of 100 AMPS.
    
    A user will reach their maximum aount of AMPS in roughly 200 days.
    """
)

# AMPS calculations
boost_per_xprism_per_hour = 0.021

avg_boost = min(
    avg_xprism * boost_per_xprism_per_hour * avg_time * 24, avg_xprism * 100
)
avg_yluna = yluna_staked / num_users
avg_boost_weight = math.sqrt(yluna_staked / num_users * avg_boost)

user_boost = min(
    user_xprism * boost_per_xprism_per_hour * user_amps_duration * 24, user_xprism * 100
)
user_boost_weight = math.sqrt(user_yluna * user_boost)

# PRISM Farm calculations
user_base_rewards = base_rewards * user_yluna / yluna_staked
user_boost_rewards = boost_rewards * user_boost_weight / (num_users * avg_boost_weight)
combined_rewards = user_base_rewards + user_boost_rewards
combined_apr = (combined_rewards * prism_price) / (user_yluna * yluna_price) * 100

col12, col13 = st.columns(2)

col12.metric("Average AMPS per User", f"{avg_boost:,.0f}")
col13.metric("User's AMPS", f"{user_boost:,.0f}")

# display output
st.subheader("PRISM Farm Rewards")
st.markdown(
    "The $PRISM earned from the PRISM Farm vests and are claimable 30 days later."
)

col6, col7, col8 = st.columns(3)

col6.metric(
    label="Base PRISM Farmed",
    value=f"{user_base_rewards:,.0f}",
    delta=f"${user_base_rewards * prism_price:,.2f}",
    delta_color="off",
)

col7.metric(
    label="Boost PRISM Farmed",
    value=f"{user_boost_rewards:,.0f}",
    delta=f"${user_boost_rewards * prism_price:,.2f}",
    delta_color="off",
)

col8.metric(
    label="Total PRISM Farmed",
    value=f"{combined_rewards:,.0f}",
    delta=f"${combined_rewards * prism_price:,.2f}",
    delta_color="off",
)

# display output
st.subheader("Luna and yLUNA Staking Yields")
st.markdown(
    """
    APR comparison between regular Luna staking, yLUNA staking, and staking yLUNA in the PRISM Farm.
    """
)

col9, col10, col11 = st.columns(3)

col9.metric(label="Luna Staking APR", value=f"{staking_yield:,.2f}%")

col10.metric(label="yLUNA Staking APR", value=f"{yluna_yield:,.2f}%")

col11.metric(label="PRISM Farm APR", value=f"{combined_apr:,.2f}%")

# disclaimer
st.warning("This tool was created for educational purposes only, not financial advice.")
