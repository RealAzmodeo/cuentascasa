from flask import Flask, request, jsonify
from flask_cors import CORS
import ingest_mod
import datetime
import os

app = Flask(__name__)
CORS(app)

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
        from openpyxl import load_workbook
        wb = load_workbook(ingest_mod.EXCEL_PATH, data_only=True)
        if 'Movimientos' not in wb.sheetnames: return jsonify([])
        sheet = wb['Movimientos']
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        recent_data = []
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        
        # 1. CLEAN: Filter out totally empty rows (ghost rows)
        sheet = wb['Movimientos']
        all_rows = list(sheet.iter_rows(min_row=2, values_only=True))
        rows = [r for r in all_rows if r and r[0] is not None]
        
        # Calculate running balances consistently
        running_balances = []
        curr = 0
        for i, r in enumerate(rows):
            if len(r) > 7 and r[7] is not None and str(r[7]).strip() != "":
                try: 
                    val = float(str(r[7]).replace(',', '.'))
                    if val != 0: curr = val
                except: pass
            else:
                try: amt = float(str(r[1] or 0).replace(',', '.'))
                except: amt = 0
                tp = str(r[4]).strip().lower() if r[4] else ""
                if tp == 'ingreso': curr += amt
                elif tp == 'gasto': curr -= amt
            running_balances.append(curr)

        recent_data = []
        # ... rest of the logic
        for i in range(len(rows) - 1, max(-1, len(rows) - 51), -1):
            row = rows[i]
            if not row[0]: continue
            dt = row[0]
            if not isinstance(dt, datetime.date):
                try: dt = datetime.datetime.strptime(str(dt).split(' ')[0], '%Y-%m-%d').date()
                except: dt = today
            
            group = "Anteriores"
            if dt == today: group = "Hoy"
            elif dt == yesterday: group = "Ayer"
            
            recent_data.append({
                "id": i + 2,
                "fecha": f"{dt.year}-{dt.month:02d}-{dt.day:02d}",
                "monto": row[1],
                "categoria": row[2],
                "detalle": row[3],
                "tipo": row[4],
                "tienda": row[5] if len(row) > 5 else "",
                "subcategoria": row[6] if len(row) > 6 else "",
                "cuenta": row[8] if len(row) > 8 else "Germán",
                "saldo": round(running_balances[i], 2),
                "group": group
            })
        return jsonify(recent_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/search', methods=['GET'])
def search():
    try:
        query = request.args.get('q', '').lower()
        from openpyxl import load_workbook
        wb = load_workbook(ingest_mod.EXCEL_PATH, data_only=True)
        if 'Movimientos' not in wb.sheetnames: return jsonify([])
        sheet = wb['Movimientos']
        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        # 1. CLEAN: Filter out totally empty rows (ghost rows)
        sheet = wb['Movimientos']
        all_rows = list(sheet.iter_rows(min_row=2, values_only=True))
        rows = [r for r in all_rows if r and r[0] is not None]

        # Calculate running balances consistently
        running_balances = []
        curr = 0
        for i, r in enumerate(rows):
            if len(r) > 7 and r[7] is not None and str(r[7]).strip() != "":
                try: 
                    val = float(str(r[7]).replace(',', '.'))
                    if val != 0: curr = val
                except: pass
            else:
                try: amt = float(str(r[1] or 0).replace(',', '.'))
                except: amt = 0
                tp = str(r[4]).lower() if r[4] else ""
                if tp == 'ingreso': curr += amt
                elif tp == 'gasto': curr -= amt
            running_balances.append(curr)
        
        # Latest bank anchor found in the filtered rows
        latest_bank_saldo = 0
        anchor_idx = -1
        latest_date = datetime.date(1900, 1, 1)
        for i, r in enumerate(rows):
            if len(r) > 7 and r[7] is not None and str(r[7]).strip() != "":
                try:
                    val = float(str(r[7]).replace(',', '.'))
                    dt = r[0]
                    if not isinstance(dt, datetime.date):
                        try: dt = datetime.datetime.strptime(str(dt).split(' ')[0], '%Y-%m-%d').date()
                        except: continue
                    else:
                        if hasattr(dt, 'date'): dt = dt.date()
                    if dt >= latest_date and val != 0:
                        latest_date = dt
                        latest_bank_saldo = val
                        anchor_idx = i
                except: continue

        results = []
        for i, row in enumerate(rows):
            if not row[0]: continue
            match = False
            if not query: match = True
            else:
                cat = str(row[2] or '').lower()
                det = str(row[3] or '').lower()
                tnd = str(row[5] or '').lower()
                if query in cat or query in det or query in tnd:
                    match = True
            
            if match:
                dt = row[0]
                if not isinstance(dt, datetime.date):
                    try: dt = datetime.datetime.strptime(str(dt).split(' ')[0], '%Y-%m-%d').date()
                    except: dt = datetime.date.today()
                
                results.append({
                    "id": i + 2,
                    "fecha": f"{dt.year}-{dt.month:02d}-{dt.day:02d}",
                    "monto": row[1],
                    "categoria": row[2],
                    "detalle": row[3],
                    "tipo": row[4],
                    "tienda": row[5] if len(row) > 5 else "",
                    "subcategoria": row[6] if len(row) > 6 else "",
                    "cuenta": row[8] if len(row) > 8 else "Germán",
                    "saldo": round(running_balances[i], 2)
                })
        return jsonify(list(reversed(results)))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    try:
        from openpyxl import load_workbook
        wb = load_workbook(ingest_mod.EXCEL_PATH, data_only=True)
        if 'Movimientos' not in wb.sheetnames: return jsonify({"total_income": 0, "total_expense": 0, "savings": 0})
        
        account_filter = request.args.get('account')
        sheet = wb['Movimientos']
        all_rows = list(sheet.iter_rows(min_row=2, values_only=True))
        rows = [r for r in all_rows if r and r[0] is not None]

        # 1. Map all accounts found
        all_accounts = list(set([str(r[8] or "Germán").strip() for r in rows]))
        
        # 2. Track per-account balances and anchors
        # Logic: For each account, find its latest bank anchor.
        # Projected Balance = sum(anchor_val + movements_after_anchor)
        
        account_data = {}
        for acc in all_accounts:
            account_data[acc] = {
                "anchor_idx": -1,
                "anchor_val": 0,
                "anchor_date": datetime.date(1900, 1, 1),
                "current_projected": 0,
                "total_income": 0,
                "total_expense": 0
            }

        # First pass: Find anchors per account
        for i, r in enumerate(rows):
            acc = str(r[8] or "Germán").strip()
            if len(r) > 7 and r[7] is not None and str(r[7]).strip() != "":
                try:
                    val = float(str(r[7]).replace(',', '.'))
                    dt = r[0]
                    if not isinstance(dt, (datetime.datetime, datetime.date)):
                        try: dt = datetime.datetime.strptime(str(dt).split(' ')[0], '%Y-%m-%d').date()
                        except: continue
                    else:
                        if hasattr(dt, 'date'): dt = dt.date()
                    
                    # Update if newer date or same date but later in sheet
                    if dt > account_data[acc]["anchor_date"]:
                        account_data[acc]["anchor_date"] = dt
                        account_data[acc]["anchor_val"] = val
                        account_data[acc]["anchor_idx"] = i
                    elif dt == account_data[acc]["anchor_date"]:
                        account_data[acc]["anchor_val"] = val
                        account_data[acc]["anchor_idx"] = i
                except: continue

        # Second pass: Calculate totals and projections
        total_income, total_expense = 0, 0
        
        for i, r in enumerate(rows):
            acc = str(r[8] or "Germán").strip()
            try: amt = float(str(r[1] or 0).replace(',', '.'))
            except: amt = 0.0
            
            tipo = str(r[4]).strip().lower() if r[4] else ""
            
            # Global or filtered stats
            if not account_filter or acc == account_filter:
                if tipo == 'ingreso': total_income += amt
                elif tipo == 'gasto': total_expense += amt

            # Per-account projection logic
            if account_data[acc]["anchor_idx"] == -1:
                # NO ANCHOR: Sum everything from the beginning
                if tipo == 'ingreso': account_data[acc]["current_projected"] += amt
                elif tipo == 'gasto': account_data[acc]["current_projected"] -= amt
            else:
                # WITH ANCHOR: Start from anchor and only count subsequent movements
                if i == account_data[acc]["anchor_idx"]:
                    account_data[acc]["current_projected"] = account_data[acc]["anchor_val"]
                elif i > account_data[acc]["anchor_idx"]:
                    if tipo == 'ingreso': account_data[acc]["current_projected"] += amt
                    elif tipo == 'gasto': account_data[acc]["current_projected"] -= amt

        total_projected = 0
        if account_filter:
            total_projected = account_data.get(account_filter, {}).get("current_projected", 0)
        else:
            total_projected = sum(data["current_projected"] for data in account_data.values())

        return jsonify({
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "savings": round(total_projected, 2),
            "accounts": all_accounts,
            "account_details": {k: {"projected": round(v["current_projected"], 2), "anchor": v["anchor_val"]} for k, v in account_data.items()}
        })
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

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
        cfg = ingest_mod.load_config()
        return jsonify({
            "taxonomy": cfg.get('taxonomy', {}),
            "preferred_accounts": cfg.get('preferred_accounts', ["Germán", "eToro", "Esposa", "Efectivo"])
        })
    else:
        try:
            new_config = request.json
            with open(ingest_mod.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4)
            return jsonify({"status": "success", "message": "Configuración guardada"})
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
        
        result = ingest_mod.process_bank_statement(temp.name)
        os.unlink(temp.name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ingest_data', methods=['POST'])
def ingest_data():
    try:
        data = request.json
        transactions = data.get('transactions', [])
        success, info = ingest_mod.append_to_excel(transactions, force=True)
        return jsonify(info)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/debug/clear-activity', methods=['POST'])
def debug_clear_activity():
    try:
        from openpyxl import load_workbook
        if not os.path.exists(ingest_mod.EXCEL_PATH):
            return jsonify({"status": "error", "message": "No se encontró el archivo Excel"}), 404
            
        wb = load_workbook(ingest_mod.EXCEL_PATH)
        sheet = wb['Movimientos']
        # Delete all rows except header (row 1)
        if sheet.max_row > 1:
            sheet.delete_rows(2, sheet.max_row)
        wb.save(ingest_mod.EXCEL_PATH)
        return jsonify({"status": "success", "message": "Actividad borrada correctamente"}), 200
    except PermissionError:
        return jsonify({"status": "error", "message": "El archivo Excel está abierto. Ciérralo e inténtalo de nuevo."}), 403
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
