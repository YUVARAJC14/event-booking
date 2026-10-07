import os
from dotenv import load_dotenv
from config import Config
from app import create_app, db, limiter
import pytest

load_dotenv()


def _test_uri():
    uri = os.environ.get("TEST_DATABASE_URL")
    if not uri:
        raise RuntimeError("TEST_DATABASE_URL is not set. Add it to your .env file.")
    for prefix in ("postgres://", "postgresql://"):
        if uri.startswith(prefix):
            uri = "postgresql+psycopg://" + uri[len(prefix):]
    if not uri.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must point to a database whose name ends in _test.")
    return uri


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = _test_uri()
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
    RATELIMIT_ENABLED = False

class LimitedConfig(TestingConfig):
    RATELIMIT_ENABLED = True


@pytest.fixture
def limited_app():
    """An app with rate limiting switched ON."""
    app = create_app(LimitedConfig)
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield app
    limiter.reset()
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()