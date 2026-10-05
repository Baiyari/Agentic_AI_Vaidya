import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

logger = logging.getLogger(__name__)

# Create engine with pool_pre_ping for resilient connections
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db(max_retries: int = 6, initial_delay: float = 2.0, backoff_factor: float = 1.5) -> bool:
    """
    Initializes database tables with retry logic and exponential backoff
    to prevent container crashes if PostgreSQL takes a moment to become ready.
    """
    current_delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Checking database connection (attempt {attempt}/{max_retries})...")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                if not settings.DATABASE_URL.startswith("sqlite"):
                    try:
                        conn.execute(text("ALTER TABLE triage_records ALTER COLUMN duration_days TYPE DOUBLE PRECISION;"))
                        conn.execute(text("ALTER TABLE triage_records ADD COLUMN IF NOT EXISTS duration_hours DOUBLE PRECISION;"))
                        conn.commit()
                    except Exception as migration_err:
                        logger.debug(f"Schema upgrade note (may already be upgraded): {migration_err}")
            Base.metadata.create_all(bind=engine)
            logger.info("Database connection established and metadata synchronized successfully.")
            return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying database initialization in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= backoff_factor
            else:
                logger.error("Exhausted all database connection attempts.")
                raise e


def get_db():
    """Dependency to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

