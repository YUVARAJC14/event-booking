from tests.helpers import make_user, make_event, login
from tests.test_bookings import book


def test_login_is_rate_limited(limited_app):
    client = limited_app.test_client()
    responses = [client.post("/auth/login", data={"email": "x@test.com", "password": "wrong"})
                 for _ in range(12)]
    assert 429 in [r.status_code for r in responses]
    assert b"Slow down" in responses[-1].data


def test_booking_is_rate_limited(limited_app):
    with limited_app.app_context():
        org = make_user("org@test.com", "organizer")
        make_user("a@test.com")
        event_id = make_event(org, capacity=50)
    client = limited_app.test_client()
    login(client, "a@test.com")
    codes = [book(client, event_id, 1).status_code for _ in range(12)]
    assert codes[0] == 302
    assert 429 in codes


def test_security_headers_are_present(app, world):
    r = app.test_client().get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"