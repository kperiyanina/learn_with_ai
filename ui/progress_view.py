import csv
import io

import streamlit as st

from storage.database import (
    get_all_plans,
    get_study_stats,
    log_study_session,
)


def render_progress(user_id: int) -> None:
    st.header("Статистика обучения")
    plans = get_all_plans(user_id)
    if not plans:
        st.info("Создайте учебный план, чтобы увидеть статистику.")
        return

    labels = {plan.id: plan.goal for plan in plans}
    plan_id = st.selectbox(
        "План",
        options=list(labels),
        format_func=lambda value: labels[value],
        key="stats_plan_id",
    )
    stats = get_study_stats(plan_id, user_id)
    completed_total = stats.completed_tasks + stats.completed_theory + stats.passed_quizzes
    total_total = stats.total_tasks + stats.total_weeks * 2
    if stats.total_materials:
        completed_total += stats.completed_materials
        total_total += stats.total_materials

    first, second, third, fourth = st.columns(4)
    first.metric("Общий прогресс", f"{stats.progress * 100:.0f}%")
    second.metric("Задачи", f"{stats.completed_tasks}/{stats.total_tasks}")
    third.metric("Тесты", f"{stats.passed_quizzes}/{stats.total_quizzes}")
    fourth.metric("Время", _format_minutes(stats.study_minutes))
    st.progress(stats.progress)

    st.subheader("Детализация")
    st.write(
        f"Теория: {stats.completed_theory}/{stats.total_weeks} недель · "
        f"Практика: {stats.completed_tasks}/{stats.total_tasks} задач · "
        f"Материалы: {stats.completed_materials}/{stats.total_materials}"
    )

    with st.expander("Добавить занятие в журнал"):
        with st.form(f"study_session_form_{plan_id}"):
            minutes = st.number_input(
                "Продолжительность, минут",
                min_value=1,
                max_value=1440,
                value=30,
                step=5,
            )
            note = st.text_input("Комментарий (необязательно)")
            submitted = st.form_submit_button("Сохранить занятие")
        if submitted:
            try:
                log_study_session(user_id, plan_id, int(minutes), note)
                st.success("Занятие добавлено в журнал.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    csv_data = build_statistics_csv(
        labels[plan_id],
        stats.progress,
        stats.completed_tasks,
        stats.total_tasks,
        stats.completed_theory,
        stats.total_weeks,
        stats.passed_quizzes,
        stats.total_quizzes,
        stats.completed_materials,
        stats.total_materials,
        stats.study_minutes,
    )
    st.download_button(
        "Скачать статистику CSV",
        csv_data,
        file_name="learnwithai_progress.csv",
        mime="text/csv",
    )


def build_statistics_csv(
    plan_label: str,
    progress: float,
    completed_tasks: int,
    total_tasks: int,
    completed_theory: int,
    total_weeks: int,
    passed_quizzes: int,
    total_quizzes: int,
    completed_materials: int,
    total_materials: int,
    study_minutes: int,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Показатель", "Значение"])
    writer.writerows(
        [
            ("План", plan_label),
            ("Прогресс", f"{progress * 100:.0f}%"),
            ("Задачи выполнены", f"{completed_tasks}/{total_tasks}"),
            ("Теория пройдена", f"{completed_theory}/{total_weeks}"),
            ("Тесты пройдены", f"{passed_quizzes}/{total_quizzes}"),
            ("Материалы пройдены", f"{completed_materials}/{total_materials}"),
            ("Учебное время, минут", study_minutes),
        ]
    )
    return output.getvalue().encode("utf-8-sig")


def _format_minutes(minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {remainder} мин"
    return f"{remainder} мин"
