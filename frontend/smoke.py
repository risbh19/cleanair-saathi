"""Exercise the running fixture UI, API and database with a fresh browser session."""
import os

from playwright.sync_api import expect, sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.getenv("CHROME_BIN"))
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(os.getenv("UI_URL", "http://127.0.0.1:5173"))
    expect(page.get_by_text("Very poor", exact=True).first).to_be_visible()
    page.get_by_text("View all 48 hours", exact=False).click()
    expect(page.locator("tbody tr")).to_have_count(48)
    page.get_by_role("button", name="Set up household").click()
    page.get_by_label("Locality", exact=True).fill("Central Delhi")
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Add commute").click()
    page.get_by_role("button", name="Save household").click()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    page.get_by_role("button", name="हिन्दी").click()
    expect(page.locator("html")).to_have_attribute("lang", "hi")
    expect(page.get_by_role("heading", name="आज की हवा")).to_be_visible()
    page.get_by_role("button", name="घर की हवा", exact=True).click()
    page.get_by_role("button", name="तुलना करें").click()
    expect(page.get_by_role("heading", name="साँस में गया अनुमानित PM2.5")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="परिवार", exact=True).click()
    expect(page.get_by_label("इलाका", exact=True)).to_have_value("Central Delhi")
    page.get_by_role("button", name="परिवार मिटाएँ").click()
    page.get_by_role("button", name="मिटाने की पुष्टि करें").click()
    expect(page.get_by_role("button", name="परिवार जोड़ें")).to_be_visible()
    assert not errors, errors
    browser.close()
