import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "Не найден GROQ_API_KEY. "
        "Проверь файл .env."
    )

client = Groq(api_key=api_key)


def generate_ai_plan(goal, level, weeks, hours_per_week):

    prompt = f"""
Ты — AI-помощник по планированию обучения.

Создай персональный учебный план.

Параметры пользователя:

Цель:
{goal}

Текущий уровень:
{level}

Продолжительность:
{weeks} недель

Доступное время:
{hours_per_week} часов в неделю

Требования:

1. Создай план ровно на {weeks} недель.
2. Для каждой недели укажи тему.
3. Для каждой недели создай от 3 до 5 конкретных учебных задач.
4. Задачи должны соответствовать цели и уровню пользователя.
5. Учитывай доступные {hours_per_week} часов в неделю.
6. Постепенно повышай сложность.
7. Последняя неделя должна включать практическое итоговое задание.
8. Не добавляй лишний текст.

Верни результат ТОЛЬКО в формате JSON:

{{
    "weeks": [
        {{
            "week": 1,
            "topic": "Название темы",
            "hours": {hours_per_week},
            "tasks": [
                "Задача 1",
                "Задача 2",
                "Задача 3"
            ]
        }}
    ]
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    content = response.choices[0].message.content

    # Убираем возможные markdown-обёртки
    content = content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    try:
        return json.loads(content)

    except json.JSONDecodeError:
        raise ValueError(
            "ИИ вернул некорректный JSON.\n\n"
            f"Ответ модели:\n{content}"
        )