import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger(__name__)

def create_configured_engine():
    """Initialise le moteur de base de données PostgreSQL avec repli automatique SQLite WAL."""
    db_url = settings.DATABASE_URL
    
    # 1. Tentative de connexion PostgreSQL si configuré
    if db_url.startswith("postgres"):
        try:
            eng = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DATABASE] Connecté avec succès au serveur PostgreSQL : {db_url.split('@')[-1]}")
            return eng
        except Exception as exc:
            print(f"[DATABASE WARNING] Serveur PostgreSQL non accessible ({exc}).")
            print(f"[DATABASE INFO] Utilisation du moteur de données local SQLite WAL : {settings.SQLITE_FALLBACK_URL}")
            db_url = settings.SQLITE_FALLBACK_URL

    # 2. Moteur SQLite (WAL mode)
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )

engine = create_configured_engine()

# Activation automatique du mode WAL et des contraintes sous SQLite
@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()
    except Exception:
        # Ignoré sur PostgreSQL
        pass

@event.listens_for(Engine, "checkout")
def reset_checkout_connection(dbapi_connection, connection_record, connection_proxy):
    try:
        dbapi_connection.rollback()
    except Exception:
        pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
