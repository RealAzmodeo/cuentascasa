from openpyxl import load_workbook
import os

EXCEL_STMT = "d:/Proyectos/Antigravity Offline/Cuentas-Casa/Extractos bancarios/2026Y-01M-25D-10_15_21-Últimos movimientos.xlsx"

def inspect_new_excel():
    if not os.path.exists(EXCEL_STMT):
        print(f"Error: {EXCEL_STMT} not found.")
        return

    print(f"Inspecting NEW statement: {EXCEL_STMT}")
    # Using data_only=False first to see if there are formulas, then True for values
    wb = load_workbook(EXCEL_STMT, data_only=True)
    sheet = wb.active # Usually the first and only sheet
    
    print(f"Sheet Name: {sheet.title}")
    
    # Read first 15 rows to find headers and data start
    for i, row in enumerate(sheet.iter_rows(max_row=15, values_only=True)):
        print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    inspect_new_excel()
