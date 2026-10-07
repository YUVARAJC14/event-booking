from app.models import Booking
from app.reports import summary, event_report
from tests.helpers import make_event
from tests.test_bookings import book, client_for


def test_dashboard_only_for_organizers(app, world):
    assert client_for(app, "a@test.com").get("/dashboard/").status_code == 403
    # an organizer with no events still gets a working page
    assert client_for(app, "org@test.com").get("/dashboard/").status_code == 200


def test_report_numbers_add_up(app, world):
    with app.app_context():
        big = make_event(world["org"], capacity=10, price=100, title="Big")
        small = make_event(world["org"], capacity=10, price=50, title="Small")
    a = client_for(app, "a@test.com")
    book(a, big, 3)    # revenue 300
    book(a, small, 2)  # revenue 100
    book(a, small, 1)  # revenue 50, cancelled below
    with app.app_context():
        cancel_id = Booking.query.filter_by(quantity=1).one().id
    a.post(f"/bookings/{cancel_id}/cancel")

    with app.app_context():
        kpi = summary(world["org"])
        assert kpi.revenue == 400
        assert kpi.tickets == 5
        assert kpi.cancelled == 1

        rows = event_report(world["org"])
        assert [r.title for r in rows] == ["Big", "Small"]
        assert [r.revenue_rank for r in rows] == [1, 2]
        assert rows[0].sold == 3