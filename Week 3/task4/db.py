from __future__ import annotations

from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker

from config import Config


DATABASE_URL = Config.build_database_url()

engine = sa.create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


@contextmanager
def get_db_session():
    """Yield a SQLAlchemy session and guarantee cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def ping_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))
        return True
    except Exception:
        return False
