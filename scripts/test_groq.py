from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from backend.services.groq_parser import _get_client, parse_resume  # noqa: E402


def main():
    print("Testing Groq API Integration...")
    client = _get_client()
    if client is None:
        print("FAIL: Groq client could not be initialized (GROQ_API_KEY missing or empty).")
        return

    print("Successfully initialized Groq client.")
    print("Sending test resume to Groq API...")

    test_resume_text = (
        "John Doe\nPython Developer\nEmail: john@example.com\nSkills: Python, Docker, SQL"
    )

    try:
        result = parse_resume(test_resume_text)
        print("Response received!")
        parser_source = result.get("parser_source", "groq")
        print("Parser Source:", parser_source)

        if parser_source == "local_regex":
            print(
                "WARNING: Groq parser fell back to local regex. The API key might be invalid or rate-limited."
            )
        else:
            print("SUCCESS: Groq parsed the resume successfully! Extracted fields:")
            print("- Name:", result.get("name"))
            print("- Email:", result.get("email"))
            print("- Skills:", result.get("skills"))
    except Exception as e:
        print("ERROR: Groq call failed with exception:", e)


if __name__ == "__main__":
    main()
