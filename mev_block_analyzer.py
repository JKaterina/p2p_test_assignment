import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the API key from the environment variable
API_KEY = os.getenv("API_KEY")
BLOCK_NUMBER = 21821918  # Block number to analyze

# --- Fetch Block Reward from Etherscan ---
def fetch_block_reward(block_number):
    """
    Fetch block reward and fee recipient (builder address) directly from Etherscan.
    """
    url = f"https://api.etherscan.io/api?module=block&action=getblockreward&blockno={block_number}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if data.get("status") == "1" and "result" in data:
        result = data["result"]
        return {
            "block_number": block_number,
            "fee_recipient": result["blockMiner"],
            "block_reward": float(result["blockReward"]) / 1e18,  # Convert Wei to ETH
            "uncle_inclusion_reward": float(result["uncleInclusionReward"]) / 1e18,  # Convert Wei to ETH
            "total_reward": (float(result["blockReward"]) + float(result["uncleInclusionReward"])) / 1e18
        }
    return None

# --- Fetch Transactions ---
def fetch_transactions(address, action, block_number):
    """
    Fetch transactions (normal or internal) to the given address in a specific block using Etherscan API.
    """
    url = (
        f"https://api.etherscan.io/api?module=account"
        f"&action={action}"
        f"&address={address}"
        f"&startblock={block_number}"
        f"&endblock={block_number}"
        f"&apikey={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    
    if data.get("status") != "1":
        return []  # No transactions or an error occurred
    return data.get("result", [])

# --- Calculate Net Builder Reward ---
def main():
    print(f"Fetching data for block {BLOCK_NUMBER}...")

    # Step 1: Get Block Reward Details
    block_data = fetch_block_reward(BLOCK_NUMBER)
    if not block_data:
        print("Failed to fetch block reward data.")
        return
    
    print(f"\nBlock Number: {block_data['block_number']}")
    print(f"Fee Recipient (Builder Address): {block_data['fee_recipient']}")
    print(f"Block Reward: {block_data['block_reward']} ETH")
    print(f"Uncle Inclusion Reward: {block_data['uncle_inclusion_reward']} ETH")
    print(f"Total Block Reward: {block_data['total_reward']} ETH")

    # Step 2: Fetch Internal Transactions to Builder
    internal_txs = fetch_transactions(block_data['fee_recipient'], "txlistinternal", BLOCK_NUMBER)
    internal_received_total = sum(int(tx['value']) for tx in internal_txs) / 1e18  # Convert to ETH
    
    print(f"\nTotal Internal Transactions to Builder: {len(internal_txs)}")
    print(f"Total Internal Transfers to Builder: {internal_received_total:.6f} ETH")

    # Step 3: Calculate Net Reward
    net_builder_reward = block_data["total_reward"] - internal_received_total
    print(f"\n📊 Net Reward for Builder (Total Block Reward - Internal Transfers): {net_builder_reward:.6f} ETH")

if __name__ == "__main__":
    main()
