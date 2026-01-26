import ingest_mod
import json
from datetime import datetime

def debug_api():
    print("Fetching analytics for 'Gabi Revolut'...")
    data = ingest_mod.get_analytics(account_filter='Gabi Revolut')
    
    current_month = "2026-01"
    if current_month in data.get('months', {}):
        txs = data['months'][current_month].get('transactions', [])
        print(f"Transactions in current month ({current_month}): {len(txs)}")
        
        types = {}
        for t in txs:
            tp = t.get('tipo', 'unknown')
            types[tp] = types.get(tp, 0) + 1
        print(f"Types found: {types}")
    else:
        print(f"Current month {current_month} NOT found in months data!")

if __name__ == '__main__':
    debug_api()
