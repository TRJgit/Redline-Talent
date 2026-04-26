import streamlit as st
from engine import AdaptiveRecruiterEngine
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from utils import load_css

# Load page specific styles
load_css("assets/styles.css")
load_css("pages/discovery.css")

db = st.session_state.get("db")
if not db:
    from db_manager import SupabaseManager
    db = SupabaseManager()
    st.session_state.db = db

api_key = st.session_state.get("api_key", "")
simulate_mail = st.session_state.get("simulate_mail", True)

st.markdown('<div class="main-header">Talent Discovery</div>', unsafe_allow_html=True)

with st.container(border=True):
    job_titles = [job["title"] for job in st.session_state.jobs]
    selected_job_title = st.selectbox("ASSIGN JOB PROFILE:", job_titles)
    selected_job = next(j for j in st.session_state.jobs if j["title"] == selected_job_title)
    
    if st.button("🚀 RUN ANALYSIS", type="primary", width='stretch'):
        if not api_key: st.error("MISSING API KEY")
        else:
            engine = AdaptiveRecruiterEngine(api_key)
            with st.status("🧠 CORE PROCESSING...", expanded=True) as status:
                current_stats = st.session_state.api_stats
                current_cache = st.session_state.analysis_cache
                rubric = engine.strategist_parse_jd(selected_job["jd"], st.session_state.recruiter_memory, current_stats)
                
                # --- SCOUT AGENT PHASE ---
                st.write("🔍 **SCOUT AGENT:** Scoring & Filtering candidates...")
                scouted_candidates = engine.discovery_scout_candidates(rubric, st.session_state.candidates, min_fit=50)
                st.write(f"✅ Scout identified **{len(scouted_candidates)}** candidates with Fit > 50%.")
                
                def process(c):
                    cache_key = f"{selected_job['id']}_{c['id']}"
                    if cache_key in current_cache:
                        res = current_cache[cache_key]
                        res['candidate']['scout_fit_score'] = c.get('scout_fit_score', 0)
                        res['candidate']['scout_interest_score'] = c.get('scout_interest_score', 0)
                        return res

                    unified = engine.unified_candidate_analysis(rubric, c, selected_job["jd"], current_stats)
                    result = {
                        "candidate": c, 
                        "evaluation": unified.evaluation_xai, 
                        "audit": unified.audit, 
                        "outreach": unified.outreach
                    }
                    current_cache[cache_key] = result
                    return result

                with ThreadPoolExecutor(max_workers=2) as executor:
                    results = list(executor.map(process, scouted_candidates))
                
                st.session_state.analysis_results = {"rubric": rubric, "results": results}
                db.log_action("ANALYSIS_CYCLE", f"Analyzed {len(results)} candidates for {selected_job_title}")
                status.update(label="ANALYSIS COMPLETE", state="complete")

if st.session_state.analysis_results:
    res = st.session_state.analysis_results
    sorted_results = sorted(res["results"], key=lambda x: x["audit"].adjusted_fit_score if (x.get("audit") and x["audit"].adjusted_fit_score) else x["candidate"].get("scout_fit_score", 0), reverse=True)
    
    for item in sorted_results:
        c, e, a, o = item["candidate"], item["evaluation"], item["audit"], item["outreach"]
        with st.container(border=True):
            # Defensive access to scout scores
            fit = a.adjusted_fit_score if (a and a.adjusted_fit_score) else c.get('scout_fit_score', 0)
            interest = c.get('scout_interest_score', 0)
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="font-size: 1.4rem; font-weight: 800;">{c.get('name', 'Unknown')}</div>
                <div style="display: flex; gap: 15px;">
                    <div style="text-align: center;">
                        <span style="font-size: 0.7rem; color: var(--text-dim); display: block; text-transform: uppercase;">Fit Score</span>
                        <span style="font-size: 1.2rem; font-weight: 800; color: var(--primary-red);">{fit}%</span>
                    </div>
                    <div style="text-align: center; border-left: 1px solid var(--accent-gray); padding-left: 15px;">
                        <span style="font-size: 0.7rem; color: var(--text-dim); display: block; text-transform: uppercase;">Interest</span>
                        <span style="font-size: 1.2rem; font-weight: 800; color: var(--warning-amber);">{interest}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("VIEW REASONING, PROJECTS & OUTREACH"):
                # Use attribute access for Pydantic objects, fallback for dicts
                summary = e.summary_reasoning if hasattr(e, 'summary_reasoning') else e.get('summary_reasoning', 'No reasoning.')
                st.info(summary)
                
                with st.container(border=True):
                    st.markdown("**CANDIDATE PROJECTS**")
                    for p in c.get('projects', []):
                        st.markdown(f"- **{p['name']}**: {p['description']}")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**PROS**")
                    pros = e.xai_pros if hasattr(e, 'xai_pros') else e.get('xai_pros', [])
                    for p in pros: st.write(f"✅ {p}")
                with col2:
                    st.markdown("**RISKS**")
                    cons = e.xai_cons if hasattr(e, 'xai_cons') else e.get('xai_cons', [])
                    for r in cons: st.write(f"⚠️ {r}")
                
                if a and hasattr(a, 'auditor_notes') and a.auditor_notes:
                    st.caption(f"🛡️ AUDITOR NOTES: {a.auditor_notes}")
                
                st.divider()
                if o:
                    message_body = o.personal_message if hasattr(o, 'personal_message') else o.get('personal_message', '')
                    st.text_area("OUTREACH DRAFT:", value=message_body, height=150, key=f"m_{c['id']}")
                    if st.button("📧 SEND OUTREACH EMAIL", key=f"send_{c['id']}", type="primary", width='stretch'):
                        engine = AdaptiveRecruiterEngine(api_key)
                        receiver_email = c.get('email', 'candidate@example.com')
                        result = engine.execute_mail_agent(
                            receiver_email=receiver_email,
                            subject="Redline Candidate Reach out",
                            body_text=message_body,
                            simulate=simulate_mail
                        )
                        if "Success" in result:
                            db.log_action("OUTREACH_SENT", f"Mail Agent sent outreach to {c['name']} ({receiver_email})")
                            st.success(result)
                            st.balloons()
                        else:
                            st.error(result)
                
                # --- Feedback Loop ---
                st.markdown("---")
                st.markdown("**AGENT TRAINING: Was this match accurate?**")
                f1, f2 = st.columns(2)
                with f1:
                    if st.button("👍 ACCURATE", key=f"pos_{c['id']}", width='stretch'):
                        st.session_state.recruiter_memory["preferences"].append({
                            "type": "positive",
                            "candidate": c['name'],
                            "reason": "Accurate alignment captured by agent.",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        db.save_memory(st.session_state.recruiter_memory)
                        st.toast("Positive feedback recorded.")
                with f2:
                    if st.button("👎 INACCURATE", key=f"neg_{c['id']}", width='stretch'):
                        st.session_state.negative_feedback_for = c['id']
                
                if st.session_state.get('negative_feedback_for') == c['id']:
                    reason = st.text_input(f"Why was {c['name']} a poor match?", key=f"reason_{c['id']}")
                    if st.button("Save Feedback", key=f"save_neg_{c['id']}", type="primary", width='stretch'):
                        st.session_state.recruiter_memory["preferences"].append({
                            "type": "negative",
                            "candidate": c['name'],
                            "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        db.save_memory(st.session_state.recruiter_memory)
                        st.session_state.negative_feedback_for = None
                        st.rerun()
