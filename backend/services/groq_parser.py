import os
import json
import logging
import re
from datetime import date
from typing import Dict, Iterable

from groq import Groq

logger = logging.getLogger("ats_resume_scorer")


GROQ_MODEL = "llama-3.3-70b-versatile"

_client = None

COMMON_SKILLS = {
    ".NET",
    "AWS",
    "Azure",
    "C#",
    "C++",
    "CSS",
    "Django",
    "Docker",
    "Excel",
    "Express",
    "FastAPI",
    "Flask",
    "GCP",
    "Git",
    "GitHub",
    "HTML",
    "Java",
    "JavaScript",
    "Jenkins",
    "Kubernetes",
    "Linux",
    "Machine Learning",
    "MongoDB",
    "MySQL",
    "Next.js",
    "Node.js",
    "NumPy",
    "Pandas",
    "PostgreSQL",
    "Power BI",
    "PyTorch",
    "Python",
    "React",
    "Redis",
    "REST API",
    "SQL",
    "Scikit-learn",
    "Spark",
    "Streamlit",
    "Tableau",
    "TensorFlow",
    "TypeScript",
}

ACTION_VERBS = {
    "achieved",
    "automated",
    "built",
    "created",
    "delivered",
    "deployed",
    "designed",
    "developed",
    "implemented",
    "improved",
    "increased",
    "launched",
    "led",
    "managed",
    "migrated",
    "optimized",
    "reduced",
    "scaled",
    "shipped",
}

SECTION_ALIASES = {
    "professional_summary": {
        "summary",
        "professional summary",
        "profile",
        "about me",
        "objective",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "technologies",
        "tools",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "internships",
    },
    "education": {
        "education",
        "academic background",
        "academics",
    },
    "certifications": {
        "certifications",
        "certificates",
        "licenses",
    },
    "projects": {
        "projects",
        "personal projects",
        "academic projects",
    },
    "key_responsibilities": {
        "responsibilities",
        "key responsibilities",
        "what you will do",
        "role responsibilities",
    },
}

HEADING_TO_SECTION = {
    alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}

STOP_WORDS = {
    "and",
    "for",
    "from",
    "have",
    "into",
    "that",
    "the",
    "this",
    "with",
    "will",
    "work",
    "your",
}

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _get_client() -> Groq | None:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            logger.info("GROQ_API_KEY is not set; using local regex parser fallback.")
            return None
        _client = Groq(api_key=api_key)
    return _client


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\x00", " ")).strip()


def _clean_heading(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"^[^\w.+#]+|[^\w.+#]+$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {key: [] for key in SECTION_ALIASES}
    current: str | None = None

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading_candidate = _clean_heading(line.rstrip(":"))
        inline_heading = None
        inline_rest = ""

        if ":" in line:
            before, after = line.split(":", 1)
            before_clean = _clean_heading(before)
            if before_clean in HEADING_TO_SECTION:
                inline_heading = HEADING_TO_SECTION[before_clean]
                inline_rest = after.strip()

        if heading_candidate in HEADING_TO_SECTION:
            current = HEADING_TO_SECTION[heading_candidate]
            continue

        if inline_heading:
            current = inline_heading
            if inline_rest:
                sections[current].append(inline_rest)
            continue

        if current:
            sections[current].append(raw_line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = _normalize_space(str(value)).strip(" ,;:-")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _skill_present(normalized_text: str, skill: str) -> bool:
    normalized_skill = skill.lower()
    pattern = rf"(?<![\w.+#-]){re.escape(normalized_skill)}(?![\w.+#-])"
    return re.search(pattern, normalized_text) is not None


def _extract_known_skills(text: str) -> list[str]:
    normalized_text = _normalize_space(text).lower()
    return sorted(
        (skill for skill in COMMON_SKILLS if _skill_present(normalized_text, skill)),
        key=str.lower,
    )


def _extract_contact(text: str) -> dict[str, str | None]:
    email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text or "")
    phone_match = re.search(
        r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}",
        text or "",
    )
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s,;]+", text or "", re.I)
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[^\s,;]+", text or "", re.I)

    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
    }


def _guess_name(text: str) -> str:
    for raw_line in (text or "").splitlines()[:8]:
        line = raw_line.strip(" \t|,-")
        if not line:
            continue
        lower_line = _clean_heading(line)
        if lower_line in HEADING_TO_SECTION:
            continue
        if re.search(r"@|https?://|linkedin\.com|github\.com|\d{4,}", line, re.I):
            continue
        if 1 <= len(line.split()) <= 5:
            return line
    return ""


def _extract_summary(text: str, sections: dict[str, str]) -> str:
    if sections.get("professional_summary"):
        return _normalize_space(sections["professional_summary"])

    paragraphs = [
        _normalize_space(paragraph)
        for paragraph in re.split(r"\n\s*\n", text or "")
        if _normalize_space(paragraph)
    ]
    for paragraph in paragraphs[1:3]:
        if len(paragraph.split()) >= 8 and not re.search(
            r"@|linkedin\.com|github\.com", paragraph, re.I
        ):
            return paragraph
    return ""


def _extract_action_verbs(text: str) -> list[str]:
    verbs = []
    for line in (text or "").splitlines():
        match = re.match(r"^\s*(?:[•*\-]|\d+\.)\s*([A-Za-z]+)", line)
        if match and match.group(1).lower() in ACTION_VERBS:
            verbs.append(match.group(1).lower())

    lowered = f" {_normalize_space(text).lower()} "
    for verb in ACTION_VERBS:
        if f" {verb} " in lowered:
            verbs.append(verb)
    return _unique_preserve_order(verbs)


def _extract_years_of_experience(text: str) -> float:
    values = []
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience",
        r"(?:experience|exp)\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text or "", re.I):
            try:
                values.append(float(match.group(1)))
            except ValueError:
                continue
    return max(values, default=0.0)


def _month_index(month: str, year: str) -> int:
    return int(year) * 12 + MONTHS[month.lower()[:3]]


def _year_index(year: str) -> int:
    return int(year) * 12 + 1


def _calculate_date_range_months(text: str) -> int:
    total = 0
    month_pattern = "|".join(sorted(MONTHS.keys(), key=len, reverse=True))
    month_range = re.compile(
        rf"\b({month_pattern})\.?\s+(\d{{4}})\s*(?:-|–|—|to)\s*"
        rf"((?:{month_pattern})\.?\s+\d{{4}}|present|current)\b",
        re.I,
    )
    year_range = re.compile(
        r"\b(19\d{2}|20\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)\b", re.I
    )

    today = date.today()
    current_index = today.year * 12 + today.month

    for match in month_range.finditer(text or ""):
        start = _month_index(match.group(1), match.group(2))
        end_raw = match.group(3).lower()
        if end_raw in {"present", "current"}:
            end = current_index
        else:
            end_month, end_year = re.match(
                rf"({month_pattern})\.?\s+(\d{{4}})", end_raw, re.I
            ).groups()
            end = _month_index(end_month, end_year)
        total += max(0, end - start + 1)

    if total:
        return total

    for match in year_range.finditer(text or ""):
        start = _year_index(match.group(1))
        end_raw = match.group(2).lower()
        end = current_index if end_raw in {"present", "current"} else int(end_raw) * 12 + 12
        total += max(0, end - start + 1)

    return total


def _extract_experience_entries(text: str, sections: dict[str, str]) -> list[dict]:
    experience_text = sections.get("experience") or ""
    explicit_years = _extract_years_of_experience(text)
    duration_months = _calculate_date_range_months(experience_text or text)
    if not duration_months and explicit_years:
        duration_months = int(round(explicit_years * 12))

    if not experience_text and duration_months:
        experience_text = text

    if not experience_text.strip() and not duration_months:
        return []

    first_line = next(
        (line.strip(" •*-") for line in experience_text.splitlines() if line.strip()), ""
    )
    return [
        {
            "job_title": first_line[:80],
            "company": "",
            "start_date": "",
            "end_date": "",
            "duration_months": duration_months,
            "description": experience_text.strip(),
        }
    ]


def _extract_education(text: str, sections: dict[str, str]) -> list[dict]:
    education_text = sections.get("education") or ""
    degree_match = re.search(
        r"\b(B\.?Tech|BTech|B\.?E\.?|Bachelor(?:'s)?|M\.?Tech|MTech|Master(?:'s)?|MBA|PhD|Diploma)\b[^\n,;]*",
        education_text or text or "",
        re.I,
    )
    if not education_text and not degree_match:
        return []

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", education_text or text or "")
    institution = ""
    for line in education_text.splitlines():
        if re.search(r"university|college|institute|school", line, re.I):
            institution = line.strip()
            break

    return [
        {
            "degree": _normalize_space(degree_match.group(0)) if degree_match else "",
            "institution": _normalize_space(institution),
            "year": year_match.group(1) if year_match else "",
        }
    ]


def _extract_projects(sections: dict[str, str]) -> list[dict]:
    project_text = sections.get("projects") or ""
    if not project_text:
        return []

    title = next(
        (line.strip(" •*-") for line in project_text.splitlines() if line.strip()), "Project"
    )
    return [
        {
            "title": title[:100],
            "description": project_text,
            "technologies": _extract_known_skills(project_text),
        }
    ]


def _extract_certifications(text: str, sections: dict[str, str]) -> list[str]:
    cert_text = sections.get("certifications") or ""
    candidates = []
    for line in cert_text.splitlines():
        candidates.extend(re.split(r"[,;|]", line))

    for match in re.finditer(
        r"\b(?:AWS|Azure|Google|Microsoft|Certified)[^\n,;]{0,80}", text or "", re.I
    ):
        candidates.append(match.group(0))

    return _unique_preserve_order(candidates)[:10]


def _extract_keywords(text: str, skills: list[str], action_verbs: list[str]) -> list[str]:
    candidates = [*skills, *action_verbs]
    phrase_pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9+#.-]*(?:\s+[A-Za-z][A-Za-z0-9+#.-]*){0,2}\b")
    for match in phrase_pattern.finditer(text or ""):
        phrase = _normalize_space(match.group(0))
        words = phrase.lower().split()
        if len(phrase) < 4 or all(word in STOP_WORDS for word in words):
            continue
        if len(words) == 1 and words[0] in STOP_WORDS:
            continue
        candidates.append(phrase)
    return _unique_preserve_order(candidates)[:40]


def _local_basic_parse_resume(raw_text: str) -> Dict:
    text = (raw_text or "").replace("\x00", " ")
    sections = _split_sections(text)
    contact = _extract_contact(text)
    skills = _extract_known_skills(text)
    action_verbs = _extract_action_verbs(text)

    result = {
        "name": _guess_name(text),
        **contact,
        "professional_summary": _extract_summary(text, sections),
        "skills": skills,
        "experience": _extract_experience_entries(text, sections),
        "education": _extract_education(text, sections),
        "certifications": _extract_certifications(text, sections),
        "projects": _extract_projects(sections),
        "action_verbs": action_verbs,
        "keywords": _extract_keywords(text, skills, action_verbs),
        "parser_source": "local_regex",
        "confidence": 0.58,
    }
    return _validate_resume_result(result)


def _extract_jd_title(text: str) -> str:
    for pattern in [
        r"(?:job\s*title|title|role)\s*[:\-]\s*([^\n]+)",
        r"^\s*([A-Z][A-Za-z0-9 /+-]{3,80})\s*$",
    ]:
        match = re.search(pattern, text or "", re.I | re.M)
        if match:
            return _normalize_space(match.group(1))
    return ""


def _extract_requirement_line_skills(text: str, markers: tuple[str, ...]) -> list[str]:
    lines = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in markers):
            lines.append(line)
    return _extract_known_skills("\n".join(lines))


def _extract_key_responsibilities(text: str, sections: dict[str, str]) -> list[str]:
    source = sections.get("key_responsibilities") or text or ""
    responsibilities = []
    for line in source.splitlines():
        cleaned = line.strip(" •*-")
        if len(cleaned.split()) >= 4 and (
            re.match(r"^\s*(?:[•*\-]|\d+\.)", line)
            or re.search(
                r"\b(?:build|develop|design|manage|lead|own|collaborate|implement)\b", cleaned, re.I
            )
        ):
            responsibilities.append(cleaned)
    return _unique_preserve_order(responsibilities)[:12]


def _local_basic_parse_jd(raw_text: str) -> Dict:
    text = (raw_text or "").replace("\x00", " ")
    sections = _split_sections(text)
    all_skills = _extract_known_skills(text)
    required_skills = _extract_requirement_line_skills(
        text,
        ("required", "must have", "must-have", "requirements", "need", "proficient"),
    )
    preferred_skills = _extract_requirement_line_skills(
        text,
        ("preferred", "nice to have", "nice-to-have", "bonus", "plus"),
    )

    if not required_skills:
        required_skills = all_skills

    education_match = re.search(
        r"\b(?:Bachelor(?:'s)?|Master(?:'s)?|B\.?Tech|M\.?Tech|MBA|PhD|degree)[^\n.;]*",
        text,
        re.I,
    )
    experience_match = re.search(r"\d+(?:\.\d+)?\+?\s*(?:years?|yrs?)[^\n.;]*", text, re.I)
    keywords = _extract_keywords(text, all_skills, [])

    result = {
        "job_title": _extract_jd_title(text),
        "required_skills": required_skills,
        "preferred_skills": [skill for skill in preferred_skills if skill not in required_skills],
        "experience_required": (
            _normalize_space(experience_match.group(0)) if experience_match else ""
        ),
        "education_required": _normalize_space(education_match.group(0)) if education_match else "",
        "key_responsibilities": _extract_key_responsibilities(text, sections),
        "keywords": keywords,
        "parser_source": "local_regex",
        "confidence": 0.58,
    }
    return _validate_jd_result(result)


RESUME_SYSTEM_PROMPT = (
    "You are a resume parser. Extract information from the resume "
    "and return ONLY a valid JSON object. No explanation, no markdown."
)

RESUME_USER_PROMPT = """Extract the following from this resume and return as JSON:
{{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "linkedin": "LinkedIn URL if present, otherwise null",
  "github": "GitHub URL if present, otherwise null",
  "professional_summary": "the full text of the Summary, Profile, About Me, Objective, or Professional Summary section at the top of the resume. Copy the ENTIRE paragraph exactly as written. If no such section exists, return an empty string.",
  "skills": ["list", "of", "skills"],
  "experience": [
    {{
      "job_title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "duration_months": 0,
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": ""
    }}
  ],
  "certifications": ["list of certifications"],
  "projects": [
    {{
      "title": "project name",
      "description": "what the project does and how it was built",
      "technologies": ["tech", "used"]
    }}
  ],
  "action_verbs": ["strong action verbs used in bullet points, e.g. developed, implemented, designed"],
  "keywords": ["important keywords and phrases from the resume for ATS matching"]
}}

Important instructions:
- For duration_months, calculate the number of months between start_date and end_date. If end_date is "Present" or "Current", calculate from start_date to now.
- For skills, extract ALL technical and soft skills mentioned anywhere in the resume.
- For action_verbs, find verbs that start bullet points or describe achievements.
- For keywords, extract noun phrases and technical terms relevant to ATS matching.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Resume Text:
{raw_text}"""


def _call_groq(client: Groq, system_prompt: str, user_prompt: str) -> str:

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=4096,
    )

    return response.choices[0].message.content.strip()


def _try_parse_json(text: str) -> dict | None:

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):

        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1 :]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def parse_resume(raw_text: str) -> Dict:

    client = _get_client()
    if client is None:
        return _local_basic_parse_resume(raw_text)

    prompt = RESUME_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, prompt)
        result = _try_parse_json(raw_response)

        if result is not None:
            return _validate_resume_result(result)

        logger.warning("Groq resume parse: first attempt returned invalid JSON, retrying...")
        strict_prompt = (
            "Your previous response was not valid JSON. "
            "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
            + prompt
        )
        raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, strict_prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_resume_result(result)

        raise ValueError(
            f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
        )
    except Exception as exc:
        logger.warning(f"Groq resume parse failed; using local regex fallback: {exc}")
        return _local_basic_parse_resume(raw_text)


JD_SYSTEM_PROMPT = (
    "You are a job description parser. Extract information and "
    "return ONLY a valid JSON object. No explanation, no markdown."
)

JD_USER_PROMPT = """Extract the following from this job description and return as JSON:
{{
  "job_title": "",
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience_required": "",
  "education_required": "",
  "key_responsibilities": ["list of responsibilities"],
  "keywords": ["important keywords and phrases for ATS matching"]
}}

Important instructions:
- required_skills: skills explicitly stated as required or must-have.
- preferred_skills: skills stated as preferred, nice-to-have, or bonus.
- keywords: extract ALL important terms an ATS system would match against,
  including skills, technologies, certifications, and domain terms.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Job Description Text:
{raw_text}"""


def parse_job_description(raw_text: str) -> Dict:
    client = _get_client()
    if client is None:
        return _local_basic_parse_jd(raw_text)

    prompt = JD_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_groq(client, JD_SYSTEM_PROMPT, prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_jd_result(result)

        logger.warning("Groq JD parse: first attempt returned invalid JSON, retrying...")
        strict_prompt = (
            "Your previous response was not valid JSON. "
            "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
            + prompt
        )
        raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_jd_result(result)

        raise ValueError(
            f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
        )
    except Exception as exc:
        logger.warning(f"Groq JD parse failed; using local regex fallback: {exc}")
        return _local_basic_parse_jd(raw_text)


# it will make sure, that the parse json has all the valid fields we expect
def _validate_jd_result(result: dict) -> dict:

    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    return result


# to make sure the parse json has all the valid json fields
def _validate_resume_result(result: dict) -> dict:

    defaults = {
        "name": "",
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "professional_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "action_verbs": [],
        "keywords": [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default

        # Ensure list fields are actually lists
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    # Validate experience entries
    for exp in result.get("experience", []):
        if not isinstance(exp, dict):
            continue
        exp.setdefault("job_title", "")
        exp.setdefault("company", "")
        exp.setdefault("start_date", "")
        exp.setdefault("end_date", "")
        exp.setdefault("duration_months", 0)
        exp.setdefault("description", "")
        # Ensure duration_months is an int
        try:
            exp["duration_months"] = int(exp["duration_months"])
        except (ValueError, TypeError):
            exp["duration_months"] = 0

    # Validate project entries
    for proj in result.get("projects", []):
        if not isinstance(proj, dict):
            continue
        proj.setdefault("title", "")
        proj.setdefault("description", "")
        proj.setdefault("technologies", [])

    return result
