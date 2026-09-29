import streamlit as st


def initialize_session() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None


def is_authenticated() -> bool:
    return st.session_state.user_id is not None


def current_user_id() -> int:
    return st.session_state.user_id


def sign_in(user_id: int, email: str) -> None:
    st.session_state.user_id = user_id
    st.session_state.user_email = email


def sign_out() -> None:
    st.session_state.user_id = None
    st.session_state.user_email = None
