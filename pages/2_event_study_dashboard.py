# -*- coding: utf-8 -*-
"""2_Event_Study_Dashboard.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1DC9-1aIgF2dnA72OHdZXGn1JqlfU0XIS
"""

import streamlit as st
import pandas as pd
import os
import yfinance as yf
from utils import (
    load_stock_data,
    load_market_data,
    calculate_market_model_car,
    calculate_fama_french_car,
    plot_car_graph,
    plot_ci_graph
)
from event_scraper import get_live_events

# Set Page Config
st.set_page_config(
    page_title="Event Study Dashboard",
    page_icon="📈",
    layout="centered"
)

# Helper to trigger rerun
def trigger_analysis():
    st.session_state["run_analysis"] = True

st.title("📈 Event Study Dashboard")

# Load event data from scraper
try:
    event_data = get_live_events()
    event_data["event_date"] = pd.to_datetime(event_data["event_date"])
except Exception as e:
    st.error(f"Error loading live events: {e}")
    st.stop()

# Sidebar filters
industries = sorted(event_data["industry"].dropna().unique())
selected_industry = st.sidebar.selectbox("Select Industry", industries)

filtered_data = event_data[event_data["industry"] == selected_industry]
tickers = sorted(filtered_data["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Select Ticker", tickers)

event_dates = sorted(filtered_data[filtered_data["ticker"] == selected_ticker]["event_date"].dt.date.unique())

# 🆕 Date input with Calendar
selected_event_date = st.sidebar.date_input(
    "Select Event Date",
    value=event_dates[0],
    min_value=min(event_dates),
    max_value=max(event_dates)
)

# Model selection
model_choice = st.sidebar.radio(
    "Choose Model",
    ["Market Adjusted Model", "Fama French 3-Factor Model"],
    key="model_choice",
    on_change=trigger_analysis
)

analyze = st.sidebar.button("Analyze")

# Main Analysis
if analyze or st.session_state.get("run_analysis", False):
    st.subheader(f"Analysis for {selected_ticker} on {selected_event_date}")

    # Show logo
    logo_path = f"logos/{selected_ticker}.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.warning("Logo not available for this stock.")

    # 🆕 Event Details Card
    try:
        event_info = filtered_data[
            (filtered_data["ticker"] == selected_ticker) &
            (filtered_data["event_date"].dt.date == selected_event_date)
        ].iloc[0]

        st.markdown("---")
        st.markdown("### 📰 Event Details")
        with st.container():
            st.markdown(f"**🗓️ Date:** {selected_event_date}")
            st.markdown(f"**🗞️ Headline:** {event_info['headline']}")
            st.markdown(f"**🏷️ Event Type:** {event_info['news_type']}")
            sentiment = event_info['sentiment']
            if sentiment == "Positive":
                st.success(f"**Sentiment:** {sentiment}")
            elif sentiment == "Negative":
                st.error(f"**Sentiment:** {sentiment}")
            else:
                st.info(f"**Sentiment:** {sentiment}")
        st.markdown("---")

    except Exception as e:
        st.warning(f"Could not load event details: {e}")

    # Stock snapshot
    try:
        ticker_obj = yf.Ticker(selected_ticker)
        info = ticker_obj.info

        st.markdown("### 🏦 Stock Snapshot")
        col1, col2 = st.columns(2)
        col1.metric("💲 Current Price", f"${info.get('currentPrice', 'N/A')}")
        col2.metric("📈 1-Day Change", f"{info.get('regularMarketChangePercent', 0):.2f}%")

        st.markdown("### 📈 1-Month Price Trend")
        hist = ticker_obj.history(period="1mo")
        if not hist.empty:
            st.line_chart(hist["Close"])
        else:
            st.warning("Price history unavailable.")

        col3, col4 = st.columns(2)
        with col3:
            st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            st.write(f"**Industry:** {info.get('industry', 'N/A')}")
            st.write(f"**Market Cap:** ${info.get('marketCap', 'N/A'):,}")
        with col4:
            st.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
            st.write(f"**Dividend Yield:** {info.get('dividendYield', 'N/A')}")

        st.markdown("---")

    except Exception as e:
        st.warning(f"Could not load stock snapshot: {e}")

    # Event Study Analysis
    start_date = pd.to_datetime(selected_event_date) - pd.Timedelta(days=60)
    end_date = pd.to_datetime(selected_event_date) + pd.Timedelta(days=60)

    try:
        stock_data = load_stock_data(selected_ticker, start_date, end_date)
        market_data = load_market_data(start_date, end_date)

        if model_choice == "Market Adjusted Model":
            results = calculate_market_model_car(stock_data, market_data, pd.to_datetime(selected_event_date))
        else:
            results = calculate_fama_french_car(stock_data, pd.to_datetime(selected_event_date))

        abnormal_returns = results['abnormal_return']
        CAR_final = abnormal_returns.cumsum().iloc[-1] * 100
        normal_return = results['expected_return'].cumsum().iloc[-1] * 100
        actual_return = results['stock_return'].cumsum().iloc[-1] * 100

        st.markdown("### 📊 Event Impact Metrics")
        col5, col6, col7 = st.columns(3)
        col5.metric("📈 Actual Return", f"{actual_return:.2f}%")
        col6.metric("📉 Expected Return (Normal)", f"{normal_return:.2f}%")
        col7.metric("🚀 CAR (Impact)", f"{CAR_final:.2f}%")

        st.markdown("---")
        st.pyplot(plot_car_graph(results))
        st.pyplot(plot_ci_graph(results))

        st.session_state["run_analysis"] = False

    except Exception as e:
        st.error(f"Error during analysis: {e}")