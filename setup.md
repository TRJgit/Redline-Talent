# Local Setup Guide | Redline Talent

Follow these instructions to get the Redline Agentic Recruiter running on your local machine.

## 1. Prerequisites
- **Python 3.10+**
- **Git**
- **Supabase Account** (or any PostgreSQL instance)
- **Google AI Studio API Key** (for Gemma 3 4B-IT access)

## 2. Clone the Repository
```bash
git clone https://github.com/TRJgit/Redline-Talent.git
cd Redline-Talent
```

## 3. Environment Configuration
Create a `.env` file in the root directory and add the following:
```env
Gemini_API_Key=your_google_ai_studio_key
SUPABASE_DB_URL=your_postgresql_connection_string
SENDER_EMAIL=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
```
*Note: For `EMAIL_PASSWORD`, use a Google App Password if using Gmail and enable 2-step Verification.*

## 4. Virtual Environment & Dependencies
It is recommended to use a virtual environment:
```bash
# Create environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## 5. Database Initialization
The system uses `db_manager.py` to automatically initialize tables upon the first connection. You do not need to run manual SQL scripts; simply starting the app will create the `JOBS`, `CANDIDATES`, `RECRUITER_MEMORY`, and `ACTION_HISTORY` tables in your Supabase instance.

## 6. Running the Application
Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

## 7. Troubleshooting
- **Model Errors**: Ensure your Gemini API Key has access to `gemma-3-4b-it`. 
- **Database Connection**: If you get a connection error, verify that your `SUPABASE_DB_URL` includes the correct password and that your local IP is allowed in the Supabase "Network Restrictions" settings.
- **Port Conflicts**: Streamlit defaults to port 8501. If it's busy, use `streamlit run app.py --server.port 8502`.
