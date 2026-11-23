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
    expect(page.get_by_text("No effective CAQM order has been recorded.")).to_be_visible()
    weather_hour = page.get_by_label("Forecast hour")
    expect(weather_hour.locator("option")).to_have_count(48)
    weather_hour.select_option(index=47)
    expect(page.get_by_text("Boundary-layer height", exact=True)).to_be_visible()
    page.get_by_text("View all 48 hours", exact=False).click()
    expect(page.locator("tbody tr")).to_have_count(48)
    page.get_by_role("button", name="Commute", exact=True).click()
    page.get_by_role("button", name="Compare trips", exact=True).click()
    expect(page.get_by_role("heading", name="Estimated CO₂ per traveller")).to_be_visible()
    page.get_by_text("Calculation and source").click()
    expect(page.get_by_role("link", name="India GHG Program (2015)").first).to_be_visible()
    page.get_by_role("button", name="Today", exact=True).click()
    page.get_by_role("button", name="Set up household").click()
    page.get_by_label("Locality", exact=True).fill("Central Delhi")
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Add commute").click()
    page.get_by_role("button", name="Save household").click()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    expect(page.get_by_role("heading", name="Household action plan")).to_be_visible()
    expect(page.get_by_text("Choose where to wait", exact=True)).to_be_visible()
    progress = page.get_by_label("Progress · ").first
    progress.select_option("done")
    expect(page.get_by_text("Completed 1/", exact=False)).to_be_visible()
    page.reload()
    expect(progress).to_have_value("done")
    page.get_by_role("button", name="हिन्दी").click()
    progress_hi = page.get_by_label("प्रगति · ").first
    progress_hi.select_option("skipped")
    expect(progress_hi).to_be_enabled()
    expect(page.get_by_text("पूरे हुए 0/", exact=False)).to_be_visible()
    expect(page.get_by_text("इंतज़ार की जगह चुनें", exact=True)).to_be_visible()
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
    # Exercise station attribution without an OpenAQ account in CI.
    def station_brief(route):
        data = route.fetch().json()
        data.update(data_mode="live", stale=False, hourly_pm25_ug_m3=300, age_hours=1,
                    hourly_subindex_estimate={"band": "Severe", "value": None, "value_range": [401, 500]},
                    stations=[{"location_id": 123, "name": "Test monitor", "provider": "Test provider",
                               "as_of": data["as_of"], "distance_km": 2, "pm25_ug_m3": 300,
                               "url": "https://explore.openaq.org/locations/123"}])
        route.fulfill(json=data)
    page.route("**/api/grap/status", lambda route: route.fulfill(json={"order": {
        "stage": 2, "effective_from": "2025-11-01T00:00:00Z",
        "source_url": "https://caqm.nic.in/test-order.pdf", "entered_at": "2025-11-01T01:00:00Z"}}))
    page.route("**/api/air/now*", station_brief)
    page.reload()
    page.get_by_text("शामिल स्टेशन", exact=False).click()
    expect(page.get_by_role("link", name="Test monitor")).to_be_visible()
    expect(page.get_by_text("दर्ज चरण II", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="CAQM का आदेश पढ़ें")).to_have_attribute("href", "https://caqm.nic.in/test-order.pdf")
    expect(page.get_by_text("श्रेणी सीमा 401–500", exact=False)).to_be_visible()
    expect(page.get_by_role("link", name="CPCB की श्रेणी तालिका")).to_be_visible()
    assert not errors, errors
    browser.close()
