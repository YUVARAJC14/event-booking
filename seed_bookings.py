import random
import secrets
from datetime import datetime, timedelta, timezone

from app import create_app, db
from app.models import User, Event, Booking

random.seed(7)
app = create_app()

with app.app_context():
    organizer = User.query.filter_by(role="organizer").first()
    if organizer is None:
        raise SystemExit("Register an organizer account first.")
    events = Event.query.filter_by(organizer_id=organizer.id).all()
    if not events:
        raise SystemExit("No events yet. Run seed.py or create some events first.")

    buyers = []
    for i in range(1, 6):
        email = f"demo.buyer{i}@example.com"
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, role="user")
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
        buyers.append(user)

    now = datetime.now(timezone.utc)
    made = 0
    for _ in range(40):
        event = random.choice(events)
        qty = random.randint(1, 4)
        if event.seats_available < qty:
            continue
        cancelled = random.random() < 0.15
        db.session.add(Booking(
            user_id=random.choice(buyers).id,
            event_id=event.id,
            quantity=qty,
            total_price=event.price * qty,
            status="cancelled" if cancelled else "confirmed",
            booking_code=secrets.token_hex(4).upper(),
            created_at=now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23)),
        ))
        if not cancelled:
            event.seats_available -= qty  # cancelled bookings have already given their seats back
        made += 1

    db.session.commit()
    print(f"Added {made} demo bookings for {organizer.email}'s events.")