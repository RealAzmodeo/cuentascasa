import pandas as pd

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'
sheet = 'Gastos desglose'

print(f"\n--- Analyzing Sheet: {sheet} ---")
df = pd.read_excel(file_path, sheet_name=sheet, header=None)

# Show first 15 rows to find header
print("First 15 rows raw:")
print(df.head(15))

# Find the row that likely contains 'Fecha' or 'Monto' or 'Categoría'
possible_headers = ['Fecha', 'Categoría', 'Monto', 'Detalle', 'Descripción', 'Valor']
header_row = -1
for i, row in df.iterrows():
    row_str = " ".join([str(x) for x in row.values])
    if any(h in row_str for h in possible_headers):
        header_row = i
        break

if header_row != -1:
    print(f"Header found at row {header_row}")
    df = pd.read_excel(file_path, sheet_name=sheet, header=header_row)
    print("Columns:")
    print(df.columns.tolist())
    print("\nData sample:")
    print(df.head(5))
else:
    print("Could not find a structured header in the first few rows.")
