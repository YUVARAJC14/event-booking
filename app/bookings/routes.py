import secrets
from datetime import datetime, timezone
from flask import redirect, url_for, flash, abort, render_template
from flask_login import login_required, current_user
from sqlalchemy import update
from sqlalchemy.orm import joinedload
from app import db, limiter
from app.bookings import bp
from app.bookings.forms import BookingForm
from app.models import Event, Booking

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, so codes are easy to read out


def new_booking_code():
    while True:
        code = "".join(secrets.choice(CODE_CHARS) for _ in range(8))
        if not db.session.query(Booking.id).filter_by(booking_code=code).first():
            return code


@bp.route("/")
@login_required
def history():
    bookings = db.session.execute(
        db.select(Booking)
        .where(Booking.user_id == current_user.id)
        .options(joinedload(Booking.event))  # fetch each event in the same query
        .order_by(Booking.created_at.desc())
    ).scalars().all()

    now = datetime.now(timezone.utc)
    upcoming = [b for b in bookings if b.status == "confirmed" and b.event.starts_at > now]
    upcoming.sort(key=lambda b: b.event.starts_at)
    upcoming_ids = {b.id for b in upcoming}
    past = [b for b in bookings if b.id not in upcoming_ids]
    return render_template("bookings/history.html", upcoming=upcoming, past=past)


@bp.route("/event/<int:event_id>", methods=["POST"])
@login_required
@limiter.limit("10 per minute", key_func=lambda: f"user:{current_user.get_id()}")
def create(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    back = redirect(url_for("events.detail", event_id=event_id))

    form = BookingForm()
    if not form.validate_on_submit():
        flash("Choose between 1 and 10 seats.", "danger")
        return back
    quantity = form.quantity.data

    if event.organizer_id == current_user.id:
        flash("You can't book your own event.", "danger")
        return back
    if event.starts_at <= datetime.now(timezone.utc):
        flash("This event has already started.", "danger")
        return back

    # Check the seats AND take them in one statement.
    row = db.session.execute(
        update(Event)
        .where(Event.id == event_id, Event.seats_available >= quantity)
        .values(seats_available=Event.seats_available - quantity)
        .returning(Event.price)
        .execution_options(synchronize_session=False)
    ).first()

    if row is None:  # no row updated, so there weren't enough seats
        db.session.rollback()
        flash("Not enough seats left for that many tickets.", "danger")
        return back

    booking = Booking(
        user_id=current_user.id,
        event_id=event_id,
        quantity=quantity,
        total_price=row.price * quantity,
        booking_code=new_booking_code(),
    )
    db.session.add(booking)
    db.session.commit()  # seats taken and booking saved together, or neither
    flash("Booking confirmed.", "success")
    return redirect(url_for("bookings.detail", booking_id=booking.id))


@bp.route("/<int:booking_id>")
@login_required
def detail(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.user_id != current_user.id:
        abort(404)  # you can only see your own bookings
    can_cancel = (booking.status == "confirmed"
                  and booking.event.starts_at > datetime.now(timezone.utc))
    return render_template("bookings/detail.html", booking=booking, can_cancel=can_cancel)


@bp.route("/<int:booking_id>/cancel", methods=["POST"])
@login_required
@limiter.limit("20 per minute", key_func=lambda: f"user:{current_user.get_id()}")
def cancel(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.user_id != current_user.id:
        abort(404)
    if booking.event.starts_at <= datetime.now(timezone.utc):
        flash("This event has already started, so the booking can't be cancelled.", "danger")
        return redirect(url_for("bookings.detail", booking_id=booking_id))

    # Step 1: mark it cancelled only if it is still confirmed.
    # A second click (or a second tab) finds nothing to update.
    row = db.session.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.status == "confirmed")
        .values(status="cancelled")
        .returning(Booking.quantity, Booking.event_id)
        .execution_options(synchronize_session=False)
    ).first()

    if row is None:
        db.session.rollback()
        flash("This booking was already cancelled.", "info")
        return redirect(url_for("bookings.history"))

    # Step 2: give the seats back, in the same transaction.
    db.session.execute(
        update(Event)
        .where(Event.id == row.event_id)
        .values(seats_available=Event.seats_available + row.quantity)
        .execution_options(synchronize_session=False)
    )
    db.session.commit()  # status change and seats returned together, or neither
    flash("Booking cancelled. Your seats were released.", "success")
    return redirect(url_for("bookings.history"))