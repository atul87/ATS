import logging

try:
    from weasyprint import HTML, CSS

    WEASYPRINT_INSTALLED = True
    WEASYPRINT_IMPORT_ERROR = None
except (ImportError, OSError) as exc:
    HTML = None
    CSS = None
    WEASYPRINT_INSTALLED = False
    WEASYPRINT_IMPORT_ERROR = exc

logger = logging.getLogger("ats_resume_scorer")


def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    if not WEASYPRINT_INSTALLED:
        logger.warning(
            f"WeasyPrint is unavailable ({WEASYPRINT_IMPORT_ERROR}). Falling back to ReportLab for basic PDF generation."
        )
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        import re

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "ATS Resume Scorer Report (Fallback Mode)")
        y -= 25

        # Subtitle
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(
            50, y, "Note: High-fidelity rendering (WeasyPrint) is not installed on this system."
        )
        y -= 30

        # Basic text parser for HTML to draw summary sections
        c.setFont("Helvetica", 10)
        for section_name, html_str in html_docs.items():
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"--- {section_name.replace('_', ' ').title()} ---")
            y -= 20
            c.setFont("Helvetica", 10)

            # Strip HTML tags basic regex
            clean_text = re.sub(r"<[^>]+>", "\n", html_str)
            for line in clean_text.split("\n"):
                line_str = line.strip()
                if not line_str:
                    continue
                if len(line_str) > 90:
                    line_str = line_str[:87] + "..."
                c.drawString(50, y, line_str)
                y -= 15
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 10)
            y -= 15

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    documents = []

    # Render all 3 HTML strings to WeasyPrint Document objects
    for name, html_str in html_docs.items():
        doc = HTML(string=html_str).render()
        documents.append(doc)

    # Merge them into the first document
    first_doc = documents[0]
    for other_doc in documents[1:]:
        for page in other_doc.pages:
            first_doc.pages.append(page)

    # Write combined PDF bytes
    pdf_bytes = first_doc.write_pdf()
    return pdf_bytes
