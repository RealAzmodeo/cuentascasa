import os
import json
from google import genai

# HARDCODED NON-LEAKED KEY - DO NOT USE os.getenv
API_KEY = "AIzaSyCSA0I0B_RTKbl-gL11xiNEnQ2vqIc4V1U"
client = genai.Client(api_key=API_KEY)

folder = r'd:\Proyectos\Antigravity Offline\Cuentas-Casa\Extractos bancarios'
files = os.listdir(folder)

print(f"Buscando archivos en: {folder}")
for filename in files:
    filepath = os.path.join(folder, filename)
    ext = os.path.splitext(filename)[1].lower()
    
    print(f"\n--- Analizando: {filename} ---")
    
    try:
        if ext == '.pdf':
            with open(filepath, 'rb') as f:
                uploaded_file = client.files.upload(file=f, config={'mime_type': 'application/pdf'})
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=[uploaded_file, "Identifica el titular de la cuenta o el nombre de esta cuenta bancaria. Devuelve solo el nombre."]
            )
            print(f"IDENTIFICADO: {response.text.strip()}")
            
        elif ext in ['.xlsx', '.xls']:
            from openpyxl import load_workbook
            wb = load_workbook(filepath, data_only=True)
            sheet = wb.active
            rows = []
            for row in sheet.iter_rows(max_row=10, values_only=True):
                rows.append([str(c) for c in row if c is not None])
            
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=f"Identifica el titular o el nombre de la cuenta de este extracto bancario.\n\nDatos:\n{json.dumps(rows)}"
            )
            print(f"IDENTIFICADO: {response.text.strip()}")
    except Exception as e:
        print(f"ERROR: {e}")
