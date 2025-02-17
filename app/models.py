from flask_login import UserMixin
from app.db import get_db_connection

class User(UserMixin):
    """Класс пользователя"""
    def __init__(self, id, login, role, password):
        self.id = id
        self.login = login
        self.role = role
        self.password = password

    @staticmethod
    def get_by_id(user_id):
        """Получение пользователя по ID"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, login, role, password FROM visitor WHERE id = %s", (user_id,))
                user_data = cur.fetchone()
                return User(*user_data) if user_data else None

    @staticmethod
    def get_by_login(login):
        """Получение пользователя по логину"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, login, role, password FROM visitor WHERE login = %s", (login,))
                user_data = cur.fetchone()
                return User(*user_data) if user_data else None

class Student(User):
    """Класс студента"""
    def __init__(self, id, login, role, password, first_name, middle_name, lastname, studyform, stipend, group_number, record_number):
        super().__init__(id, login, role, password)
        self.first_name = first_name      # Имя
        self.middle_name = middle_name    # Отчество
        self.lastname = lastname          # Фамилия
        self.studyform = studyform
        self.stipend = stipend
        self.group_number = group_number  # Здесь номер группы (grouppanumber), а не ID
        self.record_number = record_number



    @staticmethod
    def get_by_id(visitor_id):
        """Получение студента по ID пользователя"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT v.id, v.login, v.role, v.password, s.second_name, s.study_form, s.stipend, s.grouppa_id, s.record_number
                    FROM student s
                    JOIN visitor v ON s.visitor_id = v.id
                    WHERE v.id = %s
                    """,
                    (visitor_id,))
                student_data = cur.fetchone()
                return Student(*student_data) if student_data else None

class Teacher(User):
    """Класс преподавателя"""
    def __init__(self, id, login, role, password, secondname, email, department):
        super().__init__(id, login, role, password)
        self.secondname = secondname
        self.email = email
        self.department = department

    @staticmethod
    def get_by_id(visitor_id):
        """Получение преподавателя по ID пользователя"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT v.id, v.login, v.role, v.password, t.second_name, t.email, t.department
                    FROM teacher t
                    JOIN visitor v ON t.visitor_id = v.id
                    WHERE v.id = %s
                    """,
                    (visitor_id,))
                teacher_data = cur.fetchone()
                return Teacher(*teacher_data) if teacher_data else None

class Subject(UserMixin):
    """Класс предмета"""
    def __init__(self, subjid, subjname):
        self.id = subjid
        self.name = subjname

