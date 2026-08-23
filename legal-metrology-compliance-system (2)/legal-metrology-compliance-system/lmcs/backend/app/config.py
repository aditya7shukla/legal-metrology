"""
Centralized application configuration.
All values are overridable via environment variables / .env for 12-factor deployment.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Legal Metrology Compliance Checking System"
    ENV: str = "development"  # development | staging | production
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_A_STRONG_RANDOM_SECRET"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite:///./lmcs.db"  # override with postgresql:// URL in production

    # File storage
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent / "storage" / "uploads")
    REPORT_DIR: str = str(Path(__file__).resolve().parent.parent / "storage" / "reports")
    MAX_UPLOAD_SIZE_MB: int = 15
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

    # OCR
    TESSERACT_CMD: str | None = None  # e.g. /usr/bin/tesseract ; None = use system PATH
    OCR_LANGUAGES: str = "eng"  # e.g. "eng+hin" for English + Hindi labels

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings = Settings()

# Ensure storage directories exist at import time
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.REPORT_DIR).mkdir(parents=True, exist_ok=True)
