import json
import os
import re
import time
import random
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import errors
from dotenv import load_dotenv
from send_mail import send_outreach_email

load_dotenv()

# --- STEP 1: Strict Pydantic Schemas ---

class CandidateProject(BaseModel):
    name: str
    description: str

class CandidateMetadata(BaseModel):
    last_active_days_ago: int = Field(default=0)
    willing_to_relocate: bool = Field(default=True)
    open_to_work: bool = Field(default=True)

class Candidate(BaseModel):
    id: str = Field(description="Unique ID like CAND_001")
    name: str
    email: str = Field(description="Email address extracted from the resume or default")
    current_role: str
    years_of_experience: int
    skills: List[str]
    projects: List[CandidateProject]
    metadata: CandidateMetadata

class RubricCategory(BaseModel):
    category_name: str
    weight_percentage: int
    reasoning_for_weight: str

class JDRubric(BaseModel):
    categories: List[RubricCategory] = Field(description="List of grading categories, weights MUST sum to 100")
    keywords: List[str] = Field(description="Top 10 critical technical keywords or skills extracted from the JD")
    related_concepts: Dict[str, List[str]] = Field(description="Mapping of primary keywords to their synonyms or related technologies (e.g., 'Python': ['Django', 'FastAPI', 'Flask'])")

class ScoredCandidate(BaseModel):
    fit_score: int = Field(default=0, description="Score 1-100. Use the preliminary score if no change needed.")
    interest_score: int = Field(default=0, description="Score 1-100. Use the preliminary score if no change needed.")
    xai_pros: List[str] = Field(description="2 specific points of alignment")
    xai_cons: List[str] = Field(description="1-2 missing elements or risks")
    summary_reasoning: str = Field(description="Punchy, 2-sentence Chain-of-Thought explaining the final score")

class AuditedEvaluation(BaseModel):
    is_hallucination: bool
    bias_detected: bool
    auditor_notes: str = Field(description="Brief note on accuracy or bias")
    adjusted_fit_score: int

class OutreachDraft(BaseModel):
    personal_message: str = Field(description="Highly personalized outreach message under 150 words")

class UnifiedAnalysis(BaseModel):
    evaluation_xai: ScoredCandidate
    audit: AuditedEvaluation
    outreach: OutreachDraft

# --- STEP 2: Foundational Gemini LLM Functions ---

class AdaptiveRecruiterEngine:
    def __init__(self, api_key: str = None):
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("Gemini_API_Key")
            except ImportError:
                pass
        
        self.api_key = api_key or os.getenv("Gemini_API_Key")
        if not self.api_key:
            raise ValueError("API Key not found. Please set Gemini_API_Key in .env or streamlit secrets.")
            
        self.client = genai.Client(api_key=self.api_key)
        self.primary_model = "gemma-3-4b-it"

    def _generate_with_fallback(self, prompt: str, schema: Any, stats: Dict[str, int] = None) -> Any:
        """Generates content and manually parses JSON since JSON mode is not supported on this model."""
        if stats is not None: stats["total"] += 1
        
        max_retries = 3
        backoff_base = 2
        
        # Inject JSON instruction into prompt
        json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY a valid JSON object matching this schema. Do not include markdown formatting like ```json or extra text.\nSCHEMA: {schema.model_json_schema()}"
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.primary_model,
                    contents=json_prompt
                )
                
                text = response.text
                # Try to find JSON block
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    parsed_dict = json.loads(json_str)
                    if stats is not None: stats["success"] += 1
                    return schema.model_validate(parsed_dict)
                else:
                    # Try direct load if no braces found (though unlikely for valid JSON)
                    parsed_dict = json.loads(text.strip())
                    if stats is not None: stats["success"] += 1
                    return schema.model_validate(parsed_dict)

            except Exception as e:
                if ("429" in str(e) or "503" in str(e)) and attempt < max_retries - 1:
                    wait_time = (backoff_base ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                
                print(f"❌ Gemini Error: {e}")
                raise e

    def strategist_parse_jd(self, jd_input: str, recruiter_memory: Dict[str, Any], stats: Dict[str, int] = None) -> JDRubric:
        """Analyze JD and Recruiter Memory to generate a weighted rubric."""
        prompt = f"""        
        You are the 'Strategist Agent'. Your goal is to create a grading rubric that adapts to the recruiter's evolving style.
        
        RECRUITER'S LEARNED PREFERENCES (Historical Feedback):
        {json.dumps(recruiter_memory)}
        
        JOB DESCRIPTION:
        {jd_input}
        
        CRITICAL LOGIC:
        1. Analyze the 'Learned Preferences'. If the recruiter has frequently rejected candidates for a specific reason (e.g., "lack of Python"), increase the weight of that category.
        2. If the recruiter has praised specific traits, ensure those are represented in the rubric.
        3. The sum of weights MUST equal 100.
        4. Provide clear 'reasoning_for_weight' that references the recruiter's memory if applicable.
        5. Extract the top 10 most important technical 'keywords'.
        6. For each keyword, provide a list of 'related_concepts' (synonyms, frameworks, or parent technologies) to allow for semantic flexibility during scoring.
        """
        
        try:
            return self._generate_with_fallback(prompt, JDRubric, stats)
        except Exception as e:
            return JDRubric(
                categories=[
                    RubricCategory(category_name="Technical Skills", weight_percentage=50, reasoning_for_weight=f"Fallback due to error: {str(e)}"),
                    RubricCategory(category_name="Experience", weight_percentage=50, reasoning_for_weight="Standard assessment criteria.")
                ],
                keywords=["Python", "FastAPI", "React", "Node.js"],
                related_concepts={"Python": ["Django", "Flask"], "React": ["Next.js", "Redux"]}
            )

    def discovery_scout_candidates(self, rubric: JDRubric, candidates: List[Dict[str, Any]], min_fit: int = 40) -> List[Dict[str, Any]]:
        """
        Enhanced 'Scout Agent' Logic:
        1. Overlap Coefficient: Better for matching requirements than Jaccard.
        2. Ontological Credit: Partial points for related technologies.
        3. Semantic Saturation (BM25-like): Diminishing returns for keyword repetition.
        """
        processed_candidates = []
        keywords = [k.lower() for k in rubric.keywords]
        related = {k.lower(): [v.lower() for v in vals] for k, vals in rubric.related_concepts.items()}

        for cand in candidates:
            # --- 1. OVERLAP SKILL SIMILARITY (Max 50 points) ---
            cand_skills = set([s.lower() for s in cand.get('skills', [])])
            jd_skills = set(keywords)
            
            # Intersection (Direct matches)
            direct_matches = cand_skills.intersection(jd_skills)
            
            # Ontological matches (Partial credit for related concepts)
            semantic_matches = 0
            remaining_jd = jd_skills - direct_matches
            for jd_k in remaining_jd:
                related_to_k = set(related.get(jd_k, []))
                if cand_skills.intersection(related_to_k):
                    semantic_matches += 0.8 # 80% credit for related technology
            
            # Overlap Coefficient Logic: (Matches / JD_Requirement_Count)
            match_total = len(direct_matches) + semantic_matches
            overlap_score = (match_total / max(1, len(jd_skills))) * 100
            
            # Skill Score contributes up to 50 points
            skill_score = min(50, overlap_score * 0.5)
            
            # --- 2. EXPERIENCE ALIGNMENT (Max 30 points) ---
            fit_score = skill_score
            is_senior_role = any(k in ['senior', 'lead', 'architect', 'principal'] for k in keywords)
            exp = cand.get('years_of_experience', 0)
            if is_senior_role:
                if exp >= 7: fit_score += 30
                elif exp >= 5: fit_score += 20
                elif exp >= 3: fit_score += 10
            else:
                if exp >= 3: fit_score += 30
                elif exp >= 1: fit_score += 20
                else: fit_score += 10
            
            # --- 3. ROLE/PROJECT SATURATION (Max 20 points) ---
            cand_text = " ".join([(p.get('description') or "").lower() for p in cand.get('projects', [])])
            cand_text += " " + (cand.get('current_role') or "").lower()
            
            project_points = 0
            for k in keywords:
                count = cand_text.count(k)
                if count > 0:
                    # Logarithmic-style saturation: 1st mention = 5pt, 2nd = 3pt, 3rd+ = 2pt
                    project_points += min(10, 5 + (count - 1) * 3 if count > 1 else 5)
            
            fit_score += min(20, project_points)
            final_fit = min(100, int(fit_score))

            # --- 4. INTEREST SCORE (Deterministic) ---
            interest_score = 50 
            meta = cand.get('metadata', {})
            if meta.get('open_to_work'): interest_score += 20
            if meta.get('willing_to_relocate'): interest_score += 10
            
            activity_days = meta.get('last_active_days_ago', 30)
            if activity_days <= 3: interest_score += 20
            elif activity_days <= 7: interest_score += 10
            elif activity_days > 20: interest_score -= 10
            
            final_interest = min(100, max(0, int(interest_score)))

            if final_fit >= min_fit:
                cand_copy = cand.copy()
                cand_copy['scout_fit_score'] = final_fit
                cand_copy['scout_interest_score'] = final_interest
                processed_candidates.append(cand_copy)

        return sorted(processed_candidates, key=lambda x: x['scout_fit_score'], reverse=True)

    def unified_candidate_analysis(self, rubric: JDRubric, candidate: Dict[str, Any], jd_input: str, stats: Dict[str, int] = None) -> UnifiedAnalysis:
        """API call for Semantic Cross-Encoding, XAI and Outreach generation."""
        prompt = f"""
        You are the 'Semantic Cross-Encoder & Auditor'. 
        
        CONTEXT:
        CANDIDATE: {json.dumps(candidate)}
        JOB DESCRIPTION: {jd_input[:1000]}
        RUBRIC: {json.dumps(rubric.model_dump() if hasattr(rubric, 'model_dump') else rubric)}
        
        PRELIMINARY SCORES:
        - Fit Score: {candidate.get('scout_fit_score')}%
        - Interest Score: {candidate.get('scout_interest_score')}%

        TASK:
        Perform a deep semantic analysis. You MUST return a JSON object with EXACTLY three top-level keys:
        1. "evaluation_xai": Object containing "fit_score", "interest_score", "xai_pros" (list of 2), "xai_cons" (list of 2), "summary_reasoning" (2 sentences).
        2. "audit": Object containing "is_hallucination" (bool), "bias_detected" (bool), "auditor_notes" (string), "adjusted_fit_score" (int).
        3. "outreach": Object containing "personal_message" (string).

        Be critical. If the Scout's preliminary Fit Score is too high or too low, correct it in the "adjusted_fit_score".
        """
        try:
            return self._generate_with_fallback(prompt, UnifiedAnalysis, stats)
        except Exception as e:
            eval_xai = ScoredCandidate(
                fit_score=candidate.get('scout_fit_score', 50),
                interest_score=candidate.get('scout_interest_score', 50),
                xai_pros=["Match found by Scout"],
                xai_cons=["API Error"],
                summary_reasoning="XAI generation failed."
            )
            audit_fallback = AuditedEvaluation(is_hallucination=False, bias_detected=False, auditor_notes="N/A", adjusted_fit_score=candidate.get('scout_fit_score', 50))
            outreach_fallback = OutreachDraft(personal_message=f"Hi {candidate.get('name', 'there')}, I'd love to chat! [Recruiter Name]")
            return UnifiedAnalysis(evaluation_xai=eval_xai, audit=audit_fallback, outreach=outreach_fallback)
    
    

    def execute_mail_agent(self, receiver_email: str, subject: str, body_text: str, simulate: bool = False) -> str:
        """
        The Mail Agent: Sends a tailored outreach email to the candidate.
        """
        # Convert plaintext draft to simple HTML here before passing it to send_mail
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #DB3434;">Redline Talent Discovery</h2>
                    <p>{body_text.replace('\n', '<br>')}</p>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <p style="font-size: 0.8rem; color: #777;">This message was generated by the Redline Agentic Discovery system.</p>
                </div>
            </body>
        </html>
        """
        
        # Offload the actual sending to your dedicated script
        return send_outreach_email(receiver_email, subject, html_body, simulate)

    def parser_extract_candidate(self, resume_text: str, candidate_id: str, stats: Dict[str, int] = None) -> Candidate:
        """Enhanced parser to extract email from resume."""
        prompt = f"""
        Extract candidate information from the following resume text.
        RESUME TEXT: {resume_text}
        CANDIDATE ID: {candidate_id}
        
        CRITICAL: Extract the candidate's email address if present. If not found, use 'candidate@example.com'.
        """
        try:
            return self._generate_with_fallback(prompt, Candidate, stats)
        except Exception as e:
            return Candidate(
                id=candidate_id, name="Unknown Candidate", email="unknown@example.com",
                current_role="Unknown", years_of_experience=0, skills=[], projects=[], metadata=CandidateMetadata()
            )
