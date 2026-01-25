import os
import sys
import json
import datetime
import time
from google import genai
from openpyxl import load_workbook
from dotenv import load_dotenv
import bank_parser
import uuid

# Load environment variables
load_dotenv()

# Configuration
API_KEY = "AIzaSyA_vUyepkn_HR-I18EVugVKvulV-t7OgZc"
EXCEL_PATH = os.getenv("EXCEL_PATH")
client = genai.Client(api_key=API_KEY)
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
# client = genai.Client(api_key=API_KEY) # This line is moved and updated above

def try_parse_json(text):
    """Extracts JSON from text, handling markdown backticks and common junk."""
    if not text: return None
    import re
    # Try direct parse
    try: return json.loads(text.strip())
    except: pass
    # Try regex match for JSON block
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
    # Try stripping markdown backticks manually
    clean = text.replace('```json', '').replace('```', '').strip()
    try: return json.loads(clean)
    except: return None

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
    
    Cuentas disponibles: Germán, eToro, Esposa, Efectivo.
    
    Debes devolver un JSON válido con este formato:
    {{
        "intent": "regular" | "refund" | "transfer",
        "transactions": [
            {{
                "fecha": "YYYY-MM-DD",
                "monto": 0.0,
                "categoria": "Una de las llaves principales de la taxonomía",
                "subcategoria": "Una de las subcategorías correspondientes",
                "tienda": "Nombre del comercio o establecimiento. Si no se menciona, deja en blanco.",
                "detalle": "Resumen breve",
                "tipo": "Gasto" | "Ingreso",
                "cuenta": "Nombre de la cuenta (ej. Germán, eToro, Esposa)",
                "destinatario": "Si es una transferencia (intent='transfer'), nombre de la cuenta destino",
                "link_id": "Genera un ID único (ej. timestamp_random) si es una transferencia"
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

def get_analytics(account_filter=None):
    wb = load_workbook(EXCEL_PATH, data_only=True)
    if 'Movimientos' not in wb.sheetnames: return {}
    sheet = wb['Movimientos']
    data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            # Filter by account if requested
            acc = str(row[8] or 'Germán').strip()
            if account_filter and acc != account_filter:
                continue
            
            try:
                dt = row[0] if isinstance(row[0], (datetime.datetime, datetime.date)) else datetime.datetime.strptime(str(row[0]).split(' ')[0], '%Y-%m-%d')
                data.append({
                    "fecha": dt,
                    "monto": float(row[1]),
                    "categoria": str(row[2]),
                    "detalle": str(row[3]) if row[3] else "",
                    "tipo": str(row[4]).lower(),
                    "tienda": str(row[5]) if len(row) > 5 and row[5] else "Desconocido",
                    "subcategoria": str(row[6]) if len(row) > 6 and row[6] else "Varios",
                    "cuenta": acc
                })
            except: continue

    if not data: return {"months": {}, "history": [], "current_month_key": "", "sorted_months": [], "accounts": []}
    
    # Extract unique accounts from the full dataset (before filtering)
    # We do this from the sheet original rows to be sure we see all accounts
    all_accounts = sorted(list(set([str(row[8] or 'Germán').strip() for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]])))
    
    # Structure: { "YYYY-MM": { "total": 0, "categories": {}, "subcategories": {}, "stores": {}, "top_transactions": {} } }
    monthly_stats = {}
    
    for idx, d in enumerate(data):
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
            
            # Keep transaction list per month for Timeline
            if "transactions" not in stats:
                stats["transactions"] = []
            
            stats["transactions"].append({
                "id": idx + 2, # Use the actual index from enumerate
                "fecha": d['fecha'].strftime('%Y-%m-%d'),
                "monto": d['monto'],
                "categoria": d['categoria'],
                "detalle": d.get('detalle', d['tienda']),
                "tipo": d['tipo'].capitalize(),
                "tienda": d['tienda'],
                "subcategoria": d['subcategoria'],
                "cuenta": d['cuenta']
            })

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
    current_month_key = now_key if now_key in monthly_stats else (sorted_months[0] if sorted_months else now_key)
    
    return {
        "months": monthly_stats,
        "history": history_list,
        "current_month_key": current_month_key,
        "sorted_months": sorted_months,
        "accounts": all_accounts
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

def expand_transfers(data_list):
    """Processes a list of transactions to add counterparts for transfers."""
    expanded = []
    for t in data_list:
        expanded.append(t)
        if t.get('intent') == 'transfer':
            dest = t.get('destinatario')
            if dest and dest != t.get('cuenta'):
                # Create the income/expense in the other account
                counterpart = t.copy()
                counterpart['cuenta'] = dest
                counterpart['tipo'] = 'Ingreso' if t['tipo'] == 'Gasto' else 'Gasto'
                counterpart['detalle'] = f"Transf. de {t.get('cuenta')}: {t['detalle']}"
                # The LinkID is already set by Gemini or manual input
                expanded.append(counterpart)
    return expanded

def append_to_excel(data_list, force=False):
    # Apply transfer logic before appending
    processed_list = expand_transfers(data_list)
    
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    added, dups = 0, []
    for data in processed_list:
        # Use the same reconcile logic as bank ingestion for all insertions
        exists, status = reconcile_transaction(data, wb)
        if not force and exists:
            dups.append(data)
            print(f"DEBUG: Duplicado detectado e ignorado: {data['detalle']} ({data['monto']})")
            continue
        
        sheet.append([
            data['fecha'], data['monto'], data['categoria'], data['detalle'], data['tipo'],
            data.get('tienda', ''), data.get('subcategoria', ''), data.get('saldo_banco', ''),
            data.get('cuenta', 'Germán'), data.get('link_id', '')
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
        sheet.append(['Fecha', 'Monto', 'Categoría', 'Detalle', 'Tipo', 'Tienda', 'Subcategoría', 'Saldo Banco', 'Cuenta', 'LinkID'])
        
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
            r_account = str(row_account or 'Germán').strip()
            new_account = str(data.get('cuenta', 'Germán')).strip()
            
            if (abs(r_amt - new_amt) < 0.001 and 
                str(row_type).lower() == str(data['tipo']).lower() and
                abs((new_date - r_date).days) <= 1 and
                r_account == new_account):
                
                # If exact date and exact detail, definitely duplicate
                r_detail_norm = str(row_detail or '').lower().strip()
                if new_date == r_date and new_detail_norm == r_detail_norm:
                    return True, "duplicate"
                
                # If date is within 1 day but details match well, likely same transaction
                if new_detail_norm in r_detail_norm or r_detail_norm in new_detail_norm:
                    return True, "duplicate_likely"
        except: continue
            
    return False, "new"

def process_bank_statement(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    wb = load_workbook(EXCEL_PATH, data_only=True)
    current_taxonomy = get_taxonomy()
    
    # 1. Extract transactions and account info
    transactions = []
    cfg = load_config()
    current_taxonomy = get_taxonomy()
    detected_account = "Germán" # Default
    
    if ext == '.pdf':
        print(f"DEBUG: Procesando PDF con Gemini...")
        try:
            # Upload file to Gemini
            with open(filepath, 'rb') as f:
                uploaded_file = client.files.upload(file=f, config={'mime_type': 'application/pdf'})
            
            prompt = f"""
            Analiza este extracto bancario en PDF con PRECISIÓN QUIRÚRGICA. 
            
            1. Identifica el titular (Germán, eToro, Esposa, Efectivo, o un nombre nuevo). 
            2. Extrae todos los movimientos.
            
            Taxonomía Obligatoria:
            {json.dumps(current_taxonomy, indent=2)}
            
            Instrucciones de Categorización (CRÍTICO):
            - NO uses 'Otros' si el detalle del banco da alguna pista de la actividad (ej: "RESTAURANTE", "FORN", "BAR", "VIPS" -> Diario/Restaurants).
            - Si el gasto es una suscripción (Netflix, Spotify, Google, etc.), usa 'Entretenimiento'.
            - Si es un recibo de servicios (Luz, Agua, Teléfono), usa 'Servicios'.
            - Si es un ingreso, usa 'Ingresos'.
            - Solo usa 'Otros' como ÚLTIMO RECURSO si el texto es totalmente ilegible o no financiero.

            Devuelve un JSON con:
            {{
                "account_name": "Nombre detectado",
                "transactions": [
                    {{
                        "fecha": "YYYY-MM-DD",
                        "monto": 0.0,
                        "detalle": "Concepto original",
                        "tipo": "Gasto" | "Ingreso",
                        "categoria": "Categoría de la taxonomía",
                        "subcategoria": "Subcategoría de la taxonomía",
                        "saldo_banco": 0.0,
                        "intent": "regular" | "transfer",
                        "destinatario": "..."
                    }}
                ]
            }}
            """
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[uploaded_file, prompt]
            )
            data = try_parse_json(response.text)
            if not data:
                print(f"ERROR IA PDF: No se pudo parsear JSON de la respuesta.")
                return {"status": "error", "message": "Respuesta de IA inválida"}
                
            transactions = data.get('transactions', [])
            detected_account = data.get('account_name', detected_account)
            
            # Normalize detected account to known accounts
            if "ETORO" in detected_account.upper(): detected_account = "eToro"
            elif "GERMAN" in detected_account.upper(): detected_account = "Germán"
            elif "ELENA" in detected_account.upper() or "ESPOSA" in detected_account.upper(): detected_account = "Esposa"
            
            # Assign account to all
            for t in transactions: t['cuenta'] = detected_account
            
        except Exception as e:
            print(f"ERROR procesando PDF: {e}")
            return {"status": "error", "message": f"Error procesando PDF: {str(e)}"}
            
    else: # Excel
        print(f"DEBUG: Procesando Excel...")
        transactions, error = bank_parser.parse_bbva_excel(filepath)
        
        # If native parser fails, try Gemini for the whole Excel content
        if error:
            print(f"DEBUG: Parser nativo falló ({error}). Reintentando con Gemini...")
            try:
                # Read all rows as text for Gemini
                excel_wb = load_workbook(filepath, data_only=True)
                sheet = excel_wb.active
                all_data = []
                for row in sheet.iter_rows(max_row=100, values_only=True): # Cap at 100 rows for cost/context
                    if any(row): all_data.append([str(c) if c is not None else "" for c in row])
                
                prompt = f"""
                Analiza este extracto bancario en formato Excel (convertido a JSON).
                1. Identifica el titular de la cuenta (Germán, eToro, Esposa, Efectivo, o un nombre nuevo).
                2. Extrae todos los movimientos (fecha YYYY-MM-DD, monto positivo, detalle, tipo Gasto/Ingreso).
                
                Taxonomía: {json.dumps(current_taxonomy, indent=2)}
                
                Devuelve un JSON con:
                {{
                    "account_name": "Nombre detectado",
                    "transactions": [
                        {{
                            "fecha": "YYYY-MM-DD",
                            "monto": 0.0,
                            "detalle": "Concepto",
                            "tipo": "Gasto" | "Ingreso",
                            "categoria": "Categoría",
                            "subcategoria": "Subcategoría",
                            "saldo_banco": 0.0
                        }}
                    ]
                }}
                
                Datos:
                {json.dumps(all_data)}
                """
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                data = try_parse_json(response.text)
                if not data:
                    print(f"ERROR IA Excel Ingest: No se pudo parsear JSON.")
                    raise ValueError("Respuesta AI inválida")
                    
                transactions = data.get('transactions', [])
                detected_account = data.get('account_name', "Germán")
            except Exception as e:
                return {"status": "error", "message": f"Falló parsing de Excel (Nativo y AI): {str(e)}"}
        else:
            # If native parser worked, identify account using Gemini on sample
            try:
                excel_wb = load_workbook(filepath, data_only=True)
                sheet = excel_wb.active
                sample_data = []
                for row in sheet.iter_rows(max_row=10, values_only=True):
                    sample_data.append([str(c) for c in row if c is not None])
                
                prompt = f"""
                Identifica el titular de la cuenta bancaria de estos datos. 
                Cuentas sugeridas: {', '.join(cfg.get('preferred_accounts', []))}.
                Si ves un nombre que no está en la lista pero parece ser el titular, devuélvelo.
                
                Datos: {json.dumps(sample_data)}
                
                Devuelve SOLO el nombre.
                """
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                detected_account = response.text.strip()
                
                # Smart normalization
                ua = detected_account.upper()
                pref = cfg.get('preferred_accounts', ["Germán", "eToro", "Esposa", "Efectivo"])
                for p in pref:
                    if p.upper() in ua:
                        detected_account = p
                        break
            except: pass

        # BBVA gives newest first. We want oldest first for Excel (chronological ledger).
        transactions.reverse()
        
        # 2. Categorize New Transactions (Rules first, then Gemini)
        results = []
        new_indices = []
        for i, t in enumerate(transactions):
            t['cuenta'] = detected_account
            exists, status = reconcile_transaction(t, wb)
            t['status'] = status
            results.append(t)
            if status == 'new':
                new_indices.append(i)
        
        if new_indices:
            print(f"DEBUG: Categorizando {len(new_indices)} transacciones de Excel...")
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
                total_to_classify = len(still_to_classify_indices)
                chunk_size = 100 # Increased for speed with Gemini 2.5
                for i in range(0, total_to_classify, chunk_size):
                    print(f"DEBUG: Progreso IA: {i}/{total_to_classify} movimientos clasificados...")
                    chunk = still_to_classify_indices[i:i + chunk_size]
                    to_classify = [{"id": idx, "desc": results[idx]['detalle'], "type": results[idx]['tipo']} for idx in chunk]
                    
                    prompt = f"""
                    Eres un experto contable de ÉLITE. Categoriza estos movimientos bancarios con MÁXIMA EXIGENCIA.
                    
                    Taxonomía Permitida:
                    {json.dumps(current_taxonomy, indent=2)}
                    
                    Movimientos a procesar:
                    {json.dumps(to_classify, indent=2)}
                    
                    Cuentas de la casa: {', '.join(cfg.get('preferred_accounts', []))}.

                    Protocolo de Clasificación (SÍGUELO ESTRICTAMENTE):
                    1. Analiza el campo 'desc' (Concepto del banco). 
                    2. Busca coincidencias semánticas en la taxonomía. Ejemplos:
                       - "AMAZON" -> 'Diario' (si es compra) o 'Entretenimiento' (si es Prime). Default: 'Diario'.
                       - "RECAUDACION" -> 'Hogar' (si es alquiler/comunidad) o 'Ingresos' (si es cobro).
                       - "SEGURO" -> 'Seguros' (mapping directo).
                    3. PROHIBICIÓN DE 'OTROS': Solo puedes usar 'Otros' si tras analizar el texto 3 veces NO encuentras NINGUNA relación con las categorías de arriba. 
                    4. Si es un 'Ingreso', debe ir obligatoriamente a la categoría 'Ingresos'.
                    
                    Devuelve un JSON estrictamente con este formato:
                    {{"classifications": [{{"id": 0, "categoria": "Categoría", "subcategoria": "Subcategoría", "intent": "regular"|"transfer", "justificacion": "Breve explicación de por qué esta categoría y no 'Otros'"}}]}}
                    """
                    try:
                        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                        data = try_parse_json(response.text)
                        
                        if data and 'classifications' in data:
                            for item in data.get('classifications', []):
                                idx = item['id']
                                results[idx]['categoria'] = item['categoria']
                                results[idx]['subcategoria'] = item['subcategoria']
                                results[idx]['intent'] = item.get('intent', 'regular')
                                results[idx]['destinatario'] = item.get('destinatario')
                                results[idx]['link_id'] = item.get('link_id', str(uuid.uuid4())[:8])
                        else:
                            raise ValueError("JSON de clasificación vacío o inválido")
                    except Exception as e:
                        print(f"ERROR IA Excel: {e}")
                        for idx in chunk:
                            results[idx]['categoria'] = "Otros"
                            results[idx]['subcategoria'] = "Varios"
        
        transactions = results

    # Final cleanup: ensure all have account and status
    for t in transactions:
        if 'cuenta' not in t: t['cuenta'] = detected_account
        if 'status' not in t:
            exists, status = reconcile_transaction(t, wb)
            t['status'] = status

    return {"status": "success", "transactions": transactions, "account_detected": detected_account}

def process_text(text, force=False, account_override=None):
    analysis = extract_transaction(text)
    if not analysis: return {"status": "error", "message": "Fallo de análisis AI"}
    transactions = analysis.get("transactions", [])
    
    # Pre-process transactions with intent and account
    for t in transactions:
        t['intent'] = analysis.get('intent')
        if account_override:
            t['cuenta'] = account_override
    
    # Fix for batch processing if Gemini returns multiple
    processed = []
    for t in transactions:
        if t.get("intent") == "refund" and not force:
            candidates = find_candidates(t['categoria'], load_workbook(EXCEL_PATH))
            if len(candidates) > 1: return {"status": "needs_disambiguation", "candidates": candidates, "original_intent": analysis}
            elif len(candidates) == 1:
                t['monto'] = candidates[0]['monto']
                t['detalle'] = f"Reembolso: {candidates[0]['detalle']}"
        processed.append(t)
        
    return append_to_excel(processed, force)[1]
