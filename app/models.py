from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"   # "user" is a reserved word in Postgres, so we avoid it
    __table_args__ = (
        CheckConstraint("role IN ('user', 'organizer')", name="ck_users_role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    events = db.relationship("Event", backref="organizer", lazy=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_organizer(self):
        return self.role == "organizer"


class Event(db.Model):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_events_capacity_positive"),
        CheckConstraint("seats_available >= 0", name="ck_events_seats_not_negative"),
        CheckConstraint("seats_available <= capacity", name="ck_events_seats_within_capacity"),
        CheckConstraint("price >= 0", name="ck_events_price_not_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    venue = db.Column(db.String(150), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    bookings = db.relationship("Booking", backref="event", lazy=True)


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 10", name="ck_bookings_quantity"),
        CheckConstraint("status IN ('confirmed', 'cancelled')", name="ck_bookings_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="confirmed")
    booking_code = db.Column(db.String(12), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))