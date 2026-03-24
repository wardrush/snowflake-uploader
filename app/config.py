import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'app.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_NAME = os.getenv("APP_NAME", "Lab File Intake")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))
    ALLOWED_EXTENSIONS = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_EXTENSIONS", ".xls,.xlsx,.csv,.zip").split(",")
        if ext.strip()
    )
    UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", str(INSTANCE_DIR / "uploads"))
    HANDOFF_STAGING_ROOT = os.getenv("HANDOFF_STAGING_ROOT", str(INSTANCE_DIR / "handoff_staging"))
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    HANDOFF_BACKEND = os.getenv("HANDOFF_BACKEND", "database_queue")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True

    WTF_CSRF_TIME_LIMIT = None
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_STDOUT = os.getenv("LOG_TO_STDOUT", "true").lower() == "true"
    LOG_FILE = os.getenv("LOG_FILE", str(INSTANCE_DIR / "logs" / "app.log"))
    LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    USE_PROXY_FIX = os.getenv("USE_PROXY_FIX", "false").lower() == "true"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LOG_TO_STDOUT = False
    LOG_FILE = None


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
