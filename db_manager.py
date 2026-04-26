import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    def __init__(self):
        # Try environment variables first, then streamlit secrets as fallback
        self.db_url = os.getenv("SUPABASE_DB_URL")
        
        if not self.db_url:
            try:
                import streamlit as st
                # Using st.secrets.get() can still raise StreamlitSecretNotFoundError if no secrets.toml exists
                self.db_url = st.secrets.get("SUPABASE_DB_URL")
            except Exception:
                # If st.secrets is not available or raises an error, we just move on
                pass
            
        self.enabled = True
        if not self.db_url:
            raise ValueError("SUPABASE_DB_URL not found in environment variables or streamlit secrets")
        self.init_tables()

    def get_connection(self):
        # Connect to Supabase via the connection string
        conn = psycopg2.connect(self.db_url)
        return conn

    def init_tables(self):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # Recruiter Memory
                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS RECRUITER_MEMORY (
                        ID TEXT PRIMARY KEY,
                        MEMORY_JSON TEXT,
                        UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)
                    # Action History
                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS ACTION_HISTORY (
                        ID TEXT PRIMARY KEY,
                        EVENT_TYPE TEXT,
                        DESCRIPTION TEXT,
                        EVENT_TIME TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)
                    # Jobs
                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS JOBS (
                        ID TEXT PRIMARY KEY,
                        TITLE TEXT,
                        JD TEXT,
                        POSTED_DATE TEXT,
                        APPLICANTS INTEGER,
                        METADATA TEXT
                    )
                    """)
                    # Candidates
                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS CANDIDATES (
                        ID TEXT PRIMARY KEY,
                        NAME TEXT,
                        EMAIL TEXT,
                        "current_role" TEXT,
                        YEARS_OF_EXPERIENCE INTEGER,
                        SKILLS TEXT,
                        PROJECTS TEXT,
                        METADATA TEXT,
                        UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)
        finally:
            conn.close()

    # --- Memory Management ---
    def save_memory(self, memory_dict: Dict[str, Any]):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    memory_json = json.dumps(memory_dict)
                    cur.execute("""
                    INSERT INTO RECRUITER_MEMORY (ID, MEMORY_JSON, UPDATED_AT)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(ID) DO UPDATE SET 
                        MEMORY_JSON=EXCLUDED.MEMORY_JSON,
                        UPDATED_AT=CURRENT_TIMESTAMP
                    """, ('GLOBAL_MEMORY', memory_json))
        finally:
            conn.close()

    def load_memory(self) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT MEMORY_JSON FROM RECRUITER_MEMORY WHERE ID = 'GLOBAL_MEMORY'")
                row = cur.fetchone()
                if row:
                    return json.loads(row.get('memory_json', '{}'))
        except Exception:
            pass
        finally:
            conn.close()
        return {"preferences": []}

    # --- Action History ---
    def log_action(self, event_type: str, description: str):
        import uuid
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO ACTION_HISTORY (ID, EVENT_TYPE, DESCRIPTION) VALUES (%s, %s, %s)",
                        (str(uuid.uuid4()), event_type, description)
                    )
        finally:
            conn.close()

    def get_history(self, limit=10) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT EVENT_TYPE, DESCRIPTION, EVENT_TIME FROM ACTION_HISTORY ORDER BY EVENT_TIME DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                return [{"event": r.get('event_type'), "desc": r.get('description'), "time": r.get('event_time')} for r in rows]
        finally:
            conn.close()

    # --- Jobs Management ---
    def save_job(self, job: Dict[str, Any]):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    INSERT INTO JOBS (ID, TITLE, JD, POSTED_DATE, APPLICANTS, METADATA)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(ID) DO UPDATE SET
                        TITLE=EXCLUDED.TITLE,
                        JD=EXCLUDED.JD,
                        POSTED_DATE=EXCLUDED.POSTED_DATE,
                        APPLICANTS=EXCLUDED.APPLICANTS,
                        METADATA=EXCLUDED.METADATA
                    """, (job['id'], job['title'], job['jd'], job['posted_date'], job['applicants'], json.dumps(job.get('metadata', {}))))
        finally:
            conn.close()

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM JOBS")
                rows = cur.fetchall()
                jobs = []
                for r in rows:
                    job = {
                        'id': r.get('id'),
                        'title': r.get('title'),
                        'jd': r.get('jd'),
                        'posted_date': r.get('posted_date'),
                        'applicants': r.get('applicants'),
                        'metadata': json.loads(r.get('metadata', '{}')) if r.get('metadata') else {}
                    }
                    jobs.append(job)
                return jobs
        finally:
            conn.close()

    # --- Candidates Management ---
    def save_candidate(self, cand: Dict[str, Any]):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    INSERT INTO CANDIDATES (ID, NAME, EMAIL, "current_role", YEARS_OF_EXPERIENCE, SKILLS, PROJECTS, METADATA, UPDATED_AT)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(ID) DO UPDATE SET
                        NAME=EXCLUDED.NAME,
                        EMAIL=EXCLUDED.EMAIL,
                        "current_role"=EXCLUDED."current_role",
                        YEARS_OF_EXPERIENCE=EXCLUDED.YEARS_OF_EXPERIENCE,
                        SKILLS=EXCLUDED.SKILLS,
                        PROJECTS=EXCLUDED.PROJECTS,
                        METADATA=EXCLUDED.METADATA,
                        UPDATED_AT=CURRENT_TIMESTAMP
                    """, (
                        cand['id'], 
                        cand['name'], 
                        cand.get('email', 'candidate@example.com'), 
                        cand['current_role'], 
                        cand['years_of_experience'],
                        json.dumps(cand['skills']),
                        json.dumps(cand['projects']),
                        json.dumps(cand.get('metadata', {}))
                    ))
        finally:
            conn.close()

    def get_all_candidates(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM CANDIDATES")
                rows = cur.fetchall()
                candidates = []
                for r in rows:
                    cand = {
                        "id": r.get('id'),
                        "name": r.get('name'),
                        "email": r.get('email'),
                        "current_role": r.get('current_role'),
                        "years_of_experience": r.get('years_of_experience'),
                        "skills": json.loads(r.get('skills', '[]')) if r.get('skills') else [],
                        "projects": json.loads(r.get('projects', '[]')) if r.get('projects') else [],
                        "metadata": json.loads(r.get('metadata', '{}')) if r.get('metadata') else {}
                    }
                    candidates.append(cand)
                return candidates
        finally:
            conn.close()

    def delete_job(self, job_id: str):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM JOBS WHERE ID = %s", (job_id,))
        finally:
            conn.close()

    def delete_candidate(self, candidate_id: str):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM CANDIDATES WHERE ID = %s", (candidate_id,))
        finally:
            conn.close()
