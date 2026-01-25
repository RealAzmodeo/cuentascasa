import os
import sys
import json
import datetime
import time
from google import genai
from openpyxl import load_workbook
from dotenv import load_dotenv
import bank_parser

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
EXCEL_PATH = os.getenv("EXCEL_PATH")
MODEL_NAME = 'gemini-2.5-flash'

CONFIG_PATH = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/taxonomy.json'

# Initial load
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"taxonomy": {}, "classification_rules": []}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_taxonomy():
    cfg = load_config()
    return {k: v['subcategories'] for k, v in cfg.get('taxonomy', {}).items()}

TAXONOMY = get_taxonomy()
CATEGORIES = list(TAXONOMY.keys())

# Initialize Gemini Client (New SDK)
client = genai.Client(api_key=API_KEY)

def apply_rules(text, t_type=None):
    cfg = load_config()
    rules = cfg.get('classification_rules', [])
    text_upper = text.upper()
    
    for rule in rules:
        pattern = rule['pattern'].upper()
        # If rule specified a type, it must match
        if rule.get('type') and t_type and rule['type'].lower() != t_type.lower():
            continue
            
        if pattern in text_upper:
            return {
                "categoria": rule['category'],
                "subcategoria": rule['subcategory'],
                "confianza": "high"
            }
    return None

def extract_transaction(text, retries=3):
    # 1. Try manual rules first
    guessed_type = "Ingreso" if any(x in text.upper() for x in ["NOMINA", "SALARIO", "DEVOLUCION", "REEMBOLSO", "TRASP", "INGRESO"]) else "Gasto"
    rule_match = apply_rules(text, guessed_type)
    
    # 2. Prepare prompt
    current_taxonomy = get_taxonomy()
    global TAXONOMY, CATEGORIES
    TAXONOMY = current_taxonomy
    CATEGORIES = list(current_taxonomy.keys())
    
    rule_hint = f"\n\nREGLA SUGERIDA (Priorizar si es coherente): Categoría {rule_match['categoria']}, Subcategoría {rule_match['subcategoria']}" if rule_match else ""
    
    prompt = f"""
    Eres un asistente contable de ELITE. Tu tarea es extraer información detallada de una descripción financiera.
    
    Entrada: "{text}"
    Fecha de hoy: {datetime.date.today()}
    Tipo detectado: {guessed_type}{rule_hint}
    
    Taxonomía Profesional:
    {json.dumps(current_taxonomy, indent=2)}
    
    Debes devolver un JSON válido con este formato:
    {{
        "intent": "regular" | "refund",
        "transactions": [
            {{
                "fecha": "YYYY-MM-DD",
                "monto": 0.0,
                "categoria": "Una de las llaves principales de la taxonomía",
                "subcategoria": "Una de las subcategorías correspondientes",
                "tienda": "Nombre del comercio o establecimiento. Si no se menciona, deja en blanco.",
                "detalle": "Resumen breve",
                "tipo": "Gasto" | "Ingreso"
            }}
        ]
    }}
    """
    
    for i in range(retries):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            content = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(content)
            return data
        except Exception as e:
            if "429" in str(e):
                time.sleep(5 * (i+1))
                continue
            print(f"Error en Gemini/Parsing: {e}")
            return None
    return None

def find_candidates(category, wb):
    sheet = wb['Movimientos']
    candidates = []
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    for i, row in enumerate(reversed(rows)):
        # row[2] is Category
        if str(row[2]).lower() == category.lower() and str(row[4]).lower() == 'gasto':
            candidates.append({
                "id": len(rows) - i + 1,
                "fecha": str(row[0]),
                "monto": row[1],
                "categoria": row[2],
                "detalle": row[3],
                "tienda": row[5] if len(row) > 5 else ""
            })
        if len(candidates) >= 5: break
    return candidates

def check_for_duplicates(data, wb):
    sheet = wb['Movimientos']
    new_date = datetime.datetime.strptime(data['fecha'], '%Y-%m-%d').date() if isinstance(data['fecha'], str) else data['fecha']
    if hasattr(new_date, 'date'): new_date = new_date.date()

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_date, row_amount, row_cat = row[0], row[1], row[2]
        if not isinstance(row_date, (datetime.datetime, datetime.date)):
            try: row_date = datetime.datetime.strptime(str(row_date).split(' ')[0], '%Y-%m-%d').date()
            except: continue
        else:
            if hasattr(row_date, 'date'): row_date = row_date.date()
        
        if (abs(new_date - row_date).days <= 1 and 
            abs(float(row_amount) - float(data['monto'])) < 0.01 and 
            str(row_cat).lower() == str(data['categoria']).lower()):
            return True
    return False

def get_analytics():
    wb = load_workbook(EXCEL_PATH, data_only=True)
    if 'Movimientos' not in wb.sheetnames: return {}
    sheet = wb['Movimientos']
    data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            try:
                dt = row[0] if isinstance(row[0], (datetime.datetime, datetime.date)) else datetime.datetime.strptime(str(row[0]).split(' ')[0], '%Y-%m-%d')
                data.append({
                    "fecha": dt,
                    "monto": float(row[1]),
                    "categoria": str(row[2]),
                    "tipo": str(row[4]).lower(),
                    "tienda": str(row[5]) if len(row) > 5 and row[5] else "Desconocido",
                    "subcategoria": str(row[6]) if len(row) > 6 and row[6] else "Varios"
                })
            except: continue

    if not data: return {}
    
    # Structure: { "YYYY-MM": { "total": 0, "categories": {}, "subcategories": {}, "stores": {}, "top_transactions": {} } }
    monthly_stats = {}
    
    for d in data:
        if d['tipo'] == 'gasto':
            m_key = d['fecha'].strftime('%Y-%m')
            if m_key not in monthly_stats:
                monthly_stats[m_key] = {"total": 0, "categories": {}, "subcategories": {}, "stores": {}, "top_transactions": {}}
            
            stats = monthly_stats[m_key]
            stats["total"] += d['monto']
            stats["categories"][d['categoria']] = stats["categories"].get(d['categoria'], 0) + d['monto']
            stats["stores"][d['tienda']] = stats["stores"].get(d['tienda'], 0) + d['monto']
            
            # Track top transactions for breakdown
            if d['categoria'] not in stats["top_transactions"]:
                stats["top_transactions"][d['categoria']] = []
            
            stats["top_transactions"][d['categoria']].append({
                "detalle": d['tienda'] if d['tienda'] != "Desconocido" else d['detalle'],
                "monto": d['monto'],
                "fecha": d['fecha'].strftime('%d/%m')
            })

            if d['categoria'] not in stats["subcategories"]:
                stats["subcategories"][d['categoria']] = {}
            sub = d['subcategoria']
            stats["subcategories"][d['categoria']][sub] = stats["subcategories"][d['categoria']].get(sub, 0) + d['monto']

    # Sort transactions by amount descending (Largest First)
    for m in monthly_stats:
        for cat in monthly_stats[m]["top_transactions"]:
            monthly_stats[m]["top_transactions"][cat].sort(key=lambda x: x['monto'], reverse=True)

    # Sort months descending (Latest First)
    sorted_months = sorted(monthly_stats.keys(), reverse=True)
    
    # Calculate MoM growth and history list (ascending for chart logic)
    ascending_months = sorted(monthly_stats.keys())
    history_list = []
    for i, m in enumerate(ascending_months):
        curr_total = monthly_stats[m]["total"]
        prev_total = monthly_stats[ascending_months[i-1]]["total"] if i > 0 else 0
        growth = round(((curr_total - prev_total) / prev_total * 100), 1) if prev_total > 0 else 0
        history_list.append({
            "month": m,
            "total": round(curr_total, 2),
            "growth": growth
        })
    
    now_key = datetime.datetime.now().strftime('%Y-%m')
    current_month_key = now_key if now_key in monthly_stats else (sorted_months[-1] if sorted_months else now_key)
    
    return {
        "months": monthly_stats,
        "history": history_list,
        "current_month_key": current_month_key,
        "sorted_months": sorted_months
    }

def update_transaction(row_id, data):
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    if row_id < 2 or row_id > sheet.max_row: return False, "ID inválido"
    try:
        sheet.cell(row=row_id, column=1).value = data['fecha']
        sheet.cell(row=row_id, column=2).value = data['monto']
        sheet.cell(row=row_id, column=3).value = data['categoria']
        sheet.cell(row=row_id, column=4).value = data['detalle']
        sheet.cell(row=row_id, column=5).value = data['tipo']
        if len(data.get('tienda', '')) > 0: sheet.cell(row=row_id, column=6).value = data['tienda']
        if len(data.get('subcategoria', '')) > 0: sheet.cell(row=row_id, column=7).value = data['subcategoria']
        wb.save(EXCEL_PATH)
        sort_excel_by_date()
        return True, "Actualizado"
    except Exception as e: return False, str(e)

def delete_transaction(row_id):
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    if row_id < 2 or row_id > sheet.max_row: return False, "ID inválido"
    try:
        sheet.delete_rows(row_id)
        wb.save(EXCEL_PATH)
        sort_excel_by_date()
        return True, "Eliminado"
    except Exception as e: return False, str(e)

def append_to_excel(data_list, force=False):
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    added, dups = 0, []
    for data in data_list:
        # Use the same reconcile logic as bank ingestion for all insertions
        exists, status = reconcile_transaction(data, wb)
        if not force and exists:
            dups.append(data)
            print(f"DEBUG: Duplicado detectado e ignorado: {data['detalle']} ({data['monto']})")
            continue
        
        sheet.append([
            data['fecha'], data['monto'], data['categoria'], data['detalle'], data['tipo'],
            data.get('tienda', ''), data.get('subcategoria', ''), data.get('saldo_banco', '')
        ])
        added += 1
    wb.save(EXCEL_PATH)
    sort_excel_by_date()
    if dups and not force: return False, {"status": "duplicate_found", "duplicates": dups}
    return True, {"status": "success", "added": added}

def sort_excel_by_date():
    """Forces the Excel to be sorted by date (column 1) and removes empty/ghost rows.
    Maintains relative order for transactions on the same day to preserve ledger flow.
    """
    try:
        wb = load_workbook(EXCEL_PATH)
        if 'Movimientos' not in wb.sheetnames: return
        sheet = wb['Movimientos']
        
        # 1. Read all valid data rows with their original index to maintain stable sort
        data = []
        for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True)):
            if row[0] is not None: # Header must have a date
                data.append((list(row), i))
        
        if not data:
            if sheet.max_row > 1:
                sheet.delete_rows(2, sheet.max_row)
            wb.save(EXCEL_PATH)
            return
        
        # 2. Sort by date, then by original index to keep same-day order
        def get_sort_key(item):
            r, original_idx = item
            d = r[0]
            if isinstance(d, (datetime.datetime, datetime.date)):
                dt = d.date() if hasattr(d, 'date') else d
            else:
                try: dt = datetime.datetime.strptime(str(d).split(' ')[0], '%Y-%m-%d').date()
                except: 
                    try: dt = datetime.datetime.strptime(str(d).split(' ')[0], '%d/%m/%Y').date()
                    except: dt = datetime.date(1900, 1, 1)
            return (dt, original_idx)

        data.sort(key=get_sort_key)
        
        # 3. Clean and Re-write the sheet completely
        wb.remove(sheet)
        sheet = wb.create_sheet('Movimientos', 0)
        sheet.append(['Fecha', 'Monto', 'Categoría', 'Detalle', 'Tipo', 'Tienda', 'Subcategoría', 'Saldo Banco'])
        
        for row_data, _ in data:
            sheet.append(row_data)
            
        wb.save(EXCEL_PATH)
        print(f"DEBUG: Excel rebuilt and sorted ({len(data)} rows).")
    except Exception as e:
        print(f"DEBUG: Error sorting Excel: {e}")

def reconcile_transaction(data, wb):
    """Checks if a transaction from the bank already exists in the Excel.
    Uses date, amount, type, AND a fuzzy match on details to avoid false positives.
    """
    sheet = wb['Movimientos']
    
    if isinstance(data['fecha'], str):
        try: new_date = datetime.datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        except: 
            try: new_date = datetime.datetime.strptime(data['fecha'], '%d/%m/%Y').date()
            except: new_date = datetime.date.today()
    else:
        new_date = data['fecha'].date() if hasattr(data['fecha'], 'date') else data['fecha']

    new_detail_norm = str(data.get('detalle') or '').lower().strip()
    new_amt = round(float(data['monto']), 2)

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_date, row_amount, row_cat, row_detail, row_type = row[0], row[1], row[2], row[3], row[4]
        
        if row_date is None or row_amount is None:
            continue

        if not isinstance(row_date, (datetime.datetime, datetime.date)):
            try: r_date = datetime.datetime.strptime(str(row_date).split(' ')[0], '%Y-%m-%d').date()
            except: continue
        else:
            r_date = row_date.date() if hasattr(row_date, 'date') else row_date
        
        # Match logic: 
        # 1. Exact amount
        # 2. Same type (Gasto / Ingreso)
        # 3. Same date (Bank statements are usually exact, manual entries might differ by 1 day)
        # 4. Detail check: If details are significantly different, it's NOT a duplicate
        try:
            r_amt = round(float(row_amount), 2)
            if (abs(r_amt - new_amt) < 0.001 and 
                str(row_type).lower() == str(data['tipo']).lower() and
                abs((new_date - r_date).days) <= 1):
                
                # If exact date and exact detail, definitely duplicate
                r_detail_norm = str(row_detail or '').lower().strip()
                if new_date == r_date and new_detail_norm == r_detail_norm:
                    return True, "duplicate"
                
                # If date is within 1 day but details match well, likely same transaction reported differently
                # (e.g. "MERCADONA" vs "MERCADONA CERDANYOLA")
                if new_detail_norm in r_detail_norm or r_detail_norm in new_detail_norm:
                    return True, "duplicate_likely"
        except: continue
            
    return False, "new"

def process_bank_statement(filepath):
    transactions, error = bank_parser.parse_bbva_excel(filepath)
    if error: return {"status": "error", "message": error}
    
    # BBVA gives newest first. We want oldest first for Excel (chronological ledger).
    transactions.reverse()
    
    wb = load_workbook(EXCEL_PATH, data_only=True)
    results = []
    
    # 1. Identify New Transactions
    new_indices = []
    for i, t in enumerate(transactions):
        exists, status = reconcile_transaction(t, wb)
        t['status'] = status
        results.append(t)
        if status == 'new':
            new_indices.append(i)
    
    # 2. Categorize New Transactions (Rules first, then Gemini)
    if new_indices:
        print(f"DEBUG: Categorizando {len(new_indices)} transacciones nuevas...")
        current_taxonomy = get_taxonomy()
        
        still_to_classify_indices = []
        for idx in new_indices:
            t = results[idx]
            match = apply_rules(t['detalle'], t['tipo'])
            if match:
                results[idx]['categoria'] = match['categoria']
                results[idx]['subcategoria'] = match['subcategoria']
            else:
                still_to_classify_indices.append(idx)
        
        if still_to_classify_indices:
            print(f"DEBUG: {len(still_to_classify_indices)} movimientos requieren IA...")
            # Chunk size of 40 to avoid token/timeout limits
            chunk_size = 40
            for i in range(0, len(still_to_classify_indices), chunk_size):
                chunk = still_to_classify_indices[i:i + chunk_size]
                to_classify = [{"id": idx, "desc": results[idx]['detalle'], "type": results[idx]['tipo']} for idx in chunk]
                
                print(f"DEBUG: Procesando bloque {i//chunk_size + 1} ({len(to_classify)} items)")
                
                prompt = f"""
                Eres un experto contable. Categoriza estos movimientos bancarios usando esta taxonomía:
                {json.dumps(current_taxonomy, indent=2)}
                
                Movimientos:
                {json.dumps(to_classify, indent=2)}
                
                Reglas:
                - Si el tipo es 'Ingreso', busca en la categoría 'Ingresos'.
                - Devuelve SOLO un JSON con este formato:
                {{
                    "classifications": [
                        {{"id": 0, "categoria": "Categoría", "subcategoria": "Subcategoría"}},
                        ...
                    ]
                }}
                """
                
                try:
                    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                    content = response.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(content)
                    for item in data.get('classifications', []):
                        idx = item['id']
                        results[idx]['categoria'] = item['categoria']
                        results[idx]['subcategoria'] = item['subcategoria']
                except Exception as e:
                    print(f"ERROR categorizando bloque: {e}")
                    for idx in chunk:
                        if 'categoria' not in results[idx]:
                            results[idx]['categoria'] = "Otros"
                            results[idx]['subcategoria'] = "Varios"
        
        print("DEBUG: Categorización completada.")
        
    return {"status": "success", "transactions": results}

def process_text(text, force=False):
    analysis = extract_transaction(text)
    if not analysis: return {"status": "error", "message": "Fallo de análisis AI"}
    transactions = analysis.get("transactions", [])
    
    # Fix for batch processing if Gemini returns multiple
    processed = []
    for t in transactions:
        if analysis.get("intent") == "refund" and not force:
            candidates = find_candidates(t['categoria'], load_workbook(EXCEL_PATH))
            if len(candidates) > 1: return {"status": "needs_disambiguation", "candidates": candidates, "original_intent": analysis}
            elif len(candidates) == 1:
                t['monto'] = candidates[0]['monto']
                t['detalle'] = f"Reembolso: {candidates[0]['detalle']}"
        processed.append(t)
        
    return append_to_excel(processed, force)[1]
