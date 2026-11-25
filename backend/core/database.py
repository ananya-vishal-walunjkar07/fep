import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

Base = declarative_base()


def get_engine():
    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    connect_args = {}
    if "postgresql" in db_url:
        connect_args["connect_timeout"] = 3
        try:
            # Test if PostgreSQL is reachable
            test_engine = create_engine(db_url, echo=False, connect_args=connect_args)
            with test_engine.connect() as conn:
                pass
            return test_engine
        except Exception as e:
            # Cloud DB offline / paused -> fall back to local SQLite for development
            sqlite_path = Path(__file__).resolve().parent.parent / "careerai_local.db"
            sqlite_url = f"sqlite:///{sqlite_path}"
            return create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

    return create_engine(db_url, echo=False)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    try:
        import modules.auth.models
        import modules.resumes.models
        import modules.reports.models
        import modules.jobs.models
        import modules.applications.models
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("Database initialization notice:", e)


init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
