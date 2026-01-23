from openpyxl import load_workbook

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'
wb = load_workbook(file_path, data_only=False)
sheet = wb['Gastos']

print("--- Inspecting 'Gastos' Layout ---")
# Print first 10 rows and 15 columns to see the physical layout
for r in range(1, 15):
    row_data = []
    for c in range(1, 20):
        cell = sheet.cell(row=r, column=c)
        val = cell.value
        row_data.append(f"[{cell.coordinate}: {val}]")
    print(" ".join(row_data))

wb.close()
