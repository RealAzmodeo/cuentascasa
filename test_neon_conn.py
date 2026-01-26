import os
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Testing connection to: {DATABASE_URL.split('@')[-1] if DATABASE_URL else 'None'}")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    exit(1)

try:
    print(f"[{datetime.datetime.now()}] Creating engine...")
    engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})
    
    print(f"[{datetime.datetime.now()}] Connecting...")
    with engine.connect() as conn:
        print(f"[{datetime.datetime.now()}] Connected! Running simple query...")
        result = conn.execute(text("SELECT 1"))
        print(f"[{datetime.datetime.now()}] Query result: {result.fetchone()}")
        
        print(f"[{datetime.datetime.now()}] Testing Transaction count...")
        result = conn.execute(text("SELECT count(*) FROM transactions"))
        print(f"[{datetime.datetime.now()}] Transaction count: {result.fetchone()[0]}")

    print(f"[{datetime.datetime.now()}] Test SUCCESSFUL.")
except Exception as e:
    print(f"[{datetime.datetime.now()}] Test FAILED: {e}")
