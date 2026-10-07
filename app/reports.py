from sqlalchemy import text
from app import db

SUMMARY_SQL = text("""
    SELECT
        COALESCE(SUM(b.total_price) FILTER (WHERE b.status = 'confirmed'), 0) AS revenue,
        COALESCE(SUM(b.quantity)    FILTER (WHERE b.status = 'confirmed'), 0) AS tickets,
        COUNT(b.id)                 FILTER (WHERE b.status = 'cancelled')     AS cancelled
    FROM events e
    LEFT JOIN bookings b ON b.event_id = e.id
    WHERE e.organizer_id = :oid
""")

EVENT_REPORT_SQL = text("""
    WITH per_event AS (
        SELECT e.id, e.title, e.starts_at, e.capacity,
               COALESCE(SUM(b.quantity)    FILTER (WHERE b.status = 'confirmed'), 0) AS sold,
               COALESCE(SUM(b.total_price) FILTER (WHERE b.status = 'confirmed'), 0) AS revenue
        FROM events e
        LEFT JOIN bookings b ON b.event_id = e.id
        WHERE e.organizer_id = :oid
        GROUP BY e.id, e.title, e.starts_at, e.capacity
    )
    SELECT id, title, starts_at, capacity, sold, revenue,
           ROUND(100.0 * sold / capacity) AS fill_pct,
           COALESCE(ROUND(100.0 * revenue / NULLIF(SUM(revenue) OVER (), 0)), 0) AS share_pct,
           RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
    FROM per_event
    ORDER BY revenue_rank, starts_at
""")

DAILY_SQL = text("""
    SELECT d::date AS day, COALESCE(x.tickets, 0) AS tickets
    FROM generate_series(CURRENT_DATE - 13, CURRENT_DATE, interval '1 day') AS d
    LEFT JOIN (
        SELECT b.created_at::date AS booked_on, SUM(b.quantity) AS tickets
        FROM bookings b
        JOIN events e ON e.id = b.event_id
        WHERE e.organizer_id = :oid
          AND b.status = 'confirmed'
          AND b.created_at >= CURRENT_DATE - 13
        GROUP BY b.created_at::date
    ) x ON x.booked_on = d::date
    ORDER BY day
""")


def summary(organizer_id):
    return db.session.execute(SUMMARY_SQL, {"oid": organizer_id}).one()


def event_report(organizer_id):
    return db.session.execute(EVENT_REPORT_SQL, {"oid": organizer_id}).all()


def tickets_per_day(organizer_id):
    return db.session.execute(DAILY_SQL, {"oid": organizer_id}).all()