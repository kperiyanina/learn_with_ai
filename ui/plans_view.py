import streamlit as st

from storage.database import (
    get_all_plans,
    get_plan_progress,
    get_plan_tasks,
    get_adaptive_recommendation,
    get_learning_block,
    get_learning_block_quiz_attempts,
    get_plan_learning_blocks,
    get_plan_materials,
    get_plan_preferred_format,
    delete_plan,
    mark_learning_block_theory_completed,
    save_learning_block,
    save_learning_block_quiz_result,
    delete_week_materials,
    update_task_status,
    update_material_status,
)
from services.materials import generate_learning_material


def render_plans(user_id: int) -> None:
    if st.session_state.get("learning_block") is not None:
        plan_id, week = st.session_state.learning_block
        render_learning_block(plan_id, week, user_id)
        return

    st.header("Мои учебные планы")
    plans = get_all_plans(user_id)

    if not plans:
        st.info("У вас пока нет сохранённых учебных планов.")
        return

    plan_options = {
        plan.id: f"{plan.goal} — {plan.weeks} недель"
        for plan in plans
    }
    if st.session_state.get("selected_plan_id") not in plan_options:
        st.session_state.selected_plan_id = plans[0].id
    selected_plan_id = st.selectbox(
        "Выберите план",
        options=list(plan_options.keys()),
        format_func=lambda plan_id: plan_options[plan_id],
        key="selected_plan_id",
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
    _render_plan_deletion(selected_plan.id, selected_plan.goal, user_id)
    st.divider()

    progress = get_plan_progress(selected_plan.id, user_id)
    st.subheader("Прогресс")
    st.progress(progress)
    st.write(f"Выполнено: {progress * 100:.0f}%")
    recommendation = get_adaptive_recommendation(selected_plan.id, user_id)
    if recommendation:
        st.info(f"Адаптивная рекомендация: {recommendation}")
    st.divider()

    _render_blocks(selected_plan.id, user_id)


def _render_plan_deletion(plan_id: int, goal: str, user_id: int) -> None:
    with st.container(key="delete-plan-section"):
        with st.expander("Удалить учебный план", icon=":material/delete:"):
            st.error(
                f'План «{goal}» и весь его прогресс будут удалены без возможности восстановления.'
            )
            confirm_key = f"confirm_delete_plan_{plan_id}"
            if st.checkbox("Я понимаю, что удаление необратимо", key=confirm_key):
                if st.button(
                    "Удалить план",
                    key=f"delete_plan_{plan_id}",
                    type="secondary",
                ):
                    try:
                        delete_plan(plan_id, user_id)
                        st.session_state.pop("learning_block", None)
                        st.session_state.pop("selected_plan_id", None)
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))


def _render_blocks(plan_id: int, user_id: int) -> None:
    tasks = get_plan_tasks(plan_id, user_id)
    blocks_by_week = {
        block.week: block
        for block in get_plan_learning_blocks(plan_id, user_id)
    }
    materials_by_week = {}
    for material in get_plan_materials(plan_id, user_id):
        materials_by_week.setdefault(material.week, []).append(material)
    weeks = sorted({task.week for task in tasks})
    for week in weeks:
        week_tasks = [task for task in tasks if task.week == week]
        topic = week_tasks[0].topic
        week_materials = materials_by_week.get(week, [])
        block = blocks_by_week.get(week)
        completed_steps = sum(task.completed for task in week_tasks)
        completed_steps += int(block is not None and block.theory_completed)
        completed_steps += int(block is not None and block.quiz_passed)
        completed_steps += sum(item.completed for item in week_materials)
        total_steps = len(week_tasks) + 2 + len(week_materials)

        st.subheader(f"Неделя {week}")
        st.write(f"**Тема:** {topic}")
        st.caption(f"Прогресс недели: {completed_steps} из {total_steps} шагов")
        st.progress(completed_steps / total_steps)
        if st.button("Открыть блок", key=f"open_block_{plan_id}_{week}"):
            st.session_state.learning_block = (plan_id, week)
            st.rerun()

        for task in week_tasks:
            checked = st.checkbox(
                task.task,
                value=task.completed,
                key=f"task_{task.id}",
            )
            if checked != task.completed:
                update_task_status(task.id, checked, user_id)
                st.rerun()


def render_learning_block(plan_id: int, week: int, user_id: int) -> None:
    plans = get_all_plans(user_id)
    plan = next((item for item in plans if item.id == plan_id), None)
    if plan is None:
        st.error("Учебный план не найден.")
        st.session_state.pop("learning_block", None)
        return

    tasks = [
        task for task in get_plan_tasks(plan_id, user_id)
        if task.week == week
    ]
    if not tasks:
        st.error("Учебный блок не найден.")
        st.session_state.pop("learning_block", None)
        return

    if st.button("← Вернуться к плану", key=f"back_plan_{plan_id}_{week}"):
        st.session_state.pop("learning_block", None)
        st.rerun()

    topic = tasks[0].topic
    st.header(f"Блок {week}: {topic}")
    st.write(f"**Цель:** {plan.goal}")
    st.write(f"**Задачи блока:** {len(tasks)}")
    preferred_format = get_plan_preferred_format(plan_id, user_id)
    st.write(f"**Лимит на всю неделю:** {plan.hours_per_week} часов")
    st.write(f"**Формат занятий:** {preferred_format}")
    st.caption("Время распределяется между теорией, задачами и тестом этой недели.")

    learning_block = get_learning_block(plan_id, week, user_id)
    if learning_block is None:
        try:
            preferred_format = get_plan_preferred_format(plan_id, user_id)
            with st.container(horizontal_alignment="center"):
                st.markdown(
                    "**ИИ создаёт теорию и тест для блока.**  \n"
                    "Материал будет сохранён автоматически.",
                    text_alignment="center",
                )
                with st.spinner("Подготавливаем учебный блок..."):
                    generated_material = generate_learning_material(
                        plan.goal,
                        plan.level,
                        topic,
                        plan.hours_per_week,
                        tasks=tuple(task.task for task in tasks),
                        preferred_format=preferred_format,
                    )
                    save_learning_block(
                        plan_id=plan_id,
                        week=week,
                        topic=topic,
                        theory=generated_material["theory"],
                        quiz=generated_material["quiz"],
                        resources=generated_material.get("resources", []),
                        task_guides=generated_material.get("task_guides", []),
                        user_id=user_id,
                    )
        except (RuntimeError, ValueError) as error:
            st.error(f"Не удалось создать учебный блок: {error}")
            if st.button("Повторить генерацию", key=f"retry_generation_{plan_id}_{week}"):
                st.rerun()
            return
        learning_block = get_learning_block(plan_id, week, user_id)

    if learning_block is None:
        st.error("Не удалось сохранить учебный материал блока.")
        return

    _render_learning_material(learning_block, tasks, user_id)

    materials = [
        item for item in get_plan_materials(plan_id, user_id)
        if item.week == week
    ]

    if not materials:
        return

    completed_count = sum(item.completed for item in materials)
    st.progress(completed_count / len(materials))
    st.write(f"Пройдено материалов: {completed_count} из {len(materials)}")
    if st.button(
        "Перегенерировать материалы блока",
        key=f"regenerate_block_{plan_id}_{week}",
        help="Удалит текущие материалы блока и подберёт их заново с проверкой содержимого.",
    ):
        delete_week_materials(plan_id, week, user_id)
        st.rerun()
    for material in materials:
        with st.container(border=True):
            st.markdown(f"**{material.title}** · {material.material_type}")
            st.write(f"[Открыть материал]({material.url})")
            if material.tags:
                st.caption(f"Теги: {material.tags}")
            checked = st.checkbox(
                "Материал пройден",
                value=material.completed,
                key=f"block_material_{material.id}",
            )
            if checked != material.completed:
                update_material_status(
                    material.id,
                    completed=checked,
                    user_id=user_id,
                )
                st.rerun()


def _render_learning_material(learning_block, tasks, user_id: int) -> None:
    st.subheader("Теория")
    st.caption("Шаг 1 из 2: изучите теорию и отметьте её завершённой.")
    st.markdown(learning_block.theory)
    if not learning_block.theory_completed and st.button(
        "Отметить теорию как пройденную",
        key=f"theory_completed_{learning_block.plan_id}_{learning_block.week}",
    ):
        mark_learning_block_theory_completed(
            learning_block.plan_id,
            learning_block.week,
            user_id,
        )
        st.rerun()

    st.subheader("Практика блока")
    for index, task in enumerate(tasks):
        guide = (
            learning_block.task_guides[index]
            if index < len(learning_block.task_guides)
            else {
                "instruction": "Выполните задачу по материалу блока.",
                "expected_result": "Получите проверенный результат.",
            }
        )
        with st.container(border=True):
            st.markdown(f"**Задача {index + 1}. {task.task}**")
            st.markdown(f"**Как выполнить:**\n\n{guide['instruction']}")
            st.write(f"**Ожидаемый результат:** {guide['expected_result']}")
            checked = st.checkbox(
                "Задача выполнена",
                value=task.completed,
                key=f"block_task_{task.id}",
            )
            if checked != task.completed:
                update_task_status(task.id, checked, user_id)
                st.rerun()

    st.caption("Шаг 2 из 2: ответьте на вопросы и наберите не менее 70%.")
    st.subheader("Проверка знаний")
    material_key = f"quiz_{learning_block.plan_id}_{learning_block.week}"
    seed_key = f"{material_key}_seed"
    quiz_seed = st.session_state.setdefault(seed_key, 0)
    answers = []
    for index, question in enumerate(learning_block.quiz):
        question_key = f"{material_key}_question_{quiz_seed}_{index}"
        answer = st.radio(
            question["question"],
            question["options"],
            key=question_key,
        )
        answers.append(answer)

    current_result = st.session_state.get(f"{material_key}_result")
    if current_result is not None:
        _render_quiz_feedback(learning_block, current_result[0], current_result[1])
    elif (
        learning_block.quiz_last_score is not None
        and learning_block.quiz_total_questions is not None
    ):
        st.caption(
            "Последний сохранённый результат: "
            f"{learning_block.quiz_last_score}/{learning_block.quiz_total_questions} "
            f"(попыток: {learning_block.quiz_attempts})"
        )
        if learning_block.quiz_passed:
            st.info("Тест пройден.")
        else:
            st.warning("Порог 70% не достигнут. Попробуйте тест ещё раз.")
        if learning_block.quiz_best_score is not None:
            st.caption(
                "Лучший результат: "
                f"{learning_block.quiz_best_score}/"
                f"{learning_block.quiz_best_total_questions}"
            )

    attempts = get_learning_block_quiz_attempts(
        learning_block.plan_id,
        learning_block.week,
        user_id,
    )
    if attempts:
        with st.expander("История попыток"):
            for number, attempt in enumerate(attempts, start=1):
                status = "пройден" if attempt["passed"] else "не пройден"
                st.write(
                    f"Попытка {len(attempts) - number + 1}: "
                    f"{attempt['score']}/{attempt['total_questions']} — {status} "
                    f"({attempt['created_at']})"
                )

    if st.button("Проверить тест", key=f"{material_key}_check"):
        score = sum(
            answer == question["options"][question["correct"]]
            for answer, question in zip(answers, learning_block.quiz)
        )
        save_learning_block_quiz_result(
            learning_block.plan_id,
            learning_block.week,
            score=score,
            total_questions=len(learning_block.quiz),
            user_id=user_id,
        )
        st.session_state[f"{material_key}_result"] = (score, answers)
        _render_quiz_feedback(learning_block, score, answers)

    if learning_block.quiz_attempts > 0 and st.button(
        "Пройти тест заново",
        key=f"{material_key}_retry",
    ):
        st.session_state[seed_key] = quiz_seed + 1
        st.session_state.pop(f"{material_key}_result", None)
        st.rerun()

    resources = learning_block.resources
    if resources:
        st.subheader("Материалы для углубления")
        for resource in resources:
            st.markdown(f"- [{resource['title']}]({resource['url']})")
    else:
        st.caption("Дополнительные материалы для этого блока не требуются.")


def _render_quiz_feedback(learning_block, score: int, answers: list[str]) -> None:
    total = len(learning_block.quiz)
    if score / total >= 0.7:
        st.info(f"Результат: {score} из {total}. Тест пройден.")
    else:
        st.warning(
            f"Результат: {score} из {total}. Нужно набрать не менее 70%, "
            "чтобы завершить тест."
        )
    for question, answer in zip(learning_block.quiz, answers):
        correct_answer = question["options"][question["correct"]]
        if answer != correct_answer:
            st.warning(
                f"{question['question']}: правильный ответ — {correct_answer}. "
                f"{question['explanation']}"
            )
