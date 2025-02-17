import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()


class Config(object):
    # Сервер базы данных
    DB_SERVER = os.environ.get('DB_SERVER')  # Например, localhost или IP-адрес

    # Имя базы данных
    DB_NAME = os.environ.get('DB_NAME')  # Название используемой базы данных

    # Имя пользователя для базы данных
    DB_USER = os.environ.get('DB_USER')  # Имя пользователя для подключения

    # Пароль пользователя для базы данных
    DB_PASSWORD = os.environ.get('DB_PASSWORD')  # Пароль пользователя базы данных

    # Порт подключения к базе данных
    DB_PORT = os.environ.get('DB_PORT')  # Порт подключения (обычно 5432 для PostgreSQL)

    # Секретный ключ приложения Flask
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Используется для безопасности сессий и CSRF
