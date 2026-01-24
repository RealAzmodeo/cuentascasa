import os
import sys
import json
import datetime
import time
from google.generativeai import GenerativeModel, configure
from openpyxl import load_workbook
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
EXCEL_PATH = os.getenv("EXCEL_PATH")
MODEL_NAME = 'gemini-2.5-flash'

CONFIG_PATH = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/taxonomy.json'

def load_config():
    if not os.path.exists(CONFIG_PATH):
        # Fallback if file missing (shouldn't happen)
        return {
            "taxonomy": {
                "Vivienda": {"subcategories": ["Varios"], "budget": 0},
                "Otros": {"subcategories": ["Varios"], "budget": 0}
            }
        }
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_taxonomy():
    cfg = load_config()
    return {k: v['subcategories'] for k, v in cfg['taxonomy'].items()}

# Initial load
TAXONOMY = get_taxonomy()
CATEGORIES = list(TAXONOMY.keys())

configure(api_key=API_KEY)
model = GenerativeModel(MODEL_NAME)

def extract_transaction(text, retries=3):
    # Reload taxonomy to ensure it's dynamic
    current_taxonomy = get_taxonomy()
    global TAXONOMY, CATEGORIES
    TAXONOMY = current_taxonomy
    CATEGORIES = list(current_taxonomy.keys())
    
    flat_subcats = [item for sublist in current_taxonomy.values() for item in sublist]
    prompt = f"""
    Eres un asistente contable de ELITE. Tu tarea es extraer información detallada de una descripción financiera.
    
    Entrada: "{text}"
    Fecha de hoy: {datetime.date.today()}
    
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
                "tienda": "Nombre del comercio o establecimiento (ej: Mercadona, Amazon, Repsol, Hacienda). Si no se menciona, deja en blanco.",
                "detalle": "Resumen breve",
                "tipo": "Gasto" | "Ingreso"
            }}
        ]
    }}
    
    Reglas de Oro:
    1. Si menciona una tienda (Mercadona, Zara, etc.), extráela en el campo "tienda".
    2. Clasifica con precisión usando la taxonomía proporcionada.
    3. Si es una devolución (reembolso), pon el intent en "refund" e "Ingreso" en el tipo.
    """
    
    for i in range(retries):
        try:
            response = model.generate_content(prompt)
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
    
    now = datetime.datetime.now()
    this_month_key = now.strftime('%Y-%m')
    
    stats = {
        "current_month": {"total": 0, "categories": {}, "stores": {}, "subcategories": {}},
        "history": {}, # Using map for all months
        "all_time_categories": {}
    }

    for d in data:
        if d['tipo'] == 'gasto':
            m_key = d['fecha'].strftime('%Y-%m')
            stats["history"][m_key] = stats["history"].get(m_key, 0) + d['monto']
            stats["all_time_categories"][d['categoria']] = stats["all_time_categories"].get(d['categoria'], 0) + d['monto']
            
            if m_key == this_month_key:
                stats["current_month"]["total"] += d['monto']
                stats["current_month"]["categories"][d['categoria']] = stats["current_month"]["categories"].get(d['categoria'], 0) + d['monto']
                stats["current_month"]["stores"][d['tienda']] = stats["current_month"]["stores"].get(d['tienda'], 0) + d['monto']
                
                # Nested subcategories
                if d['categoria'] not in stats["current_month"]["subcategories"]:
                    stats["current_month"]["subcategories"][d['categoria']] = {}
                sub = d['subcategoria']
                stats["current_month"]["subcategories"][d['categoria']][sub] = stats["current_month"]["subcategories"][d['categoria']].get(sub, 0) + d['monto']

    # Sort history
    sorted_months = sorted(stats["history"].keys())
    history_list = [{"month": m, "total": stats["history"][m]} for m in sorted_months]
    stats["history"] = history_list
    
    # Calculate Mom Growth
    if len(history_list) >= 2:
        curr = history_list[-1]["total"]
        prev = history_list[-2]["total"]
        stats["mom_growth"] = round(((curr - prev) / prev * 100), 1) if prev > 0 else 0
    else:
        stats["mom_growth"] = 0
        
    return stats

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
        return True, "Actualizado"
    except Exception as e: return False, str(e)

def delete_transaction(row_id):
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    if row_id < 2 or row_id > sheet.max_row: return False, "ID inválido"
    try:
        sheet.delete_rows(row_id)
        wb.save(EXCEL_PATH)
        return True, "Eliminado"
    except Exception as e: return False, str(e)

def append_to_excel(data_list, force=False):
    wb = load_workbook(EXCEL_PATH)
    sheet = wb['Movimientos']
    added, dups = 0, []
    for data in data_list:
        if not force and check_for_duplicates(data, wb):
            dups.append(data); continue
        sheet.append([
            data['fecha'], data['monto'], data['categoria'], data['detalle'], data['tipo'],
            data.get('tienda', ''), data.get('subcategoria', '')
        ])
        added += 1
    wb.save(EXCEL_PATH)
    if dups and not force: return False, {"status": "duplicate_found", "duplicates": dups}
    return True, {"status": "success", "added": added}

def reconcile_transaction(data, wb):
    """Checks if a transaction from the bank already exists in the Excel."""
    sheet = wb['Movimientos']
    
    # Standardize date
    if isinstance(data['fecha'], str):
        try: new_date = datetime.datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        except: 
            try: new_date = datetime.datetime.strptime(data['fecha'], '%d/%m/%Y').date()
            except: new_date = datetime.date.today()
    else:
        new_date = data['fecha'].date() if hasattr(data['fecha'], 'date') else data['fecha']

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_date, row_amount, row_type = row[0], row[1], row[4]
        
        if not isinstance(row_date, (datetime.datetime, datetime.date)):
            try: row_date = datetime.datetime.strptime(str(row_date).split(' ')[0], '%Y-%m-%d').date()
            except: continue
        else:
            if hasattr(row_date, 'date'): row_date = row_date.date()
        
        # Match logic: Same amount (approx) AND same type AND date within 3 days
        if (abs(float(row_amount) - float(data['monto'])) < 0.01 and 
            str(row_type).lower() == str(data['tipo']).lower() and
            abs((new_date - row_date).days) <= 3):
            return True, "duplicate"
            
    return False, "new"

def process_bank_statement(filepath):
    import bank_parser
    transactions, error = bank_parser.parse_bbva_excel(filepath)
    if error: return {"status": "error", "message": error}
    
    wb = load_workbook(EXCEL_PATH, data_only=True)
    results = []
    
    for t in transactions:
        exists, status = reconcile_transaction(t, wb)
        t['status'] = status
        # If new, try to auto-categorize using Gemini later or a local map
        results.append(t)
        
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
