import json
import logging

from groq import Groq

from core.config import GROQ_API_KEY, GROQ_MODEL
from core.models import LearningPlan, PlanRequest

logger = logging.getLogger(__name__)


def generate_ai_plan(goal, level, weeks, hours_per_week) -> LearningPlan:
    PlanRequest(goal, level, weeks, hours_per_week)

    if not GROQ_API_KEY:
        raise RuntimeError(
            "AI-сервис недоступен: не задан GROQ_API_KEY. "
            "Добавьте ключ в файл .env."
        )

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

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    content = _strip_json_fences(response.choices[0].message.content)

    try:
        raw_plan = json.loads(content)
    except json.JSONDecodeError as error:
        logger.error("ИИ вернул некорректный JSON")
        raise ValueError(
            "ИИ вернул некорректный JSON. Попробуйте повторить запрос."
        ) from error

    return LearningPlan.from_dict(
        raw_plan,
        expected_weeks=weeks,
        expected_hours=hours_per_week,
    )


def _strip_json_fences(content):
    content = (content or "").strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    return content