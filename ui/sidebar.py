import streamlit as st

from ui.session import sign_out


PAGES = [
    "🎯 Создать план",
    "📚 Мои планы",
    "📊 Статистика",
    "⚙️ Расписание",
    "👤 Профиль",
]


def render_sidebar(email: str) -> str:
    with st.sidebar:
        st.caption(f"Пользователь: {email}")
        if st.button("Выйти"):
            sign_out()
            st.rerun()
        if st.session_state.get("current_page") not in PAGES:
            st.session_state.current_page = PAGES[0]
        st.markdown("**Разделы**")
        for page in PAGES:
            if st.button(
                page,
                key=f"navigation_{page}",
                type="primary"
                if page == st.session_state.current_page
                else "secondary",
                width="stretch",
            ):
                st.session_state.current_page = page
                st.rerun()
        return st.session_state.current_page
