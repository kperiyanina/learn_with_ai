from core.models import PlanRequest, PlanWeek


def generate_plan(goal, level, weeks, hours_per_week) -> list[PlanWeek]:
    request = PlanRequest(goal, level, weeks, hours_per_week)
    plan = []

    topics = [
        "Основы и ключевые понятия",
        "Базовые инструменты",
        "Практика и закрепление",
        "Работа над небольшим проектом",
        "Продвинутые темы",
        "Итоговый проект",
    ]

    for week in range(1, request.weeks + 1):
        topic = topics[(week - 1) % len(topics)]

        tasks = [
            f"Изучить тему: {topic}",
            f"Выполнить практические упражнения по теме «{topic}»",
            "Закрепить материал на небольшом практическом задании",
        ]

        plan.append(PlanWeek(week, topic, request.hours_per_week, tuple(tasks)))

    return plan