import bank_parser
import json
import os

EXCEL_STMT = "d:/Proyectos/Antigravity Offline/Cuentas-Casa/Extractos bancarios/2026Y-01M-25D-10_15_21-Últimos movimientos.xlsx"

def test_parser():
    if not os.path.exists(EXCEL_STMT):
        print("File not found")
        return
    
    transactions, error = bank_parser.parse_bbva_excel(EXCEL_STMT)
    if error:
        print(f"Error: {error}")
    else:
        print(f"Found {len(transactions)} transactions")
        # Print last 3 (most recent in bank order)
        for t in transactions[:3]:
            print(json.dumps(t, indent=2))

if __name__ == "__main__":
    test_parser()
