import sqlite3
import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    sqlite_db = "catalyst.db"
    supabase_url = os.getenv("SUPABASE_DB_URL")

    print("\n" + "="*40)
    print("🚀 SUPABASE MIGRATION TOOL")
    print("="*40 + "\n")

    if not supabase_url:
        print("❌ ERROR: SUPABASE_DB_URL not found in .env file.")
        return

    if not os.path.exists(sqlite_db):
        print(f"⚠️  WARNING: Local SQLite database '{sqlite_db}' not found.")
        local_data_exists = False
    else:
        local_data_exists = True

    print("🔗 Connecting to Supabase...")
    try:
        p_conn = psycopg2.connect(supabase_url)
        print("✅ Successfully connected to Supabase!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    if local_data_exists:
        print("📂 Opening local SQLite database...")
        s_conn = sqlite3.connect(sqlite_db)
        s_conn.row_factory = sqlite3.Row
    else:
        s_conn = None

    try:
        with p_conn:
            with p_conn.cursor() as p_cur:
                print("🛠️  Initializing table structures...")
                p_cur.execute("""
                CREATE TABLE IF NOT EXISTS RECRUITER_MEMORY (
                    ID TEXT PRIMARY KEY, MEMORY_JSON TEXT, UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ACTION_HISTORY (
                    ID TEXT PRIMARY KEY, EVENT_TYPE TEXT, DESCRIPTION TEXT, EVENT_TIME TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS JOBS (
                    ID TEXT PRIMARY KEY, TITLE TEXT, JD TEXT, POSTED_DATE TEXT, APPLICANTS INTEGER, METADATA TEXT
                );
                CREATE TABLE IF NOT EXISTS CANDIDATES (
                    ID TEXT PRIMARY KEY, NAME TEXT, EMAIL TEXT, "current_role" TEXT, YEARS_OF_EXPERIENCE INTEGER, 
                    SKILLS TEXT, PROJECTS TEXT, METADATA TEXT, UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)

                if s_conn:
                    # 1. Migrate RECRUITER_MEMORY
                    print("📤 Migrating RECRUITER_MEMORY...")
                    rows = s_conn.execute("SELECT * FROM RECRUITER_MEMORY").fetchall()
                    for row in rows:
                        p_cur.execute("""
                        INSERT INTO RECRUITER_MEMORY (ID, MEMORY_JSON, UPDATED_AT)
                        VALUES (%s, %s, %s)
                        ON CONFLICT(ID) DO UPDATE SET MEMORY_JSON=EXCLUDED.MEMORY_JSON, UPDATED_AT=EXCLUDED.UPDATED_AT
                        """, (row['ID'], row['MEMORY_JSON'], row['UPDATED_AT']))

                    # 2. Migrate ACTION_HISTORY
                    print("📤 Migrating ACTION_HISTORY...")
                    rows = s_conn.execute("SELECT * FROM ACTION_HISTORY").fetchall()
                    for row in rows:
                        p_cur.execute("""
                        INSERT INTO ACTION_HISTORY (ID, EVENT_TYPE, DESCRIPTION, EVENT_TIME)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT(ID) DO NOTHING
                        """, (row['ID'], row['EVENT_TYPE'], row['DESCRIPTION'], row['EVENT_TIME']))

                    # 3. Migrate JOBS
                    print("📤 Migrating JOBS...")
                    rows = s_conn.execute("SELECT * FROM JOBS").fetchall()
                    for row in rows:
                        p_cur.execute("""
                        INSERT INTO JOBS (ID, TITLE, JD, POSTED_DATE, APPLICANTS, METADATA)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT(ID) DO UPDATE SET 
                            TITLE=EXCLUDED.TITLE, JD=EXCLUDED.JD, POSTED_DATE=EXCLUDED.POSTED_DATE, 
                            APPLICANTS=EXCLUDED.APPLICANTS, METADATA=EXCLUDED.METADATA
                        """, (row['ID'], row['TITLE'], row['JD'], row['POSTED_DATE'], row['APPLICANTS'], row['METADATA']))

                    # 4. Migrate CANDIDATES
                    print("📤 Migrating CANDIDATES...")
                    rows = s_conn.execute("SELECT * FROM CANDIDATES").fetchall()
                    for row in rows:
                        p_cur.execute("""
                        INSERT INTO CANDIDATES (ID, NAME, EMAIL, "current_role", YEARS_OF_EXPERIENCE, SKILLS, PROJECTS, METADATA, UPDATED_AT)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(ID) DO UPDATE SET
                            NAME=EXCLUDED.NAME, EMAIL=EXCLUDED.EMAIL, "current_role"=EXCLUDED."current_role",
                            YEARS_OF_EXPERIENCE=EXCLUDED.YEARS_OF_EXPERIENCE, SKILLS=EXCLUDED.SKILLS,
                            PROJECTS=EXCLUDED.PROJECTS, METADATA=EXCLUDED.METADATA, UPDATED_AT=EXCLUDED.UPDATED_AT
                        """, (row['ID'], row['NAME'], row['EMAIL'], row['CURRENT_ROLE'], 
                              row['YEARS_OF_EXPERIENCE'], row['SKILLS'], row['PROJECTS'], 
                              row['METADATA'], row['UPDATED_AT']))

        print("\n" + "="*40)
        print("🎉 SUCCESS: Migration completed!")
        print("Your project is now using Supabase.")
        print("="*40 + "\n")
    except Exception as e:
        print(f"\n❌ ERROR during migration: {e}")
    finally:
        if s_conn:
            s_conn.close()
        p_conn.close()

if __name__ == "__main__":
    migrate()
