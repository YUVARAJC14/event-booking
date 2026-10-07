from app import db
from app.models import Booking, Event
from tests.helpers import make_event, login, seats_left


def book(client, event_id, qty=1):
    return client.post(f"/bookings/event/{event_id}", data={"quantity": qty})


def client_for(app, email):
    client = app.test_client()
    login(client, email)
    return client


def test_only_organizers_can_create_events(app, world):
    client = client_for(app, "a@test.com")
    assert client.get("/events/new").status_code == 403


def test_search_finds_matching_events(app, world):
    with app.app_context():
        make_event(world["org"], title="Rooftop Film Night")
        make_event(world["org"], title="Pottery Class")
    r = app.test_client().get("/events/?q=film")
    assert b"Rooftop Film Night" in r.data
    assert b"Pottery Class" not in r.data


def test_booking_reduces_seats_and_stores_total(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5, price=250)
    book(client_for(app, "a@test.com"), event_id, 2)
    with app.app_context():
        assert seats_left(event_id) == 3
        booking = Booking.query.one()
        assert booking.quantity == 2
        assert booking.total_price == 500


def test_cannot_book_more_than_available(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=2)
    book(client_for(app, "a@test.com"), event_id, 3)
    with app.app_context():
        assert seats_left(event_id) == 2
        assert Booking.query.count() == 0


def test_last_seat_can_only_be_sold_once(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=1)
    book(client_for(app, "a@test.com"), event_id, 1)
    book(client_for(app, "b@test.com"), event_id, 1)
    with app.app_context():
        assert seats_left(event_id) == 0
        assert Booking.query.count() == 1


def test_cancel_returns_seats_only_once(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5)
    client = client_for(app, "a@test.com")
    book(client, event_id, 2)
    with app.app_context():
        booking_id = Booking.query.one().id
        assert seats_left(event_id) == 3
    client.post(f"/bookings/{booking_id}/cancel")
    client.post(f"/bookings/{booking_id}/cancel")  # second click must change nothing
    with app.app_context():
        assert seats_left(event_id) == 5
        assert Booking.query.one().status == "cancelled"


def test_cannot_cancel_someone_elses_booking(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5)
    book(client_for(app, "a@test.com"), event_id, 1)
    with app.app_context():
        booking_id = Booking.query.one().id
    r = client_for(app, "b@test.com").post(f"/bookings/{booking_id}/cancel")
    assert r.status_code == 404
    with app.app_context():
        assert Booking.query.one().status == "confirmed"


def test_organizer_cannot_book_own_event(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5)
    book(client_for(app, "org@test.com"), event_id, 1)
    with app.app_context():
        assert Booking.query.count() == 0
        assert seats_left(event_id) == 5


def test_cannot_book_past_event(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5, days=-1)
    book(client_for(app, "a@test.com"), event_id, 1)
    with app.app_context():
        assert Booking.query.count() == 0
        assert seats_left(event_id) == 5


def test_event_with_bookings_cannot_be_deleted(app, world):
    with app.app_context():
        event_id = make_event(world["org"], capacity=5)
    book(client_for(app, "a@test.com"), event_id, 1)
    client_for(app, "org@test.com").post(f"/events/{event_id}/delete")
    with app.app_context():
        assert db.session.get(Event, event_id) is not None