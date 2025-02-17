from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, SelectMultipleField, DateField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import InputRequired, Length, DataRequired, Optional, Email


class LoginForm(FlaskForm):
    username = StringField('Login', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Login')

class StudUpdateForm(FlaskForm):
    first_name = StringField("Имя", validators=[DataRequired()])
    middle_name = StringField("Отчество")
    second_name = StringField("Фамилия", validators=[DataRequired()])
    studyForm = SelectField("Форма обучения", validators=[DataRequired()], choices=[])
    groupnumber = SelectField("Группа", validators=[DataRequired()], choices=[])
    stipend = StringField("Стипендия", validators=[DataRequired()])
    submit = SubmitField("Обновить")


class StudRegisterForm(FlaskForm):
    studlogin = StringField("Логин", validators=[DataRequired()])
    studpassword = PasswordField("Пароль", validators=[DataRequired()])
    first_name = StringField("Имя", validators=[DataRequired()])
    middle_name = StringField("Отчество")
    last_name = StringField("Фамилия", validators=[DataRequired()])
    studentid = StringField("Номер зачетной книжки", validators=[DataRequired()])
    studyForm = SelectField("Форма обучения", choices=[], validators=[DataRequired()])
    groupnumber = SelectField("Группа", choices=[], validators=[DataRequired()])
    submit = SubmitField("Зарегистрировать")

class TeachRegisterForm(FlaskForm):
    teacherlogin = StringField("Логин", validators=[DataRequired()])
    teacherpassword = PasswordField("Пароль", validators=[DataRequired()])
    first_name = StringField("Имя", validators=[DataRequired()])
    middle_name = StringField("Отчество")
    last_name = StringField("Фамилия", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    department = SelectField("Кафедра", choices=[], validators=[DataRequired()])
    subjects = SelectMultipleField("Предметы", choices=[], validators=[DataRequired()])
    submit = SubmitField("Зарегистрировать")


class TeachUpdateForm(FlaskForm):
    first_name = StringField("Имя", validators=[DataRequired()])
    middle_name = StringField("Отчество")  # Отчество может быть необязательным
    second_name = StringField("Фамилия", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    department = SelectField("Кафедра", choices=[], validators=[DataRequired()])
    subjects = SelectMultipleField("Предметы", choices=[])  # Выбор нескольких предметов
    groups = SelectMultipleField("Группы", choices=[])  # Выбор нескольких групп
    submit = SubmitField("Обновить")


class AddGroupForm(FlaskForm):
    institute = StringField('Институт', validators=[Length(max=255), Optional()])
    groupnumber = StringField('Номер группы', validators=[DataRequired(), Length(min=4, max=6)])
    admissionyear = StringField('Год поступления', validators=[DataRequired(), Length(min=4, max=4)])
    submit = SubmitField('Добавить')

class UpdateGroupForm(FlaskForm):
    groupnumber = StringField('Номер группы', validators=[DataRequired(), Length(max=255)])
    institute = StringField('Институт', validators=[Length(max=255), Optional()])
    admissionyear = IntegerField('Год поступления', validators=[DataRequired()])
    lider = SelectField('Староста', choices=[], coerce=lambda x: int(x) if x and x.isdigit() else None)  # ✅ Исправлено
    submit = SubmitField('Обновить')


class AddSubjectForm(FlaskForm):
    subjectname = StringField('Название предмета', validators=[DataRequired(), Length(max=40)])
    submit = SubmitField('Добавить')

class GroupForSubjectForm(FlaskForm):
    groups = SelectMultipleField('Группы', choices=[], validators=[InputRequired()])
    submit = SubmitField('Подтвердить')

class AddNewWorkForm(FlaskForm):
    name = StringField('Название работы', validators=[DataRequired(), Length(max=40)])
    subject = SelectField('Название предмета', choices=[])
    date = DateField('Дата проведения/крайний срок сдачи', validators=[DataRequired()])
    group = SelectField('Номер группы', choices=[], validators=[DataRequired()])
    type = SelectField('Тип работы', choices=[])
    submit = SubmitField('Добавить')

class UpdateWorkForm(FlaskForm):
    date = DateField('Дата проведения/крайний срок сдачи', validators=[DataRequired()])
    submit = SubmitField('Изменить')
class GroupForSubject(FlaskForm):  # Класс формы назначения групп преподавателю
    groups = SelectMultipleField('Группы', choices=[], validators=[InputRequired()])  # Поле для выбора групп
    submit = SubmitField('Подтвердить')  # Кнопка для подтверждения выбора групп

class GroupForTeacher(FlaskForm):  # Класс формы назначения групп преподавателю
    groups = SelectMultipleField('Группы', choices=[], validators=[InputRequired()])  # Поле для выбора групп
    submit = SubmitField('Подтвердить')  # Кнопка для подтверждения выбора групп