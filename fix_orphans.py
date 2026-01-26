from database import SessionLocal
from models import Transaction

def migrate():
    db = SessionLocal()
    try:
        # German -> German prueba
        count1 = db.query(Transaction).filter(Transaction.cuenta == "German").update({"cuenta": "German prueba"})
        # Gabi - Revolut -> Gabi Revolut
        count2 = db.query(Transaction).filter(Transaction.cuenta == "Gabi - Revolut").update({"cuenta": "Gabi Revolut"})
        db.commit()
        print(f"Migrated {count1} transactions to 'German prueba'")
        print(f"Migrated {count2} transactions to 'Gabi Revolut'")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
