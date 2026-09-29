import streamlit as st

from storage.database import init_database
from ui.auth_view import render_authentication
from ui.create_plan_view import render_create_plan
from ui.plans_view import render_plans
from ui.profile_view import render_profile
from ui.session import current_user_id, initialize_session, is_authenticated
from ui.sidebar import render_sidebar


init_database()
st.set_page_config(page_title="LearnAI", page_icon="🎓")
initialize_session()

if not is_authenticated():
    render_authentication()
    st.stop()

user_id = current_user_id()
email = st.session_state.user_email

st.title("🎓 LearnWithAI")
st.write("Персональный план обучения с помощью ИИ")

page = render_sidebar(email)

if page == "🎯 Создать план":
    render_create_plan(user_id)
elif page == "📚 Мои планы":
    render_plans(user_id)
elif page == "👤 Профиль":
    render_profile(user_id, email)
