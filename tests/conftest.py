import pytest
from app import create_app, db, limiter
from tests.testconfig import TestingConfig
from tests.helpers import make_user


class LimitedConfig(TestingConfig):
    RATELIMIT_ENABLED = True


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def world(app):
    """Two organizers and two normal users, ready to use."""
    with app.app_context():
        return {
            "org": make_user("org@test.com", "organizer"),
            "other_org": make_user("org2@test.com", "organizer"),
            "a": make_user("a@test.com"),
            "b": make_user("b@test.com"),
        }


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