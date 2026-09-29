import streamlit as st
import logging

from ai import generate_ai_plan
from database import (
    init_database,
    save_plan,
    get_all_plans,
    get_plan_tasks,
    update_task_status,
    get_plan_progress,
)

logger = logging.getLogger(__name__)

# Инициализация базы данных
init_database()


# Настройка страницы
st.set_page_config(
    page_title="LearnAI",
    page_icon="🎓"
)


# Заголовок
st.title("🎓 LearnWithAI")
st.write("Персональный план обучения с помощью ИИ")


# Боковая навигация
page = st.sidebar.radio(
    "Раздел",
    [
        "🎯 Создать план",
        "📚 Мои планы"
    ]
)


# ============================================================
# СОЗДАНИЕ ПЛАНА
# ============================================================

if page == "🎯 Создать план":

    st.header("Создать учебный план")

    goal = st.text_input(
        "Чему вы хотите научиться?",
        placeholder="Например: Python для анализа данных"
    )

    level = st.selectbox(
        "Ваш текущий уровень",
        [
            "Начинающий",
            "Средний",
            "Продвинутый"
        ]
    )

    weeks = st.number_input(
        "Количество недель",
        min_value=1,
        max_value=12,
        value=4
    )

    hours_per_week = st.number_input(
        "Часов в неделю",
        min_value=1,
        max_value=40,
        value=5
    )

    if st.button("Создать учебный план"):

        if not goal.strip():
            st.warning(
                "Пожалуйста, укажите, чему вы хотите научиться."
            )

        else:

            try:

                with st.spinner(
                    "ИИ составляет ваш учебный план..."
                ):

                    # ==================================================
                    # ЗДЕСЬ ТЕПЕРЬ ИСПОЛЬЗУЕТСЯ AI
                    # ==================================================

                    plan_data = generate_ai_plan(
                        goal=goal,
                        level=level,
                        weeks=weeks,
                        hours_per_week=hours_per_week
                    )

                    # Сохраняем план в базу
                plan_id = save_plan(
                    goal,
                    level,
                    weeks,
                    hours_per_week,
                    plan_data
                )

                st.success(
                    "Учебный план успешно создан!"
                )

                st.subheader("Ваш учебный план")

                # Показываем созданный план
                for week in plan_data.weeks:

                    st.markdown(
                        f"### Неделя {week.week}"
                    )

                    st.write(
                        f"**Тема:** {week.topic}"
                    )

                    st.write(
                        f"**Время:** {week.hours} часов"
                    )

                    for task in week.tasks:
                        st.write(
                            f"• {task}"
                        )

                    st.divider()

            except Exception as error:
                logger.exception("Failed to create learning plan")

                st.error(
                    f"Не удалось создать учебный план: {error}"
                )


# ============================================================
# МОИ ПЛАНЫ
# ============================================================

elif page == "📚 Мои планы":

    st.header("Мои учебные планы")

    plans = get_all_plans()

    if not plans:

        st.info(
            "У вас пока нет сохранённых учебных планов."
        )

    else:

        # Создаём список названий планов
        plan_options = {
            plan.id: (
                f"{plan.goal} — "
                f"{plan.weeks} недель"
            )
            for plan in plans
        }

        selected_plan_id = st.selectbox(
            "Выберите план",
            options=list(plan_options.keys()),
            format_func=lambda plan_id:
                plan_options[plan_id]
        )

        # Получаем информацию о выбранном плане
        selected_plan = next(
            plan
            for plan in plans
            if plan.id == selected_plan_id
        )

        plan_id = selected_plan.id
        goal = selected_plan.goal
        level = selected_plan.level
        weeks = selected_plan.weeks
        hours_per_week = selected_plan.hours_per_week

        st.subheader(goal)

        st.write(
            f"**Уровень:** {level}"
        )

        st.write(
            f"**Продолжительность:** {weeks} недель"
        )

        st.write(
            f"**Время:** {hours_per_week} часов в неделю"
        )

        st.divider()

        # ========================================================
        # ПРОГРЕСС
        # ========================================================

        progress = get_plan_progress(plan_id)

        st.subheader("Прогресс")

        st.progress(progress)

        st.write(
            f"Выполнено: {progress * 100:.0f}%"
        )

        st.divider()

        # ========================================================
        # ЗАДАЧИ
        # ========================================================

        tasks = get_plan_tasks(plan_id)

        current_week = None

        for task in tasks:

            task_id = task.id
            week = task.week
            topic = task.topic
            task_text = task.task
            completed = task.completed

            # Если началась новая неделя
            if week != current_week:

                current_week = week

                st.subheader(
                    f"Неделя {week}"
                )

                st.write(
                    f"**Тема:** {topic}"
                )

            # Чекбокс задачи
            checked = st.checkbox(
                task_text,
                value=bool(completed),
                key=f"task_{task_id}"
            )

            # Если пользователь изменил состояние
            if checked != bool(completed):

                update_task_status(
                    task_id,
                    checked
                )

                st.rerun()