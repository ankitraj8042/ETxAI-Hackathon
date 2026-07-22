"""
DCBrain Core Configuration
Loads environment variables and provides settings to the application.
"""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "dcbrain.db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "DCBrain"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # LLM
    GEMINI_API_KEY: str = ""

    # Database (Defaults to SQLite for local zero-config run, can override with Postgres in .env)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
