import pandas as pd
import json

file_path = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/Presupuesto-Anual-2025.xlsx'

def extract_taxonomy():
    try:
        df = pd.read_excel(file_path, sheet_name='Gastos', header=None)
        taxonomy = {}
        current_cat = None
        
        for i, row in df.iterrows():
            c0 = str(row[0]).strip()
            c2 = str(row[2]).strip()
            
            # Parent categories are in column 0
            if pd.notna(row[0]) and c0 != 'nan' and c0 not in ['H', 'TOTAL']:
                current_cat = c0
                if current_cat not in taxonomy:
                    taxonomy[current_cat] = []
            
            # Subcategories are in column 2
            if current_cat and pd.notna(row[2]) and c2 != 'nan' and c2 not in ['Gastos', 'Total Mensual', 'Monthly totals:', 'Categoría']:
                if c2 not in taxonomy[current_cat]:
                    taxonomy[current_cat].append(c2)
        
        # Clean up empty or header categories
        taxonomy = {k: v for k, v in taxonomy.items() if v and k not in ['Categoría', 'TOTAL']}
        
        # Add Income category
        df_inc = pd.read_excel(file_path, sheet_name='Ingresos', header=None)
        taxonomy['Ingresos'] = []
        for i, row in df_inc.iterrows():
            c2 = str(row[2]).strip()
            if pd.notna(row[2]) and c2 != 'nan' and c2 not in ['Ingresos', 'Total Mensual', 'Monthly totals:']:
                taxonomy['Ingresos'].append(c2)
        
        return taxonomy
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    tax = extract_taxonomy()
    if tax:
        print(json.dumps(tax, indent=4))
        with open('d:/Proyectos/Antigravity Offline/Cuentas-Casa/taxonomy_extracted.json', 'w', encoding='utf-8') as f:
            json.dump(tax, f, indent=4)
