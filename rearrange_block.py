import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the API key from the environment variable
API_KEY = os.getenv("API_KEY")
BLOCK_NUMBER = 21821918 
NUM_TXS = 5           
START_IDX = 10

# --- Helper Functions ---
def hex_to_int(hex_str):
    """Convert a hexadecimal string (with 0x prefix) to an integer."""
    return int(hex_str, 16)

def fetch_block(block_number):
    """
    Fetch block data (including full transaction objects) from Etherscan.
    """
    hex_block = hex(block_number)
    url = (
        f"https://api.etherscan.io/api?module=proxy"
        f"&action=eth_getBlockByNumber"
        f"&tag={hex_block}"
        f"&boolean=true"
        f"&apikey={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if data.get("result") is None:
        raise Exception("No block data returned. Check API key, block number, and parameters.")
    return data["result"]

def fetch_tx_receipt(tx_hash):
    """
    Fetch the transaction receipt from Etherscan.
    This is used to extract the actual gas used by the transaction.
    """
    url = (
        f"https://api.etherscan.io/api?module=proxy"
        f"&action=eth_getTransactionReceipt"
        f"&txhash={tx_hash}"
        f"&apikey={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if data.get("result") is None:
        raise Exception(f"No receipt data returned for transaction {tx_hash}.")
    return data["result"]

def compute_effective_priority_fee(tx, base_fee):
    """
    Compute the effective priority fee (tip) for a transaction.
    
    - For EIP‑1559 transactions, we use 'maxPriorityFeePerGas'.
    - For legacy transactions, we subtract the block base fee from 'gasPrice'.
    """
    if "maxPriorityFeePerGas" in tx and tx["maxPriorityFeePerGas"]:
        return hex_to_int(tx["maxPriorityFeePerGas"])
    else:
        gas_price = hex_to_int(tx["gasPrice"])
        tip = gas_price - base_fee
        return tip if tip > 0 else 0

def simulate_transaction_with_order(tx, order_index):
    """
    Simulate a transaction's gas usage as a function of its position in the block.
    
    This toy model takes the base gas used (fetched from the transaction's receipt)
    and applies an artificial multiplier that increases the gas usage by 5% per
    position index. For example:
    
        - Position 0: multiplier = 1.0 (no change)
        - Position 1: multiplier = 1.05 (5% increase)
        - Position 2: multiplier = 1.10 (10% increase)
    
    The idea is to mimic the potential impact of execution order on gas consumption.
    """
    base_gas_used = tx.get("gasUsed", 21000)  # Default to minimal gas if not provided.
    simulated_gas_used = base_gas_used * (1 + 0.05 * order_index)
    return simulated_gas_used

def simulate_block(transactions, base_fee, block_gas_limit):
    """
    Simulate the execution of a block given an ordering of transactions.
    
    For each transaction, we:
      - Check that the transaction's nonce is in proper order for the sender.
      - Compute the simulated gas usage (which increases based on its order position).
      - Check that the cumulative gas does not exceed the block gas limit.
      - Compute the builder's revenue contribution as (simulated gas used * effective tip).
    
    Transactions that violate nonce ordering or would exceed the block gas limit are skipped.
    """
    total_revenue = 0
    total_gas_used = 0
    last_nonce_for_sender = {}  # Keep track of the last nonce seen per sender.
    
    for index, tx in enumerate(transactions):
        # --- Nonce Check ---
        sender = tx.get("from")
        tx_nonce = hex_to_int(tx.get("nonce"))
        if sender in last_nonce_for_sender:
            # Ensure that each subsequent transaction from the same sender has a higher nonce.
            if tx_nonce <= last_nonce_for_sender[sender]:
                print(f"Skipping tx {tx['hash']} due to nonce violation (nonce {tx_nonce} <= last {last_nonce_for_sender[sender]}).")
                continue
        last_nonce_for_sender[sender] = tx_nonce
        
        # --- Gas Limit Check ---
        simulated_gas = simulate_transaction_with_order(tx, index)
        if total_gas_used + simulated_gas > block_gas_limit:
            print(f"Skipping tx {tx['hash']} because adding simulated gas {simulated_gas:.0f} exceeds block gas limit {block_gas_limit} (total gas used so far: {total_gas_used:.0f}).")
            continue
        
        total_gas_used += simulated_gas
        
        # --- Revenue Calculation ---
        effective_tip = compute_effective_priority_fee(tx, base_fee)
        revenue = simulated_gas * effective_tip
        total_revenue += revenue
        
    print(f"Total simulated gas used: {total_gas_used:.0f} (Block gas limit: {block_gas_limit})")
    return total_revenue

# --- Main Script ---
def main():
    # 1. Fetch block data from Etherscan.
    block = fetch_block(BLOCK_NUMBER)
    base_fee = hex_to_int(block.get("baseFeePerGas", "0x0"))
    block_gas_limit = hex_to_int(block.get("gasLimit"))
    transactions = block.get("transactions", [])
    print(f"Block {BLOCK_NUMBER} has {len(transactions)} transactions. Block gas limit: {block_gas_limit}.")
    
    # 2. Work with a subset of transactions (first NUM_TXS).
    subset_txs = transactions[START_IDX:START_IDX + NUM_TXS]
    
    # 3. For each transaction, fetch its receipt to get the actual gasUsed.
    print("Fetching transaction receipts to extract gasUsed values...")
    for tx in subset_txs:
        tx_hash = tx["hash"]
        receipt = fetch_tx_receipt(tx_hash)
        tx["gasUsed"] = hex_to_int(receipt.get("gasUsed", "0x0"))
        tip = compute_effective_priority_fee(tx, base_fee)
        print(f"Tx {tx_hash} | gasUsed: {tx['gasUsed']} | Effective tip: {tip}")
        # Pause briefly to avoid hitting rate limits.
        time.sleep(0.2)
    
    # 4. Simulate block execution for the original ordering.
    revenue_original = simulate_block(subset_txs, base_fee, block_gas_limit)
    print("\nOriginal ordering builder revenue:", revenue_original)
    
    # 5. Reorder transactions by descending effective tip (as a simple heuristic).
    sorted_txs = sorted(subset_txs, key=lambda tx: compute_effective_priority_fee(tx, base_fee), reverse=True)
    revenue_reordered = simulate_block(sorted_txs, base_fee, block_gas_limit)
    print("Reordered transactions builder revenue:", revenue_reordered)
    
    # 6. Compare the results.
    if revenue_reordered > revenue_original:
        print("\nReordering increased builder revenue in this simulation.")
    else:
        print("\nReordering did not improve revenue in this simulation.")

if __name__ == "__main__":
    main()

