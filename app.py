import streamlit as st
import logging

from ai import generate_ai_plan
from database import (
    authenticate_user,
    claim_legacy_plans,
    get_profile,
    init_database,
    save_plan,
    get_all_plans,
    get_plan_tasks,
    register_user,
    update_profile,
    update_task_status,
    get_plan_progress,
)
from models import PlanRequest

logger = logging.getLogger(__name__)

# Инициализация базы данных
init_database()


# Настройка страницы
st.set_page_config(
    page_title="LearnAI",
    page_icon="🎓"
)

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None


def show_authentication():
    st.title("🎓 LearnWithAI")
    st.write("Войдите или зарегистрируйтесь, чтобы сохранять свои планы.")

    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Электронная почта", key="login_email")
            password = st.text_input(
                "Пароль",
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button("Войти")

        if submitted:
            try:
                user = authenticate_user(email, password)
                st.session_state.user_id = user.id
                st.session_state.user_email = user.email
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    with register_tab:
        with st.form("register_form"):
            email = st.text_input(
                "Электронная почта",
                key="register_email",
            )
            password = st.text_input(
                "Пароль",
                type="password",
                key="register_password",
            )
            password_confirmation = st.text_input(
                "Повторите пароль",
                type="password",
                key="register_password_confirmation",
            )
            submitted = st.form_submit_button("Зарегистрироваться")

        if submitted:
            if password != password_confirmation:
                st.error("Пароли не совпадают.")
            else:
                try:
                    user = register_user(email, password)
                    claim_legacy_plans(user.id)
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))


if st.session_state.user_id is None:
    show_authentication()
    st.stop()

user_id = st.session_state.user_id
profile = get_profile(user_id)

# Заголовок
st.title("🎓 LearnWithAI")
st.write("Персональный план обучения с помощью ИИ")

with st.sidebar:
    st.caption(f"Пользователь: {st.session_state.user_email}")
    if st.button("Выйти"):
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.rerun()


# Боковая навигация
page = st.sidebar.radio(
    "Раздел",
    [
        "🎯 Создать план",
        "📚 Мои планы",
        "👤 Профиль",
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
        value=4,
        step=1
    )

    hours_per_week = st.number_input(
        "Часов в неделю",
        value=5,
        step=1
    )

    if st.button("Создать учебный план"):

        try:
            PlanRequest(
                goal=goal,
                level=level,
                weeks=weeks,
                hours_per_week=hours_per_week,
            )
        except ValueError as error:
            st.error(str(error))
            st.stop()

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
                plan_data,
                user_id=user_id,
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
            logger.exception("Не удалось создать учебный план")

            st.error(
                f"Не удалось создать учебный план: {error}"
            )


# ============================================================
# МОИ ПЛАНЫ
# ============================================================

elif page == "📚 Мои планы":

    st.header("Мои учебные планы")

    plans = get_all_plans(user_id)

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

        progress = get_plan_progress(plan_id, user_id)

        st.subheader("Прогресс")

        st.progress(progress)

        st.write(
            f"Выполнено: {progress * 100:.0f}%"
        )

        st.divider()

        # ========================================================
        # ЗАДАЧИ
        # ========================================================

        tasks = get_plan_tasks(plan_id, user_id)

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
                    checked,
                    user_id,
                )

                st.rerun()

# ============================================================
# ПРОФИЛЬ
# ============================================================

elif page == "👤 Профиль":

    st.header("Профиль")
    st.write(f"**Электронная почта:** {st.session_state.user_email}")

    with st.form("profile_form"):
        display_name = st.text_input(
            "Имя или название профиля",
            value=profile.display_name,
        )
        submitted = st.form_submit_button("Сохранить профиль")

    if submitted:
        try:
            update_profile(
                user_id,
                display_name,
            )
            st.success("Профиль сохранён.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))