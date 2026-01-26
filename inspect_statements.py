from openpyxl import load_workbook
import os
import json

files = [
    r'd:\Proyectos\Antigravity Offline\Cuentas-Casa\Extractos bancarios\2026Y-01M-25D-18_56_40-Últimos movimientos.xlsx',
    r'd:\Proyectos\Antigravity Offline\Cuentas-Casa\Extractos bancarios\2026Y-01M-25D-10_15_21-Últimos movimientos.xlsx'
]

results = {}
for f in files:
    if os.path.exists(f):
        wb = load_workbook(f, data_only=True)
        sheet = wb.active
        # Look for possible account signatures in first 5 rows
        sample = []
        for i, row in enumerate(sheet.iter_rows(max_row=10, values_only=True)):
            sample.append([str(c) for c in row if c is not None])
        results[os.path.basename(f)] = sample

print(json.dumps(results, indent=2))
