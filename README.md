# seatly: event booking with no double bookings

Browse events, book seats, cancel, and manage events as an organizer. The app is built so the
last seat can only be sold once, even when many people click at the same moment.

**Live demo:** LIVE-URL (free hosting sleeps when idle, so the first load can take about a minute)

| Role | Email | Password |
|---|---|---|
| Organizer | demo.organizer@example.com | DemoPass2026 |
| Attendee | demo.user@example.com | DemoPass2026 |

![Home](docs/home.png)
![Dashboard](docs/dashboard.png)

## Features
- Roles: attendees book and cancel, organizers create events and see a sales dashboard
- Search, sort, "hide sold out" and pagination on the events list
- Booking with seat counts, booking codes and a ticket page; cancelling returns the seats
- Organizer dashboard: revenue, tickets per day, events ranked by revenue (raw SQL: CTE, window functions)
- Rate limiting, CSRF protection, ownership checks, security headers

## The interesting problem: the last seat
A "read the seats, check, then write" booking flow oversells when many people book at once.
seatly takes the seats with a single statement:

```sql
UPDATE events SET seats_available = seats_available - :qty
WHERE id = :id AND seats_available >= :qty
```

Postgres locks the row, so a second buyer waits and then fails the `WHERE` check. The booking is saved
in the same transaction, and CHECK constraints are a second safety net. Cancelling is also safe against
double clicks (only the first cancel finds a `confirmed` booking). `race_test.py` fires 30 buyers at
5 seats at the same moment:

| Version | Bookings made | Result |
|---|---|---|
| Naive read, check, write | PASTE-YOUR-NUMBER | oversold |
| seatly's booking route | 5 | correct |

## Data model
```
users (id, email, password_hash, role)
events (id, organizer_id -> users, title, venue, starts_at, price, capacity, seats_available)
bookings (id, user_id -> users, event_id -> events, quantity, total_price, status, booking_code)
```

## Tech stack
Python, Flask, SQLAlchemy, PostgreSQL, Flask-Login, Flask-WTF, Flask-Limiter, Chart.js, pytest, gunicorn.
Hosted on Render (app) and Neon (database).

## Run it locally
```bash
git clone https://github.com/YOUR-USERNAME/event-booking.git
cd event-booking
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file:
```
SECRET_KEY=any-long-random-string
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/seatly
TEST_DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/seatly_test
```
Create both databases in Postgres, then:
```bash
python seed_demo.py   # optional demo data
python run.py
pytest                # tests (need the _test database)
python race_test.py   # the concurrency demo
```

## Design decisions
- **Atomic seat updates** instead of check-then-write (see above)
- **Row lock** (`FOR UPDATE`) when an organizer edits capacity, so a booking can't slip in mid-edit
- **Analytics in SQL**, including gap-free daily counts with `generate_series`
- **Separate test database** that the test setup refuses to use unless its name ends in `_test`
- **Ownership checks** on every booking and event route

## What I'd add next
Idempotency keys for bookings, payments, email confirmations, a POST-only logout, a Content Security
Policy, and Redis for rate-limit storage once there is more than one server.