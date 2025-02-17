from flask import  flash, redirect, url_for
from flask_login import  logout_user
from app import app, login_manager
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя по ID для Flask-Login"""
    return User.get_by_id(user_id)

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы успешно вышли из аккаунта.', 'success')
    return redirect(url_for('login'))
