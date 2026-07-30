from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Construction CRM"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = (
        "postgresql+asyncpg://user:password@localhost:5432/construction_crm"
    )

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440

    UPLOAD_DIR: str = "uploads/avatars"
    MAX_AVATAR_SIZE_MB: int = 5

    LOG_LEVEL: str = "INFO"


settings = Settings()
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
