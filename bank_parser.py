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
        header_idx = {}
        found_header = False
        
        # 1. Dynamically find the header row using a more flexible approach
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            row_str = [str(cell).lower() if cell else "" for cell in row]
            
            # Check if this row looks like a header row (must have at least date and amount/importe)
            if any('fecha' in s for s in row_str) and (any('monto' in s for s in row_str) or any('importe' in s for s in row_str) or any('movimiento' in s for s in row_str)):
                for col_idx, cell in enumerate(row_str):
                    if 'fecha' in cell: header_idx['fecha'] = col_idx
                    if 'concepto' in cell or 'título' in cell: header_idx['concepto'] = col_idx
                    if any(k in cell for k in ['importe', 'monto', 'movimiento']): header_idx['importe'] = col_idx
                    if any(k in cell for k in ['saldo', 'disponible']): header_idx['saldo'] = col_idx
                    if any(k in cell for k in ['información', 'observaciones', 'detallada']): header_idx['detalle_ext'] = col_idx
                
                found_header = True
                continue # The next rows will be data

            if not found_header:
                continue

            # 2. Extract transactions from data rows
            try:
                # We need at least the basics
                if 'fecha' not in header_idx or 'importe' not in header_idx:
                    continue
                
                raw_date = row[header_idx['fecha']]
                raw_amount = row[header_idx['importe']]
                
                if not raw_date or raw_amount is None:
                    continue
                
                # Standardize Date
                if isinstance(raw_date, (datetime.datetime, datetime.date)):
                    iso_date = raw_date.strftime('%Y-%m-%d')
                else:
                    date_str = str(raw_date).strip()
                    # Try patterns like DD/MM/YYYY or YYYY-MM-DD
                    match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
                    if not match: continue
                    try:
                        iso_date = datetime.datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                    except:
                        try: iso_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
                        except: continue

                # Extraction
                concept = str(row[header_idx.get('concepto', 0)] or "").strip()
                # Clean redundant concept info from detail if detail_ext exists
                detail_ext = str(row[header_idx.get('detalle_ext', header_idx.get('concepto', 0))] or "").strip()
                
                if concept.lower() in detail_ext.lower():
                    final_detail = detail_ext
                else:
                    final_detail = f"{concept} | {detail_ext}" if concept != detail_ext and detail_ext else concept

                # Numeric cleanup
                if isinstance(raw_amount, (int, float)):
                    amount = float(raw_amount)
                else:
                    amount = float(str(raw_amount).replace('.', '').replace(',', '.'))
                
                raw_balance = row[header_idx['saldo']] if header_idx.get('saldo') is not None else None
                if isinstance(raw_balance, (int, float)):
                    balance = float(raw_balance)
                else:
                    try: 
                        b_str = str(raw_balance or "").replace('.', '').replace(',', '.')
                        balance = float(b_str) if b_str else None
                    except: balance = None
                
                # Determine type
                t_type = "Gasto" if amount < 0 else "Ingreso"
                
                transactions.append({
                    "fecha": iso_date,
                    "monto": abs(amount),
                    "tipo": t_type,
                    "detalle": final_detail,
                    "tienda": re.sub(r'\d{12,}', '', concept).strip(), 
                    "saldo_banco": balance
                })
            except (ValueError, TypeError, KeyError, IndexError):
                continue
                
        if not found_header:
            return None, "No se encontró una cabecera reconocible (Fecha, Importe, Concepto)"
            
        return transactions, None
    except Exception as e:
        return None, str(e)
