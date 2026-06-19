from playwright.sync_api import sync_playwright, TimeoutError

FRONTEND = "http://127.0.0.1:8501"
TEST_EMAIL = "playwright-test@example.com"
TEST_PASSWORD = "password123"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{FRONTEND}?e2e=true")
    try:
        page.wait_for_selector("text=Sign in", timeout=15000)
        # Sign up flow
        page.get_by_role("tab", name="Sign up").click()
        page.locator("input[aria-label='Email']:visible").first.fill(TEST_EMAIL)
        page.locator("input[aria-label='Password (min 6 chars)']:visible").first.fill(TEST_PASSWORD)
        page.locator("button:has-text('Create account')").click()
        page.wait_for_selector(f"text=Signed in as {TEST_EMAIL}", timeout=15000)
        print("Sign-up: OK")
        # Sign out
        page.locator("button:has-text('Sign out')").click()
        page.wait_for_selector("text=Sign in", timeout=15000)
        print("Sign-out after signup: OK")
        # Sign in flow
        page.wait_for_selector("text=Sign in", timeout=15000)
        page.locator("input[aria-label='Email']:visible").first.fill(TEST_EMAIL)
        page.locator("input[aria-label='Password']:visible").first.fill(TEST_PASSWORD)
        page.locator("[data-testid='stFormSubmitButton'] button:visible").first.click()
        page.wait_for_selector(f"text=Signed in as {TEST_EMAIL}", timeout=15000)
        print("Sign-in: OK")
        # Final sign out
        page.locator("button:has-text('Sign out')").click()
        page.wait_for_selector("text=Sign in", timeout=15000)
        print("Sign-out: OK")
    except TimeoutError as e:
        print("E2E auth script failed:", e)
        raise
    finally:
        try:
            context.close()
            browser.close()
        except Exception:
            pass
