from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, EmailField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class AdminLoginForm(FlaskForm):
    email = EmailField("Correo Electrónico", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    captcha = IntegerField("Verificación", validators=[DataRequired()])


class TwoFAForm(FlaskForm):
    code = StringField(
        "Código de Seguridad",
        validators=[DataRequired(), Length(min=6, max=6)],
    )


class CreateUserForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=100)])
    email = EmailField("Correo", validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=8, max=128)])
    role = SelectField(
        "Rol",
        choices=[("admin", "Administrador"), ("super_admin", "Super Admin")],
        validators=[DataRequired()],
    )


class EditUserForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=100)])
    role = SelectField(
        "Rol",
        choices=[("admin", "Administrador"), ("super_admin", "Super Admin")],
        validators=[DataRequired()],
    )


class CreateBookForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=200)])
    author = StringField("Autor", validators=[DataRequired(), Length(max=150)])
    isbn = StringField("ISBN", validators=[Optional(), Length(max=20)])
    genre = StringField("Género", validators=[Optional(), Length(max=100)])
    year = IntegerField("Año", validators=[Optional(), NumberRange(min=1, max=2100)])
    publisher = StringField("Editorial", validators=[Optional(), Length(max=150)])
    total_copies = IntegerField("Ejemplares", validators=[DataRequired(), NumberRange(min=1)])
    description = TextAreaField("Descripción", validators=[Optional()])
    location = StringField("Ubicación", validators=[Optional(), Length(max=100)])


class EditBookForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=200)])
    author = StringField("Autor", validators=[DataRequired(), Length(max=150)])
    isbn = StringField("ISBN", validators=[Optional(), Length(max=20)])
    genre = StringField("Género", validators=[Optional(), Length(max=100)])
    year = IntegerField("Año", validators=[Optional(), NumberRange(min=1, max=2100)])
    publisher = StringField("Editorial", validators=[Optional(), Length(max=150)])
    total_copies = IntegerField("Ejemplares totales", validators=[DataRequired(), NumberRange(min=1)])
    available_copies = IntegerField("Ejemplares disponibles", validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField("Descripción", validators=[Optional()])
    location = StringField("Ubicación", validators=[Optional(), Length(max=100)])
