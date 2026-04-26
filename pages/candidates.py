import streamlit as st
from engine import AdaptiveRecruiterEngine
from utils import load_css, extract_text_from_pdf, extract_text_from_docx

# Load page specific styles
load_css("assets/styles.css")
load_css("pages/candidates.css")

db = st.session_state.get("db")
if not db:
    from db_manager import SupabaseManager
    db = SupabaseManager()
    st.session_state.db = db

if "candidates" not in st.session_state:
    st.session_state.candidates = db.get_all_candidates()

if "api_stats" not in st.session_state:
    st.session_state.api_stats = {"success": 0, "total": 0}

api_key = st.session_state.get("api_key", "")

st.markdown('<div class="main-header">Candidate Pool</div>', unsafe_allow_html=True)

with st.expander("📤 Bulk Import (Resumes)", expanded=False):
    uploaded_files = st.file_uploader("Upload PDF or DOCX resumes", type=["pdf", "docx"], accept_multiple_files=True)
    if uploaded_files and st.button("🚀 Parse & Import", type="primary", width='content'):
        try:
            engine = AdaptiveRecruiterEngine(api_key if api_key else None)
            with st.status("📄 PARSING RESUMES...", expanded=True) as status:
                existing_ids = [int(c['id'].split('_')[1]) for c in st.session_state.candidates if c['id'].startswith('CAND_')]
                base_id_num = max(existing_ids) if existing_ids else 0
                for i, uploaded_file in enumerate(uploaded_files):
                    try:
                        file_bytes = uploaded_file.read()
                        text = extract_text_from_pdf(file_bytes) if uploaded_file.name.endswith(".pdf") else extract_text_from_docx(file_bytes)
                        new_id = f"CAND_{base_id_num + i + 1:03d}"
                        parsed = engine.parser_extract_candidate(text, new_id, st.session_state.api_stats)
                        
                        # Save to DB
                        db.save_candidate(parsed.model_dump())
                        st.write(f"✅ Imported: **{parsed.name}** ({parsed.email})")
                    except Exception as e:
                        st.error(f"Error parsing {uploaded_file.name}: {e}")
                
                st.session_state.candidates = db.get_all_candidates() # Refresh local state
                db.log_action("CANDIDATE_IMPORT", f"Imported {len(uploaded_files)} resumes.")
                status.update(label="IMPORT COMPLETE", state="complete")
                st.rerun()
        except Exception as e:
            st.error(f"Engine Error: {e}")

st.divider()
for cand in st.session_state.candidates:
    with st.container(border=True):
        st.markdown(f"### {cand['name']}")
        st.markdown(f"**ROLE:** `{cand['current_role']}` | **EXP:** `{cand['years_of_experience']}Y` | **EMAIL:** `{cand.get('email', 'N/A')}`")
        
        with st.expander("🛠️ Projects"):
            for p in cand.get('projects', []):
                st.markdown(f"- **{p['name']}**: {p['description']}")
        
        skills_html = "".join([f'<span class="skill-tag">{s}</span>' for s in cand['skills']])
        st.markdown(skills_html, unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            if cand.get('metadata', {}).get('open_to_work'):
                st.markdown("<span style='color: var(--primary-red); font-weight: 800;'>● ACTIVE</span>", unsafe_allow_html=True)
        with col2:
            if st.button("🗑️", key=f"del_{cand['id']}", help=f"Delete {cand['name']}"):
                db.delete_candidate(cand['id'])
                db.log_action("CANDIDATE_DELETED", f"Deleted candidate: {cand['name']}")
                st.session_state.candidates = db.get_all_candidates()
                st.toast(f"Candidate '{cand['name']}' removed.")
                st.rerun()
