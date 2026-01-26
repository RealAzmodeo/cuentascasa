import os
import sys
import json
import datetime
import time
from google import genai
from dotenv import load_dotenv
import bank_parser
import uuid

# Load environment variables
load_dotenv()

from database import db_session, SessionLocal
from models import Transaction
from sqlalchemy import desc, extract, and_, or_

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
EXCEL_PATH = os.getenv("EXCEL_PATH")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY no encontrada en el archivo .env")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

CONFIG_PATH = 'd:/Proyectos/Antigravity Offline/Cuentas-Casa/taxonomy.json'

def rename_account_in_db(old_name, new_name):
    """Updates all transactions from one account name to another."""
    from models import Transaction
    db = SessionLocal()
    try:
        updated = db.query(Transaction).filter(Transaction.cuenta == old_name).update({Transaction.cuenta: new_name})
        db.commit()
        return True, f"Actualizados {updated} movimientos de {old_name} a {new_name}"
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def add_classification_rule(pattern, category, subcategory=None, rule_type='Gasto'):
    """Adds a new learning rule to taxonomy.json."""
    config = load_config()
    rules = config.get('classification_rules', [])
    
    # Check if duplicate exists
    for r in rules:
        if r['pattern'].upper() == pattern.upper() and r.get('type') == rule_type:
            r['category'] = category
            r['subcategory'] = subcategory
            save_config_file(config)
            return True
            
    rules.append({
        "pattern": pattern.upper(),
        "category": category,
        "subcategory": subcategory,
        "type": rule_type
    })
    config['classification_rules'] = rules
    save_config_file(config)
    return True

def save_config_file(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"taxonomy": {}, "classification_rules": []}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"taxonomy": {}, "classification_rules": []}
            return json.loads(content)
    except (json.JSONDecodeError, Exception):
        return {"taxonomy": {}, "classification_rules": []}

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

def find_candidates(category):
    """Finds recent transactions in the database for refund/matching."""
    db = SessionLocal()
    try:
        return db.query(Transaction).filter(
            Transaction.categoria == category,
            Transaction.tipo == 'Gasto'
        ).order_by(desc(Transaction.fecha)).limit(5).all()
    finally:
        db.close()

def bulk_reconcile(transactions, account):
    """Checks a list of transactions against the DB in a single batch to avoid N+1 queries."""
    if not transactions: return []
    
    # Get the date range of the transactions to narrow down the query
    dates = []
    for t in transactions:
        try:
            d = datetime.datetime.strptime(t['fecha'], '%Y-%m-%d').date() if isinstance(t['fecha'], str) else t['fecha']
            dates.append(d)
        except: continue
    
    if not dates: return transactions

    min_date = min(dates) - datetime.timedelta(days=2)
    max_date = max(dates) + datetime.timedelta(days=2)
    
    db = SessionLocal()
    try:
        # Fetch all existing transactions in the relevant range
        existing = db.query(Transaction).filter(
            Transaction.cuenta == account,
            Transaction.fecha >= min_date,
            Transaction.fecha <= max_date
        ).all()
        
        # Build a lookup set for fast O(1) matching
        # Key: (date, round(amount, 2), tipo.lower())
        lookup = set()
        for ex in existing:
            lookup.add((ex.fecha, round(float(ex.monto), 2), ex.tipo.lower()))
            
        for t in transactions:
            t_date = datetime.datetime.strptime(t['fecha'], '%Y-%m-%d').date() if isinstance(t['fecha'], str) else t['fecha']
            t_amt = round(float(t['monto']), 2)
            t_type = t['tipo'].lower()
            
            # Check for match (incl exact date or +-1 day for robustness)
            matched = False
            for d_off in [0, -1, 1]:
                check_date = t_date + datetime.timedelta(days=d_off)
                if (check_date, t_amt, t_type) in lookup:
                    matched = True
                    break
            
            t['status'] = 'duplicate' if matched else 'new'
            
        return transactions
    finally:
        db.close()

def reconcile_transaction(data):
    """Old single-row version, keeping for backward compatibility but redirecting to optimized logic if possible."""
    res = bulk_reconcile([data], data.get('cuenta', 'Germán'))
    if res:
        return (res[0]['status'] == 'duplicate'), res[0]['status']
    return False, "error"

def get_analytics(account_filter=None):
    """Retrieves analytics using SQL aggregates for speed."""
    from database import log_debug
    from sqlalchemy import func
    log_debug("DB: get_analytics started")
    db = SessionLocal()
    try:
        # 1. Basic Stats: Totals by Month/Account/Type
        # Using extraction to group by month
        month_field = func.to_char(Transaction.fecha, 'YYYY-MM') if 'postgresql' in str(db.bind.url) else func.strftime('%Y-%m', Transaction.fecha)
        
        query = db.query(
            month_field.label('month'),
            Transaction.tipo,
            Transaction.categoria,
            func.sum(Transaction.monto).label('sum_monto')
        )
        
        if account_filter:
            query = query.filter(Transaction.cuenta == account_filter)
        
        agg_data = query.group_by('month', Transaction.tipo, Transaction.categoria).all()
        
        if not agg_data:
            return {"months": {}, "history": [], "current_month_key": "", "sorted_months": [], "accounts": []}

        # 2. Reconstruct the structure needed by frontend
        monthly_stats = {}
        for month, tipo, cat, monto in agg_data:
            if month not in monthly_stats:
                monthly_stats[month] = {"total": 0, "income": 0, "categories": {}, "subcategories": {}, "stores": {}, "top_transactions": {}, "transactions": []}
            
            stats = monthly_stats[month]
            monto = float(monto or 0)
            tipo_low = tipo.lower()
            
            if tipo_low == 'gasto':
                stats["total"] += monto
                stats["categories"][cat] = stats["categories"].get(cat, 0) + monto
            elif tipo_low == 'ingreso':
                stats["income"] += monto

        # 3. Get recent transactions for the "View Transactions" part (limited)
        log_debug("DB: get_analytics fetching detailed transactions...")
        tx_query = db.query(Transaction)
        if account_filter:
            tx_query = tx_query.filter(Transaction.cuenta == account_filter)
        
        # Only fetch last 200 transactions to keep it snappy. Analytics should be about trends anyway.
        recent_tx = tx_query.order_by(desc(Transaction.fecha)).limit(300).all()
        
        for t in recent_tx:
            m_key = t.fecha.strftime('%Y-%m')
            if m_key in monthly_stats:
                monthly_stats[m_key]["transactions"].append({
                    "id": t.id,
                    "fecha": t.fecha.isoformat(),
                    "monto": float(t.monto),
                    "categoria": t.categoria,
                    "detalle": t.detalle or t.tienda,
                    "tipo": t.tipo.capitalize(),
                    "tienda": t.tienda,
                    "subcategoria": t.subcategoria,
                    "cuenta": t.cuenta
                })

        sorted_months = sorted(monthly_stats.keys(), reverse=True)
        ascending_months = sorted(monthly_stats.keys())
        history_list = []
        for i, m in enumerate(ascending_months):
            curr_total = monthly_stats[m]["total"]
            prev_total = monthly_stats[ascending_months[i-1]]["total"] if i > 0 else 0
            growth = round(((curr_total - prev_total) / prev_total * 100), 1) if prev_total > 0 else 0
            history_list.append({ "month": m, "total": round(curr_total, 2), "growth": growth })
        
        now_key = datetime.datetime.now().strftime('%Y-%m')
        current_month_key = now_key if now_key in monthly_stats else (sorted_months[0] if sorted_months else now_key)
        
        # 4. Get unique accounts list
        all_accounts = [r[0] for r in db.query(Transaction.cuenta).distinct().all()]

        return {
            "months": monthly_stats,
            "history": history_list,
            "current_month_key": current_month_key,
            "sorted_months": sorted_months,
            "accounts": sorted(all_accounts)
        }
    except Exception as e:
        log_debug(f"Error in analytics: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

def get_current_summary(account_filter=None):
    """Calculates totals and projections from the Database using SQL aggregates for speed."""
    from database import log_debug
    from sqlalchemy import func
    log_debug("DB: get_current_summary started")
    db = SessionLocal()
    try:
        log_debug("DB: get_current_summary aggregate query start")
        # Query: sum of monto grouped by account and type
        stats = db.query(
            Transaction.cuenta, 
            Transaction.tipo, 
            func.sum(Transaction.monto)
        ).group_by(Transaction.cuenta, Transaction.tipo).all()

        if not stats:
            return {"total_income": 0, "total_expense": 0, "savings": 0, "accounts": [], "account_details": {}}

        all_accounts = sorted(list(set([row[0] for row in stats])))
        account_data = {acc: {"projected": 0} for acc in all_accounts}
        
        total_income = 0
        total_expense = 0

        for acc, tipo, amt in stats:
            amt = float(amt or 0)
            tipo_lower = (tipo or "Gasto").lower()
            
            if tipo_lower == 'ingreso':
                account_data[acc]["projected"] += amt
                if not account_filter or acc == account_filter:
                    total_income += amt
            else:
                account_data[acc]["projected"] -= amt
                if not account_filter or acc == account_filter:
                    total_expense += amt
                    
        total_projected = account_data.get(account_filter, {}).get("projected", 0) if account_filter else sum(a["projected"] for a in account_data.values())
        
        return {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "savings": round(total_projected, 2),
            "accounts": all_accounts,
            "account_details": {k: {"projected": round(v["projected"], 2), "anchor": 0} for k, v in account_data.items()},
            "current_account": account_filter
        }
    except Exception as e:
        log_debug(f"Error in summary: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

def update_transaction(row_id, data):
    """Updates a transaction in the database."""
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.id == row_id).first()
        if tx:
            tx.fecha = datetime.datetime.strptime(data['fecha'], '%Y-%m-%d').date() if isinstance(data['fecha'], str) else data['fecha']
            tx.monto = float(data['monto'])
            tx.categoria = data['categoria']
            tx.detalle = data['detalle']
            tx.tipo = data['tipo']
            tx.tienda = data.get('tienda', '')
            tx.subcategoria = data.get('subcategoria', '')
            db.commit()
            return True, "Actualizado en DB"
        return False, "Transacción no encontrada"
    except Exception as e:
        db.rollback()
        return False, f"DB Update error: {e}"
    finally:
        db.close()

def delete_transaction(row_id):
    """Deletes a transaction from the database."""
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.id == row_id).first()
        if tx:
            db.delete(tx)
            db.commit()
            return True, "Eliminado de DB"
        return False, "Transacción no encontrada"
    except Exception as e:
        db.rollback()
        return False, f"DB Delete error: {e}"
    finally:
        db.close()

def expand_transfers(data_list):
    """Processes a list of transactions to add counterparts for transfers."""
    expanded = []
    for t in data_list:
        expanded.append(t)
        if t.get('intent') == 'transfer':
            dest = t.get('destinatario')
            if dest and dest != t.get('cuenta'):
                counterpart = t.copy()
                counterpart['cuenta'] = dest
                counterpart['tipo'] = 'Ingreso' if t['tipo'] == 'Gasto' else 'Gasto'
                counterpart['detalle'] = f"Transf. de {t.get('cuenta')}: {t['detalle']}"
                expanded.append(counterpart)
    return expanded

def process_bank_statement(filepath):
    """Parses a bank statement (PDF/Excel) and reconciles with DB."""
    ext = os.path.splitext(filepath)[1].lower()
    current_taxonomy = get_taxonomy()
    cfg = load_config()
    detected_account = "Germán"
    transactions = []
    
    if ext == '.pdf':
        try:
            uploaded_file = client.files.upload(file=filepath, config={'mime_type': 'application/pdf'})
            
            prompt = f"""
            Analiza este extracto bancario en PDF con PRECISIÓN QUIRÚRGICA. 
            1. Identifica el titular (Germán, eToro, Esposa, Efectivo, o un nombre por defecto: Germán). 
            2. Extrae todos los movimientos del periodo.
            
            Taxonomía Obligatoria:
            {json.dumps(current_taxonomy, indent=2)}
            
            Instrucciones de Categorización (CRÍTICO):
            - ANALIZA EL DETALLE: Si el banco dice "Pago con tarjeta" BUSCA el nombre del comercio en el texto.
            - HIJOS: Si el beneficiario es "Bruno", "Jazz", "Dibujo" o "Piscina", usa 'Hijos'.
            - TRANSFERENCIAS: Si es una transferencia a "Bruno", "Alicia", "Fili" o "Gabi", usa 'Transferencias'.
            - DIARIO: Si el comercio es un supermercado (Mercadona, Carrefour, Lidl, etc.) o restaurante, usa 'Diario'.
            - NO uses 'Otros' si puedes deducir la categoría por la taxonomía.
            
            Devuelve un JSON estrictamente con este formato:
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
                        "destinatario": "Nombre de la cuenta destino si es transfer",
                        "link_id": "ID único corto (8 chars) para transacciones vinculadas"
                    }}
                ]
            }}
            """
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[uploaded_file, prompt]
            )
            data = try_parse_json(response.text)
            if data:
                transactions = data.get('transactions', [])
                detected_account = data.get('account_name', detected_account)
            else:
                print(f"ERROR: No se pudo parsear JSON de Gemini para PDF.")
        except Exception as e:
            print(f"ERROR PDF: {e}")
            return {"status": "error", "message": f"Error procesando PDF: {str(e)}"}
            
    else: # Excel
        transactions, error = bank_parser.parse_bbva_excel(filepath)
        if error:
            try:
                from openpyxl import load_workbook 
                excel_wb = load_workbook(filepath, data_only=True)
                sheet = excel_wb.active
                all_data = []
                for row in sheet.iter_rows(max_row=100, values_only=True):
                    if any(row): all_data.append([str(c) if c is not None else "" for c in row])
                
                prompt = f"""
                Analiza este extracto Excel. Identifica el titular y extrae movimientos.
                Taxonomía: {json.dumps(current_taxonomy, indent=2)}
                Datos: {json.dumps(all_data)}
                Devuelve JSON con 'account_name' y 'transactions'.
                """
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                data = try_parse_json(response.text)
                if data:
                    transactions = data.get('transactions', [])
                    detected_account = data.get('account_name', detected_account)
            except Exception as e:
                print(f"ERROR Excel AI: {e}")
                return {"status": "error", "message": f"Error Excel AI: {str(e)}"}
        else:
            # Native parser worked, apply rules for categorization
            for t in transactions:
                rule = apply_rules(t['detalle'], t['tipo'])
                if rule:
                    t['categoria'] = rule['categoria']
                    t['subcategoria'] = rule['subcategoria']
                else:
                    t['categoria'] = "Otros"
                    t['subcategoria'] = "Varios"
            
            # Simple account assignment: Use first account from pref list or "Germán"
            prefs = current_taxonomy.get('preferred_accounts', ["Germán"])
            detected_account = prefs[0] if prefs else "Germán"

    # Normalize and Reconcile in Bulk
    results = bulk_reconcile(transactions, detected_account)
    for t in results:
        t['cuenta'] = detected_account
    
    return {"status": "success", "transactions": results, "account_detected": detected_account}

def process_text(text, force=False, account_override=None):
    """Processes natural language input using Gemini."""
    analysis = extract_transaction(text)
    if not analysis: return {"status": "error", "message": "Fallo de análisis AI"}
    transactions = analysis.get("transactions", [])
    
    for t in transactions:
        t['intent'] = analysis.get('intent')
        if account_override: t['cuenta'] = account_override
    
    processed = []
    for t in transactions:
        if t.get("intent") == "refund" and not force:
            candidates = find_candidates(t['categoria'])
            if len(candidates) > 1: return {"status": "needs_disambiguation", "candidates": candidates, "original_intent": analysis}
            elif len(candidates) == 1:
                t['monto'] = float(candidates[0].monto)
                t['detalle'] = f"Reembolso: {candidates[0].detalle}"
        processed.append(t)
        
    return add_transactions(processed, force)[1]

def add_transactions(data_list, force=False):
    """Adds a list of transactions to the database."""
    processed_list = expand_transfers(data_list)
    db_added = 0
    db = SessionLocal()
    try:
        # Optimization: Only reconcile if not force
        to_save = processed_list
        if not force:
            # We don't have a clean way to group by account here reliably in a single bulk_reconcile call
            # without knowing the accounts upfront, but usually it's one account.
            # For now, let's just optimize the 'force' case which is the most common for bank ingest.
            pass 
        
        for data in to_save:
            if not force:
                exists, status = reconcile_transaction(data)
                if exists: continue
            
            new_date = datetime.datetime.strptime(data['fecha'], '%Y-%m-%d').date() if isinstance(data['fecha'], str) else data['fecha']
            new_tx = Transaction(
                fecha=new_date,
                monto=float(data['monto']),
                categoria=data['categoria'],
                subcategoria=data.get('subcategoria', 'Varios'),
                detalle=data.get('detalle', ''),
                tipo=data['tipo'],
                tienda=data.get('tienda', ''),
                cuenta=data.get('cuenta', 'Germán'),
                saldo_banco=float(data.get('saldo_banco')) if data.get('saldo_banco') else None,
                link_id=data.get('link_id', '')
            )
            db.add(new_tx)
            db_added += 1
        db.commit()
        return True, {"status": "success", "added": db_added}
    except Exception as e:
        db.rollback()
        return False, {"status": "error", "message": str(e)}
    finally:
        db.close()
