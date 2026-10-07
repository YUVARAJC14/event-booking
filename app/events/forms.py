from datetime import datetime, timezone
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError
from app.utils import from_local

class EventForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=3, max=150)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    venue = StringField("Venue", validators=[DataRequired(), Length(max=150)])
    starts_at = DateTimeLocalField("Starts at", format="%Y-%m-%dT%H:%M",
                                   validators=[DataRequired()])
    price = DecimalField("Price per seat (₹)", places=2, default=0,
                         validators=[InputRequired(), NumberRange(min=0, max=100000)])
    capacity = IntegerField("Capacity (seats)",
                            validators=[InputRequired(), NumberRange(min=1, max=10000)])
    submit = SubmitField("Save event")

    def validate_starts_at(self, field):
        if from_local(field.data) <= datetime.now(timezone.utc):
            raise ValidationError("The event must start in the future.")