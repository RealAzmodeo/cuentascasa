from flask import Flask, request, jsonify
from flask_cors import CORS
import ingest_mod
import datetime
import os
import json

app = Flask(__name__)
CORS(app)

from database import log_debug

@app.errorhandler(Exception)
def handle_exception(e):
    log_debug(f"GLOBAL ERROR: {str(e)}")
    return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ingest', methods=['POST'])
def ingest():
    try:
        data = request.json
        text = data.get('text')
        force = data.get('force', False)
        account_override = data.get('account_override')
        if not text:
            return jsonify({"status": "error", "message": "No text provided"}), 400
        result = ingest_mod.process_text(text, force=force, account_override=account_override)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/recent', methods=['GET'])
def recent():
    try:
        from database import log_debug
        log_debug("EP: /recent started")
        # Use DB for recent transactions
        from database import SessionLocal
        from models import Transaction
        from sqlalchemy import desc
        db = SessionLocal()
        account_filter = request.args.get('account')
        query = db.query(Transaction)
        if account_filter:
            query = query.filter(Transaction.cuenta == account_filter)
        
        rows = query.order_by(desc(Transaction.fecha), desc(Transaction.id)).limit(50).all()
        
        # Logic for running balance in DB is a bit different, 
        # for now simplified as we would need the full history for exact running balance
        # or just use the analytical summary anchor.
        summary_data = ingest_mod.get_current_summary(account_filter)
        if isinstance(summary_data, dict) and summary_data.get("status") == "error":
             return jsonify(summary_data), 500
             
        projected = summary_data.get("savings", 0)
        
        recent_data = []
        curr_bal = projected
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        # Reverse rows to calculate backwards if we want accurate running balance from the "now" anchor
        # but rows are already desc. So the first one is the newest.
        for tx in rows:
            dt = tx.fecha
            group = "Anteriores"
            if dt == today: group = "Hoy"
            elif dt == yesterday: group = "Ayer"
            
            recent_data.append({
                "id": tx.id,
                "fecha": tx.fecha.isoformat(),
                "monto": tx.monto,
                "categoria": tx.categoria,
                "detalle": tx.detalle,
                "tipo": tx.tipo,
                "tienda": tx.tienda,
                "subcategoria": tx.subcategoria,
                "cuenta": tx.cuenta,
                "saldo": round(curr_bal, 2),
                "group": group
            })
            # Adjust curr_bal for the NEXT (older) record
            tp = (tx.tipo or "gasto").lower()
            if tp == 'ingreso': curr_bal -= tx.monto
            else: curr_bal += tx.monto
        
        db.close()
        log_debug("EP: /recent finished")
        return jsonify(recent_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/search', methods=['GET'])
def search():
    try:
        from database import SessionLocal
        from models import Transaction
        from sqlalchemy import or_
        db = SessionLocal()
        
        query_str = request.args.get('q', '').lower()
        account_filter = request.args.get('account')
        
        db_query = db.query(Transaction)
        if account_filter:
            db_query = db_query.filter(Transaction.cuenta == account_filter)
            
        if query_str:
            db_query = db_query.filter(or_(
                Transaction.categoria.ilike(f'%{query_str}%'),
                Transaction.detalle.ilike(f'%{query_str}%'),
                Transaction.tienda.ilike(f'%{query_str}%')
            ))
            
        rows = db_query.order_by(Transaction.fecha.desc(), Transaction.id.desc()).limit(100).all()
        
        # For simplicity in search, we might not show exact running balance per row 
        # unless we want to do the full calculation. Let's provide a basic list.
        results = []
        for t in rows:
            results.append({
                "id": t.id,
                "fecha": t.fecha.isoformat(),
                "monto": t.monto,
                "categoria": t.categoria,
                "detalle": t.detalle,
                "tipo": t.tipo,
                "tienda": t.tienda,
                "subcategoria": t.subcategoria,
                "cuenta": t.cuenta,
                "saldo": 0 # Simplified for search
            })
            
        db.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    from database import log_debug
    log_debug("EP: /summary started")
    account_filter = request.args.get('account')
    data = ingest_mod.get_current_summary(account_filter)
    log_debug("EP: /summary finished")
    if isinstance(data, dict) and "status" in data and data["status"] == "error":
        return jsonify(data), 500
    return jsonify(data)

@app.route('/analytics', methods=['GET'])
def analytics():
    try:
        account_filter = request.args.get('account')
        data = ingest_mod.get_analytics(account_filter)
        return jsonify(data)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/taxonomy', methods=['GET'])
def taxonomy():
    return jsonify(ingest_mod.get_taxonomy())

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        log_debug("EP: /config started")
        cfg = ingest_mod.load_config()
        log_debug("EP: /config finished")
        return jsonify(cfg)
    else:
        try:
            new_config = request.json
            with open(ingest_mod.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4)
            return jsonify({"status": "success", "message": "Configuración guardada"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/account/rename', methods=['POST'])
def rename_account():
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not old_name or not new_name:
            return jsonify({"status": "error", "message": "Faltan nombres para el cambio"}), 400
            
        # 1. Update Config (Taxonomy)
        cfg = ingest_mod.load_config()
        if old_name in cfg.get('preferred_accounts', []):
            idx = cfg['preferred_accounts'].index(old_name)
            cfg['preferred_accounts'][idx] = new_name
            
        if 'account_details' in cfg and old_name in cfg['account_details']:
            details = cfg['account_details'].pop(old_name)
            cfg['account_details'][new_name] = details
            
        ingest_mod.save_config_file(cfg)
        
        # 2. Update Database
        success, message = ingest_mod.rename_account_in_db(old_name, new_name)
        
        return jsonify({"status": "success" if success else "error", "message": message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/rules/learn', methods=['POST'])
def learn_rule():
    try:
        data = request.json
        pattern = data.get('pattern')
        category = data.get('category')
        subcategory = data.get('subcategory')
        rule_type = data.get('type', 'Gasto')
        
        if not pattern or not category:
            return jsonify({"status": "error", "message": "Faltan datos para la regla"}), 400
            
        ingest_mod.add_classification_rule(pattern, category, subcategory, rule_type)
        return jsonify({"status": "success", "message": f"Regla para '{pattern}' guardada"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/rules/list', methods=['GET'])
def list_rules():
    try:
        cfg = ingest_mod.load_config()
        return jsonify(cfg.get('classification_rules', []))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/rules/delete', methods=['POST'])
def delete_rule():
    try:
        data = request.json
        pattern = data.get('pattern')
        rule_type = data.get('type', 'Gasto')
        
        config = ingest_mod.load_config()
        rules = config.get('classification_rules', [])
        config['classification_rules'] = [r for r in rules if not (r['pattern'] == pattern and r.get('type') == rule_type)]
        ingest_mod.save_config_file(config)
        return jsonify({"status": "success", "message": "Regla eliminada"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/insights', methods=['GET'])
def insights():
    try:
        data = ingest_mod.get_analytics()
        # Simple AI insight generation
        prompt = f"""
        Eres un asesor financiero de ELITE. Analiza estos datos de gasto mensual y da un consejo breve (max 2 frases) y profesional.
        Datos: {json.dumps(data.get('current_month', {}), indent=2)}
        Comparativa: {data.get('mom_growth', 0)}% vs mes pasado.
        """
        response = ingest_mod.client.models.generate_content(
            model=ingest_mod.MODEL_NAME,
            contents=prompt
        )
        return jsonify({"insight": response.text.strip()})
    except Exception as e:
        return jsonify({"insight": "No se pudo generar el consejo en este momento."})

@app.route('/update', methods=['POST'])
def update():
    try:
        data = request.json
        row_id = int(data.get('id'))
        success, message = ingest_mod.update_transaction(row_id, data)
        return jsonify({"status": "success" if success else "error", "message": message})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete', methods=['POST'])
def delete():
    try:
        data = request.json
        row_id = int(data.get('id'))
        success, message = ingest_mod.delete_transaction(row_id)
        return jsonify({"status": "success" if success else "error", "message": message})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/bank/process', methods=['POST'])
def process_bank():
    from database import log_debug
    import time
    start = time.time()
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No hay archivo"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Archivo sin nombre"}), 400
        
        # Determine extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.xlsx', '.xls', '.pdf']:
            return jsonify({"status": "error", "message": f"Extensión {ext} no soportada"}), 400

        # Save temp file preserving extension
        import tempfile
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        file.save(temp.name)
        temp.close()
        
        log_debug(f"EP: Processing bank file: {file.filename}")
        result = ingest_mod.process_bank_statement(temp.name)
        os.unlink(temp.name)
        
        duration = time.time() - start
        log_debug(f"EP: Bank processing finished in {duration:.2f}s")
        return jsonify(result)
    except Exception as e:
        log_debug(f"EP: Bank processing ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ingest_data', methods=['POST'])
def ingest_data():
    try:
        from database import log_debug
        log_debug("EP: /ingest_data started")
        data = request.json
        transactions = data.get('transactions', [])
        success, info = ingest_mod.add_transactions(transactions, force=True)
        log_debug(f"EP: /ingest_data finished: {info}")
        return jsonify(info)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/debug/clear-activity', methods=['POST'])
def debug_clear_activity():
    try:
        from database import SessionLocal
        from models import Transaction
        db = SessionLocal()
        db.query(Transaction).delete()
        db.commit()
        db.close()
        return jsonify({"status": "success", "message": "Actividad borrada correctamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    from database import init_db
    init_db()
    app.run(port=5000, debug=False)
