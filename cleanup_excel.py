import ingest_mod
import os

def cleanup():
    print("--- SURGICAL CLEANUP START ---")
    print(f"Targeting: {ingest_mod.EXCEL_PATH}")
    
    if not os.path.exists(ingest_mod.EXCEL_PATH):
        print("Error: File not found.")
        return

    # Call the new sort and rebuild logic
    ingest_mod.sort_excel_by_date()
    print("--- CLEANUP FINISHED ---")

if __name__ == "__main__":
    cleanup()
