import sqlite3


DATABASE_NAME = "learnai.db"


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


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

    connection.commit()
    connection.close()


def save_plan(goal, level, weeks, hours_per_week, plan):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO plans (
            goal,
            level,
            weeks,
            hours_per_week
        )
        VALUES (?, ?, ?, ?)
    """, (
        goal,
        level,
        weeks,
        hours_per_week
    ))

    plan_id = cursor.lastrowid

    for week in plan:
        for task in week["tasks"]:
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
                week["week"],
                week["topic"],
                task
            ))

    connection.commit()
    connection.close()

    return plan_id

def get_all_plans():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, goal, level, weeks, hours_per_week
        FROM plans
        ORDER BY id DESC
    """)

    plans = cursor.fetchall()

    connection.close()

    return plans


def get_plan_tasks(plan_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, week, topic, task, completed
        FROM tasks
        WHERE plan_id = ?
        ORDER BY week, id
    """, (plan_id,))

    tasks = cursor.fetchall()

    connection.close()

    return tasks

def update_task_status(task_id, completed):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE tasks
        SET completed = ?
        WHERE id = ?
    """, (
        int(completed),
        task_id
    ))

    connection.commit()
    connection.close()


def get_plan_progress(plan_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(completed) AS completed
        FROM tasks
        WHERE plan_id = ?
    """, (plan_id,))

    result = cursor.fetchone()

    connection.close()

    total = result[0]
    completed = result[1] or 0

    if total == 0:
        return 0

    return completed / total