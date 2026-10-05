from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    APP_NAME: str = "Vaidya Health-Triage Advisor"
    FLASK_HOST: str = "0.0.0.0"
    FLASK_PORT: int = 5000
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vaidya"
    POSTGRES_USER: str = "vaidya"
    POSTGRES_PASSWORD: str = "vaidya"

    # PostgreSQL Database connection URL.
    # Defaults to Docker internal network URL; can be overridden via DATABASE_URL env var.
    DATABASE_URL: str = "postgresql+psycopg2://vaidya:vaidya@postgres:5432/vaidya"
    
    # Optional Gemini LLM API Key (free tier; graceful fallback to deterministic templates if unset)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # Security & Dashboard Admin Credentials
    SECRET_KEY: str = "vaidya-secret-clinical-key-2026"
    DASHBOARD_ADMIN_USER: str = "admin"
    DASHBOARD_ADMIN_PASSWORD: str = "vaidya123"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # MCP Settings
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Global settings instance
settings = Settings()
