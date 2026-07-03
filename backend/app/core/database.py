import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("sebi_copilot.database")

# Auto-detect database connectivity and fail over if enabled
db_url = settings.DATABASE_URL
engine = None

if "postgresql" in db_url:
    try:
        # Dry run connection check
        logger.info(f"Attempting connection to primary PostgreSQL: {db_url.split('@')[-1]}")
        temp_engine = create_engine(db_url, connect_args={"connect_timeout": 3})
        with temp_engine.connect() as conn:
            pass
        engine = temp_engine
        logger.info("Successfully connected to primary PostgreSQL database.")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        if settings.AUTO_FALLBACK:
            logger.info("AUTO_FALLBACK is enabled. Switching to local SQLite: sqlite:///./sebi_copilot.db")
            db_url = "sqlite:///./sebi_copilot.db"
        else:
            raise e

if engine is None:
    # Use SQLite or whatever fallback URL is resolved
    connect_args = {}
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)
    logger.info(f"Initialized database engine using: {db_url}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
