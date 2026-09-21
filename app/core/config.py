from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables or .env file.
    Following 12-Factor App principles: Strict separation of config from code.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Metadata
    APP_NAME: str = "GiveNaija API"
    APP_ENV: str = "development"
    PORT: int = 8000
    DEBUG: bool = True

    # Security & JWT Authentication
    SECRET_KEY: str = "give-naija-super-secret-key-32-chars-minimum-safe"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL Database Connection URLs (Docker)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5433/givenaija"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5433/givenaija_test"

    # Redis Caching & Rate Limiting URL
    REDIS_URL: str = "redis://localhost:6379/0"

    # Payment Webhook Verification Secret (used with HMAC-SHA256)
    WEBHOOK_SECRET: str = "mysecret"

    # Firestore Project ID & Optional Emulator Host
    FIRESTORE_PROJECT_ID: str = "givenaija-dev"
    FIRESTORE_EMULATOR_HOST: Optional[str] = None

    # Rate Limiting Controls (Requests Per Minute)
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 60

    # Admin/Cron API Key for triggering scheduled background sweeps
    CRON_API_KEY: str = "give-naija-cron-secret-api-key"


settings = Settings()
