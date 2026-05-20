"""
core/database.py
================
SQLAlchemy engine + session factory derived from settings.
All services import from here — no more duplicate setups.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# Use AWS_DATABASE_URL if set, otherwise fall back to DATABASE_URL
db_url = settings.db_url

# Configure connection pool settings for PostgreSQL
if db_url.startswith("postgresql"):
    engine = create_engine(
        db_url,
        pool_size=5,                     # Number of connections to maintain
        max_overflow=10,                 # Additional connections when pool is full
        pool_timeout=30,                 # Seconds to wait for connection
        pool_recycle=300,                # Recycle connections every 5 minutes
        pool_pre_ping=True,              # Test connections before using them
        echo_pool=False,                 # Disable pool logging for performance
        connect_args={
            "connect_timeout": 10,       # Connection timeout in seconds
            "keepalives": 1,             # Enable TCP keepalives
            "keepalives_idle": 10,       # Send keepalive after 10 seconds
            "keepalives_interval": 5,    # Send keepalive every 5 seconds
            "keepalives_count": 5,       # Number of keepalives before giving up
            "options": "-c statement_timeout=30000"  # 30 second query timeout
        }
    )
elif db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(db_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and ensures it closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
