import streamlit as st
from utils import load_css

# Load page specific styles
load_css("assets/styles.css")
load_css("pages/dashboard.css")

db = st.session_state.get("db")
if not db:
    from db_manager import SupabaseManager
    db = SupabaseManager()
    st.session_state.db = db

if "candidates" not in st.session_state:
    st.session_state.candidates = db.get_all_candidates()

if "jobs" not in st.session_state:
    st.session_state.jobs = db.get_all_jobs()

if "api_stats" not in st.session_state:
    st.session_state.api_stats = {"success": 0, "total": 0}

st.markdown('<div class="main-header">Dashboard</div>', unsafe_allow_html=True)

new_matches_count = len([c for c in st.session_state.candidates if c.get('metadata', {}).get('last_active_days_ago', 10) <= 3])
total_calls = st.session_state.api_stats.get("total", 0)
success_calls = st.session_state.api_stats.get("success", 0)
uptime = (success_calls / total_calls * 100) if total_calls > 0 else 100.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Active Jobs", len(st.session_state.jobs))
m2.metric("Total Pool", len(st.session_state.candidates))
m3.metric("New Matches", new_matches_count)
m4.metric("Agent Uptime", f"{uptime:.1f}%", delta=f"{success_calls}/{total_calls} calls")

st.divider()
st.subheader("📡 Activity Feed")

if db.enabled:
    history = db.get_history(limit=5)
    for h in history:
        st.markdown(f"""
        <div class="activity-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1rem; font-weight: 700; color: var(--primary-red);">⚪ {h['event']}</span>
                    <p style="margin: 2px 0; color: var(--text-main); font-size: 0.9rem;">{h['desc']}</p>
                </div>
                <div style="text-align: right;">
                    <span class="status-badge" style="border: 1px solid #4CAF50; color: #4CAF50;">OK</span>
                    <p style="margin: 2px 0; color: var(--text-dim); font-size: 0.75rem;">{h['time']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    activities = [
        {"icon": "🔴", "event": "DATA SYNC", "desc": "Candidate profiles updated successfully.", "status": "OK", "color": "#4CAF50", "time": "5M AGO"},
        {"icon": "⚪", "event": "AI CYCLE", "desc": "Analysis complete for active requisitions.", "status": "DONE", "color": "#4CAF50", "time": "1H AGO"},
        {"icon": "⚠️", "event": "RATE LIMIT", "desc": "Primary model threshold reached; fallback active.", "status": "INFO", "color": "#FFC107", "time": "3H AGO"},
        {"icon": "⚙️", "event": "SYSTEM", "desc": "Local database integrity verified.", "status": "STABLE", "color": "#DB3434", "time": "1D AGO"}
    ]
    for act in activities:
        st.markdown(f"""
        <div class="activity-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1rem; font-weight: 700; color: var(--primary-red);">{act['icon']} {act['event']}</span>
                    <p style="margin: 2px 0; color: var(--text-main); font-size: 0.9rem;">{act['desc']}</p>
                </div>
                <div style="text-align: right;">
                    <span class="status-badge" style="border: 1px solid {act['color']}; color: {act['color']};">{act['status']}</span>
                    <p style="margin: 2px 0; color: var(--text-dim); font-size: 0.75rem;">{act['time']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
