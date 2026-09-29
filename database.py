import sqlite3

from config import DATABASE_PATH
from auth import hash_password, validate_credentials, verify_password
from models import (
    LearningPlan,
    PlanRecord,
    ProfileRecord,
    TaskRecord,
    UserRecord,
)


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


def save_plan(
    goal,
    level,
    weeks,
    hours_per_week,
    plan: LearningPlan,
    user_id: int | None = None,
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

    result = cursor.fetchone()

    connection.close()

    total = result[0]
    completed = result[1] or 0

    if total == 0:
        return 0

    return completed / total