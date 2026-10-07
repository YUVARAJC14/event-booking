import secrets
import threading
import time

from app import create_app, db
from app.models import Booking, Event
from tests.helpers import make_user, make_event, login
from tests.testconfig import TestingConfig

SEATS, BUYERS = 5, 30


class RaceConfig(TestingConfig):
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_size": BUYERS, "max_overflow": 0}


app = create_app(RaceConfig)


def reset():
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        org = make_user("org@test.com", "organizer")
        event_id = make_event(org, capacity=SEATS)
        buyers = [make_user(f"buyer{i}@test.com") for i in range(BUYERS)]
    return event_id, buyers


def naive_worker(event_id, user_id, barrier):
    """The WRONG way: read the seats, check, think, then write."""
    with app.app_context():
        barrier.wait()  # everyone starts at the same moment
        event = db.session.get(Event, event_id)
        if event.seats_available >= 1:
            time.sleep(0.05)  # a tiny pause, like any real server has
            event.seats_available = event.seats_available - 1
            db.session.add(Booking(
                user_id=user_id, event_id=event_id, quantity=1,
                total_price=event.price, booking_code=secrets.token_hex(4).upper()))
            db.session.commit()


def safe_worker(event_id, email, barrier):
    """The RIGHT way: our real booking route."""
    client = app.test_client()
    login(client, email)
    barrier.wait()
    client.post(f"/bookings/event/{event_id}", data={"quantity": 1})


def run(worker, event_id, who):
    barrier = threading.Barrier(len(who))
    threads = [threading.Thread(target=worker, args=(event_id, w, barrier)) for w in who]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def report(title, event_id):
    with app.app_context():
        left = db.session.scalar(db.select(Event.seats_available).where(Event.id == event_id))
        made = db.session.scalar(db.select(db.func.count(Booking.id)))
    ok = made <= SEATS and made == SEATS - left
    print(f"\n{title}")
    print(f"  buyers:          {BUYERS}")
    print(f"  seats for sale:  {SEATS}")
    print(f"  bookings made:   {made}")
    print(f"  seats left:      {left}")
    print("  RESULT:", "OK, no overselling" if ok else "BUG, more bookings than seats")


if __name__ == "__main__":
    event_id, buyer_ids = reset()
    run(naive_worker, event_id, buyer_ids)
    report("1) NAIVE: read, check, then write", event_id)

    event_id, _ = reset()
    run(safe_worker, event_id, [f"buyer{i}@test.com" for i in range(BUYERS)])
    report("2) SAFE: the real booking route", event_id)