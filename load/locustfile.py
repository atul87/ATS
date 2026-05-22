import io

from docx import Document
from locust import HttpUser, between, task
from pypdf import PdfWriter


def _make_docx_bytes(lines):
    document = Document()
    for line in lines:
        document.add_paragraph(line)

    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _make_pdf_bytes(text_lines=None, image_only=False):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader as ReportLabImageReader
    from reportlab.pdfgen import canvas
    from PIL import Image, ImageDraw

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    if image_only:
        image = Image.new("RGB", (int(width), int(height)), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.text((50, 100), "Scanned resume with Python, FastAPI, Docker", fill=(0, 0, 0))
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        pdf.drawImage(ReportLabImageReader(image_buffer), 0, 0, width=width, height=height)
    else:
        y = height - 100
        for line in text_lines or []:
            pdf.drawString(50, y, line)
            y -= 14

    pdf.showPage()
    pdf.save()
    return output.getvalue()


def _make_malformed_pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()[:20]


NORMAL_RESUME = _make_docx_bytes(
    [
        "Jane Doe",
        "jane@example.com",
        "Skills: Python, FastAPI, Docker, SQL, AWS",
        "Experience: Backend engineer building APIs and reports.",
    ]
)

OCR_RESUME = _make_pdf_bytes(image_only=True)
MALFORMED_RESUME = _make_malformed_pdf_bytes()


class ResumeScoringUser(HttpUser):
    wait_time = between(1, 3)

    def _post_resume(self, filename, content, content_type, job_description=""):
        return self.client.post(
            "/api/v1/analyze-resume",
            data={"job_description": job_description},
            files={"resume": (filename, content, content_type)},
            name="/api/v1/analyze-resume",
        )

    @task(6)
    def upload_normal_resume(self):
        self._post_resume(
            "normal_resume.docx",
            NORMAL_RESUME,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            job_description="Python, FastAPI, Docker, SQL, AWS",
        )

    @task(3)
    def upload_ocr_resume(self):
        self._post_resume("scanned_resume.pdf", OCR_RESUME, "application/pdf")

    @task(1)
    def upload_malformed_resume(self):
        self._post_resume("malformed.pdf", MALFORMED_RESUME, "application/pdf")
