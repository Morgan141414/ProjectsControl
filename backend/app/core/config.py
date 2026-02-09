from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_URL = f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Productivity Control API"
    DATABASE_URL: str = DEFAULT_SQLITE_URL
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    STORAGE_DRIVER: str = "local"
    STORAGE_PATH: str = "./data/recordings"
    MAX_UPLOAD_MB: int = 2048
    RETENTION_DAYS: int = 90
    METRICS_MAX_GAP_SECONDS: int = 300
    EVENTS_RETENTION_DAYS: int = 30
    REPORTS_PATH: str = "./data/reports"
    REPORTS_MAX_EXPORT_MB: int = 50
    REPORTS_WEBHOOK_TIMEOUT_SECONDS: int = 5
    SCHEDULE_TICK_SECONDS: int = 300
    GOOGLE_OAUTH_CLIENT_ID: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)


settings = Settings()
