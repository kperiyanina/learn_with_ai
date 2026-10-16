import sqlite3
import json
from urllib.parse import urlparse

from core.config import DATABASE_PATH
from core.models import (
    LearningBlockRecord,
    LearningPlan,
    MaterialRecord,
    PlanRecord,
    ProfileRecord,
    TaskRecord,
    UserRecord,
)
from security.passwords import hash_password, validate_credentials, verify_password

QUIZ_PASS_PERCENT = 0.7


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            level TEXT NOT NULL,
            weeks INTEGER NOT NULL,
            hours_per_week INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            topic TEXT NOT NULL,
            task TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            display_name TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT 'Начинающий',
            hours_per_week INTEGER NOT NULL DEFAULT 5,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_diagnostics (
            plan_id INTEGER PRIMARY KEY,
            interests TEXT NOT NULL DEFAULT '',
            preferred_format TEXT NOT NULL DEFAULT 'Смешанный формат',
            available_days TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            task_id INTEGER,
            week INTEGER,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            material_type TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            is_favorite INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            topic TEXT NOT NULL,
            theory TEXT NOT NULL,
            quiz_json TEXT NOT NULL,
            resources_json TEXT NOT NULL DEFAULT '[]',
            task_guides_json TEXT NOT NULL DEFAULT '[]',
            theory_completed INTEGER NOT NULL DEFAULT 0,
            quiz_completed INTEGER NOT NULL DEFAULT 0,
            quiz_last_score INTEGER,
            quiz_total_questions INTEGER,
            quiz_attempts INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(plan_id, week),
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_block_quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            passed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)
    block_columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(learning_blocks)").fetchall()
    }
    if "task_guides_json" not in block_columns:
        cursor.execute(
            "ALTER TABLE learning_blocks ADD COLUMN task_guides_json TEXT NOT NULL DEFAULT '[]'"
        )

    plan_columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(plans)").fetchall()
    }
    if "user_id" not in plan_columns:
        cursor.execute(
            "ALTER TABLE plans ADD COLUMN user_id INTEGER REFERENCES users(id)"
        )

    connection.commit()
    connection.close()


def register_user(email: str, password: str) -> UserRecord:
    validate_credentials(email, password)
    salt, password_hash = hash_password(password)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, password_salt, password_hash)
            VALUES (?, ?, ?)
            """,
            (email.strip().lower(), salt, password_hash),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO profiles (user_id) VALUES (?)",
            (user_id,),
        )
        connection.commit()
        return UserRecord(user_id, email.strip().lower())
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ValueError("Пользователь с такой почтой уже зарегистрирован.") from error
    finally:
        connection.close()


def authenticate_user(email: str, password: str) -> UserRecord:
    validate_credentials(email, password)
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT id, email, password_salt, password_hash
            FROM users
            WHERE email = ? COLLATE NOCASE
            """,
            (email.strip(),),
        ).fetchone()
    finally:
        connection.close()

    if row is None or not verify_password(password, row[2], row[3]):
        raise ValueError("Неверная электронная почта или пароль.")
    return UserRecord(row[0], row[1])


def get_profile(user_id: int) -> ProfileRecord:
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT user_id, display_name
            FROM profiles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("Профиль пользователя не найден.")
    return ProfileRecord(*row)


def update_profile(
    user_id: int,
    display_name: str,
) -> None:
    if not display_name.strip():
        raise ValueError("Укажите имя или название профиля.")

    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE profiles
            SET display_name = ?
            WHERE user_id = ?
            """,
            (display_name.strip(), user_id),
        )
        connection.commit()
    finally:
        connection.close()


def claim_legacy_plans(user_id: int) -> None:
    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE plans
            SET user_id = ?
            WHERE user_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM users WHERE id < ?
              )
            """,
            (user_id, user_id),
        )
        connection.commit()
    finally:
        connection.close()


def get_plan_preferred_format(
    plan_id: int,
    user_id: int | None = None,
) -> str:
    connection = get_connection()
    try:
        query = """
            SELECT d.preferred_format
            FROM plan_diagnostics d
            JOIN plans p ON p.id = d.plan_id
            WHERE d.plan_id = ?
        """
        params = [plan_id]
        if user_id is not None:
            query += " AND p.user_id = ?"
            params.append(user_id)
        row = connection.execute(query, params).fetchone()
        return row[0] if row else "Смешанный формат"
    finally:
        connection.close()


def save_plan(
    goal,
    level,
    weeks,
    hours_per_week,
    plan: LearningPlan,
    user_id: int | None = None,
    diagnostic=None,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO plans (
            goal,
            level,
            weeks,
            hours_per_week,
            user_id
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        goal,
        level,
        weeks,
        hours_per_week,
        user_id,
    ))

    plan_id = cursor.lastrowid

    for week in plan.weeks:
        for task in week.tasks:
            cursor.execute("""
                INSERT INTO tasks (
                    plan_id,
                    week,
                    topic,
                    task
                )
                VALUES (?, ?, ?, ?)
            """, (
                plan_id,
                week.week,
                week.topic,
                task
            ))

    if diagnostic is not None:
        connection.execute(
            """
            INSERT INTO plan_diagnostics (
                plan_id, interests, preferred_format, available_days
            ) VALUES (?, ?, ?, ?)
            """,
            (
                plan_id,
                diagnostic.interests,
                diagnostic.preferred_format,
                ",".join(diagnostic.available_days),
            ),
        )
    connection.commit()
    connection.close()

    return plan_id

def get_all_plans(user_id: int | None = None) -> list[PlanRecord]:
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT id, goal, level, weeks, hours_per_week
        FROM plans
    """
    params = ()
    if user_id is not None:
        query += " WHERE user_id = ?"
        params = (user_id,)
    query += " ORDER BY id DESC"
    cursor.execute(query, params)

    plans = cursor.fetchall()

    connection.close()

    return [PlanRecord(*plan) for plan in plans]


def get_plan_tasks(plan_id, user_id: int | None = None) -> list[TaskRecord]:
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT id, week, topic, task, completed
        FROM tasks
        WHERE plan_id = ?
    """
    params = [plan_id]
    if user_id is not None:
        query += " AND plan_id IN (SELECT id FROM plans WHERE user_id = ?)"
        params.append(user_id)
    query += " ORDER BY week, id"
    cursor.execute(query, params)

    tasks = cursor.fetchall()

    connection.close()

    return [
        TaskRecord(
            id=task[0],
            week=task[1],
            topic=task[2],
            task=task[3],
            completed=bool(task[4]),
        )
        for task in tasks
    ]

def update_task_status(task_id, completed, user_id: int | None = None):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        UPDATE tasks
        SET completed = ?
        WHERE id = ?
    """
    params = [int(completed), task_id]
    if user_id is not None:
        query += " AND plan_id IN (SELECT id FROM plans WHERE user_id = ?)"
        params.append(user_id)
    cursor.execute(query, params)

    connection.commit()
    connection.close()


def get_plan_progress(plan_id, user_id: int | None = None):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            COUNT(*) AS total,
            SUM(completed) AS completed
        FROM tasks
        WHERE plan_id = ?
    """
    params = [plan_id]
    if user_id is not None:
        query += " AND plan_id IN (SELECT id FROM plans WHERE user_id = ?)"
        params.append(user_id)
    cursor.execute(query, params)

    task_result = cursor.fetchone()
    material_query = """
        SELECT COUNT(*), COALESCE(SUM(completed), 0)
        FROM materials
        WHERE plan_id = ?
    """
    material_params = [plan_id]
    if user_id is not None:
        material_query += " AND plan_id IN (SELECT id FROM plans WHERE user_id = ?)"
        material_params.append(user_id)
    material_result = cursor.execute(material_query, material_params).fetchone()
    weeks_query = "SELECT weeks FROM plans WHERE id = ?"
    weeks_params = [plan_id]
    if user_id is not None:
        weeks_query += " AND user_id = ?"
        weeks_params.append(user_id)
    plan_result = cursor.execute(weeks_query, weeks_params).fetchone()
    weeks_count = plan_result[0] if plan_result else 0
    block_query = """
        SELECT
            COALESCE(SUM(theory_completed), 0),
            COALESCE(SUM(quiz_completed), 0)
        FROM learning_blocks
        WHERE plan_id = ?
    """
    block_params = [plan_id]
    if user_id is not None:
        block_query += " AND plan_id IN (SELECT id FROM plans WHERE user_id = ?)"
        block_params.append(user_id)
    block_result = cursor.execute(block_query, block_params).fetchone()

    connection.close()

    total = task_result[0] + material_result[0] + (weeks_count * 2)
    completed = (
        (task_result[1] or 0)
        + material_result[1]
        + block_result[0]
        + block_result[1]
    )

    if total == 0:
        return 0

    return completed / total


def get_next_tasks(plan_id: int, user_id: int, limit: int = 3) -> list[TaskRecord]:
    tasks = get_plan_tasks(plan_id, user_id)
    return [task for task in tasks if not task.completed][:limit]


def get_adaptive_recommendation(plan_id: int, user_id: int) -> str | None:
    plan = next(
        (item for item in get_all_plans(user_id) if item.id == plan_id),
        None,
    )
    hours = f" Уделите этому до {plan.hours_per_week} часов на этой неделе." if plan else ""
    for block in sorted(get_plan_learning_blocks(plan_id, user_id), key=lambda item: item.week):
        if not block.theory_completed:
            return f"Изучите теорию в блоке недели {block.week}.{hours}"
        if not block.quiz_passed:
            if block.quiz_attempts:
                return (
                    f"Повторите тест в блоке недели {block.week}: "
                    f"последний результат {block.quiz_last_score}/"
                    f"{block.quiz_total_questions}.{hours}"
                )
            return f"Пройдите тест в блоке недели {block.week}.{hours}"
    materials = get_plan_materials(plan_id, user_id)
    next_material = next((item for item in materials if not item.completed), None)
    if next_material is not None:
        return (
            f"Продолжите с материала «{next_material.title}» "
            f"(неделя {next_material.week}).{hours}"
        )
    next_task = get_next_tasks(plan_id, user_id, limit=1)
    if next_task:
        return f"Перейдите к задаче «{next_task[0].task}».{hours}"
    return None


def save_material(
    plan_id: int,
    title: str,
    url: str,
    material_type: str,
    tags: str = "",
    task_id: int | None = None,
    week: int | None = None,
    user_id: int | None = None,
) -> int:
    if not title.strip():
        raise ValueError("Название материала не может быть пустым.")
    parsed_url = urlparse(url.strip())
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Ссылка материала должна начинаться с http:// или https://.")
    if material_type not in {"Курс", "Статья", "Видео", "Книга", "Документация", "Тренажёр"}:
        raise ValueError("Выбран некорректный тип материала.")

    connection = get_connection()
    try:
        owner_query = "SELECT 1 FROM plans WHERE id = ?"
        owner_params = [plan_id]
        if user_id is not None:
            owner_query += " AND user_id = ?"
            owner_params.append(user_id)
        if connection.execute(owner_query, owner_params).fetchone() is None:
            raise ValueError("План не найден.")
        if task_id is not None:
            task_query = "SELECT 1 FROM tasks WHERE id = ? AND plan_id = ?"
            if connection.execute(task_query, (task_id, plan_id)).fetchone() is None:
                raise ValueError("Задача не найдена в выбранном плане.")
        cursor = connection.execute(
            """
            INSERT INTO materials (
                plan_id, task_id, week, title, url, material_type, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, task_id, week, title.strip(), url.strip(),
                material_type, tags.strip(),
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def get_plan_materials(
    plan_id: int,
    user_id: int | None = None,
) -> list[MaterialRecord]:
    connection = get_connection()
    try:
        query = """
            SELECT m.id, m.plan_id, m.task_id, m.week, m.title, m.url,
                   m.material_type, m.tags, m.is_favorite, m.completed
            FROM materials m
            JOIN plans p ON p.id = m.plan_id
            WHERE m.plan_id = ?
        """
        params = [plan_id]
        if user_id is not None:
            query += " AND p.user_id = ?"
            params.append(user_id)
        query += " ORDER BY m.week, m.id"
        rows = connection.execute(query, params).fetchall()
        return [
            MaterialRecord(
                id=row[0], plan_id=row[1], task_id=row[2], week=row[3],
                title=row[4], url=row[5], material_type=row[6], tags=row[7],
                is_favorite=bool(row[8]), completed=bool(row[9]),
            )
            for row in rows
        ]
    finally:
        connection.close()


def save_learning_block(
    plan_id: int,
    week: int,
    topic: str,
    theory: str,
    quiz: list[dict],
    resources: list[dict],
    task_guides: list[dict] | None = None,
    user_id: int | None = None,
) -> None:
    if week < 1:
        raise ValueError("Номер блока должен быть положительным.")
    if not topic.strip():
        raise ValueError("Тема блока не может быть пустой.")
    if not theory.strip():
        raise ValueError("Теория блока не может быть пустой.")
    if not isinstance(quiz, list) or not quiz:
        raise ValueError("Тест блока не может быть пустым.")
    task_guides = task_guides or []
    if not isinstance(task_guides, list):
        raise ValueError("Практические задачи блока указаны некорректно.")

    connection = get_connection()
    try:
        owner_query = "SELECT 1 FROM plans WHERE id = ?"
        owner_params = [plan_id]
        if user_id is not None:
            owner_query += " AND user_id = ?"
            owner_params.append(user_id)
        if connection.execute(owner_query, owner_params).fetchone() is None:
            raise ValueError("План не найден.")

        connection.execute(
            """
            INSERT INTO learning_blocks (
                plan_id,
                week,
                topic,
                theory,
                quiz_json,
                resources_json,
                task_guides_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plan_id, week)
            DO UPDATE SET
                topic = excluded.topic,
                theory = excluded.theory,
                quiz_json = excluded.quiz_json,
                resources_json = excluded.resources_json,
                task_guides_json = excluded.task_guides_json,
                theory_completed = 0,
                quiz_completed = 0,
                quiz_last_score = NULL,
                quiz_total_questions = NULL,
                quiz_attempts = 0,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                plan_id,
                week,
                topic.strip(),
                theory.strip(),
                json.dumps(quiz, ensure_ascii=False),
                json.dumps(resources, ensure_ascii=False),
                json.dumps(task_guides, ensure_ascii=False),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def get_learning_block(
    plan_id: int,
    week: int,
    user_id: int | None = None,
) -> LearningBlockRecord | None:
    connection = get_connection()
    try:
        query = """
            SELECT
                lb.plan_id,
                lb.week,
                lb.topic,
                lb.theory,
                lb.quiz_json,
                lb.resources_json,
                lb.task_guides_json,
                lb.theory_completed,
                lb.quiz_completed,
                lb.quiz_last_score,
                lb.quiz_total_questions,
                lb.quiz_attempts,
                COALESCE((
                    SELECT MAX(CAST(a.score AS REAL) / a.total_questions)
                    FROM learning_block_quiz_attempts a
                    WHERE a.plan_id = lb.plan_id AND a.week = lb.week
                ), 0),
                COALESCE((
                    SELECT a.total_questions
                    FROM learning_block_quiz_attempts a
                    WHERE a.plan_id = lb.plan_id AND a.week = lb.week
                    ORDER BY CAST(a.score AS REAL) / a.total_questions DESC, a.created_at DESC
                    LIMIT 1
                ), NULL),
                lb.quiz_completed
            FROM learning_blocks lb
            JOIN plans p ON p.id = lb.plan_id
            WHERE lb.plan_id = ? AND lb.week = ?
        """
        params = [plan_id, week]
        if user_id is not None:
            query += " AND p.user_id = ?"
            params.append(user_id)
        row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return LearningBlockRecord(
            plan_id=row[0],
            week=row[1],
            topic=row[2],
            theory=row[3],
            quiz=tuple(json.loads(row[4])),
            resources=tuple(json.loads(row[5])),
            task_guides=tuple(json.loads(row[6])),
            theory_completed=bool(row[7]),
            quiz_completed=bool(row[8]),
            quiz_last_score=row[9],
            quiz_total_questions=row[10],
            quiz_attempts=row[11],
            quiz_best_score=(
                round(row[12] * row[13]) if row[13] is not None else None
            ),
            quiz_best_total_questions=row[13],
            quiz_passed=bool(row[14]),
        )
    finally:
        connection.close()


def get_plan_learning_blocks(
    plan_id: int,
    user_id: int | None = None,
) -> list[LearningBlockRecord]:
    connection = get_connection()
    try:
        query = """
            SELECT
                lb.plan_id,
                lb.week,
                lb.topic,
                lb.theory,
                lb.quiz_json,
                lb.resources_json,
                lb.task_guides_json,
                lb.theory_completed,
                lb.quiz_completed,
                lb.quiz_last_score,
                lb.quiz_total_questions,
                lb.quiz_attempts,
                COALESCE((
                    SELECT MAX(CAST(a.score AS REAL) / a.total_questions)
                    FROM learning_block_quiz_attempts a
                    WHERE a.plan_id = lb.plan_id AND a.week = lb.week
                ), 0),
                COALESCE((
                    SELECT a.total_questions
                    FROM learning_block_quiz_attempts a
                    WHERE a.plan_id = lb.plan_id AND a.week = lb.week
                    ORDER BY CAST(a.score AS REAL) / a.total_questions DESC, a.created_at DESC
                    LIMIT 1
                ), NULL),
                lb.quiz_completed
            FROM learning_blocks lb
            JOIN plans p ON p.id = lb.plan_id
            WHERE lb.plan_id = ?
        """
        params = [plan_id]
        if user_id is not None:
            query += " AND p.user_id = ?"
            params.append(user_id)
        query += " ORDER BY lb.week"
        rows = connection.execute(query, params).fetchall()
        return [
            LearningBlockRecord(
                plan_id=row[0],
                week=row[1],
                topic=row[2],
                theory=row[3],
                quiz=tuple(json.loads(row[4])),
                resources=tuple(json.loads(row[5])),
                task_guides=tuple(json.loads(row[6])),
                theory_completed=bool(row[7]),
                quiz_completed=bool(row[8]),
                quiz_last_score=row[9],
                quiz_total_questions=row[10],
                quiz_attempts=row[11],
                quiz_best_score=(
                    round(row[12] * row[13]) if row[13] is not None else None
                ),
                quiz_best_total_questions=row[13],
                quiz_passed=bool(row[14]),
            )
            for row in rows
        ]
    finally:
        connection.close()


def mark_learning_block_theory_completed(
    plan_id: int,
    week: int,
    user_id: int | None = None,
) -> None:
    connection = get_connection()
    try:
        query = """
            UPDATE learning_blocks
            SET theory_completed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE plan_id = ? AND week = ?
              AND plan_id IN (SELECT id FROM plans
        """
        params = [plan_id, week]
        if user_id is None:
            query += ")"
        else:
            query += " WHERE user_id = ?)"
            params.append(user_id)
        cursor = connection.execute(query, params)
        if cursor.rowcount == 0:
            raise ValueError("Учебный блок не найден.")
        connection.commit()
    finally:
        connection.close()


def save_learning_block_quiz_result(
    plan_id: int,
    week: int,
    score: int,
    total_questions: int,
    user_id: int | None = None,
) -> None:
    if not isinstance(score, int) or not isinstance(total_questions, int):
        raise ValueError("Результат теста указан некорректно.")
    if total_questions < 1 or score < 0 or score > total_questions:
        raise ValueError("Результат теста указан некорректно.")

    connection = get_connection()
    try:
        query = """
            UPDATE learning_blocks
            SET
                quiz_completed = ?,
                quiz_last_score = ?,
                quiz_total_questions = ?,
                quiz_attempts = quiz_attempts + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE plan_id = ? AND week = ?
              AND plan_id IN (SELECT id FROM plans
        """
        passed = int(score / total_questions >= QUIZ_PASS_PERCENT)
        params = [passed, score, total_questions, plan_id, week]
        if user_id is None:
            query += ")"
        else:
            query += " WHERE user_id = ?)"
            params.append(user_id)
        cursor = connection.execute(query, params)
        if cursor.rowcount == 0:
            raise ValueError("Учебный блок не найден.")
        connection.execute(
            """
            INSERT INTO learning_block_quiz_attempts (
                plan_id, week, score, total_questions, passed
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (plan_id, week, score, total_questions, passed),
        )
        connection.commit()
    finally:
        connection.close()


def get_learning_block_quiz_attempts(
    plan_id: int,
    week: int,
    user_id: int | None = None,
) -> list[dict[str, int | bool | str]]:
    connection = get_connection()
    try:
        query = """
            SELECT a.score, a.total_questions, a.passed, a.created_at
            FROM learning_block_quiz_attempts a
            JOIN plans p ON p.id = a.plan_id
            WHERE a.plan_id = ? AND a.week = ?
        """
        params = [plan_id, week]
        if user_id is not None:
            query += " AND p.user_id = ?"
            params.append(user_id)
        query += " ORDER BY a.id DESC"
        rows = connection.execute(query, params).fetchall()
        return [
            {
                "score": row[0],
                "total_questions": row[1],
                "passed": bool(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]
    finally:
        connection.close()


def delete_week_materials(plan_id: int, week: int, user_id: int | None = None) -> None:
    connection = get_connection()
    try:
        owner_query = "SELECT 1 FROM plans WHERE id = ?"
        owner_params = [plan_id]
        if user_id is not None:
            owner_query += " AND user_id = ?"
            owner_params.append(user_id)
        if connection.execute(owner_query, owner_params).fetchone() is None:
            raise ValueError("План не найден.")
        connection.execute(
            "DELETE FROM materials WHERE plan_id = ? AND week = ?",
            (plan_id, week),
        )
        connection.commit()
    finally:
        connection.close()


def update_material_status(
    material_id: int,
    completed: bool | None = None,
    is_favorite: bool | None = None,
    user_id: int | None = None,
) -> None:
    updates = []
    params = []
    if completed is not None:
        updates.append("completed = ?")
        params.append(int(completed))
    if is_favorite is not None:
        updates.append("is_favorite = ?")
        params.append(int(is_favorite))
    if not updates:
        raise ValueError("Не указано изменение материала.")

    query = (
        f"UPDATE materials SET {', '.join(updates)} "
        "WHERE id = ? AND plan_id IN (SELECT id FROM plans"
    )
    params.append(material_id)
    if user_id is None:
        query += ")"
    else:
        query += " WHERE user_id = ?)"
        params.append(user_id)
    connection = get_connection()
    try:
        cursor = connection.execute(query, params)
        if cursor.rowcount == 0:
            raise ValueError("Материал не найден.")
        connection.commit()
    finally:
        connection.close()