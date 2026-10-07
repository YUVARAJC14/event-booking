from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import User, Event

SAMPLES = [
    ("Rooftop Film Night", "The Terrace, Block C", 499, 50),
    ("Indie Music Fest", "Open Air Arena", 1499, 300),
    ("Stand-up Comedy Evening", "The Laugh Lounge", 699, 80),
    ("Startup Pitch Night", "Innovation Hub", 299, 120),
    ("Sunrise Yoga Session", "Lakeside Park", 199, 40),
    ("Photography Walk", "Old Town Square", 349, 25),
    ("Board Game Cafe Meetup", "Dice and Dragons Cafe", 149, 30),
    ("Classical Guitar Recital", "City Auditorium", 799, 150),
    ("Street Food Festival", "Riverside Grounds", 99, 500),
    ("Python Workshop for Beginners", "Tech Park, Hall 2", 0, 60),
    ("Art and Wine Evening", "Gallery 12", 1199, 45),
    ("Charity Fun Run", "Central Stadium", 250, 400),
]

app = create_app()
with app.app_context():
    organizer = User.query.filter_by(role="organizer").first()
    if organizer is None:
        raise SystemExit("Register an organizer account first, then run this again.")
    if Event.query.count() > 0:
        raise SystemExit("Events already exist, so nothing was added.")

    now = datetime.now(timezone.utc)
    for i, (title, venue, price, cap) in enumerate(SAMPLES, start=1):
        db.session.add(Event(
            organizer_id=organizer.id, title=title, venue=venue,
            description="Sample event for testing.",
            starts_at=now + timedelta(days=i * 3, hours=i),
            price=price, capacity=cap, seats_available=cap,
        ))
    db.session.commit()
    print(f"Added {len(SAMPLES)} events for {organizer.email}")