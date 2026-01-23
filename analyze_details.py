import pandas as pd

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'
target_sheets = ['Ingresos', 'Gastos', 'Gastos desglose']

for sheet in target_sheets:
    print(f"\n--- Sheet: {sheet} ---")
    try:
        # Load the sheet and find the first row that looks like headers (has data)
        df = pd.read_excel(file_path, sheet_name=sheet, header=None)
        
        # Look for the first row that is not all NaN
        header_row = 0
        for i, row in df.iterrows():
            if row.notna().sum() > 1: # Row with more than 1 non-NaN value
                header_row = i
                break
        
        # Reload with the correct header
        df = pd.read_excel(file_path, sheet_name=sheet, header=header_row)
        print("Final Headers:")
        print(df.columns.tolist())
        print("\nFirst 3 data rows:")
        print(df.head(3))
    except Exception as e:
        print(f"Error reading {sheet}: {e}")
