from datetime import timezone, timedelta

# Event times are entered and shown in IST (UTC+5:30) and stored in UTC.
LOCAL_TZ = timezone(timedelta(hours=5, minutes=30), "IST")

def to_local(dt):
    return dt.astimezone(LOCAL_TZ)

def from_local(naive_dt):
    return naive_dt.replace(tzinfo=LOCAL_TZ)

def money(value):
    if value == 0:
        return "Free"
    if value == value.to_integral_value():
        return f"₹{value:,.0f}"
    return f"₹{value:,.2f}"