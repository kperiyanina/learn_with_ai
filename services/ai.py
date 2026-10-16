import json
import logging

from groq import Groq

from core.config import (
    AI_FALLBACK_ENABLED,
    AI_MAX_RETRIES,
    AI_TIMEOUT_SECONDS,
    GROQ_API_KEY,
    GROQ_MODEL,
)
from core.models import LearningDiagnostic, LearningPlan, PlanRequest
from services.planner import generate_plan

logger = logging.getLogger(__name__)


def generate_ai_plan(
    goal,
    level,
    weeks,
    hours_per_week,
    diagnostic: LearningDiagnostic | None = None,
) -> LearningPlan:
    request = PlanRequest(goal, level, weeks, hours_per_week)
    diagnostic = diagnostic or LearningDiagnostic()

    if not GROQ_API_KEY:
        return _fallback_plan(request, "не задан ключ AI-сервиса")

    prompt = _build_prompt(request, diagnostic)
    try:
        content = _request_plan(prompt)
        raw_plan = json.loads(_strip_json_fences(content))
        return LearningPlan.from_dict(
            raw_plan,
            expected_weeks=request.weeks,
            expected_hours=request.hours_per_week,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        logger.warning("ИИ вернул некорректный учебный план: %s", error)
        return _fallback_plan(request, "ИИ вернул некорректный ответ")
    except Exception as error:
        logger.warning("Ошибка запроса к AI-сервису: %s", error)
        return _fallback_plan(request, "AI-сервис временно недоступен")


def _build_prompt(
    request: PlanRequest,
    diagnostic: LearningDiagnostic,
) -> str:
    return f"""
Ты — AI-помощник по планированию обучения.

Создай персональный учебный план.

Параметры пользователя:

Цель:
{request.goal}

Текущий уровень:
{request.level}

Продолжительность:
{request.weeks} недель

Доступное время:
{request.hours_per_week} часов в неделю

Интересы и предпочтения:
{diagnostic.interests or "не указаны"}
Формат занятий:
{diagnostic.preferred_format}
Доступные дни:
{", ".join(diagnostic.available_days) or "не указаны"}

Требования:

1. Создай план ровно на {request.weeks} недель.
2. Для каждой недели укажи тему.
3. Для каждой недели создай от 3 до 5 конкретных учебных задач.
4. Задачи должны соответствовать цели и уровню пользователя.
5. Учитывай доступные {request.hours_per_week} часов в неделю.
6. Постепенно повышай сложность.
7. Последняя неделя должна включать практическое итоговое задание.
8. Не добавляй лишний текст.

Верни результат ТОЛЬКО в формате JSON:

{{
    "weeks": [
        {{
            "week": 1,
            "topic": "Название темы",
            "hours": {request.hours_per_week},
            "tasks": [
                "Задача 1",
                "Задача 2",
                "Задача 3"
            ]
        }}
    ]
}}
"""


def _request_plan(prompt: str) -> str:
    client = Groq(api_key=GROQ_API_KEY, timeout=AI_TIMEOUT_SECONDS)
    last_error = None
    for attempt in range(AI_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content or ""
        except Exception as error:
            last_error = error
            if attempt < AI_MAX_RETRIES:
                logger.warning(
                    "Сбой AI-запроса, повтор %s/%s",
                    attempt + 1,
                    AI_MAX_RETRIES,
                )
    raise RuntimeError("AI-запрос не выполнен.") from last_error


def _fallback_plan(request: PlanRequest, reason: str) -> LearningPlan:
    if not AI_FALLBACK_ENABLED:
        raise RuntimeError(
            "Не удалось получить учебный план от AI-сервиса. Попробуйте позже."
        )
    logger.info("Используется локальный генератор учебного плана: %s", reason)
    return LearningPlan(tuple(generate_plan(
        request.goal,
        request.level,
        request.weeks,
        request.hours_per_week,
    )))


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