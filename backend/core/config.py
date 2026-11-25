import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

class Settings(BaseSettings):
    app_name: str = "CareerAI"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/careerai"
    jwt_secret: str = "careerai-development-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    gemini_api_key: str = ""
    cors_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        extra="ignore"
    )

settings = Settings()
