import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services import ats_scorer
import numpy as np


class FakeEmbedder:
    def encode(self, text, convert_to_tensor=False):
        # deterministic pseudo-embedding: map chars to numbers
        arr = np.array([ord(c) % 97 for c in text[:128]], dtype=float)
        if arr.size == 0:
            return np.zeros(64)
        # pad or trim to 64
        if arr.size < 64:
            arr = np.pad(arr, (0, 64 - arr.size))
        else:
            arr = arr[:64]
        return arr


embedder = FakeEmbedder()

# Test validate_skills_with_projects
skills = ["Python", "FastAPI", "Docker", "Kubernetes"]
projects = [
    {"title": "Project A", "description": "Built APIs using FastAPI and Python"},
    {"title": "Infra", "description": "Containerized with Docker and deployed to Kubernetes"},
]
experience = [
    {
        "job_title": "Dev",
        "company": "ACME",
        "description": "Worked on backend using Python and FastAPI",
    }
]

validation = ats_scorer.validate_skills_with_projects(
    skills, projects, experience, embedder, threshold=0.2
)
print("Skill validation:", validation)

# Test formatting score
parsed_resume = {
    "experience": experience,
    "education": [{"degree": "BS"}],
    "skills": skills,
    "professional_summary": "Experienced backend dev",
    "projects": projects,
}
text = "\n".join(["• did X", "• did Y"])
format_score = ats_scorer._calc_formatting_score(parsed_resume, text)
print("Formatting score:", format_score)

# Test keywords score
resume_keywords = ["FastAPI", "Python", "SQL", "Docker", "Kubernetes"]
jd_keywords = ["Python", "FastAPI", "SQL", "AWS"]
kw_score = ats_scorer._calc_keywords_score(resume_keywords, skills, jd_keywords)
print("Keywords score:", kw_score)

# Test content score
action_verbs = ["Developed", "Built", "Led"]
grammar_results = {"penalty_applied": 0.0, "total_errors": 0, "critical_errors": []}
content_score = ats_scorer._calc_content_score(
    "Developed API serving 1000 users", action_verbs, grammar_results
)
print("Content score:", content_score)

# Location results
location_results = {"penalty_applied": 0.0, "privacy_risk": "none"}

# Combine into overall
overall = ats_scorer.calculate_overall_score(
    "Developed API serving 1000 users",
    parsed_resume,
    skills,
    resume_keywords,
    action_verbs,
    validation,
    grammar_results,
    location_results,
    jd_keywords,
)
print("Overall:", overall)

# Interpretations
print("Interpretation:", overall["overall_interpretation"])
