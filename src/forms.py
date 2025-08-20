from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from wtforms.fields import DateField, DateTimeLocalField
from datetime import datetime
from src.models.user import User, Room
from src.utils.timezone_utils import get_brazil_now, is_in_past

# --- Login ---
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')


# --- Criar Usuário ---
class CreateUserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Administrador')
    submit = SubmitField('Criar Usuário')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este e-mail já está cadastrado.')


# --- Agendar Reunião ---
class MeetingForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    description = TextAreaField('Descrição', validators=[Optional()])

    start_datetime = DateTimeLocalField('Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_datetime = DateTimeLocalField('Término', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])

    participants = SelectMultipleField('Participantes', coerce=int, validators=[Optional()])
    room_id = SelectField('Sala', coerce=int, validators=[DataRequired()])

    is_recurring = BooleanField('Reunião Recorrente')
    recurrence_type = SelectField('Frequência', choices=[
        ('daily', 'Diária'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensal')
    ], validators=[Optional()])
    recurrence_end = DateField('Fim da Recorrência', validators=[Optional()])

    submit = SubmitField('Agendar Reunião')

    def __init__(self, *args, **kwargs):
        super(MeetingForm, self).__init__(*args, **kwargs)
        self.room_id.choices = [(r.id, r.name) for r in Room.query.filter_by(is_active=True).all()]
        self.participants.choices = [(u.id, u.username) for u in User.query.all()]

    def validate_end_datetime(self, end_datetime):
        if self.start_datetime.data and end_datetime.data:
            if end_datetime.data <= self.start_datetime.data:
                raise ValidationError('A hora de término deve ser posterior à hora de início.')
            if end_datetime.data.date() != self.start_datetime.data.date():
                raise ValidationError('A reunião deve começar e terminar no mesmo dia.')

    def validate_start_datetime(self, start_datetime):
        if start_datetime.data and is_in_past(start_datetime.data):
            raise ValidationError('A data e hora de início não pode ser no passado.')

    def validate_recurrence_end(self, recurrence_end):
        if self.is_recurring.data and not recurrence_end.data:
            raise ValidationError('Para reuniões recorrentes, é necessário definir o fim da recorrência.')
        if recurrence_end.data and self.start_datetime.data:
            recurrence_end_dt = datetime.combine(recurrence_end.data, datetime.min.time())
            if recurrence_end_dt <= self.start_datetime.data:
                raise ValidationError('O fim da recorrência deve ser posterior à data de início.')


# --- Editar Reunião ---
class EditMeetingForm(MeetingForm):
    edit_all_recurring = SelectField('Aplicar edição a:', choices=[
        ('this_only', 'Apenas esta reunião'),
        ('all_recurring', 'Todas as reuniões da série')
    ], validators=[Optional()])
    submit = SubmitField('Atualizar Reunião')

    def __init__(self, *args, **kwargs):
        meeting = kwargs.pop('obj', None)
        super(EditMeetingForm, self).__init__(*args, **kwargs)
        if meeting and meeting.participants:
            participant_names = [name.strip() for name in meeting.participants.split(',')]
            participant_ids = []
            for name in participant_names:
                user = User.query.filter_by(username=name).first()
                if user:
                    participant_ids.append(user.id)
            self.participants.data = participant_ids


# --- Trocar Senha ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Senha Atual', validators=[DataRequired()])
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Confirmar Nova Senha', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Alterar Senha')



# --- Esqueci minha Senha ---
class ForgotPasswordForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    submit = SubmitField("Redefinir Senha")




# --- Redefinir Senha ---
class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Confirmar Nova Senha', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Redefinir Senha')

