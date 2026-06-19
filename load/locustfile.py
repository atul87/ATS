import io
import os

from docx import Document
from locust import HttpUser, between, events, task
from pypdf import PdfWriter

P95_THRESHOLD_MS = float(os.getenv("LOCUST_P95_THRESHOLD_MS", "2000"))
FAILURE_RATE_THRESHOLD = float(os.getenv("LOCUST_FAILURE_RATE_THRESHOLD", "0.01"))
AUTH_TOKEN = os.getenv("LOAD_TEST_TOKEN", "mock-access-token")


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

    def _post_resume(
        self,
        filename,
        content,
        content_type,
        job_description="",
        expected_statuses=(200,),
    ):
        with self.client.post(
            "/api/v1/analyze-resume",
            data={"job_description": job_description},
            files={"resume": (filename, content, content_type)},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            name="/api/v1/analyze-resume",
            catch_response=True,
        ) as response:
            if response.status_code in expected_statuses:
                response.success()
            else:
                response.failure(
                    f"Expected {expected_statuses}, got {response.status_code}: {response.text[:200]}"
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
        self._post_resume(
            "scanned_resume.pdf", OCR_RESUME, "application/pdf", expected_statuses=(200, 422)
        )

    @task(1)
    def upload_malformed_resume(self):
        self._post_resume(
            "malformed.pdf",
            MALFORMED_RESUME,
            "application/pdf",
            expected_statuses=(422,),
        )


@events.quitting.add_listener
def enforce_thresholds(environment, **_kwargs):
    total = environment.stats.total
    if total.num_requests == 0:
        environment.process_exit_code = 1
        print("Load test failed: no requests were recorded.")
        return

    p95 = total.get_response_time_percentile(0.95) or 0
    failure_rate = total.fail_ratio
    print(
        f"Load thresholds: p95={p95:.0f}ms/{P95_THRESHOLD_MS:.0f}ms, "
        f"failure_rate={failure_rate:.2%}/{FAILURE_RATE_THRESHOLD:.2%}"
    )

    if p95 > P95_THRESHOLD_MS or failure_rate > FAILURE_RATE_THRESHOLD:
        environment.process_exit_code = 1
