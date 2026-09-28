from ai import generate_ai_plan

print("1. Файл запустился")

plan = generate_ai_plan(
    goal="Научиться Python для анализа данных",
    level="Начинающий",
    weeks=4,
    hours_per_week=5
)

print("2. AI ответил")
print(plan)

for week in plan["weeks"]:
    print()
    print(f"НЕДЕЛЯ {week['week']}")
    print(f"Тема: {week['topic']}")
    print(f"Часы: {week['hours']}")

    for task in week["tasks"]:
        print(f"  - {task}")

print("3. Готово")