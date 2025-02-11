import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the API key from the environment variable
API_KEY = os.getenv("API_KEY")

API_KEY = os.environ.get("API_KEY")


def fetch_block_transactions(block_number):
    """
    Fetch all transactions for a given block number from Etherscan.
    """
    url = f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag={hex(block_number)}&boolean=true&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "result" not in data or not data["result"]["transactions"]:
        print("No transactions found or an error occurred.")
        return []

    return data["result"]["transactions"]

def check_transaction_order(transactions):
    """
    Check if transactions are ordered by gas fee (priority fee + base fee).
    """
    gas_fees = []

    for tx in transactions:
        # Extract gas price (in Wei)
        gas_price = int(tx["gasPrice"], 16)  # Convert hex to int

        gas_fees.append((tx["hash"], gas_price))  # Store (tx hash, gas price)

    # Check if sorted in descending order
    sorted_gas_fees = sorted(gas_fees, key=lambda x: x[1], reverse=True)

    if gas_fees == sorted_gas_fees:
        return "✅ Transactions are ordered by gas price (likely non-MEV block)."
    else:
        return "❌ Transactions are NOT ordered by gas price (potential MEV block)."

# def main():
#     block_number = 21821918
#     transactions = fetch_block_transactions(block_number)

#     if transactions:
#         check_transaction_order(transactions)

# if __name__ == "__main__":
#     main()
