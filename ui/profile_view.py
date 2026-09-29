import streamlit as st

from storage.database import get_profile, update_profile


def render_profile(user_id: int, email: str) -> None:
    profile = get_profile(user_id)
    st.header("Профиль")
    st.write(f"**Электронная почта:** {email}")

    with st.form("profile_form"):
        display_name = st.text_input(
            "Имя или название профиля",
            value=profile.display_name,
        )
        submitted = st.form_submit_button("Сохранить профиль")

    if submitted:
        try:
            update_profile(user_id, display_name)
            st.success("Профиль сохранён.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
