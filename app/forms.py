from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class UploadForm(FlaskForm):
    files = MultipleFileField("Files", validators=[DataRequired(message="Select at least one file.")])
    lab_name = StringField("Lab name", validators=[Optional(), Length(max=255)])
    batch_id = StringField("Batch ID", validators=[Optional(), Length(max=255)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Upload files")
