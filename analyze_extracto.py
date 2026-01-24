import openpyxl
import os

filepath = r"d:\Proyectos\Antigravity Offline\Cuentas-Casa\Extractos bancarios\2026Y-01M-24D-11_13_52-Últimos movimientos.xlsx"

if not os.path.exists(filepath):
    print(f"Error: File not found at {filepath}")
    exit(1)

wb = openpyxl.load_workbook(filepath, data_only=True)
sheet = wb.active

print(f"Sheet Name: {sheet.title}")

for row in sheet.iter_rows(min_row=1, max_row=20, values_only=True):
    # Print row with indices to identify columns
    print([f"{i}:{v}" for i, v in enumerate(row)])
