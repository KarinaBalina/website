import psycopg
from app.config import Config

def get_db_connection():
    """Создает подключение к базе данных PostgreSQL"""
    return psycopg.connect(
        host=Config.DB_SERVER,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        dbname=Config.DB_NAME,
        port=Config.DB_PORT
    )
