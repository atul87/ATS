from pathlib import Path


def main() -> int:
    pdf_path = Path("tests/fixtures/generated/resume_scanned_image.pdf")
    if not pdf_path.exists():
        print("MISSING_FIXTURE")
        return 2

    try:
        from pdf2image import convert_from_path
    except Exception as e:
        print("NO_PDF2IMAGE", e)
        return 3

    try:
        import pytesseract
    except Exception as e:
        print("NO_PYTESSERACT", e)
        return 4

    try:
        imgs = convert_from_path(str(pdf_path), first_page=1, last_page=1)
        img = imgs[0]
        text = pytesseract.image_to_string(img)
        print("OCR_OK")
        print(text[:500])
    except Exception as e:
        print("OCR_FAILED", repr(e))
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
