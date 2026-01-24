import bank_parser
import json

filepath = r"d:\Proyectos\Antigravity Offline\Cuentas-Casa\Extractos bancarios\2026Y-01M-24D-11_13_52-Últimos movimientos.xlsx"

transactions, error = bank_parser.parse_bbva_excel(filepath)

if error:
    print(f"Error: {error}")
else:
    print(f"Parsed {len(transactions)} transactions.")
    # Print first 3 for verification
    for t in transactions[:3]:
        print(json.dumps(t, indent=2, default=str))
