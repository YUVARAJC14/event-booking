from tests.helpers import make_event
from tests.test_bookings import book, client_for


def test_hide_sold_out_filter(app, world):
    with app.app_context():
        make_event(world["org"], title="Open Event", capacity=5)
        full_id = make_event(world["org"], title="Full Event", capacity=1)
    book(client_for(app, "a@test.com"), full_id, 1)
    r = app.test_client().get("/events/?available=1")
    assert b"Open Event" in r.data
    assert b"Full Event" not in r.data


def test_sort_by_price_high_to_low(app, world):
    with app.app_context():
        make_event(world["org"], title="Cheap One", price=50)
        make_event(world["org"], title="Pricey One", price=900)
    r = app.test_client().get("/events/?sort=price_high")
    assert r.data.index(b"Pricey One") < r.data.index(b"Cheap One")


def test_page_beyond_the_last_redirects(app, world):
    with app.app_context():
        make_event(world["org"])
    r = app.test_client().get("/events/?page=99")
    assert r.status_code == 302
    assert "page=1" in r.headers["Location"]


def test_home_shows_upcoming_events(app, world):
    with app.app_context():
        make_event(world["org"], title="Jazz By The Sea")
    assert b"Jazz By The Sea" in app.test_client().get("/").data