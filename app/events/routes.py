from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, abort, request
from flask_login import current_user
from sqlalchemy import or_, func
from app import db
from app.decorators import organizer_required
from app.events import bp
from app.events.forms import EventForm
from app.models import Event, Booking
from app.utils import from_local, to_local
from app.bookings.forms import BookingForm

PER_PAGE = 9

SORTS = {
    "soonest": (Event.starts_at.asc(), Event.id.asc()),
    "price_low": (Event.price.asc(), Event.starts_at.asc(), Event.id.asc()),
    "price_high": (Event.price.desc(), Event.starts_at.asc(), Event.id.asc()),
}


def owned_event_or_404(event_id):
    event = db.session.get(Event, event_id)
    if event is None or event.organizer_id != current_user.id:
        abort(404)  # other organizers' events look like they don't exist
    return event


@bp.route("/")
def list_events():
    q = request.args.get("q", "").strip()[:100]
    sort = request.args.get("sort", "soonest")
    if sort not in SORTS:
        sort = "soonest"
    only_available = request.args.get("available") == "1"
    page = request.args.get("page", 1, type=int)

    stmt = db.select(Event).where(Event.starts_at >= datetime.now(timezone.utc))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Event.title.ilike(like), Event.venue.ilike(like)))
    if only_available:
        stmt = stmt.where(Event.seats_available > 0)
    stmt = stmt.order_by(*SORTS[sort])

    events = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)

    if events.pages and page > events.pages:  # e.g. ?page=99, so go to the last real page
        return redirect(url_for("events.list_events", q=q or None,
                                sort=None if sort == "soonest" else sort,
                                available="1" if only_available else None,
                                page=events.pages))

    return render_template("events/list.html", events=events, q=q, sort=sort,
                           only_available=only_available)

@bp.route("/<int:event_id>")
def detail(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    form = BookingForm()
    form.quantity.choices = [(i, str(i)) for i in range(1, min(10, event.seats_available) + 1)]
    is_past = event.starts_at <= datetime.now(timezone.utc)
    return render_template("events/detail.html", event=event,
                           booking_form=form, is_past=is_past)

@bp.route("/mine")
@organizer_required
def mine():
    events = db.session.execute(
        db.select(Event).where(Event.organizer_id == current_user.id)
        .order_by(Event.starts_at.desc())
    ).scalars().all()
    return render_template("events/mine.html", events=events)


@bp.route("/new", methods=["GET", "POST"])
@organizer_required
def new():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            organizer_id=current_user.id,
            title=form.title.data.strip(),
            description=(form.description.data or "").strip() or None,
            venue=form.venue.data.strip(),
            starts_at=from_local(form.starts_at.data),
            price=form.price.data,
            capacity=form.capacity.data,
            seats_available=form.capacity.data,
        )
        db.session.add(event)
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/form.html", form=form, heading="Create an event",
                          cancel_url=url_for("events.mine"))


@bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@organizer_required
def edit(event_id):
    event = owned_event_or_404(event_id)
    form = EventForm(obj=event)

    if request.method == "GET":
        form.starts_at.data = to_local(event.starts_at).replace(tzinfo=None)

    if form.validate_on_submit():
        # Lock the row, so a booking can't slip in while we recalculate the seats.
        locked = db.session.execute(
            db.select(Event).where(Event.id == event.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
        booked = locked.capacity - locked.seats_available

        if form.capacity.data < booked:
            db.session.rollback()  # releases the lock
            form.capacity.errors = list(form.capacity.errors) + [
                f"Capacity can't be lower than the {booked} seats already booked."]
        else:
            locked.title = form.title.data.strip()
            locked.description = (form.description.data or "").strip() or None
            locked.venue = form.venue.data.strip()
            locked.starts_at = from_local(form.starts_at.data)
            locked.price = form.price.data
            locked.capacity = form.capacity.data
            locked.seats_available = form.capacity.data - booked
            db.session.commit()  # also releases the lock
            flash("Event updated.", "success")
            return redirect(url_for("events.detail", event_id=locked.id))

    return render_template("events/form.html", form=form, heading="Edit event",
                           cancel_url=url_for("events.detail", event_id=event_id))

@bp.route("/<int:event_id>/delete", methods=["POST"])
@organizer_required
def delete(event_id):
    event = owned_event_or_404(event_id)
    booking_count = db.session.scalar(
        db.select(func.count(Booking.id)).where(Booking.event_id == event.id))
    if booking_count:
        flash("This event already has bookings, so it can't be deleted.", "danger")
        return redirect(url_for("events.detail", event_id=event.id))
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "success")
    return redirect(url_for("events.mine"))