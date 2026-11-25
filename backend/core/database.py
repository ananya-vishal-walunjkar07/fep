from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import settings

db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "postgresql" in db_url:
    connect_args["connect_timeout"] = 3

engine = create_engine(
    db_url,
    echo=False,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all database models
Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
