import streamlit as st

from storage.database import get_study_preferences, update_study_preferences


_DAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_TIMEZONES = ("Europe/Moscow", "Europe/Kaliningrad", "Asia/Yekaterinburg", "UTC")
_FREQUENCIES = ("Ежедневно", "Только в дни занятий", "Еженедельно")


def render_settings(user_id: int) -> None:
    st.header("Расписание и напоминания")
    preferences = get_study_preferences(user_id)
    with st.form("study_preferences_form"):
        days = st.multiselect(
            "Дни занятий",
            _DAYS,
            default=list(preferences.study_days) or ["Пн", "Ср", "Пт"],
        )
        study_time = st.time_input("Время занятий", value=_parse_time(preferences.study_time))
        timezone = st.selectbox(
            "Часовой пояс",
            _TIMEZONES,
            index=_TIMEZONES.index(preferences.timezone)
            if preferences.timezone in _TIMEZONES
            else 0,
        )
        reminders = st.checkbox(
            "Показывать напоминания в приложении",
            value=preferences.reminders_enabled,
        )
        frequency = st.selectbox(
            "Частота",
            _FREQUENCIES,
            index=_FREQUENCIES.index(preferences.reminder_frequency)
            if preferences.reminder_frequency in _FREQUENCIES
            else 0,
        )
        submitted = st.form_submit_button("Сохранить расписание")
    if submitted:
        try:
            update_study_preferences(
                user_id,
                tuple(days),
                study_time.strftime("%H:%M"),
                timezone,
                reminders,
                frequency,
            )
            st.success("Расписание сохранено.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if preferences.reminders_enabled and preferences.study_days:
        st.info(
            f"Напоминания будут показываться в приложении в {preferences.study_time} "
            f"({preferences.timezone}) по дням: {', '.join(preferences.study_days)}."
        )
    st.caption(
        "Сейчас это настройки расписания и внутренняя подсказка приложения. "
        "Фоновые email и push-уведомления будут добавлены вместе с планировщиком."
    )


def _parse_time(value: str):
    hour, minute = (int(part) for part in value.split(":"))
    return __import__("datetime").time(hour, minute)
