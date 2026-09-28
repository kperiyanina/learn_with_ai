def generate_plan(goal, level, weeks, hours_per_week):
    plan = []

    topics = [
        "Основы и ключевые понятия",
        "Базовые инструменты",
        "Практика и закрепление",
        "Работа над небольшим проектом",
        "Продвинутые темы",
        "Итоговый проект",
    ]

    for week in range(1, weeks + 1):
        topic = topics[(week - 1) % len(topics)]

        tasks = [
            f"Изучить тему: {topic}",
            f"Выполнить практические упражнения по теме «{topic}»",
            "Закрепить материал на небольшом практическом задании",
        ]

        plan.append(
            {
                "week": week,
                "topic": topic,
                "hours": hours_per_week,
                "tasks": tasks,
            }
        )

    return plan