import streamlit as st

from storage.database import init_database
from ui.auth_view import render_authentication
from ui.create_plan_view import render_create_plan
from ui.plans_view import render_plans
from ui.profile_view import render_profile
from ui.progress_view import render_progress
from ui.settings_view import render_settings
from ui.session import current_user_id, initialize_session, is_authenticated
from ui.sidebar import render_sidebar


init_database()
st.set_page_config(page_title="LearnAI", page_icon="🎓")
initialize_session()
st.html(
    """
    <style>
    div[class*="st-key-delete_plan_"] button {
        background-color: #d32f2f;
        border-color: #b71c1c;
        color: white;
    }
    div[class*="st-key-delete_plan_"] button:hover {
        background-color: #b71c1c;
        border-color: #8e0000;
        color: white;
    }
    div[class*="st-key-delete-plan-section"] [data-testid="stExpander"] {
        border: 1px solid #b71c1c;
        border-radius: 0.5rem;
        overflow: hidden;
    }
    div[class*="st-key-delete-plan-section"] [data-testid="stExpander"] details > summary {
        background-color: #d32f2f;
        color: white;
    }
    div[class*="st-key-delete-plan-section"] [data-testid="stExpander"] details > summary:hover {
        background-color: #b71c1c;
    }
    div[class*="st-key-delete-plan-section"] [data-testid="stExpander"] details > summary span,
    div[class*="st-key-delete-plan-section"] [data-testid="stExpander"] details > summary svg {
        color: white;
        fill: white;
    }
    </style>
    """
)

if not is_authenticated():
    render_authentication()
    st.stop()

user_id = current_user_id()
email = st.session_state.user_email

st.title("🎓 LearnWithAI")
st.write("Персональный план обучения с помощью ИИ")

# Apply navigation requests before creating the sidebar widget. This avoids
# modifying a widget's state after it has already been instantiated.
navigation_target = st.session_state.pop("navigation_target", None)
if navigation_target is not None:
    st.session_state.current_page = navigation_target

page = render_sidebar(email)

if page == "🎯 Создать план":
    render_create_plan(user_id)
elif page == "📚 Мои планы":
    render_plans(user_id)
elif page == "📊 Статистика":
    render_progress(user_id)
elif page == "⚙️ Расписание":
    render_settings(user_id)
elif page == "👤 Профиль":
    render_profile(user_id, email)
