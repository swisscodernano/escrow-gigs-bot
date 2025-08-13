import os
from pydantic import BaseModel

class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "escrowdb")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "escrow")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "escrowpass")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    PRIMARY_ASSET: str = os.getenv("PRIMARY_ASSET", "USDT-TRON")
    TRON_PRIVATE_KEY: str = os.getenv("TRON_PRIVATE_KEY", "")
    TRON_API_KEY: str = os.getenv("TRON_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
