import streamlit as st
from datetime import datetime
from utils import load_css

# Load page specific styles
load_css("assets/styles.css")
load_css("pages/jobs.css")

db = st.session_state.get("db")
if not db:
    from db_manager import SupabaseManager
    db = SupabaseManager()
    st.session_state.db = db

if "jobs" not in st.session_state:
    st.session_state.jobs = db.get_all_jobs()

if "show_add_job" not in st.session_state:
    st.session_state.show_add_job = False

st.markdown('<div class="main-header">Job Management</div>', unsafe_allow_html=True)

if not st.session_state.show_add_job:
    if st.button("➕ New Requisition", type="primary", width='content'):
        st.session_state.show_add_job = True
        st.rerun()
        
if st.session_state.show_add_job:
    with st.container(border=True):
        st.subheader("New Specification")
        new_title = st.text_input("Job Title")
        new_jd = st.text_area("Description (Markdown)", height=200)
        
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            if st.button("💾 Save", type="primary", width='stretch'):
                if new_title and new_jd:
                    # Robust ID generation
                    existing_ids = [int(j['id'].split('_')[1]) for j in st.session_state.jobs if j['id'].startswith('JOB_')]
                    next_id_num = max(existing_ids) + 1 if existing_ids else 1
                    new_job = {
                        "id": f"JOB_{next_id_num:03d}", 
                        "title": new_title, 
                        "jd": new_jd, 
                        "posted_date": datetime.now().strftime("%Y-%m-%d"), 
                        "applicants": 0
                    }
                    db.save_job(new_job)
                    st.session_state.jobs = db.get_all_jobs() # Refresh local state
                    db.log_action("JOB_CREATED", f"New job requisition: {new_title}")
                    st.session_state.show_add_job = False
                    st.rerun()
        with c2:
            if st.button("❌ Cancel", type="secondary", width='stretch'):
                st.session_state.show_add_job = False
                st.rerun()

st.divider()
for job in st.session_state.jobs:
    with st.expander(f"**{job['title']}**"):
        st.markdown(job['jd'])
        if st.button(f"🗑️ Delete {job['title']}", key=f"del_{job['id']}", type="secondary"):
            db.delete_job(job['id'])
            db.log_action("JOB_DELETED", f"Deleted job requisition: {job['title']}")
            st.session_state.jobs = db.get_all_jobs()
            st.toast(f"Job '{job['title']}' deleted.")
            st.rerun()
