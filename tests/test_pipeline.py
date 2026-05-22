import io
import time
from types import SimpleNamespace

from docx import Document
from pypdf import PdfWriter

from backend.services import resume_parser

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def make_docx_bytes(lines):
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def make_blank_pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def post_docx(client, monkeypatch, lines, job_description=""):
    monkeypatch.setattr(resume_parser.magic, "from_buffer", lambda *_args, **_kwargs: DOCX_MIME)
    return client.post(
        "/api/v1/analyze-resume",
        data={"job_description": job_description},
        files={
            "resume": (
                "resume.docx",
                make_docx_bytes(lines),
                DOCX_MIME,
            )
        },
    )


STRONG_RESUME = [
    "Jane Doe",
    "jane@example.com | +1 415 555 0134 | linkedin.com/in/janedoe | github.com/janedoe",
    "Professional Summary: Backend engineer with 4 years of experience building APIs.",
    "Technical Skills: Python, FastAPI, SQL, PostgreSQL, Docker, AWS, React, Git",
    "Experience:",
    "Software Engineer - Acme (Jan 2022 - Dec 2024)",
    "- Developed FastAPI REST APIs serving 10K requests per day.",
    "- Reduced API latency by 40% using PostgreSQL indexes and Redis caching.",
    "- Deployed Docker services on AWS.",
    "Projects:",
    "ATS Analyzer",
    "- Built a resume scoring app with Python, FastAPI, Docker, and SQL.",
    "Education:",
    "Bachelor of Technology, Example University, 2021",
]


def test_analyze_resume_docx_pipeline_with_jd(client, monkeypatch):
    response = post_docx(
        client,
        monkeypatch,
        STRONG_RESUME,
        job_description=(
            "Title: Backend Engineer\n"
            "Required: Python, FastAPI, Docker, PostgreSQL and REST API.\n"
            "Preferred: AWS."
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ATS_score"] > 0
    assert "Python" in body["skills"]
    assert body["jd_match_analysis"] is not None
    assert body["skill_validation_details"]["total"] >= 3

    history = client.get("/api/v1/history")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_analyze_resume_reports_missing_skills(client, monkeypatch):
    response = post_docx(
        client,
        monkeypatch,
        [
            "Alex Candidate",
            "alex@example.com",
            "Experience:",
            "Associate - Local Store (2021 - 2023)",
            "- Helped customers and prepared daily reports.",
            "Education:",
            "Bachelor degree, City College, 2020",
        ],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["skills"] == []
    assert "Missing or Weak Skills Section" in body["issues_summary"]
    assert body["ATS_score"] < 80


def test_analyze_resume_accepts_empty_job_description(client, monkeypatch):
    response = post_docx(client, monkeypatch, STRONG_RESUME, job_description="   ")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["jd_match_analysis"] is None
    assert body["keyword_match"] == 0.0


def test_analyze_resume_rejects_image_only_pdf(client, monkeypatch):
    monkeypatch.setattr(
        resume_parser.magic, "from_buffer", lambda *_args, **_kwargs: "application/pdf"
    )
    monkeypatch.setattr(
        resume_parser,
        "convert_from_bytes",
        lambda *_args, **_kwargs: [object()],
    )
    monkeypatch.setattr(
        resume_parser,
        "pytesseract",
        SimpleNamespace(
            image_to_string=lambda *_args, **_kwargs: "OCR fallback resume with Python, FastAPI, Docker"
        ),
    )

    response = client.post(
        "/api/v1/analyze-resume",
        data={"job_description": ""},
        files={
            "resume": (
                "blank.pdf",
                make_blank_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ATS_score"] >= 0
    assert "Python" in body["skills"]


def test_analyze_resume_performance_smoke(client, monkeypatch):
    start = time.perf_counter()
    response = post_docx(client, monkeypatch, STRONG_RESUME)
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, response.text
    assert 0 <= response.json()["ATS_score"] <= 100
    assert elapsed < 10
