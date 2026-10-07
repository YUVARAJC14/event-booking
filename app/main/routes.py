from datetime import datetime, timezone
from flask import render_template
from app import db
from app.main import bp
from app.models import Event


@bp.route("/")
def index():
    upcoming = db.session.execute(
        db.select(Event)
        .where(Event.starts_at >= datetime.now(timezone.utc), Event.seats_available > 0)
        .order_by(Event.starts_at.asc(), Event.id.asc())
        .limit(3)
    ).scalars().all()
    return render_template("index.html", upcoming=upcoming)