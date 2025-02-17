from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app import app
from app.forms import StudRegisterForm, TeachRegisterForm
from app.db import get_db_connection

@app.route('/studentregister', methods=['GET', 'POST'])
def studentRegister():
    """ Регистрация студента """
    form = StudRegisterForm()

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute('SELECT DISTINCT grouppanumber FROM grouppa')
        grouppanumber = cur.fetchall()
        form.groupnumber.choices = [(grn[0], grn[0]) for grn in grouppanumber]

        cur.execute('SELECT DISTINCT study_form FROM student')
        studform = cur.fetchall()
        form.studyForm.choices = [(stdf[0], stdf[0]) for stdf in studform]

    if form.validate_on_submit():
        login = form.studlogin.data
        hashed_password = generate_password_hash(form.studpassword.data)
        first_name = form.first_name.data
        middle_name = form.middle_name.data
        last_name = form.last_name.data
        student_id = form.studentid.data
        study_form = form.studyForm.data
        group_number = form.groupnumber.data

        try:
            with get_db_connection() as con:
                cur = con.cursor()
                # Проверка наличия пользователя
                cur.execute("SELECT * FROM visitor WHERE login = %s", (login,))
                if cur.fetchone():
                    flash('Ошибка: пользователь уже существует', category='error')
                    return redirect(url_for('studentRegister'))

                # Проверка наличия студента по record_number
                cur.execute("SELECT * FROM student WHERE record_number = %s", (student_id,))
                if cur.fetchone():
                    flash('Ошибка: студент уже существует', category='error')
                    return redirect(url_for('studentRegister'))

                cur.execute("SELECT id FROM grouppa WHERE grouppanumber = %s", (group_number,))
                group = cur.fetchone()

                cur.execute("INSERT INTO visitor (login, password, role) VALUES (%s, %s, 'student')",
                            (login, hashed_password))
                con.commit()

                cur.execute("SELECT id FROM visitor WHERE login = %s", (login,))
                user_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO student (id, first_name, middle_name, second_name, record_number, study_form, grouppa_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, first_name, middle_name, last_name, student_id, study_form, group[0])
                )
                con.commit()

            flash("Студент успешно зарегистрирован!", "success")
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Ошибка при регистрации студента: {e}")
            flash("Ошибка при регистрации. Попробуйте снова.", "danger")

    return render_template('stud_register.html', form=form)

@app.route('/teacherregister', methods=['GET', 'POST'])
def teacherRegister():
    """ Регистрация преподавателя """
    form = TeachRegisterForm()

    with get_db_connection() as con:
        cur = con.cursor()

        # Получаем список кафедр
        cur.execute("SELECT DISTINCT department FROM teacher")
        departments = cur.fetchall()

        # Получаем список предметов
        cur.execute("SELECT DISTINCT subject_name FROM subject")
        subjects = cur.fetchall()

    # Заполняем варианты выбора
    form.subjects.choices = [(sub[0], sub[0]) for sub in subjects]
    form.department.choices = [(dep[0], dep[0]) for dep in departments]

    if form.validate_on_submit():
        login = form.teacherlogin.data
        hashed_password = generate_password_hash(form.teacherpassword.data)
        first_name = form.first_name.data
        middle_name = form.middle_name.data
        last_name = form.last_name.data
        email = form.email.data
        department = form.department.data
        selected_subjects = request.form.getlist('subjects')

        try:
            with get_db_connection() as con:
                cur = con.cursor()

                # Проверяем, существует ли пользователь с таким логином
                cur.execute("SELECT id FROM visitor WHERE login = %s", (login,))
                if cur.fetchone():
                    flash('Ошибка: пользователь уже существует', category='error')
                    return redirect(url_for('teacherRegister'))

                # Добавляем преподавателя в `visitor`
                cur.execute("INSERT INTO visitor (login, password, role) VALUES (%s, %s, 'teacher')",
                            (login, hashed_password))
                con.commit()

                # Получаем ID нового преподавателя
                cur.execute("SELECT id FROM visitor WHERE login = %s", (login,))
                user_id = cur.fetchone()[0]  # Теперь user_id доступен

                # Добавляем преподавателя в `teacher`
                cur.execute("""
                    INSERT INTO teacher (id, first_name, middle_name, second_name, email, department)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, first_name, middle_name, last_name, email, department))
                con.commit()

                # Связываем преподавателя с предметами
                for sub in selected_subjects:
                    cur.execute("SELECT id FROM subject WHERE subject_name = %s", (sub,))
                    sub_id = cur.fetchone()
                    if sub_id:
                        cur.execute("INSERT INTO subjectteacher (subject_id, teacher_id) VALUES (%s, %s)",
                                    (sub_id[0], user_id))

                con.commit()

            flash("Преподаватель успешно зарегистрирован!", "success")
            return redirect(url_for('teachers'))  # Возвращаемся к списку преподавателей

        except Exception as e:
            print(f"Ошибка при регистрации преподавателя: {e}")
            flash("Ошибка при регистрации. Попробуйте снова.", "danger")

    return render_template('teacher_register.html', form=form)
