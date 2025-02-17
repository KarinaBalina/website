
from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager

from app.config import Config

# Инициализация приложения Flask
app = Flask(__name__)

# Подключение Bootstrap для упрощённого создания интерфейса
bootstrap = Bootstrap5(app)

# Загрузка конфигурации приложения из объекта Config
app.config.from_object(Config)

# Настройка менеджера входа
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Перенаправление на страницу логина

# Импорт маршрутов
from app import route
from app import admin
from app import student
from app import teacher
from app import loaders
from app import config
from app import db
from app import forms
from app import models
from app import register
from app import logout
