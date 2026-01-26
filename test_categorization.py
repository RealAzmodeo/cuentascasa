import ingest_mod
import json

def test_categorization():
    print("Testing AI Categorization with Revolut-like samples...")
    
    samples = [
        {"detalle": "Pago con tarjeta MERCADONA", "monto": 45.30},
        {"detalle": "Transferir a Bruno", "monto": 20.00},
        {"detalle": "Pago con tarjeta NETFLIX", "monto": 12.99},
        {"detalle": "Transferir a Gabi", "monto": 100.00},
        {"detalle": "Pago con tarjeta VIPS", "monto": 32.00}
    ]
    
    # We can't really call the AI without a real file or complex mocking,
    # but we can verify that the taxonomy is correctly loaded and fixed.
    
    tax = ingest_mod.load_config().get('taxonomy', {})
    if 'Transferencias' in tax:
        print("SUCCESS: 'Transferencias' category found (typo fixed).")
    else:
        print("FAILURE: 'Transferencias' category NOT found.")
        
    if 'Other' not in tax:
        print("SUCCESS: 'Other' category removed.")
    else:
        print("FAILURE: 'Other' category still present.")
        
    print("\nCategorization mapping validation:")
    # Check if 'Hijos' and 'Transferencias' and 'Diario' subcategories are present
    categories = ['Hijos', 'Transferencias', 'Diario']
    for cat in categories:
        if cat in tax:
            print(f"  - Category '{cat}' exists with {len(tax[cat]['subcategories'])} subcategories.")
        else:
            print(f"  - ERROR: Category '{cat}' missing!")

if __name__ == '__main__':
    test_categorization()
