from flask import Flask, request, jsonify
from flask_cors import CORS
import ingest_mod
import datetime

app = Flask(__name__)
CORS(app)

@app.route('/ingest', methods=['POST'])
def ingest():
    try:
        data = request.json
        text = data.get('text')
        force = data.get('force', False)
        if not text:
            return jsonify({"status": "error", "message": "No se proporcionó texto"}), 400
        result = ingest_mod.process_text(text, force=force)
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
        
        # Reverse to get recent first
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
                "fecha": str(dt),
                "monto": row[1],
                "categoria": row[2],
                "detalle": row[3],
                "tipo": row[4],
                "tienda": row[5] if len(row) > 5 else "",
                "subcategoria": row[6] if len(row) > 6 else "",
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
        results = []
        for i, row in enumerate(rows):
            if not row[0]: continue
            # row[2]: cat, row[3]: detalle, row[5]: tienda
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
                    "fecha": str(dt),
                    "monto": row[1],
                    "categoria": row[2],
                    "detalle": row[3],
                    "tipo": row[4],
                    "tienda": row[5] if len(row) > 5 else "",
                    "subcategoria": row[6] if len(row) > 6 else ""
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
        sheet = wb['Movimientos']
        total_income, total_expense = 0, 0
        for row in sheet.iter_rows(min_row=2, values_only=True):
            amount = row[1] or 0
            tipo = str(row[4]).lower() if row[4] else ""
            if tipo == 'ingreso': total_income += float(amount)
            elif tipo == 'gasto': total_expense += float(amount)
        return jsonify({
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "savings": round(total_income - total_expense, 2)
        })
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analytics', methods=['GET'])
def analytics():
    try:
        data = ingest_mod.get_analytics()
        return jsonify(data)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/taxonomy', methods=['GET'])
def taxonomy():
    return jsonify(ingest_mod.get_taxonomy())

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(ingest_mod.load_config())
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
        response = ingest_mod.model.generate_content(prompt)
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

@app.route('/ingest_data', methods=['POST'])
def ingest_data():
    try:
        data = request.json
        transactions = data.get('transactions', [])
        success, info = ingest_mod.append_to_excel(transactions, force=True)
        return jsonify(info)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
