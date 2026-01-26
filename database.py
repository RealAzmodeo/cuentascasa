import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# For local development/testing if DATABASE_URL is missing, we could use sqlite
# but since the user wants Neon.tech, we will assume PostgreSQL
if not DATABASE_URL:
    # Fallback to local sqlite for safety during setup, so app doesn't crash
    DATABASE_URL = "sqlite:///./local_finance.db"
    print("WARNING: DATABASE_URL not found in .env. Using local SQLite for now.")

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

def log_debug(msg):
    with open("d:/Proyectos/Antigravity Offline/Cuentas-Casa/app_debug.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} - {msg}\n")

def init_db():
    try:
        log_debug("Starting init_db...")
        Base.metadata.create_all(bind=engine)
        log_debug("init_db success.")
        print("Database tables initialized.")
    except Exception as e:
        log_debug(f"init_db ERROR: {e}")
        print(f"Error initializing DB: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
