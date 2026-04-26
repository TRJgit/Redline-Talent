# Redline Talent | High-Performance Agentic Recruiter

Redline Talent is an advanced, AI-driven talent discovery platform designed to automate and enhance the recruitment lifecycle. Built on a "First Principles" reasoning engine, it transforms static job descriptions into dynamic evaluation rubrics and performs deep-dive candidate analysis using Google's Gemma 3 models and advanced similarity heuristics.

---

## System Architecture & Data Integrity

Redline Talent uses a modern Native Multi-Page Streamlit architecture. To ensure production-grade persistence and scalability, all data is centralized in a **Supabase (PostgreSQL) Backend**, ensuring:
*   Transactional Integrity: All imports, job creations, and feedback loops are ACID-compliant.
*   Cloud Persistence: Data persists across deployments, sessions, and devices.
*   Decoupled Pages: Each module (Dashboard, Jobs, Candidates, Discovery) is optimized for specific recruitment workflows.

---

## Multi-Agent Architecture

### 1. The Strategist Agent
**Core Function**: Context-Aware Rubric & Ontological Generation  
The Strategist analyzes the Job Description (JD) and the Recruiter’s Memory. It generates a weighted grading rubric and an Ontological Map—a dictionary of synonyms and related frameworks (e.g., identifying "Django" as a relative of "Python") to ensure semantic flexibility.

### 2. The Scout Agent
**Core Function**: High-Throughput Requirement Matching  
**Mechanism**: Overlap Coefficient & BM25-like Saturation  
The Scout performs the initial screening. It uses the Overlap Coefficient to measure how many JD requirements a candidate meets, ensuring they aren't penalized for having additional skills outside the JD. It also applies BM25-inspired Saturation, where repeated mentions of a skill have diminishing returns to prevent "keyword stuffing."

### 3. The Parser Agent
**Core Function**: Semantic Entity Extraction  
Transforms raw PDF/DOCX resumes into structured data stored in the centralized database.

### 4. The Semantic Cross-Encoder (Auditor)
**Core Function**: High-Precision Validation  
A deep-intelligence layer that performs a "Cross-Encoder" analysis. It evaluates the Contextual Quality of experience, verifying if the candidate's project impact truly aligns with the JD's requirements, and can issue an adjusted fit score.

### 5. The Mail Agent
**Core Function**: Automated Outreach Delivery  
Generates professional HTML-styled outreach emails and logs all communication events to the action history.

---

## ML & Similarity Methodology

Redline Talent utilizes a hybrid architecture of Agentic LLMs and Advanced Heuristic Similarity techniques to ensure high-accuracy talent matching.

### A. Overlap Coefficient (Requirement Matching)
We calculate the overlap between a candidate's skills and the JD requirements. Unlike Jaccard, which penalizes candidates for having a large breadth of skills, the Overlap Coefficient focuses strictly on how much of the "requested" set is satisfied. This recognizes that a "Full-Stack Engineer" with 50 skills is not a worse fit for a "React Developer" role than someone with only 5 skills, provided they both have the React requirement.

### B. BM25-Inspired Saturation (Project Relevance)
We evaluate the frequency of JD keywords within project descriptions using logarithmic term frequency scoring. The first mention of a skill provides a high score, while subsequent mentions provide diminishing returns. This rewards candidates who have used a skill across multiple projects (demonstrating depth) while preventing "Keyword Stuffing" from artificially inflating scores.

### C. Semantic Cross-Encoding (The Auditor)
While standard vector search looks at resumes and JDs separately, our Auditor Agent acts as a Cross-Encoder. It processes the JD and the Candidate profile simultaneously within the same attention window to understand contextual nuance and high-impact experience.

---

## Key Features

*   **Command Center**: Real-time metrics on active listings, total applicants, and pipeline health with a chronological action history.
*   **Job Specification Management**: Create and manage high-fidelity job descriptions with Markdown support.
*   **Candidate Pool**: Centralized directory with project-first profiles and automated entity extraction from resumes.
*   **Agentic Discovery**: Intelligent matching engine that ranks candidates by both Fit Match (skill alignment) and Interest Pulse (likelihood of engagement).

---

## Technical Stack

*   **Frontend**: Streamlit (Python)
*   **Intelligence**: Google Gemma 3 4B-IT
*   **Database**: Supabase (PostgreSQL)
*   **Data Validation**: Pydantic
*   **Parsing**: PyMuPDF & python-docx

---

## Setup & Installation

1. **Clone & Install**
   ```bash
   git clone <repository-url>
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file:
   ```env
   Gemini_API_Key=your_key
   SUPABASE_DB_URL=your_postgresql_uri
   SENDER_EMAIL=your_email
   EMAIL_PASSWORD=your_app_password
   ```

3. **Run Application**
   ```bash
   streamlit run app.py
   ```
