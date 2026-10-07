import os
from dotenv import load_dotenv

load_dotenv()

def _db_uri():
    uri = os.environ.get("DATABASE_URL")
    if not uri:
        raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")
    for prefix in ("postgres://", "postgresql://"):
        if uri.startswith(prefix):
            return "postgresql+psycopg://" + uri[len(prefix):]
    return uri

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set COOKIE_SECURE=1 on the live site (HTTPS) so cookies never travel over plain HTTP.
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
    # Set BEHIND_PROXY=1 on the live site so the rate limiter sees real visitor IPs.
    BEHIND_PROXY = os.environ.get("BEHIND_PROXY") == "1"