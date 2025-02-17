from flask import render_template, redirect, url_for, flash, session, request
from flask_login import current_user, login_required
from app import app
from app.db import get_db_connection
from app.forms import StudUpdateForm
from app.loaders import load_student_by_id, allowed_file
import os
from flask import request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads/student_answers'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload_answer/<int:work_id>', methods=['GET', 'POST'])
@login_required
def upload_answer(work_id):
    """Студент загружает ответ на контрольную или лабораторную работу"""
    user_id = current_user.id

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не найден!', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран!', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Формируем безопасное имя файла
            filename = secure_filename(f"student_{user_id}_work_{work_id}.{file.filename.rsplit('.', 1)[1].lower()}")
            # Абсолютный путь для сохранения файла
            upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_folder, exist_ok=True)
            absolute_path = os.path.join(upload_folder, filename)
            file.save(absolute_path)
            # Относительный путь для хранения в БД
            relative_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')

            with get_db_connection() as con:
                cur = con.cursor()

                # Проверяем, есть ли работа в control_work или lab_work
                cur.execute("SELECT id FROM control_work WHERE id = %s", (work_id,))
                is_control_work = cur.fetchone()

                cur.execute("SELECT id FROM lab_work WHERE id = %s", (work_id,))
                is_lab_work = cur.fetchone()

                print(f"DEBUG: work_id={work_id}, is_control={is_control_work}, is_lab={is_lab_work}")

                if is_control_work is not None:
                    work_type = 'control'
                elif is_lab_work is not None:
                    work_type = 'lab'
                else:
                    flash(f"Ошибка: Работа с ID {work_id} не найдена в control_work и lab_work!", "danger")
                    return redirect(url_for('student'))

                # Вставляем запись в таблицу grades с относительным путем
                cur.execute("""
                    INSERT INTO grades (student_id, work_id, work_type, file_path, status, date_given)
                    VALUES (%s, %s, %s, %s, 'Ожидает проверки', NOW())
                    ON CONFLICT (student_id, work_id, work_type)
                    DO UPDATE SET file_path = EXCLUDED.file_path, status = 'Ожидает проверки', date_given = NOW();
                """, (user_id, work_id, work_type, relative_path))

                con.commit()
                flash('Ответ успешно загружен!', 'success')

            return redirect(url_for('student'))

    return render_template('upload_answer.html', work_id=work_id)

@app.route('/student')
@login_required
def student():
    student_id = current_user.get_id()
    user = load_student_by_id(student_id)
    if user is None:
        print('Студент не найден')
        return redirect(url_for('login'))
    else:
        # Если нужно загрузить дополнительные данные для студента (например, дисциплины, на которые он записан),
        # можно добавить соответствующую функцию, например load_courses_by_student_id(student_id)
        return render_template('student.html', user=user)




@app.route('/students')
@login_required
def students():
    if current_user.is_authenticated:
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT student.id, student.record_number, student.study_form, student.stipend, 
                       COALESCE(grouppa.grouppanumber, 'Нет группы') AS grouppanumber, 
                       TRIM(CONCAT_WS(' ', student.second_name, student.first_name, student.middle_name)) AS full_name
                FROM student 
                LEFT JOIN grouppa ON student.grouppa_id = grouppa.id
            """)
            students = cur.fetchall()

        return render_template('students_list.html', students=students)

@app.route('/update_student/<int:user_id>', methods=['GET', 'POST'])
@login_required
def update_student(user_id):
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM student WHERE id=%s', (user_id,))
        student_data = cur.fetchone()

        if not student_data:
            flash("Студент не найден", "danger")
            return redirect(url_for("students"))

        # student_data имеет следующий порядок индексов:
        # 0: id
        # 1: first_name
        # 2: middle_name
        # 3: second_name
        # 4: record_number
        # 5: study_form
        # 6: stipend
        # 7: grouppa_id

        # Получаем данные о группе студента
        grouppa_id = student_data[7]
        student_group = None
        if grouppa_id:
            cur.execute('SELECT grouppanumber FROM grouppa WHERE id=%s', (grouppa_id,))
            student_group = cur.fetchone()

        group_number = str(student_group[0]) if student_group else "Нет группы"

    # Инициализируем форму начальными данными
    form = StudUpdateForm(data={
        'first_name': student_data[1],
        'middle_name': student_data[2],
        'second_name': student_data[3],  # используем столбец second_name
        'studyForm': student_data[5],
        'groupnumber': group_number,
        'stipend': str(student_data[6])
    })
    form.studyForm.choices = [("Contract", "Контракт"), ("Budget", "Бюджет")]
    # Загрузка списка групп и форм обучения
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute('SELECT DISTINCT grouppanumber FROM grouppa')
        grouppanumber = cur.fetchall()
        form.groupnumber.choices = [("Нет группы", "Нет группы")] + [(str(grn[0]), str(grn[0])) for grn in grouppanumber]

        cur.execute('SELECT DISTINCT study_form FROM student')
        studyForm = cur.fetchall()
        form.studyForm.choices = [(str(stdf[0]), str(stdf[0])) for stdf in studyForm]

    if form.validate_on_submit():
        first_name = form.first_name.data.strip()
        middle_name = form.middle_name.data.strip()
        second_name = form.second_name.data.strip()
        study_form = form.studyForm.data.strip()
        groupnumber = form.groupnumber.data
        stipend = form.stipend.data

        # Проверка: студенты на контракте не могут получать стипендию
        if study_form == 'Contract' and float(stipend) > 0:
            flash('Ошибка: Студенты на контракте не могут получать стипендию.', 'danger')
            return redirect(url_for('update_student', user_id=user_id))

        with get_db_connection() as con:
            cur = con.cursor()

            # Определяем ID группы по её номеру
            if groupnumber == "Нет группы":
                group_id = None
            else:
                cur.execute("SELECT id FROM grouppa WHERE grouppanumber=%s", (groupnumber,))
                group = cur.fetchone()
                if not group:
                    flash("Ошибка: Группа не найдена!", "danger")
                    return redirect(url_for("update_student", user_id=user_id))
                group_id = group[0]

            cur.execute(
                """
                UPDATE student 
                SET grouppa_id = %s,
                    first_name = %s,
                    middle_name = %s,
                    second_name = %s,
                    study_form = %s,
                    stipend = %s
                WHERE id = %s
                """,
                (group_id, first_name, middle_name, second_name, study_form, stipend, user_id)
            )
            con.commit()

        flash("Данные студента успешно обновлены!", "success")
        return redirect(url_for("students"))

    return render_template('updatestudent.html', form=form, user_id=user_id)


@app.route('/group_list/<string:group_no>')
@login_required
def group_list(group_no):
    students = []

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM grouppa WHERE grouppanumber=%s", (group_no,))
        group = cur.fetchone()

        if not group:
            flash("Группа не найдена", "danger")
            return redirect(url_for("students"))

        cur.execute("SELECT id, second_name, study_form FROM student WHERE grouppa_id=%s", (group[0],))
        students = cur.fetchall()

    # Передаем предыдущий URL или страницу по умолчанию
    previous_url = request.referrer or url_for("students")

    return render_template('group_list.html', students=students, group=group_no, previous_url=previous_url)

@app.route('/grades_student')
@login_required
def grades_student():
    """Страница просмотра оценок студента"""
    user_id = current_user.id

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT subject.subject_name, work.cw_name, grades.grade, grades.status, grades.file_path, grades.id
            FROM grades
            JOIN control_work work ON grades.work_id = work.id
            JOIN subject ON work.subject_id = subject.id
            WHERE grades.student_id = %s
            UNION ALL
            SELECT subject.subject_name, work.lab_name, grades.grade, grades.status, grades.file_path, grades.id
            FROM grades
            JOIN lab_work work ON grades.work_id = work.id
            JOIN subject ON work.subject_id = subject.id
            WHERE grades.student_id = %s
        """, (user_id, user_id))
        grades = cur.fetchall()

    return render_template("grades_student.html", grades=grades)
