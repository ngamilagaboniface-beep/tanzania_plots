from flask_wtf import FlaskForm
from wtforms import String_Field, PasswordField, TextAreaField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

class LoginForm(FlaskForm):
    username = String_Field('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class PasswordChangeForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])

class PlotForm(FlaskForm):
    title = String_Field('Property Title', validators=[DataRequired()])
    location = String_Field('Location (e.g. Goba)', validators=[DataRequired()])
    price = FloatField('Price (TZS)', validators=[DataRequired()])
    sqm_size = String_Field('Size (Sqm)', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Available', 'Available'), ('Sold', 'Sold')])
    description = TextAreaField('Full Description')
