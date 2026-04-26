import streamlit as st
import os
from db_manager import SupabaseManager
from dotenv import load_dotenv
from utils import load_css

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Redline Talent | Agentic Recruitment",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# --- Theme & Styling ---
load_css("assets/styles.css")

# --- Initialize Database ---
if "db" not in st.session_state:
    st.session_state.db = SupabaseManager()

db = st.session_state.db

# --- Initialize Session State from DB ---
if "recruiter_memory" not in st.session_state:
    st.session_state.recruiter_memory = db.load_memory()

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "candidates" not in st.session_state:
    st.session_state.candidates = db.get_all_candidates()
if "jobs" not in st.session_state:
    st.session_state.jobs = db.get_all_jobs()
if "show_add_job" not in st.session_state:
    st.session_state.show_add_job = False
if "api_stats" not in st.session_state:
    st.session_state.api_stats = {"success": 0, "total": 0}
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("Gemini_API_Key", "")
if "simulate_mail" not in st.session_state:
    st.session_state.simulate_mail = True

# --- Navigation Setup ---
dashboard_page = st.Page("pages/dashboard.py", title="Dashboard", icon="🏠", default=True)
jobs_page = st.Page("pages/jobs.py", title="Jobs", icon="💼")
candidates_page = st.Page("pages/candidates.py", title="Candidates", icon="👥")
discovery_page = st.Page("pages/discovery.py", title="Discovery", icon="🚀")

pg = st.navigation({
    "MAIN": [dashboard_page, jobs_page, candidates_page, discovery_page]
})

# --- Sidebar Permanent Elements ---
with st.sidebar:
    st.image("assets/SideBar.png", width='stretch')
    st.caption("Redline Talent: An Agentic Solution for Talent Acquisition and Outreach")
    
    st.divider()
    with st.expander("Configuration"):
        if st.button("Reload from .env"):
            load_dotenv(override=True)
            st.session_state.api_key = os.getenv("Gemini_API_Key", "")
            st.rerun()
        st.text_input("Gemini API Key", type="password", key="api_key")
        st.toggle("Simulate Mail Agent", key="simulate_mail")
    
    if st.button("Refresh Data", width='stretch', type="secondary"):
        st.session_state.candidates = db.get_all_candidates()
        st.session_state.jobs = db.get_all_jobs()
        st.session_state.recruiter_memory = db.load_memory()
        st.toast("State synchronized from DB.")
        st.rerun()

    if st.button("Clear Memory", width='stretch', type="secondary"):
        st.session_state.recruiter_memory = {"preferences": []}
        db.save_memory(st.session_state.recruiter_memory)
        st.rerun()

    if st.button("Clear Cache", width='stretch', type="secondary"):
        st.session_state.analysis_cache = {}
        st.session_state.analysis_results = None
        st.toast("Cache cleared.")
        st.rerun()

# --- Run Navigation ---
pg.run()
