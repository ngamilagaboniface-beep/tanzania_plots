from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, PasswordField, SubmitField, MultipleFileField
from wtforms.validators import DataRequired, EqualTo, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PlotForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price (TZS)', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    sqm_size = IntegerField('Size (Sq.m.)', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Available', 'Available'), ('Sold', 'Sold')], default='Available')
    images = MultipleFileField('Upload Images (select multiple)', validators=[Optional()])
    submit = SubmitField('Save Plot')

class PasswordChangeForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='New passwords must match')
    ])
    submit = SubmitField('Change Password')
