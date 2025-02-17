
import logging
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user
from werkzeug.security import check_password_hash
from app import app
from app.forms import LoginForm
from app.loaders import load_user_by_login  # Функция загрузки пользователя

# Включаем логирование
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def login():
    logging.debug("Форма логина загружена!")  # Проверяем, вызывается ли функция

    form = LoginForm()
    if form.validate_on_submit():
        logging.debug(f"Данные из формы: login={form.username.data}, password={form.password.data}")

        user_data = load_user_by_login(form.username.data)  # Загружаем пользователя по логину

        if user_data:
            logging.debug(f"Пользователь найден в базе: {user_data.login}, роль: {user_data.role}")

        if user_data and check_password_hash(user_data.password, form.password.data):
            login_user(user_data)
            logging.info(f"Пользователь {user_data.login} вошел в систему!")

            if user_data.role == 'student':
                logging.debug("Перенаправление на страницу студента")
                return redirect(url_for('student'))
            elif user_data.role == 'teacher':
                logging.debug("Перенаправление на страницу преподавателя")
                return redirect(url_for('teacher'))
            else:
                logging.debug("Перенаправление на страницу администратора")
                return redirect(url_for('admin'))
        else:
            logging.warning("Ошибка: Неправильный логин или пароль!")
            flash('Неправильный логин или пароль', category='danger')

    return render_template('login.html', form=form)
