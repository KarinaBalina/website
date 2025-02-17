from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import app
from app.db import get_db_connection
from app.forms import AddGroupForm, UpdateGroupForm, AddSubjectForm, GroupForTeacher
from app.loaders import load_admin_by_id, load_teacher_by_id

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    id = current_user.get_id()
    user = load_admin_by_id(id)
    if user is None:
        flash('Администратор не найден!', 'danger')
        return redirect(url_for('login'))
    return render_template('admin.html', user=user)


@app.route('/delete_group/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM grouppa WHERE id=%s", (group_id,))
        con.commit()
    flash('Группа успешно удалена!', 'success')
    return redirect(url_for('groups'))

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    with get_db_connection() as con:
        cur = con.cursor()

        # Удаляем связи предмета с преподавателями и группами
        cur.execute("DELETE FROM subjectteacher WHERE subject_id=%s", (subject_id,))
        cur.execute("DELETE FROM grouppasubject WHERE subject_id=%s", (subject_id,))

        # Удаляем сам предмет
        cur.execute("DELETE FROM subject WHERE id=%s", (subject_id,))

        con.commit()

    flash('Предмет успешно удален!', 'success')
    return redirect(url_for('subject_for_user'))

@app.route('/addgroup', methods=['GET', 'POST'])
@login_required
def addgroup():
    form = AddGroupForm()
    if form.validate_on_submit():
        groupnumber = form.groupnumber.data.strip()
        admissionyear = form.admissionyear.data
        institute = form.institute.data.strip() if form.institute.data else "Не указан"

        with get_db_connection() as con:
            cur = con.cursor()

            # Проверяем, есть ли уже такая группа
            cur.execute("SELECT 1 FROM grouppa WHERE grouppanumber = %s", (groupnumber,))
            existing_group = cur.fetchone()

            if existing_group:
                flash('Группа с таким номером уже существует!', 'danger')
                return redirect(url_for('addgroup'))

            # Если группы нет, добавляем
            cur.execute(
                'INSERT INTO grouppa (grouppanumber, admission_year, stud_number, institute) VALUES (%s, %s, %s, %s)',
                (groupnumber, admissionyear, 0, institute)
            )
            con.commit()

        flash('Группа успешно добавлена!', 'success')
        return redirect(url_for('admin'))

    return render_template('addgroup.html', form=form)


@app.route('/update_group/<int:group_id>', methods=['GET', 'POST'])
@login_required
def update_group(group_id):
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM grouppa WHERE id=%s", (group_id,))
        group_data = cur.fetchone()

        if not group_data:
            flash('Группа не найдена!', 'danger')
            return redirect(url_for('groups'))

        # Загружаем список студентов
        cur.execute('SELECT id, second_name FROM student WHERE grouppa_id=%s', (group_id,))
        lidername = cur.fetchall()

    # Заполняем форму с начальными значениями
    form = UpdateGroupForm(data={
        'groupnumber': str(group_data[1]) if group_data[1] else "",
        'institute': str(group_data[2]) if group_data[2] else "",
        'admissionyear': group_data[3] if group_data[3] is not None else 0,
    })

    # Заполняем список старост, включая "Нет старосты"
    form.lider.choices = [(None, 'Нет старосты')] + [(str(lid[0]), lid[1]) for lid in lidername]

    if form.validate_on_submit():
        groupnumber = form.groupnumber.data.strip() if form.groupnumber.data else ""
        institute = form.institute.data.strip() if form.institute.data else ""
        admissionyear = form.admissionyear.data
        lider_id = form.lider.data if form.lider.data is not None else None

        # Отладочный вывод
        print(f"DEBUG: groupnumber={groupnumber}, institute={institute}, admissionyear={admissionyear}, lider_id={lider_id}, group_id={group_id}")

        try:
            with get_db_connection() as con:
                cur = con.cursor()
                cur.execute(
                    'UPDATE grouppa SET grouppanumber = %s, institute = %s, admission_year = %s, starosta_id = %s WHERE id = %s',
                    (groupnumber, institute, admissionyear, lider_id, group_id)
                )
                con.commit()

                # Проверка, что данные обновлены
                cur.execute("SELECT * FROM grouppa WHERE id=%s", (group_id,))
                updated_group = cur.fetchone()
                print("Updated group data:", updated_group)

            flash('Группа успешно обновлена!', 'success')
            return redirect(url_for('groups'))

        except Exception as e:
            print(f"ERROR: {e}")
            flash(f'Ошибка обновления группы: {e}', 'danger')

    return render_template('updategroup.html', form=form)
@app.route('/groups')
@login_required
def groups():
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM grouppa")
        groups_data = cur.fetchall()

        groups_list = []
        for gr in groups_data:
            cur.execute("SELECT COUNT(*) FROM student WHERE grouppa_id=%s", (gr[0],))
            student_count = cur.fetchone()[0]

            lider_name = None
            if gr[5] is not None:  # Используем gr[5], так как starosta_id находится в 6-й колонке
                cur.execute("SELECT second_name FROM student WHERE id=%s", (gr[5],))
                lider = cur.fetchone()
                lider_name = lider[0] if lider else None

            groups_list.append((gr[0], gr[1], gr[3], student_count, lider_name))  # ✅ Исправлен порядок индексов

    # Обновляем данные перед рендерингом
    session['prev_url'] = request.url
    return render_template('groups_list.html', groups=groups_list)
@app.route('/subjects')
@login_required
def subjects():
    subject_info = []
    user_id = current_user.id

    if current_user.role == 'teacher':
        with get_db_connection() as con:
            cur = con.cursor()
            # Получаем предметы, которые ведёт преподаватель
            cur.execute(
                "SELECT subject.id, subject.subject_name FROM subject "
                "JOIN subjectteacher ON subject.id = subjectteacher.subject_id "
                "WHERE subjectteacher.teacher_id=%s",
                (user_id,)
            )
            subjects = cur.fetchall()

            for subject in subjects:
                # subject[0] = subject id, subject[1] = subject name

                # Получаем группы, связанные с данным предметом
                cur.execute("""
                    SELECT DISTINCT grouppa.id, grouppa.grouppanumber 
                    FROM grouppa 
                    LEFT JOIN grouppasubject ON grouppa.id = grouppasubject.grouppa_id 
                    LEFT JOIN lab_work ON grouppa.id = lab_work.group_id 
                    WHERE grouppasubject.subject_id = %s OR lab_work.subject_id = %s
                """, (subject[0], subject[0]))
                groups = cur.fetchall()

                for group in groups:
                    # Получаем номер группы по её id
                    cur.execute("SELECT grouppanumber FROM grouppa WHERE id=%s", (group[0],))
                    group_number = cur.fetchone()
                    group_number = group_number[0] if group_number else 'Неизвестно'

                    # ✅ Контрольные работы (исправлено дублирование)
                    cur.execute(
                        """
                        SELECT DISTINCT control_work.id, control_work.cw_name, eventdate.event_date
                        FROM control_work
                        JOIN eventdate ON eventdate.work_id = control_work.id
                        WHERE eventdate.work_type='control' AND control_work.subject_id=%s AND control_work.group_id=%s
                        ORDER BY eventdate.event_date
                        """,
                        (subject[0], group[0])
                    )
                    cws = cur.fetchall()
                    seen_cws = set()  # Для отслеживания уже добавленных работ

                    for cw in cws:
                        if cw[0] not in seen_cws:
                            subject_info.append((subject[1], group_number, cw[1], cw[2], cw[0], 'Контрольная'))
                            seen_cws.add(cw[0])
                    # Лабораторные работы (lab)
                    # Изменяем запрос, чтобы выбрать id лабораторной работы из lab_work
                    cur.execute(
                        "SELECT lw.id, lw.lab_name, d.due_date "
                        "FROM lab_work lw "
                        "JOIN deadline d ON d.work_id = lw.id "
                        "WHERE d.work_type='lab' AND lw.subject_id=%s AND lw.group_id=%s",
                        (subject[0], group[0])
                    )
                    labs = cur.fetchall()
                    for lab in labs:
                        # lab: (id, lab_name, due_date)
                        subject_info.append((subject[1], group_number, lab[1], lab[2], lab[0], 'lab'))

        return render_template('subject_list_teacher.html', subjects=subject_info)

    return redirect(url_for('login'))


@app.route('/addsubject', methods=['GET', 'POST'])
@login_required
def addsubject():
    form = AddSubjectForm()
    if form.validate_on_submit():
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute('INSERT INTO subject (subject_name) VALUES (%s) RETURNING id', (form.subjectname.data,))
            subject_id = cur.fetchone()[0]
            con.commit()
        return redirect(url_for('groups_for_subject', id=subject_id))
    return render_template('addsubject.html', form=form)


@app.route('/groups_for_subject/<int:id>', methods=['GET', 'POST'])
@login_required
def groups_for_subject(id):
    form = GroupForTeacher()
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT grouppanumber FROM grouppa")
        groups = cur.fetchall()
        form.groups.choices = [(gr[0], gr[0]) for gr in groups]

    if form.validate_on_submit():
        selected_groups = request.form.getlist('groups')
        with get_db_connection() as con:
            cur = con.cursor()
            for gr in selected_groups:
                cur.execute('SELECT id FROM grouppa WHERE grouppanumber=%s', (gr,))
                group = cur.fetchone()
                if group:
                    cur.execute('SELECT * FROM grouppasubject WHERE subject_id=%s AND grouppa_id=%s', (id, group[0]))
                    existing = cur.fetchone()
                    if not existing:
                        cur.execute('INSERT INTO grouppasubject (grouppa_id, subject_id) VALUES (%s, %s)', (group[0], id))
            con.commit()
        flash('Группы назначены!', 'success')
        return redirect(url_for('subjects'))

    return render_template('groups_for_subject.html', form=form, id=id)

@app.route('/subject_for_user', methods=['GET', 'POST'])
@login_required
def subject_for_user():
    subject_info = []
    user_id = current_user.id

    if current_user.role == 'teacher':
        user = load_teacher_by_id(user_id)
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT DISTINCT subject.subject_id, subject.subject_name FROM subject "
                "JOIN subjectteacher ON subject.subject_id = subjectteacher.subject_id "
                "WHERE teacher_id = %s",
                (user_id,))
            subjects = cur.fetchall()

            for subject in subjects:
                cur.execute("SELECT DISTINCT grouppa_id FROM grouppasubject WHERE subject_id = %s", (subject[0],))
                grouppa_ids = cur.fetchall()

                for group in grouppa_ids:
                    cur.execute(
                        "SELECT cw.cw_name, eventdate.date_, cw.idcw "
                        "FROM cw JOIN eventdate ON cw.idcw = eventdate.idcw "
                        "WHERE grouppa_id = %s AND cw.subject_id = %s",
                        (group[0], subject[0]))
                    cws = cur.fetchall()

                    cur.execute(
                        "SELECT lw.lw_name, deadline.date_, lw.idlw "
                        "FROM lw JOIN deadline ON lw.idlw = deadline.idlw "
                        "WHERE grouppa_id = %s AND lw.subject_id = %s",
                        (group[0], subject[0]))
                    lws = cur.fetchall()

                    cur.execute("SELECT grouppanumber FROM grouppa WHERE id = %s", (group[0],))
                    grouppanumber = cur.fetchone()
                    group = ', '.join(map(str, grouppanumber))

                    for cw in cws:
                        subject_info.append((subject[1], group, cw[0], cw[1], cw[2]))

                    for lw in lws:
                        subject_info.append((subject[1], group, lw[0], lw[1], lw[2]))

        return render_template('subject_list_teacher.html', subjects=subject_info, user=user)

    if current_user.role == "admin":
        with get_db_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM subject")
            subjects = cur.fetchall()
            subject_info = []

            for su in subjects:
                cur.execute(
                    "SELECT second_name FROM teacher "
                    "JOIN subjectteacher ON subjectteacher.teacher_id = teacher.id "
                    "WHERE subjectteacher.subject_id = %s", (su[0],))
                teachers = cur.fetchall()
                teacher_list = [te[0] for te in teachers]
                teachers = ', '.join(teacher_list)

                cur.execute(
                    "SELECT grouppanumber FROM grouppa "
                    "JOIN grouppasubject ON grouppasubject.grouppa_id = grouppa.id "
                    "WHERE grouppasubject.subject_id = %s",
                    (su[0],))
                groups = cur.fetchall()
                group_list = [gr[0] for gr in groups]
                group = ', '.join(group_list)

                subject_info.append((su[0], su[1], teachers, group))

        return render_template('subject_list_admin.html', subjects=subject_info)

    elif current_user.role == "student":
        with get_db_connection() as con:
            cur = con.cursor()

            # ✅ Получаем ID группы студента
            cur.execute("SELECT grouppa_id FROM student WHERE id = %s", (user_id,))
            group = cur.fetchone()

            if not group or not group[0]:
                flash("Вы не закреплены за группой. Обратитесь к администратору.", "danger")
                return redirect(url_for('student'))

            group_id = group[0]  # ID группы студента

            # ✅ Получаем дисциплины, привязанные к группе студента
            cur.execute("""
                SELECT subject.id, subject.subject_name 
                FROM subject 
                JOIN grouppasubject ON subject.id = grouppasubject.subject_id 
                WHERE grouppasubject.grouppa_id = %s
            """, (group_id,))
            subjects = cur.fetchall()

            if not subjects:
                flash("У вас пока нет дисциплин.", "warning")
                return redirect(url_for('student'))

            subject_info = []

            for sub in subjects:
                # ✅ Получаем преподавателей, которые ведут этот предмет
                cur.execute("""
                    SELECT DISTINCT teacher.second_name 
                    FROM teacher
                    JOIN subjectteacher ON teacher.id = subjectteacher.teacher_id
                    WHERE subjectteacher.subject_id = %s
                """, (sub[0],))
                teachers = cur.fetchall()
                teacher_names = ', '.join([t[0] for t in teachers]) if teachers else "Неизвестно"

                # ✅ Получаем контрольные работы, привязанные **только к группе студента**
                cur.execute("""
                    SELECT control_work.id, control_work.cw_name, eventdate.event_date 
                    FROM control_work
                    JOIN eventdate ON control_work.id = eventdate.work_id 
                    WHERE control_work.subject_id = %s AND control_work.group_id = %s
                """, (sub[0], group_id))
                cws = cur.fetchall()

                for cw in cws:
                    subject_info.append((sub[1], teacher_names, cw[1], cw[2], cw[0]))  # ✅ Добавлен ID работы

                # ✅ Получаем лабораторные работы, привязанные **только к группе студента**
                cur.execute("""
                    SELECT lab_work.id, lab_work.lab_name, deadline.due_date 
                    FROM lab_work
                    JOIN deadline ON lab_work.id = deadline.work_id 
                    WHERE lab_work.subject_id = %s AND lab_work.group_id = %s
                """, (sub[0], group_id))
                labs = cur.fetchall()

                for lab in labs:
                    subject_info.append((sub[1], teacher_names, lab[1], lab[2], lab[0]))  # ✅ Добавлен ID работы

        return render_template('subject_list_student.html', subjects=subject_info)

    return redirect(url_for('login'))


@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute('SELECT role FROM visitor WHERE id = %s', (user_id,))
        user_role = cur.fetchone()

        if user_role:
            user_role = user_role[0]  # Извлекаем строку из кортежа
            cur.execute("DELETE FROM visitor WHERE id=%s", (user_id,))

            if user_role == 'student':
                cur.execute('DELETE FROM student WHERE id=%s', (user_id,))
                con.commit()
                return redirect(url_for('students'))
            elif user_role == 'teacher':
                cur.execute('DELETE FROM teacher WHERE id=%s', (user_id,))
                con.commit()
                return redirect(url_for('teachers'))

        con.commit()

    flash('Пользователь удалён!', 'success')
    return redirect(url_for('admin'))
