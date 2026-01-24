import openpyxl
import os
import datetime
import re

def parse_bbva_excel(filepath):
    if not os.path.exists(filepath):
        return None, "Archivo no encontrado"
    
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        sheet = wb.active
        
        transactions = []
        
        # BBVA starts around row 5 usually, but let's look for a date-like pattern in Col 1
        for row in sheet.iter_rows(min_row=1, values_only=True):
            # Skip empty rows or header rows
            if not row[1] or not isinstance(row[1], (str, datetime.date, datetime.datetime)):
                continue
            
            date_str = str(row[1])
            # Check if it looks like DD/MM/YYYY
            if not re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                continue
            
            try:
                # Basic fields
                raw_date = row[1]
                concept = str(row[3] or "").strip()
                details = str(row[9] or row[4] or "").strip()
                amount = float(row[5])
                balance = float(row[7])
                
                # Cleanup concept
                concept = re.sub(r'\s+', ' ', concept)
                
                # Determine type
                t_type = "Gasto" if amount < 0 else "Ingreso"
                
                transactions.append({
                    "fecha": raw_date,
                    "monto": abs(amount),
                    "tipo": t_type,
                    "detalle": f"{concept} | {details}",
                    "tienda": concept, # Use concept as initial tienda
                    "saldo_banco": balance
                })
            except (ValueError, TypeError, IndexError):
                continue
                
        return transactions, None
    except Exception as e:
        return None, str(e)
