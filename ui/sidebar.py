import streamlit as st

from ui.session import sign_out


PAGES = [
    "🎯 Создать план",
    "📚 Мои планы",
    "👤 Профиль",
]


def render_sidebar(email: str) -> str:
    with st.sidebar:
        st.caption(f"Пользователь: {email}")
        if st.button("Выйти"):
            sign_out()
            st.rerun()
        return st.radio("Раздел", PAGES)
