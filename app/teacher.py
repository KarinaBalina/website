import psycopg2
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required
from app import app
from app.db import get_db_connection
from app.forms import UpdateWorkForm, AddNewWorkForm, TeachUpdateForm, GroupForTeacher
from app.loaders import load_teacher_by_id, load_subject_by_id


import os
from flask import send_file

@app.route('/download_answer/<int:grade_id>')
@login_required
def download_answer(grade_id):
    """Скачивание загруженного ответа студента"""
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT file_path FROM grades WHERE id = %s", (grade_id,))
        result = cur.fetchone()

    if result and result[0]:
        absolute_path = os.path.join(app.root_path, result[0])
        return send_file(absolute_path, as_attachment=True)
    else:
        flash("Файл не найден", "danger")
        # Если пользователь студент, перенаправляем его на grades_student, иначе на teacher
        if current_user.role == 'student':
            return redirect(url_for('grades_student'))
        else:
            return redirect(url_for('teacher'))

@app.route('/teacher')
@login_required
def teacher():
    teacher_id = current_user.get_id()
    user = load_teacher_by_id(teacher_id)
    if user is None:
        print('Преподаватель не найден')
        return redirect(url_for('login'))
    else:
        subjects = load_subject_by_id(teacher_id)
        return render_template('teacher.html', subjects=subjects, user=user)

@app.route('/groups_for_teacher/<int:id>', methods=['GET', 'POST'])
@login_required
def groups_for_teacher(id):
    form = GroupForTeacher()

    with get_db_connection() as con:
        cur = con.cursor()

        # Получаем предметы, которые ведёт преподаватель
        cur.execute("SELECT subject_id FROM subjectteacher WHERE teacher_id=%s", (id,))
        teacher_subjects = cur.fetchall()  # [(1,), (3,), ...]

        # Получаем **все** группы
        cur.execute("SELECT id, grouppanumber FROM grouppa")
        all_groups = cur.fetchall()  # [(7, "4243"), (8, "4141"), ...]

        # Получаем **группы, связанные с предметами преподавателя**
        linked_groups = set()
        for sub in teacher_subjects:
            cur.execute("SELECT grouppa_id FROM grouppasubject WHERE subject_id=%s", (sub[0],))
            linked_groups.update(gr[0] for gr in cur.fetchall())  # Добавляем ID группы

        # Заполняем форму: все группы, отмечаем привязанные
        form.groups.choices = [(group[1], group[1]) for group in all_groups]  # [(id, "4243"), (id, "4141")]
        form.groups.data = [group[1] for group in all_groups if group[0] in linked_groups]  # Только выбранные

    if form.validate_on_submit():
        selected_groups = request.form.getlist('groups')

        with get_db_connection() as con:
            cur = con.cursor()

            # Удаляем старые привязки преподавателя к группам
            cur.execute("DELETE FROM grouppateacher WHERE teacher_id=%s", (id,))

            for gr in selected_groups:
                # Получаем ID группы по её номеру
                cur.execute("SELECT id FROM grouppa WHERE grouppanumber=%s", (gr,))
                group = cur.fetchone()
                if group:
                    group_id = group[0]

                    # Привязываем преподавателя к группе
                    cur.execute("INSERT INTO grouppateacher (grouppa_id, teacher_id) VALUES (%s, %s)", (group_id, id))

                    # Для каждого предмета преподавателя проверяем, есть ли привязка к этой группе
                    for subject in teacher_subjects:
                        subject_id = subject[0]
                        cur.execute(
                            "SELECT 1 FROM grouppasubject WHERE subject_id=%s AND grouppa_id=%s",
                            (subject_id, group_id)
                        )
                        existing = cur.fetchone()
                        if not existing:
                            cur.execute(
                                "INSERT INTO grouppasubject (grouppa_id, subject_id) VALUES (%s, %s)",
                                (group_id, subject_id)
                            )
            con.commit()

        flash("Группы назначены и предметы автоматически привязаны!", "success")
        return redirect(url_for('teachers'))

    return render_template('groups_for_teacher.html', form=form, id=id)


@app.route('/update_teacher/<int:user_id>', methods=['GET', 'POST'])
@login_required
def update_teacher(user_id):
    with get_db_connection() as con:
        cur = con.cursor()

        # Извлекаем данные преподавателя
        cur.execute("""
            SELECT id, first_name, middle_name, second_name, email, department
            FROM teacher
            WHERE id = %s
        """, (user_id,))
        teacher_data = cur.fetchone()

        if not teacher_data:
            flash("Преподаватель не найден!", "danger")
            return redirect(url_for('teachers'))

        # Загружаем предметы преподавателя
        cur.execute("""
            SELECT subject_name
            FROM subject
            JOIN subjectteacher ON subject.id = subjectteacher.subject_id
            WHERE subjectteacher.teacher_id = %s
        """, (user_id,))
        assigned_subjects = [sub[0] for sub in cur.fetchall()]

        # Загружаем группы преподавателя
        cur.execute("""
            SELECT grouppa.grouppanumber
            FROM grouppa
            JOIN grouppateacher ON grouppa.id = grouppateacher.grouppa_id
            WHERE grouppateacher.teacher_id = %s
        """, (user_id,))
        assigned_groups = [grp[0] for grp in cur.fetchall()]

    # Инициализация формы с текущими данными
    form = TeachUpdateForm(data={
        'first_name': teacher_data[1],
        'middle_name': teacher_data[2],
        'second_name': teacher_data[3],
        'email': teacher_data[4],
        'department': teacher_data[5],
        'subjects': assigned_subjects,
        'groups': assigned_groups
    })

    # Загружаем возможные кафедры, предметы и группы
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT DISTINCT department FROM teacher ORDER BY department")
        form.department.choices = [(dep[0], dep[0]) for dep in cur.fetchall()]

        cur.execute("SELECT DISTINCT subject_name FROM subject")
        form.subjects.choices = [(sub[0], sub[0]) for sub in cur.fetchall()]

        cur.execute("SELECT DISTINCT grouppanumber FROM grouppa")
        form.groups.choices = [(grp[0], grp[0]) for grp in cur.fetchall()]

    if form.validate_on_submit():
        first_name = form.first_name.data
        middle_name = form.middle_name.data
        second_name = form.second_name.data
        email = form.email.data
        department = form.department.data
        selected_subjects = form.subjects.data
        selected_groups = form.groups.data

        with get_db_connection() as con:
            cur = con.cursor()

            # Обновляем данные преподавателя
            cur.execute("""
                UPDATE teacher
                SET first_name=%s,
                    middle_name=%s,
                    second_name=%s,
                    email=%s,
                    department=%s
                WHERE id=%s
            """, (first_name, middle_name, second_name, email, department, user_id))

            # Обновляем привязку к предметам
            cur.execute("DELETE FROM subjectteacher WHERE teacher_id=%s", (user_id,))
            for sub_name in selected_subjects:
                cur.execute("SELECT id FROM subject WHERE subject_name=%s", (sub_name,))
                sub_id = cur.fetchone()
                if sub_id:
                    cur.execute(
                        "INSERT INTO subjectteacher (subject_id, teacher_id) VALUES (%s, %s)",
                        (sub_id[0], user_id)
                    )

            # Обновляем привязку к группам
            cur.execute("DELETE FROM grouppateacher WHERE teacher_id=%s", (user_id,))
            for group_number in selected_groups:
                cur.execute("SELECT id FROM grouppa WHERE grouppanumber=%s", (group_number,))
                group_id = cur.fetchone()
                if group_id:
                    cur.execute(
                        "INSERT INTO grouppateacher (grouppa_id, teacher_id) VALUES (%s, %s)",
                        (group_id[0], user_id)
                    )

            con.commit()

        flash("Данные преподавателя обновлены!", "success")
        return redirect(url_for('teachers'))

    return render_template("updateteacher.html", form=form, userid=user_id)

@app.route('/teachers')
@login_required
def teachers():
    with get_db_connection() as con:
        cur = con.cursor()
        # 1. Делаем запрос, выбирая столбцы в порядке: id, first_name, middle_name, second_name, email, department
        cur.execute("""
            SELECT id, first_name, middle_name, second_name, email, department
            FROM teacher
        """)
        teachers_data = cur.fetchall()

        teachers_list = []
        for row in teachers_data:
            # 2. Распаковываем кортеж в переменные в том же порядке
            teacher_id = row[0]
            first_name = row[1]
            middle_name = row[2]
            second_name = row[3]
            email = row[4]
            department = row[5]

            # 3. Формируем ФИО (Имя + Отчество + Фамилия)
            full_name = f"{first_name} {middle_name} {second_name}"

            # Получаем предметы (если у вас есть функция load_subject_by_id)
            subjects = load_subject_by_id(teacher_id)

            # Получаем группы, где участвует преподаватель
            cur.execute("""
                SELECT grouppanumber
                FROM grouppa
                JOIN grouppateacher ON grouppa.id = grouppateacher.grouppa_id
                WHERE grouppateacher.teacher_id = %s
            """, (teacher_id,))
            groups = cur.fetchall()

            # Преобразуем список групп в строку или указываем "None", если групп нет
            group_str = ', '.join(str(g[0]) for g in groups) if groups else "None"

            # 4. Складываем всё в кортеж в том порядке,
            #    в каком хотим отображать в шаблоне
            teachers_list.append((
                teacher_id,  # [0]
                full_name,  # [1]
                email,  # [2]
                department,  # [3]
                subjects,  # [4]
                group_str  # [5]
            ))

    return render_template("teachers_list.html", teachers=teachers_list)


@app.route('/add_work', methods=['GET', 'POST'])
@login_required
def add_work():
    user_id = current_user.id
    form = AddNewWorkForm()

    with get_db_connection() as con:
        cur = con.cursor()

        # Получаем список предметов, преподаваемых текущим пользователем
        cur.execute(
            "SELECT subject_name FROM subject "
            "JOIN subjectteacher ON subject.id = subjectteacher.subject_id "
            "WHERE subjectteacher.teacher_id = %s",
            (user_id,)
        )
        subjects = cur.fetchall()

        # Получаем список номеров групп, где учит текущий пользователь
        cur.execute(
            "SELECT grouppanumber FROM grouppa "
            "JOIN grouppateacher ON grouppa.id = grouppateacher.grouppa_id "
            "WHERE grouppateacher.teacher_id = %s",
            (user_id,)
        )
        groups = cur.fetchall()

    form.subject.choices = [(sub[0], sub[0]) for sub in subjects]
    form.group.choices = [(grp[0], grp[0]) for grp in groups]
    form.type.choices = [('Лабораторная', 'Лабораторная'), ('Контрольная', 'Контрольная')]

    if form.validate_on_submit():
        groupnumber = form.group.data
        subjectname = form.subject.data
        date = form.date.data
        name = form.name.data
        work_type = form.type.data  # Лабораторная или Контрольная

        with get_db_connection() as con:
            cur = con.cursor()

            # Получаем ID предмета и группы
            cur.execute("SELECT id FROM subject WHERE subject_name = %s", (subjectname,))
            subject = cur.fetchone()
            cur.execute("SELECT id FROM grouppa WHERE grouppanumber = %s", (groupnumber,))
            grouppa = cur.fetchone()

            if not subject or not grouppa:
                flash("Ошибка: Предмет или группа не найдены!", "danger")
                return redirect(url_for('add_work'))

            subject_id = subject[0]
            group_id = grouppa[0]

            if work_type == "Контрольная":
                cur.execute(
                    "INSERT INTO control_work(subject_id, group_id, cw_name) VALUES (%s, %s, %s) RETURNING id",
                    (subject_id, group_id, name)
                )
                control_work_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO eventdate(work_id, work_type, event_date) VALUES (%s, %s, %s)",
                    (control_work_id, 'control', date)  # ✅ Разрешенное значение!
                )
                con.commit()

            elif work_type == "Лабораторная":
                # Обработка лабораторной работы
                user = load_teacher_by_id(user_id)
                cur.execute("SELECT id FROM subject WHERE subject_name = %s", (subjectname,))
                subject = cur.fetchone()
                cur.execute("SELECT id FROM grouppa WHERE grouppanumber = %s", (groupnumber,))
                grouppa = cur.fetchone()
                # Вставляем запись в таблицу lab_work и получаем новый id
                cur.execute(
                    "INSERT INTO lab_work(subject_id, group_id, lab_name) VALUES (%s, %s, %s) RETURNING id",
                    (subject[0], grouppa[0], name)
                )
                lw_record = cur.fetchone()
                # Вставляем запись в таблицу deadline согласно схеме:
                # deadline: id | work_id | work_type | due_date
                cur.execute(
                    "INSERT INTO deadline(work_id, work_type, due_date) VALUES (%s, %s, %s)",
                    (lw_record[0], 'lab', date)
                )
                con.commit()
                return render_template("teacher.html", user=user)

        return render_template("teacher.html", user=load_teacher_by_id(user_id))

    else:
        return render_template("addwork.html", form=form)
@app.route('/updatework/<int:id>/<groupnumber>', methods=['GET', 'POST'])
@login_required
def updatework(id, groupnumber):
    form = UpdateWorkForm()
    user_id = current_user.id
    user = load_teacher_by_id(user_id)
    if form.validate_on_submit():
        new_date = form.date.data  # Новая дата, введённая в форме
        with get_db_connection() as con:
            cur = con.cursor()
            # Обновляем дату контрольной работы в eventdate, используя правильное имя столбца event_date
            cur.execute(
                "UPDATE eventdate SET event_date=%s WHERE work_id=%s",
                (new_date, id)
            )
            # Обновляем дату лабораторной работы в deadline (столбец due_date)
            cur.execute(
                "UPDATE deadline SET due_date=%s WHERE work_id=%s",
                (new_date, id)
            )
            con.commit()
        return render_template("teacher.html", user=user)
    else:
        return render_template("updatework.html", form=form)

@app.route('/deletework/<int:id>', methods=['GET', 'POST'])
@login_required
def deletework(id):
    user_id = current_user.id
    user = load_teacher_by_id(user_id)

    try:
        with get_db_connection() as con:
            cur = con.cursor()

            # Проверяем, существует ли контрольная работа
            cur.execute("SELECT id FROM control_work WHERE id = %s", (id,))
            control_work = cur.fetchone()

            if control_work:
                # Удаляем связанные записи в eventdate перед удалением работы
                cur.execute("DELETE FROM eventdate WHERE work_id = %s", (id,))
                cur.execute("DELETE FROM control_work WHERE id = %s", (id,))
                con.commit()
                flash("Контрольная работа успешно удалена!", "success")
                return redirect(url_for('subjects'))

            # Проверяем, существует ли лабораторная работа
            cur.execute("SELECT id FROM lab_work WHERE id = %s", (id,))
            lab_work = cur.fetchone()

            if lab_work:
                # Удаляем связанные записи в deadline перед удалением работы
                cur.execute("DELETE FROM deadline WHERE work_id = %s", (id,))
                cur.execute("DELETE FROM lab_work WHERE id = %s", (id,))
                con.commit()
                flash("Лабораторная работа успешно удалена!", "success")
                return redirect(url_for('subjects'))

            flash("Работа с таким ID не найдена!", "danger")

    except psycopg2.OperationalError as e:
        flash(f"Ошибка подключения к БД: {e}", "danger")
        return redirect(url_for('subjects'))
    except Exception as e:
        flash(f"Ошибка при удалении работы: {e}", "danger")
    finally:
        if con and not con.closed:
            con.close()  # ✅ Закрываем соединение, если оно еще открыто

    return redirect(url_for('subjects'))

@app.route('/grades_teacher')
@login_required
def grades_teacher():
    """Просмотр оценок преподавателем"""
    user_id = current_user.id
    grades_info = []

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT first_name, second_name, subject_name, work_name, grade, status, grade_id, file_path
            FROM (
                SELECT 
                    student.first_name AS first_name, 
                    student.second_name AS second_name, 
                    subject.subject_name AS subject_name, 
                    work.cw_name AS work_name, 
                    grades.grade AS grade, 
                    grades.status AS status, 
                    grades.id AS grade_id, 
                    grades.file_path AS file_path
                FROM grades
                JOIN control_work work ON grades.work_id = work.id
                JOIN subject ON work.subject_id = subject.id
                JOIN student ON grades.student_id = student.id
                JOIN subjectteacher ON subject.id = subjectteacher.subject_id
                WHERE subjectteacher.teacher_id = %s
                UNION ALL
                SELECT 
                    student.first_name AS first_name, 
                    student.second_name AS second_name, 
                    subject.subject_name AS subject_name, 
                    work.lab_name AS work_name, 
                    grades.grade AS grade, 
                    grades.status AS status, 
                    grades.id AS grade_id, 
                    grades.file_path AS file_path
                FROM grades
                JOIN lab_work work ON grades.work_id = work.id
                JOIN subject ON work.subject_id = subject.id
                JOIN student ON grades.student_id = student.id
                JOIN subjectteacher ON subject.id = subjectteacher.subject_id
                WHERE subjectteacher.teacher_id = %s
            ) AS all_grades
            ORDER BY first_name, subject_name, work_name;
        """, (user_id, user_id))
        grades = cur.fetchall()

        for grade in grades:
            full_name = grade[0] + " " + grade[1]
            grade_value = grade[4] if grade[4] is not None else "Не оценено"
            # Итоговый кортеж: (Полное имя, Предмет, Работа, Оценка, Статус, Grade ID, File Path)
            grades_info.append((full_name, grade[2], grade[3], grade_value, grade[5], grade[6], grade[7]))

    return render_template('grades_teacher.html', grades=grades_info)

@app.route('/update_grade/<int:grade_id>', methods=['GET', 'POST'])
@login_required
def update_grade(grade_id):
    """Редактирование оценки преподавателем"""
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT grade, status FROM grades WHERE id = %s", (grade_id,))
        grade_record = cur.fetchone()
        if not grade_record:
            flash("Ошибка: Оценка не найдена!", "danger")
            return redirect(url_for('grades_teacher'))
        current_grade, current_status = grade_record

    if request.method == 'POST':
        new_grade = request.form.get('grade')
        new_status = request.form.get('status')
        if not new_grade or not new_status:
            flash("Ошибка: Заполните все поля!", "danger")
            return redirect(url_for('update_grade', grade_id=grade_id))
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE grades
                SET grade = %s, status = %s
                WHERE id = %s
            """, (new_grade, new_status, grade_id))
            con.commit()
        flash("Оценка обновлена!", "success")
        return redirect(url_for('grades_teacher'))

    return render_template('grades_student.html', grade_id=grade_id, current_grade=current_grade, current_status=current_status)



@app.route('/set_grade', methods=['POST'])
@login_required
def set_grade():
    if current_user.role != "teacher":
        return redirect(url_for("index"))

    student_id = request.form.get("student_id")
    work_id = request.form.get("work_id")
    work_type = request.form.get("work_type")
    grade = request.form.get("grade")
    status = request.form.get("status")

    if not student_id or not work_id or not grade or not status:
        flash("Ошибка: Заполните все поля!", "danger")
        return redirect(url_for("grades_teacher"))

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO grades (student_id, work_id, work_type, grade, status) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (student_id, work_id, work_type) DO UPDATE SET grade = EXCLUDED.grade, status = EXCLUDED.status",
            (student_id, work_id, work_type, grade, status)
        )
        con.commit()

    flash("Оценка и статус успешно обновлены!", "success")
    return redirect(url_for("grades_teacher"))


@app.route('/performance')
@login_required
def performance():
    """Страница общей успеваемости студентов и групп"""
    if current_user.role != "teacher":
        return redirect(url_for("index"))

    user_id = current_user.id

    with get_db_connection() as con:
        cur = con.cursor()

        # 🔹 Получаем ID предметов, которые ведёт преподаватель
        cur.execute("""
            SELECT subject.id 
            FROM subject
            JOIN subjectteacher ON subject.id = subjectteacher.subject_id 
            WHERE subjectteacher.teacher_id = %s
        """, (user_id,))
        subjects = cur.fetchall()

        # Преобразуем в список ID
        subject_ids = [sub[0] for sub in subjects]

        if not subject_ids:
            flash("Вы не ведёте ни одного предмета.", "warning")
            return redirect(url_for("teacher"))

        # 🔹 Получаем средние оценки студентов, которых учит преподаватель
        cur.execute("""
            SELECT student.id, student.first_name, student.second_name, 
                   ROUND(AVG(grades.grade), 2) AS avg_grade
            FROM grades
            JOIN student ON grades.student_id = student.id
            JOIN subjectteacher ON subjectteacher.subject_id = ANY(%s)
            WHERE grades.grade IS NOT NULL
            GROUP BY student.id, student.first_name, student.second_name;
        """, (subject_ids,))
        student_performance = cur.fetchall()

        # 🔹 Получаем среднюю успеваемость групп, которых учит преподаватель
        cur.execute("""
            SELECT grouppa.id, grouppa.grouppanumber, 
                   ROUND(AVG(grades.grade), 2) AS avg_grade
            FROM grades
            JOIN student ON grades.student_id = student.id
            JOIN grouppa ON student.grouppa_id = grouppa.id
            JOIN subjectteacher ON subjectteacher.subject_id = ANY(%s)
            WHERE grades.grade IS NOT NULL
            GROUP BY grouppa.id, grouppa.grouppanumber;
        """, (subject_ids,))
        group_performance = cur.fetchall()

    return render_template('performance.html', student_performance=student_performance, group_performance=group_performance)
