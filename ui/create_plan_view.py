import logging

import streamlit as st

from core.models import PlanRequest
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

    if not st.button("Создать учебный план"):
        return

    try:
        request = PlanRequest(
            goal=goal,
            level=level,
            weeks=weeks,
            hours_per_week=hours_per_week,
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
            )

        save_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
            plan,
            user_id=user_id,
        )
        st.success("Учебный план успешно создан!")
        render_plan(plan)
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
