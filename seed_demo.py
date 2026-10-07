import random
import secrets
from datetime import datetime, time, timedelta, timezone

from app import create_app, db
from app.models import User, Event, Booking
from app.utils import from_local, to_local

ORGANIZER = "demo.organizer@example.com"
DEMO_USER = "demo.user@example.com"
BUYERS = [f"demo.buyer{i}@example.com" for i in range(1, 7)]
PASSWORD = "DemoPass2026"

# title, venue, price, capacity, days from today, start hour, how full (0 to 1)
EVENTS = [
    ("Rooftop Film Night", "The Terrace, Block C", 499, 50, 3, 19, 0.82),
    ("Indie Music Fest", "Open Air Arena", 1499, 300, 9, 17, 0.55),
    ("Stand-up Comedy Evening", "The Laugh Lounge", 699, 80, 5, 20, 1.0),
    ("Startup Pitch Night", "Innovation Hub", 299, 120, 12, 18, 0.35),
    ("Sunrise Yoga Session", "Lakeside Park", 199, 40, 4, 6, 0.9),
    ("Photography Walk", "Old Town Square", 349, 25, 15, 7, 0.28),
    ("Board Game Cafe Meetup", "Dice and Dragons Cafe", 149, 30, 7, 16, 0.6),
    ("Classical Guitar Recital", "City Auditorium", 799, 150, 21, 19, 0.2),
    ("Street Food Festival", "Riverside Grounds", 99, 500, 18, 12, 0.45),
    ("Python Workshop for Beginners", "Tech Park, Hall 2", 0, 60, 10, 10, 0.75),
    ("Art and Wine Evening", "Gallery 12", 1199, 45, 28, 18, 0.1),
    ("Charity Fun Run", "Central Stadium", 250, 400, 35, 6, 0.15),
]

random.seed(2026)
app = create_app()
used_codes = set()


def get_or_create_user(email, role):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, role=role)
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.flush()
    return user


def unique_code():
    while True:
        code = secrets.token_hex(4).upper()
        if code not in used_codes and not Booking.query.filter_by(booking_code=code).first():
            used_codes.add(code)
            return code


def recent_time(now):
    # more bookings in recent days than in older ones
    seconds = int((random.random() ** 1.6) * 13 * 24 * 3600)
    return now - timedelta(seconds=seconds)


def add_booking(user, event, qty, now, status="confirmed"):
    if status == "confirmed":
        if event.seats_available < qty:
            return False
        event.seats_available -= qty
    db.session.add(Booking(
        user_id=user.id, event_id=event.id, quantity=qty,
        total_price=event.price * qty, status=status,
        booking_code=unique_code(), created_at=recent_time(now)))
    return True


with app.app_context():
    organizer = get_or_create_user(ORGANIZER, "organizer")
    demo_user = get_or_create_user(DEMO_USER, "user")
    buyers = [get_or_create_user(email, "user") for email in BUYERS]

    # Replace the previous demo events and their bookings. Other people's data is untouched.
    old_ids = [e.id for e in Event.query.filter_by(organizer_id=organizer.id).all()]
    if old_ids:
        Booking.query.filter(Booking.event_id.in_(old_ids)).delete(synchronize_session=False)
        Event.query.filter(Event.id.in_(old_ids)).delete(synchronize_session=False)
    db.session.commit()

    now = datetime.now(timezone.utc)
    today_local = to_local(now).date()
    created = []
    for title, venue, price, capacity, days, hour, fill in EVENTS:
        starts = from_local(datetime.combine(today_local + timedelta(days=days), time(hour, 0)))
        event = Event(organizer_id=organizer.id, title=title, venue=venue,
                      description=f"{title} at {venue}. A sample event for the demo.",
                      starts_at=starts, price=price, capacity=capacity,
                      seats_available=capacity)
        db.session.add(event)
        created.append((event, fill))
    db.session.flush()

    for event, fill in created:
        target = int(event.capacity * fill)
        sold = 0
        while sold < target:
            qty = min(random.randint(1, 4), target - sold)
            add_booking(random.choice(buyers), event, qty, now)
            sold += qty
        if target:
            for _ in range(random.randint(0, 2)):
                add_booking(random.choice(buyers), event, random.randint(1, 3), now, "cancelled")

    # A few bookings for the demo user, so "My bookings" is not empty.
    spare = [e for e, _ in created if e.seats_available >= 4]
    for event in spare[:3]:
        add_booking(demo_user, event, 2, now)
    if len(spare) > 3:
        add_booking(demo_user, spare[3], 1, now, "cancelled")

    db.session.commit()
    print(f"Created {len(created)} events and {Booking.query.count()} bookings.")
    print(f"Organizer login: {ORGANIZER} / {PASSWORD}")
    print(f"User login:      {DEMO_USER} / {PASSWORD}")