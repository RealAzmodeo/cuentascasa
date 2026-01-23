import pandas as pd

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'

def get_categories(sheet_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    categories = []
    # Identify where the table starts
    start_row = -1
    for i, row in df.iterrows():
        if 'Ene' in [str(x) for x in row.values] or 'TOTAL' in [str(x) for x in row.values]:
            start_row = i
            break
            
    if start_row != -1:
        # The categories are usually in the first or second column after the start row
        for i in range(start_row + 1, len(df)):
            val = df.iloc[i, 2] # Usually column C or similar based on previous analysis
            if pd.notna(val) and str(val).lower() not in ['total', 'total mensual', 'promedio', 'nota', 'sumatoria']:
                categories.append(str(val))
    return list(set(categories))

gastos_cat = get_categories('Gastos')
ingresos_cat = get_categories('Ingresos')

print("Categorías de Gastos:")
print(gastos_cat)
print("\nCategorías de Ingresos:")
print(ingresos_cat)
