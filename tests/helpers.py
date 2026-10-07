from datetime import datetime, timedelta, timezone
from app import db
from app.models import User, Event

PASSWORD = "password123"


def make_user(email, role="user"):
    user = User(email=email, role=role)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user.id


def make_event(organizer_id, capacity=10, price=100, days=5,
               title="Test Event", venue="Test Hall"):
    event = Event(
        organizer_id=organizer_id, title=title, venue=venue,
        starts_at=datetime.now(timezone.utc) + timedelta(days=days),
        price=price, capacity=capacity, seats_available=capacity,
    )
    db.session.add(event)
    db.session.commit()
    return event.id


def login(client, email):
    return client.post("/auth/login", data={"email": email, "password": PASSWORD})


def seats_left(event_id):
    return db.session.scalar(db.select(Event.seats_available).where(Event.id == event_id))