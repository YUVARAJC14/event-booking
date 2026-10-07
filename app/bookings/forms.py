from flask_wtf import FlaskForm
from wtforms import SelectField

class BookingForm(FlaskForm):
    quantity = SelectField("Seats", coerce=int,
                           choices=[(i, str(i)) for i in range(1, 11)], default=1)