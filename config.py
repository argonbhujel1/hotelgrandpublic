import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Aiven/Heroku sometimes use postgres:// — SQLAlchemy needs postgresql://.
    Ensure sslmode=require for Aiven managed Postgres when not already set.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # Aiven requires SSL; add if missing
    if url.startswith("postgresql://") and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-in-production"
    _db = os.environ.get("DATABASE_URL") or "sqlite:///hotel_grand.db"
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options: SQLite (local) vs Postgres (Aiven) vs serverless (Vercel)
    _uri = SQLALCHEMY_DATABASE_URI or ""
    if _uri.startswith("sqlite"):
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    elif os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        from sqlalchemy.pool import NullPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            "pool_pre_ping": True,
            "connect_args": {"connect_timeout": 10},
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        }

    HOTEL_LAT = float(os.environ.get("HOTEL_LAT", "26.6643"))
    HOTEL_LNG = float(os.environ.get("HOTEL_LNG", "87.6335"))
    HOTEL_NAME = os.environ.get("HOTEL_NAME", "Hotel Grand")
    HOTEL_TAGLINE = os.environ.get("HOTEL_TAGLINE", "Family Restaurant & Lodge")
    HOTEL_ADDRESS = os.environ.get("HOTEL_ADDRESS", "Urlabari-05, Morang, Nepal")
    HOTEL_PHONE = os.environ.get("HOTEL_PHONE", "021-541955")
    HOTEL_EMAIL = os.environ.get("HOTEL_EMAIL", "info@hotelgrand.com.np")
    CHECK_IN = "12:00 PM"
    CHECK_OUT = "11:00 AM"
    WEEKEND_DISCOUNT = 200
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
