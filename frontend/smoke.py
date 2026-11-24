"""Exercise the running fixture UI, API and database with a fresh browser session."""
import os
import re

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
    page.get_by_label("Travel mode").select_option("car")
    page.get_by_role("button", name="Save household").click()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    page.reload()
    expect(page.get_by_role("button", name="Central Delhi")).to_be_visible()
    expect(page.get_by_role("heading", name="Household action plan")).to_be_visible()
    expect(page.get_by_text("Choose where to wait", exact=True)).to_be_visible()
    page.get_by_text("Example CO₂ difference", exact=False).click()
    expect(page.get_by_role("link", name="Source (2015)").first).to_be_visible()
    progress = page.get_by_label("Progress · ").first
    progress.select_option("done")
    expect(page.get_by_text("Completed 1/", exact=False)).to_be_visible()
    page.reload()
    expect(progress).to_have_value("done")
    page.get_by_role("button", name="हिन्दी").click()
    expect(page.get_by_text("उदाहरण में CO₂ का अंतर", exact=False)).to_be_visible()
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
    page.get_by_text("मॉडल की मान्यताएँ", exact=True).click()
    expect(page.get_by_text("100 µg/m³ × 8 h", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="EPA मॉडल संदर्भ")).to_have_attribute(
        "href", "https://www.epa.gov/system/files/documents/2023-08/APEX52_UsersGuide_Vol2_June2023.pdf"
    )
    expect(page.get_by_role("heading", name="प्यूरिफ़ायर की क्षमता")).to_be_visible()
    expect(page.get_by_text("लगभग 156 m³/h", exact=False)).to_be_visible()
    expect(page.get_by_text("दोनों स्थितियों में अनुमानित मात्रा समान है।")).to_be_visible()
    page.get_by_role("group", name="कमरे की स्थिति").get_by_role("combobox").select_option("open")
    page.get_by_role("button", name="तुलना करें").click()
    expect(page.get_by_text("22% अधिक PM2.5", exact=False)).to_be_visible()
    page.get_by_role("checkbox", name="दिल्ली का घंटेवार पूर्वानुमान इस्तेमाल करें").check()
    with (page.expect_response(lambda res: res.url.endswith("/air/forecast?hours=8")) as hourly,
          page.expect_request(lambda req: req.url.endswith("/simulate/indoor")) as simulation):
        page.get_by_role("button", name="तुलना करें").click()
    forecast = hourly.value.json()
    assert simulation.value.post_data_json["outdoor_pm25_ug_m3"] == [h["pm25_ug_m3"] for h in forecast["hours"]]
    expect(page.get_by_text("डेमो · दिल्ली का कृत्रिम डेटा", exact=False)).to_be_visible()
    page.get_by_text("घंटेवार मान", exact=True).click()
    hourly_table = page.get_by_role("table", name="कमरे का अनुमानित PM2.5 (µg/m³)")
    expect(hourly_table.get_by_role("columnheader", name="समय (IST)")).to_be_visible()
    expect(hourly_table.get_by_role("rowheader")).to_have_count(8)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    forecast["hours"][0]["pm25_ug_m3"] = None
    page.route("**/air/forecast?hours=8", lambda route: route.fulfill(json=forecast))
    page.get_by_role("button", name="तुलना करें").click()
    expect(page.get_by_role("alert")).to_contain_text("कुछ घंटों का पूर्वानुमान उपलब्ध नहीं है")
    expect(page.get_by_role("heading", name="साँस में गया अनुमानित PM2.5")).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="परिवार", exact=True).click()
    expect(page.get_by_label("इलाका", exact=True)).to_have_value("Central Delhi")
    page.get_by_role("button", name="परिवार मिटाएँ").click()
    page.get_by_role("button", name="मिटाने की पुष्टि करें").click()
    expect(page.get_by_role("button", name="परिवार जोड़ें")).to_be_visible()
    page.get_by_role("button", name="परिवार जोड़ें").click()
    page.get_by_label("इलाका", exact=True).fill("Karol Bagh")
    page.get_by_text("उदाहरण परिवार चुनें", exact=True).click()
    page.get_by_role("button", name="स्कूटर से काम पर जाने वाले दो वयस्क").click()
    expect(page.get_by_label("इलाका", exact=True)).to_have_value("Karol Bagh")
    page.get_by_role("button", name="आगे बढ़ें", exact=True).click()
    page.get_by_role("button", name="आगे बढ़ें", exact=True).click()
    expect(page.get_by_role("heading", name="सदस्य 2")).to_be_visible()
    expect(page.get_by_label("दूरी (किमी)").first).to_have_value("14")
    page.get_by_label("दूरी (किमी)").first.fill("12")
    page.get_by_role("button", name="परिवार सहेजें").click()
    expect(page.get_by_role("button", name="Karol Bagh")).to_be_visible()
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
    page.get_by_role("button", name="समुदाय", exact=True).click()
    page.get_by_label("इलाका", exact=True).fill("Empty demo locality")
    page.get_by_role("button", name="सार देखें").click()
    expect(page.get_by_text("पाँच परिवारों", exact=False)).to_be_visible()
    page.get_by_role("button", name="काल्पनिक उदाहरण देखें").click()
    page.evaluate("Object.defineProperty(navigator, 'share', {value: undefined, configurable: true})")
    page.get_by_role("button", name="सार साझा करें").click()
    expect(page.get_by_label("यह सार कॉपी करें")).to_have_value(re.compile("काल्पनिक परिवार.*12"))
    if axe_script := os.getenv("AXE_SCRIPT"):
        page.add_script_tag(path=axe_script)
        findings = page.evaluate("""async () => {
            const result = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa']}});
            return result.violations.filter(v => ['serious', 'critical'].includes(v.impact))
                         .map(v => ({id:v.id, targets:v.nodes.map(n => n.target)}));
        }""")
        assert not findings, findings
    page.evaluate("window.dispatchEvent(new Event('offline'))")
    page.get_by_role("button", name="ऑफ़लाइन डेमो खोलें").click()
    expect(page.get_by_role("heading", name="ऑफ़लाइन डेमो", exact=True)).to_be_visible()
    page.get_by_text("48 घंटे का उदाहरण पूर्वानुमान", exact=True).click()
    expect(page.get_by_role("listitem")).to_have_count(48)
    assert not errors, errors
    browser.close()
