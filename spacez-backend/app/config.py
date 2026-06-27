"""
Application Configuration Module
This module loads and validates all environment variables used across the application.
It uses pydantic-settings to automatically load values from the .env file
and validate their types at startup.

Required environment variables:
- DATABASE_URL: PostgreSQL/MySQL connection string
- SECRET_KEY: Secret key for JWT token signing
- ALGORITHM: JWT signing algorithm (e.g., "HS256")
- ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration time in minutes
- GOOGLE_CLIENT_ID: Google OAuth client ID for social login
- EMAIL_HOST: SMTP server host for sending emails
- EMAIL_PORT: SMTP server port
- EMAIL_USER: SMTP username (sender email)
- EMAIL_PASS: SMTP password
"""
from pydantic_settings import BaseSettings


# ==========================================
# Settings Class Definition
# ==========================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All fields are required and will raise a validation error
    if not provided in the environment or .env file.
    """

    # Database Configuration
    DATABASE_URL: str

    # JWT / Security Configuration
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str

    # Email / SMTP Configuration
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USER: str
    EMAIL_PASS: str

    class Config:
        """Pydantic configuration to load from .env file."""
        env_file = ".env"


# ==========================================
# Global Settings Instance
# ==========================================
# Global settings instance - imported by other modules
settings = Settings()