import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config

# Dynamic connection string resolution to prevent Docker vs Host network conflicts
url = Config.DATABASE_URL

if url:
    # If running inside Docker (DB_HOST is postgres_db) but url has localhost/127.0.0.1, resolve it!
    if Config.DB_HOST not in ["localhost", "127.0.0.1", "::1"]:
        url = url.replace("@localhost", f"@{Config.DB_HOST}").replace("@127.0.0.1", f"@{Config.DB_HOST}").replace("@[::1]", f"@{Config.DB_HOST}")
else:
    # Build standard connection string
    url = f"postgresql://{Config.DB_USER}:{sa.util.preloaded.quote_plus(Config.DB_PASSWORD) if hasattr(sa.util, 'preloaded') else Config.DB_PASSWORD}@{sa.util.preloaded.quote_plus(Config.DB_HOST) if hasattr(sa.util, 'preloaded') else Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    
    # Simple fallback without quote_plus if needed
    url = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"

# Configure standard SQLAlchemy Engine
engine = sa.create_engine(
    url,
    pool_pre_ping=True,  # Automatically recycles stale connections
    pool_size=5,
    max_overflow=10
)

# Standard session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model metadata
Base = declarative_base()

def get_db_session():
    """Dependency generator to retrieve clean database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
