import streamlit as st

from storage.database import (
    get_all_plans,
    get_plan_progress,
    get_plan_tasks,
    update_task_status,
)


def render_plans(user_id: int) -> None:
    st.header("Мои учебные планы")
    plans = get_all_plans(user_id)

    if not plans:
        st.info("У вас пока нет сохранённых учебных планов.")
        return

    plan_options = {
        plan.id: f"{plan.goal} — {plan.weeks} недель"
        for plan in plans
    }
    selected_plan_id = st.selectbox(
        "Выберите план",
        options=list(plan_options.keys()),
        format_func=lambda plan_id: plan_options[plan_id],
    )
    selected_plan = next(
        plan for plan in plans if plan.id == selected_plan_id
    )

    st.subheader(selected_plan.goal)
    st.write(f"**Уровень:** {selected_plan.level}")
    st.write(f"**Продолжительность:** {selected_plan.weeks} недель")
    st.write(
        f"**Время:** {selected_plan.hours_per_week} часов в неделю"
    )
    st.divider()

    progress = get_plan_progress(selected_plan.id, user_id)
    st.subheader("Прогресс")
    st.progress(progress)
    st.write(f"Выполнено: {progress * 100:.0f}%")
    st.divider()

    _render_tasks(selected_plan.id, user_id)


def _render_tasks(plan_id: int, user_id: int) -> None:
    tasks = get_plan_tasks(plan_id, user_id)
    current_week = None

    for task in tasks:
        if task.week != current_week:
            current_week = task.week
            st.subheader(f"Неделя {task.week}")
            st.write(f"**Тема:** {task.topic}")

        checked = st.checkbox(
            task.task,
            value=task.completed,
            key=f"task_{task.id}",
        )
        if checked != task.completed:
            update_task_status(task.id, checked, user_id)
            st.rerun()
