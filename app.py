import streamlit as st
from mev_block_analyzer import *
from rearrange_block import main as rb
from transaction_order_check import *

st.title("MEV Block Analyzer for P2P")
block_number = st.number_input("Select block to analyze:")

st.header("Q1: Verify that it is a MEV block")
st.write("Check transaction order by gas fees with the function https://github.com/JKaterina/p2p_test_assignment/blob/master/transaction_order_check.py")

transactions = fetch_block_transactions(int(block_number))
if transactions:
    result = check_transaction_order(transactions)

st.write(result)

st.write("Calculate the rewards in the hypothetical scenario where this block is not an MEV block. Function used: https://github.com/JKaterina/p2p_test_assignment/blob/master/mev_block_analyzer.py")
block_data = fetch_block_reward(block_number)
st.write(analyze_block_data(block_data, block_number))

st.header("Q2: Block Reordering for Builder Profit Optimization")
output = rb()
st.write(output)