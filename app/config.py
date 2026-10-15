import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "ChangeThis_StrongPassword"
    NEO4J_DATABASE: str = "neo4j"
    
    # Security & Sessions
    SESSION_SECRET: str = "c9b2f6718d7f8a91b2e4f0a3e8c7b6d5e4f3a2b1c0d9e8f7a1b2c3d4e5f6"
    CSRF_SECRET: str = "a8b3c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0123456789abcdef"
    SESSION_COOKIE_NAME: str = "allergraph_session"
    SESSION_MAX_AGE: int = 86400 * 7  # 7 days in seconds
    
    # App Settings
    APP_NAME: str = "AllerGraph"
    APP_TAGLINE: str = "Understand Every Ingredient. Make Informed Choices."
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Password Reset
    RESET_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Optional SMTP for password reset
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "no-reply@allergraph.local"
    SMTP_TLS: bool = True

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
