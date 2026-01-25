import ingest_mod
import json

test_cases = [
    {"text": "MERCADONA CERDANYOLA", "type": "Gasto"},
    {"text": "GOOGLE ONE", "type": "Gasto"},
    {"text": "BIZUM ENVIADO", "type": "Gasto"},
    {"text": "BIZUM RECIBIDO", "type": "Ingreso"},
    {"text": "NOMINA ENERO", "type": "Ingreso"},
    {"text": "TRP REDONDEO TARJETA", "type": "Gasto"},
    {"text": "NUROIL GASOLINA", "type": "Gasto"},
    {"text": "RIP CURL VILADECANS", "type": "Gasto"}
]

def test_rules():
    print("Testing Rules Engine...")
    for case in test_cases:
        match = ingest_mod.apply_rules(case['text'], case['type'])
        if match:
            print(f"PASS: '{case['text']}' [{case['type']}] -> {match['categoria']} / {match['subcategoria']}")
        else:
            print(f"FAIL: '{case['text']}' [{case['type']}] -> No match found")

if __name__ == "__main__":
    test_rules()
