from flask import render_template
from flask_login import current_user
from app.dashboard import bp
from app.decorators import organizer_required
from app.reports import summary, event_report, tickets_per_day


@bp.route("/")
@organizer_required
def index():
    organizer_id = current_user.id
    daily = tickets_per_day(organizer_id)
    chart = {
        "labels": [r.day.strftime("%d %b") for r in daily],
        "values": [int(r.tickets) for r in daily],
    }
    return render_template("dashboard/index.html", kpi=summary(organizer_id),
                           events=event_report(organizer_id), chart=chart)