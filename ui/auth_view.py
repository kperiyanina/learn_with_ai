import streamlit as st

from storage.database import (
    authenticate_user,
    claim_legacy_plans,
    register_user,
)
from ui.session import sign_in


def render_authentication() -> None:
    st.title("🎓 LearnWithAI")
    st.write("Войдите или зарегистрируйтесь, чтобы сохранять свои планы.")

    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])

    with login_tab:
        _render_login_form()

    with register_tab:
        _render_registration_form()


def _render_login_form() -> None:
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
            sign_in(user.id, user.email)
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _render_registration_form() -> None:
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
            return
        try:
            user = register_user(email, password)
            claim_legacy_plans(user.id)
            sign_in(user.id, user.email)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
