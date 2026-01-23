from openpyxl import load_workbook
import datetime

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'
wb = load_workbook(file_path)

def update_summary_sheet(sheet_name, type_val):
    sheet = wb[sheet_name]
    print(f"Updating {sheet_name}...")
    
    # Month headers are in Row 12, Columns D to O (4 to 15)
    # Categories are in Column C (3), Rows 14 downwards
    
    for r in range(14, sheet.max_row + 1):
        category = sheet.cell(row=r, column=3).value
        # Stop if we hit 'Total' or empty
        if not category or str(category).lower() in ['total', 'total mensual', 'promedio', 'nota', 'sumatoria']:
            if category: print(f"Skipping row {r} (Category: {category})")
            continue
            
        print(f"Injecting formulas for category: {category}")
        for c in range(4, 16): # Columns D to O
            # Formula targets 'Movimientos' sheet
            # Movimientos!$A:$A is Fecha
            # Movimientos!$B:$B is Monto
            # Movimientos!$C:$C is Categoría
            # Movimientos!$E:$E is Tipo (Gasto/Ingreso)
            
            col_letter = sheet.cell(row=12, column=c).column_letter
            header_cell = f"{col_letter}$12"
            
            # Formula: SUMIFS(Monto, Categoría, $C14, Tipo, type_val, Fecha, ">=1st", Fecha, "<=End")
            # We use DATE(YEAR(...), MONTH(...), 1) and EOMONTH(...)
            
            formula = (
                f'=SUMIFS(Movimientos!$B:$B, '
                f'Movimientos!$C:$C, $C{r}, '
                f'Movimientos!$E:$E, "{type_val}", '
                f'Movimientos!$A:$A, ">="&{header_cell}, '
                f'Movimientos!$A:$A, "<="&EOMONTH({header_cell}, 0))'
            )
            sheet.cell(row=r, column=c).value = formula

update_summary_sheet('Gastos', 'Gasto')
update_summary_sheet('Ingresos', 'Ingreso')

wb.save(file_path)
print("Formulas updated and file saved.")
