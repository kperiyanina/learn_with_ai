import logging

import streamlit as st

from core.models import LearningDiagnostic, PlanRequest
from services.ai import generate_ai_plan
from storage.database import save_plan


logger = logging.getLogger(__name__)


def render_create_plan(user_id: int) -> None:
    st.header("Создать учебный план")

    goal = st.text_input(
        "Чему вы хотите научиться?",
        placeholder="Например: Python для анализа данных",
    )
    level = st.selectbox(
        "Ваш текущий уровень",
        ["Начинающий", "Средний", "Продвинутый"],
    )
    weeks = st.number_input(
        "Количество недель",
        value=4,
        step=1,
    )
    hours_per_week = st.number_input(
        "Часов в неделю",
        value=5,
        step=1,
    )
    interests = st.text_area(
        "Что вам особенно интересно изучать? (необязательно)",
        max_chars=500,
    )
    preferred_format = st.selectbox(
        "Предпочтительный формат занятий",
        ["Смешанный формат", "Теория", "Практика", "Проектная работа"],
    )
    available_days = st.multiselect(
        "В какие дни вы готовы заниматься?",
        ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
    )

    if not st.button("Создать учебный план"):
        return

    try:
        request = PlanRequest(
            goal=goal,
            level=level,
            weeks=weeks,
            hours_per_week=hours_per_week,
        )
        diagnostic = LearningDiagnostic(
            interests=interests,
            preferred_format=preferred_format,
            available_days=tuple(available_days),
        )
    except ValueError as error:
        st.error(str(error))
        st.stop()

    try:
        with st.spinner("ИИ составляет ваш учебный план..."):
            plan = generate_ai_plan(
                request.goal,
                request.level,
                request.weeks,
                request.hours_per_week,
                diagnostic,
            )

        saved_plan_id = save_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
            plan,
            user_id=user_id,
            diagnostic=diagnostic,
        )
        st.session_state.navigation_target = "📚 Мои планы"
        st.session_state.selected_plan_id = saved_plan_id
        st.rerun()
    except Exception as error:
        logger.exception("Не удалось создать учебный план")
        st.error(f"Не удалось создать учебный план: {error}")


def render_plan(plan) -> None:
    st.subheader("Ваш учебный план")
    for week in plan.weeks:
        st.markdown(f"### Неделя {week.week}")
        st.write(f"**Тема:** {week.topic}")
        st.write(f"**Время:** {week.hours} часов")
        for task in week.tasks:
            st.write(f"• {task}")
        st.divider()
