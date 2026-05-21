from backend.services import groq_parser


def test_resume_parser_uses_local_fallback_without_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    groq_parser._client = None

    result = groq_parser.parse_resume(
        """
        Jane Doe
        jane@example.com | +1 415 555 0134
        Professional Summary: Backend engineer with 3+ years experience building APIs.
        Skills: Python, FastAPI, Docker, SQL, PostgreSQL
        Experience:
        Software Engineer - Acme (Jan 2022 - Dec 2024)
        - Developed FastAPI REST APIs with PostgreSQL.
        - Reduced API latency by 40% using indexes.
        Projects:
        ATS Analyzer
        - Built a resume analyzer with Python and Docker.
        Education:
        Bachelor of Technology, Example University, 2021
        """
    )

    assert result["parser_source"] == "local_regex"
    assert result["confidence"] == 0.58
    assert {"Python", "FastAPI", "Docker", "SQL"}.issubset(set(result["skills"]))
    assert result["experience"][0]["duration_months"] >= 36
    assert "Developed FastAPI" in result["experience"][0]["description"]
    assert "developed" in result["action_verbs"]


def test_job_description_parser_uses_local_fallback_without_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    groq_parser._client = None

    result = groq_parser.parse_job_description(
        """
        Title: Backend Engineer
        Required: Python, FastAPI, Docker, SQL and PostgreSQL.
        Preferred: AWS and Kubernetes.
        Responsibilities:
        - Build REST APIs for customer-facing systems.
        - Improve service reliability.
        3+ years of backend engineering experience required.
        Bachelor's degree preferred.
        """
    )

    assert result["parser_source"] == "local_regex"
    assert {"Python", "FastAPI", "Docker"}.issubset(set(result["required_skills"]))
    assert "AWS" in result["preferred_skills"]
    assert result["experience_required"].startswith("3+ years")
    assert result["key_responsibilities"]


def test_fallback_parser_handles_malformed_unicode(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    groq_parser._client = None

    result = groq_parser.parse_resume(
        "John Dœ • Pythøn • डेवलपर • 数据科学 \ud83d\x00\n"
        "Skills: Python, Docker"
    )

    assert result["parser_source"] == "local_regex"
    assert "Python" in result["skills"]


def test_fallback_parser_returns_defaults_for_empty_text(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    groq_parser._client = None

    resume = groq_parser.parse_resume("")
    jd = groq_parser.parse_job_description("")

    assert resume["name"] == ""
    assert resume["skills"] == []
    assert resume["experience"] == []
    assert resume["parser_source"] == "local_regex"
    assert jd["required_skills"] == []
    assert jd["keywords"] == []
    assert jd["parser_source"] == "local_regex"
