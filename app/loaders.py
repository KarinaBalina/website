from app import login_manager
from app.db import get_db_connection
from app.models import User, Student

def load_user_by_login(login):
    """Загрузка пользователя по логину"""
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT id, login, role, password FROM visitor WHERE login = %s", (login,))
        user = cur.fetchone()

        if user:
            return User(user[0], user[1], user[2], user[3])
    return None

@login_manager.user_loader
def load_user_by_id(user_id):
    """Загрузка пользователя по ID"""
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT id, login, role, password FROM visitor WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if user:
            return User(user[0], user[1], user[2], user[3])
    return None


def load_student_by_id(user_id):
    """Загрузка студента по ID"""
    with get_db_connection() as con:
        cur = con.cursor()
        # Выбираем студента по полю id, а не userid
        cur.execute("SELECT * FROM student WHERE id = %s", (user_id,))
        student = cur.fetchone()
        if student:
            # student: (id, first_name, middle_name, second_name, record_number, study_form, stipend, grouppa_id)
            group_id = student[7]
            if group_id:
                cur.execute("SELECT grouppanumber FROM grouppa WHERE id = %s", (group_id,))
                group_result = cur.fetchone()
                group_number = group_result[0] if group_result else "Нет группы"
            else:
                group_number = "Нет группы"
            return Student(
                student[0],       # id
                None,             # login (если не используется в таблице student)
                None,             # role
                None,             # password
                student[1],       # first_name
                student[2],       # middle_name
                student[3],       # lastname (second_name)
                student[5],       # study_form
                student[6],       # stipend
                group_number,     # group_number (номер группы)
                student[4]        # record_number
            )
    return None

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
def allowed_file(filename):
    """Проверяет допустимый тип файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def load_teacher_by_id(teacher_id):
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM teacher WHERE id = %s", (teacher_id,))
        return cur.fetchone()


def load_admin_by_id(user_id):
    """Загрузка администратора по ID"""
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM visitor WHERE id = %s", (user_id,))
        admin = cur.fetchone()
        if admin:
            return User(admin[0], admin[1], admin[2], admin[3])
    return None

def load_subject_by_id(teacher_id):
    """
    Функция возвращает список названий предметов, которые ведёт преподаватель с заданным teacher_id.
    """
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT subject.subject_name FROM subject "
            "JOIN subjectteacher ON subject.id = subjectteacher.subject_id "
            "WHERE subjectteacher.teacher_id = %s",
            (teacher_id,)
        )
        subjects = cur.fetchall()
    return [subject[0] for subject in subjects]

