import asyncio
import json
from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest

import alfred_mail
import kinetic_find as kf
import kinetic_invoices as ki
import kinetic_outreach as ko
import kinetic_sales as ks
import kinetic_store as st
import kinetic_world as world
import freelance_store
import helpers
import memory
import tools
from config import Settings

YEAR = st.today().year

GOOD = f"""<!doctype html><html><head><title>Bloom Florist Stockport | Fresh flowers</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Fresh flowers delivered in Stockport.">
<meta property="og:image" content="/og.jpg"><link rel="icon" href="/f.png">
<script type="application/ld+json">{{"@type": "LocalBusiness", "name": "Bloom"}}</script>
</head><body><h1>Bloom</h1><a href="tel:+44161">Call</a><form></form><p>© {YEAR} Bloom</p></body></html>"""

BAD = """<html><head><title>Home</title></head><body><table><tr><td><font face="Arial">Joe's Barbers</font>
<img src=a.jpg><img src=b.jpg><img src=c.jpg><p>Copyright 2016 Joe's</p></td></tr></table>
<a href="mailto:joe@joes.test">Email</a></body></html>"""

ELEMENTS = [
    {"type": "node", "id": 1, "tags": {"name": "Joe's Barbers", "shop": "hairdresser", "website": "http://joes.test",
                                       "addr:street": "High St", "addr:housenumber": "4"}},
    {"type": "node", "id": 2, "tags": {"name": "Bloom", "shop": "florist", "website": "https://bloom.test"}},
    {"type": "node", "id": 3, "tags": {"name": "Sal's Cafe", "amenity": "cafe", "phone": "0161 000 0000"}},
    {"type": "node", "id": 4, "tags": {"name": "Costa", "amenity": "cafe", "brand": "Costa Coffee",
                                       "website": "https://costa.test"}},
    {"type": "way", "id": 5, "tags": {"name": "Gone Garage", "shop": "car_repair", "website": "https://gone.test"}},
]
queries = []


def handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    if host == "nominatim.openstreetmap.org":
        if request.url.params.get("q") == "Nowhere":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{"lat": "53.41", "lon": "-2.15", "display_name": "Stockport, Greater Manchester"}])
    if host == "overpass-api.de":
        queries.append(parse_qs(request.content.decode())["data"][0])
        return httpx.Response(200, json={"elements": ELEMENTS})
    if host == "joes.test":
        if request.url.scheme == "https":
            raise httpx.ConnectError("no tls")
        return httpx.Response(200, text=BAD, headers={"content-type": "text/html"})
    if host == "bloom.test":
        return httpx.Response(200, text=GOOD, headers={"content-type": "text/html; charset=utf-8"})
    if host == "gone.test":
        return httpx.Response(500)
    if host == "costa.test":
        raise AssertionError("chains are skipped")
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def public_links(monkeypatch):
    real = memory.check_public

    async def ok(url):
        if "127.0.0.1" in url or "192.168." in url:
            await real(url)
    monkeypatch.setattr(memory, "check_public", ok)
    queries.clear()


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def finder(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await kf.run_tool("web_client_finder", args, s, http)
    return asyncio.run(go())


def sales(s, **args):
    return asyncio.run(ks.run_tool("web_design_sales", args, s))


def inv(s, **args):
    return ki.run_tool("web_design_invoices", args, s)


def track(s, **args):
    return asyncio.run(ko.run_tool("web_design_outreach", args, s))


def test_scores_a_strong_and_a_weak_page():
    good = kf.score_page("https://bloom.test", GOOD, 0.4, len(GOOD), True, YEAR)
    assert good["score"] >= 90 and good["grade"] == "good"
    bad = kf.score_page("http://joes.test", BAD, 4.2, len(BAD), False, YEAR)
    names = " ".join(p["problem"] for p in bad["problems"])
    for bit in ("No padlock", "Not made for phones", "Slow to load", "Weak page title", "Footer says © 2016",
                "tap-to-call", "very old tech", "Images have no descriptions"):
        assert bit in names
    assert bad["grade"] == "weak" and bad["score"] < 30
    assert bad["problems"][0]["points"] == 20  # biggest first
    assert bad["emails"] == ["joe@joes.test"]


def test_find_ranks_no_website_then_broken_then_weak_and_skips_chains(s):
    out = finder(s, action="find", town="Stockport", kind="mixed")
    assert "independent businesses near Stockport" in out and "1 with no website" in out
    rows = out.card["rows"]
    names = [r[1] for r in rows]
    assert "Costa" not in names
    assert names == ["Sal's Cafe", "Gone Garage", "Joe's Barbers", "Bloom"]
    assert rows[0][4] == "no site" and rows[1][4] == "down" and rows[2][5] == "No padlock (no HTTPS)"
    assert 'nwr["shop"="hairdresser"]["name"](around:3000,53.41,-2.15)' in queries[0]
    saved = st.rows_of(s, st.PROSPECTS)
    assert len(saved) == 4 and all(r["status"] == "new" for r in saved)
    report = memory.root(s) / "Kinetic Web Designs" / "Prospects" / f"Stockport businesses {st.today().isoformat()}.md"
    assert "Joe's Barbers" in report.read_text(encoding="utf-8")
    finder(s, action="find", town="Stockport")  # running again refreshes rather than duplicating
    assert len(st.rows_of(s, st.PROSPECTS)) == 4


def test_find_kinds_and_errors(s):
    assert kf.kind_key("barber shops") == "hairdressers" and kf.kind_key("plumbers") == "trades"
    assert kf.kind_key(None) == "mixed"
    with pytest.raises(ValueError, match="Which kind"):
        kf.kind_key("spaceships")
    with pytest.raises(ValueError, match="couldn't find Nowhere"):
        finder(s, action="find", town="Nowhere")
    q = kf.overpass_query(1, 2, 500, "trades")
    assert '"craft"="plumber"' in q and '"amenity"="cafe"' not in q


def test_audit_a_url_saves_a_report_and_a_prospect(s):
    out = finder(s, action="audit", url="joes.test")
    assert "out of 100" in out and "no padlock" in out
    assert (memory.root(s) / "Kinetic Web Designs" / "Audits" / "joes.test.md").exists()
    p = st.rows_of(s, st.PROSPECTS)[0]
    assert p["website"] == "http://joes.test" and p["audit"]["grade"] == "weak"
    down = finder(s, action="audit", url="gone.test")
    assert "doesn't load" in down


def test_audit_refuses_home_network(s):
    with pytest.raises(ValueError, match="home network"):
        finder(s, action="audit", url="http://192.168.1.1")


def test_prospect_status_and_lead(s):
    finder(s, action="find", town="Stockport")
    finder(s, action="mark", business="Bloom", status="contacted")
    assert next(r for r in st.rows_of(s, st.PROSPECTS) if r["name"] == "Bloom")["contacted"]
    out = finder(s, action="add_lead", business="Sal's Cafe")
    assert "lead in your freelance pipeline" in out and "£395" in out
    lead = freelance_store.rows_of(s, freelance_store.LEADS)[0]
    assert lead["client"] == "Sal's Cafe" and lead["title"] == "New website" and lead["source"] == "Kinetic finder"
    assert "Should I remove" in finder(s, action="forget", business="Bloom")
    finder(s, action="forget", business="Bloom", confirmed=True)
    assert all(r["name"] != "Bloom" for r in st.rows_of(s, st.PROSPECTS))
    shown = finder(s, action="prospects", status="lead")
    assert [r[1] for r in shown.card["rows"]] == ["Sal's Cafe"]


def test_prices_and_details(s):
    assert "starter £395" in sales(s, action="prices")
    sales(s, action="set_price", item="business website", price=950)
    sales(s, action="set_price", item="deposit", price=30)
    p = ks.prices(s)
    assert p["packages"]["business"]["price"] == 950 and p["deposit_percent"] == 30
    with pytest.raises(ValueError, match="Which price"):
        sales(s, action="set_price", item="rocket", price=1)
    out = sales(s, action="my_details", owner="Lee", email="lee@kinetic.test")
    assert "Saved your owner, email" in out and "sort code" in out
    assert st.business(s)["owner"] == "Lee"


def test_quote_from_audited_prospect_lists_fixes(s):
    finder(s, action="find", town="Stockport")
    out = sales(s, action="quote", client="Joe's Barbers", package="business", addons=["logo", "extra_page"],
                extra_pages=2, discount=40)
    assert "Q-0001" in out and "£1,245" in out and "£622.50 deposit" in out and "Nothing has been sent" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Joe's Barbers" / "Quote Q-0001.html").read_text(encoding="utf-8")
    assert "What your new website fixes" in html and "No padlock" in html and "Logo design" in html
    assert "<script" not in html
    q = st.rows_of(s, st.QUOTES)[0]
    assert q["total"] == 1245 and q["status"] == "draft"
    sales(s, action="quote_status", quote="Q-0001", status="sent")
    assert next(r for r in st.rows_of(s, st.PROSPECTS) if r["name"] == "Joe's Barbers")["status"] == "contacted"
    assert "1 open worth £1,245" in sales(s, action="quotes")


def test_domain_owner_details_after_a_quote_is_accepted(s):
    sales(s, action="quote", client="Sal's Cafe", package="starter")
    assert "domain owner details for Sal's Cafe" in sales(s, action="quote_status", quote="Q-0001", status="accepted")
    shown = sales(s, action="domain_owner", quote="Q-0001", domain="https://www.salscafe.co.uk/", owner_name="Sal Jones")
    assert "2 of 5 saved" in shown and "OK is still needed" in shown
    body = shown.card["text"]
    assert "✓ Domain name: salscafe.co.uk" in body and "○ Postal address: still needed" in body
    assert 'reply "Yes, register salscafe.co.uk in my name."' in body
    assert "send me your postal address, email and phone number" in body
    with pytest.raises(ValueError, match="email address"):
        sales(s, action="domain_owner", client="Sal's Cafe", owner_email="not-an-email")
    done = sales(s, action="domain_owner", client="Sal's Cafe", owner_address="1 High St, Stockport",
                 owner_email="sal@salscafe.test", owner_phone="0161 000 0000", owner_ok=True)
    assert "complete" in done and "Message to send" not in done.card["text"]
    assert st.load(s, st.DOMAIN_OWNERS, {})["Sal's Cafe"]["owner_name"] == "Sal Jones"
    with pytest.raises(ValueError, match="Which client"):
        sales(s, action="domain_owner")


def test_welcome_emails_after_the_deposit_invoice(s):
    sales(s, action="my_details", owner="Lee", phone="0161 111 1111")
    sales(s, action="quote", client="Sal's Cafe", package="business", addons=["logo"])
    out = inv(s, action="invoice", quote="Q-0001")
    assert "plus £25 a month for hosting and care from go-live" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Sal's Cafe" / "Invoice INV-0001.html").read_text(encoding="utf-8")
    assert "Monthly hosting and care, £25 a month" in html and "Not included in the amount due" in html
    assert "welcome emails for Q-0001" in out and any(b["label"] == "Welcome emails" for b in out.card["buttons"])
    sales(s, action="domain_owner", client="Sal's Cafe", domain="salscafe.co.uk")
    shown = sales(s, action="welcome_emails", quote="Q-0001", contact_name="Sal")
    assert "Give me their email address" in shown and "Nothing has been sent" in shown
    body = shown.card["text"]
    assert "Subject: Thank you for choosing Kinetic Web Designs: your order is confirmed" in body
    assert "Dear Sal," in body and "- Logo design" in body and "Total: £1,045" in body
    assert "Deposit to start (50%): £522.50, invoice INV-0001" in body and "3 rounds of changes" in body
    assert "Subject: Next steps required from you" in body and "Hosting and care: £25 a month" in body
    assert 'register salscafe.co.uk in my name' in body and "Alfred, Kinetic Web Designs\n0161 111 1111" in body
    assert "Lee" not in body and "https://kineticwebdesigns.co.uk/#quote" in body  # the site's Stripe plan link
    assert "insurance" not in body.lower() and 'reply "Yes to hosting and care"' in body
    folder = memory.root(s) / "Kinetic Web Designs" / "Clients" / "Sal's Cafe"
    assert (folder / "Welcome email 2 Q-0001.md").exists()
    sales(s, action="my_details", plan_link="https://buy.stripe.test/abc")
    drafted = sales(s, action="welcome_emails", quote="Q-0001", to="sal@salscafe.test")
    assert "have NOT been sent" in drafted and "https://buy.stripe.test/abc" in drafted.card["text"]
    assert drafted.card["buttons"][0]["say"] == "Yes, send email draft 1."
    assert [d["subject"] for d in alfred_mail._load_drafts(s)] == [
        "Thank you for choosing Kinetic Web Designs: your order is confirmed", "Next steps required from you"]


def test_mockup_uses_trade_look_or_saved_design_system(s):
    finder(s, action="find", town="Stockport")
    out = sales(s, action="mockup", client="Sal's Cafe")
    path = memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Sal's Cafe" / "index.html"
    html = path.read_text(encoding="utf-8")
    assert "cafe look" in out and "Sal&#x27;s Cafe" in html and 'href="tel:01610000000"' in html
    assert "width=device-width" in html and "Concept home page" in html and "#7a4a2a" in html
    folder = memory.root(s) / "Kinetic Web Designs" / "stripe.com"
    folder.mkdir(parents=True)
    (folder / "tokens.json").write_text(json.dumps({"color": {"brand": {"$value": "#635bff"},
                                                              "background": {"$value": "</style><script>"}},
                                                    "fontFamily": {"primary": {"$value": ["Inter", "sans-serif"]}}}))
    out = sales(s, action="mockup", client="Bloom", style_from="stripe.com")
    html = (memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Bloom" / "index.html").read_text(encoding="utf-8")
    assert "style of stripe.com" in out and "#635bff" in html and "Inter, sans-serif" in html
    assert "<script>" not in html
    with pytest.raises(ValueError, match="can't find a saved design system"):
        sales(s, action="mockup", client="Bloom", style_from="nope.com")


def test_mockup_adds_cleaned_extra_sections(s):
    hero = ('<div class="glow" onclick="steal()"><h2>Fresh bread daily</h2><a href="javascript:alert(1)">Order</a>'
            '<script>alert(1)</script><iframe src="https://x.test"></iframe><img src=x onerror=alert(1)></div>')
    sales(s, action="mockup", client="Sal's Cafe", sections=[hero, "<p>Why choose us</p>"],
          section_css=".glow{background:var(--brand)}</style><script>alert(1)</script>@import url(x.css);")
    html = (memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Sal's Cafe" / "index.html").read_text(encoding="utf-8")
    assert '<section class="extra"><div class="glow"><h2>Fresh bread daily</h2>' in html and "Why choose us" in html
    assert ".glow{background:var(--brand)}" in html and "@import" not in html
    for bad in ("<script", "<iframe", "onclick", "onerror", "javascript:"):
        assert bad not in html.lower()
    assert ks.clean_section("<scr<script></script>ipt>alert(1)</script>").lower().count("<script") == 0


def test_outreach_drafts_are_never_sent(s):
    finder(s, action="find", town="Stockport")
    sales(s, action="my_details", owner="Lee", phone="07000 000000")
    email = sales(s, action="outreach", client="Joe's Barbers", contact_name="Joe", channel="email")
    body = email.card["text"]
    # problem first, then "so I made you this" and the mock-up, then "see your design before you pay anything"
    assert body.startswith("Subject: I made this for Joe's Barbers\n\nHi Joe,\n\nYour website (joes.test) is hard to "
                           "use on a phone: it shows as a tiny desktop page")
    assert ("So I made you this: a free example of a new home page for Joe's Barbers. It's attached (Joe's Barbers "
            "home page mock-up.html)") in body and "\n\nSee your design before you pay anything.\n\n" in body
    assert "No padlock" in body and "no thanks" in body and "Thanks,\nAlfred, Kinetic Web Designs\n07000" in body
    assert "Lee" not in body  # signed by Alfred for the business, never the user's own name
    assert "Nothing has been sent" in email and "sole traders" in email
    mock = "Kinetic Web Designs/Mockups/Joe's Barbers/Joe's Barbers home page mock-up.html"
    assert mock in email and "Attach it to the email" in email and "can't carry attachments" in email
    folder = memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Joe's Barbers"
    assert (folder / "index.html").exists() and "Concept home page" in (
        folder / "Joe's Barbers home page mock-up.html").read_text(encoding="utf-8")
    none = sales(s, action="outreach", client="Sal's Cafe", channel="phone").card["text"]
    assert "couldn't find a website" in none and "0161 000 0000" in none and "Lee" not in none
    assert '2. If yes: "I searched for Sal\'s Cafe online and couldn\'t find a website' in none
    assert "So I made you this: a free example of a new home page for Sal's Cafe." in none and st.PREVIEW in none
    visit = sales(s, action="outreach", client="Bloom", channel="visit").card["text"]
    assert visit.startswith("Walk-in script") and "So I made you this" in visit and st.PREVIEW in visit
    for channel in ("dm", "letter", "whatsapp"):
        text = sales(s, action="outreach", client="Gone Garage", channel=channel).card["text"]
        assert "So I made you this" in text and "Gone Garage home page mock-up.html" in text and st.PREVIEW in text
        assert "(gone.test)" in text.split("So I made you this")[0] and "won't load" in text.split("So I made you this")[0]
    plain = sales(s, action="outreach", client="Ada", mockup=False)
    assert "So I made you this" not in plain.card["text"] and "free and with no obligation" in plain.card["text"]
    assert not (memory.root(s) / "Kinetic Web Designs" / "Mockups" / "Ada").exists()
    with pytest.raises(ValueError, match="Which kind of message"):
        sales(s, action="outreach", client="Bloom", channel="fax")


def test_invoices_from_quote_paid_reminders_and_earnings(s):
    sales(s, action="my_details", owner="Lee", sort_code="12-34-56", account_number="12345678")
    sales(s, action="quote", client="Acme Plumbing", package="starter", care_plan=False)
    out = inv(s, action="invoice", quote="Q-0001")
    assert "INV-0001" in out and "£197.50" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Acme Plumbing" / "Invoice INV-0001.html").read_text(encoding="utf-8")
    assert "12-34-56" in html and "Reference: INV-0001" in html and "Deposit for starter website" in html
    assert st.rows_of(s, st.QUOTES)[0]["status"] == "accepted"
    assert "final invoice for Q-0001" in inv(s, action="paid", invoice="INV-0001")
    final = inv(s, action="invoice", quote="Q-0001", part="final")
    assert "INV-0002" in final and "£197.50" in final
    with pytest.raises(ValueError, match="invoiced in full"):
        inv(s, action="invoice", quote="Q-0001", part="final")
    rows = st.rows_of(s, st.INVOICES)
    rows[1]["due"] = (st.today() - timedelta(days=20)).isoformat()
    st.save(s, st.INVOICES, rows)
    listing = inv(s, action="invoices")
    assert "1 overdue" in listing and "overdue 20 days" in listing.card["rows"][0][4]
    chase = inv(s, action="reminder", invoice="INV-0002")
    assert "firmer" in chase and "Late Payment" in chase.card["text"] and "Nothing has been sent" in chase
    money = inv(s, action="earnings")
    assert "£197.50 this month" in money and "£197.50 is owed" in money
    assert "Should I cancel" in inv(s, action="cancel", invoice="INV-0002")


def test_invoice_from_items_without_bank_details(s):
    out = inv(s, action="invoice", client="Bob", items=[{"description": "Hosting", "qty": 12, "price": 10}])
    assert "£120" in out and "bank details aren't saved" in out
    with pytest.raises(ValueError, match="What's the invoice for"):
        inv(s, action="invoice", client="Bob")


def test_registered_with_alfred(s):
    names = {t["name"] for t in tools.client_tool_definitions(s)}
    assert {"web_client_finder", "web_design_sales", "web_design_outreach", "web_design_invoices"} <= names


def test_existing_website_takes_20_percent_off_business_and_shop(s):
    out = sales(s, action="quote", client="Ada's Cafe", package="business", existing_website=True)
    q = st.rows_of(s, st.QUOTES)[0]
    assert q["total"] == 716 and q["rebuild_discount"] == 179 and "£716" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Ada's Cafe" / "Quote Q-0001.html").read_text(encoding="utf-8")
    assert "Existing website: 20% off" in html and "-£179" in html
    sales(s, action="quote", client="Shop Co", package="shop", existing_website=True, discount=76)
    assert st.rows_of(s, st.QUOTES)[1]["total"] == 1200
    sales(s, action="quote", client="Tiny", package="starter", existing_website=True)
    assert st.rows_of(s, st.QUOTES)[2]["total"] == 395  # starter sites don't get it
    sales(s, action="quote", client="Bo", package="business", existing_website="yes")
    assert st.rows_of(s, st.QUOTES)[3]["total"] == 895  # only a real true counts


def test_care_plan_is_priced_by_package(s):
    p = ks.prices(s)
    assert [ks.care_price(p, k) for k in ("starter", "business", "shop")] == [20, 25, 30]
    for i, pk in enumerate(("starter", "business", "shop")):
        sales(s, action="quote", client=f"Shop {i}", package=pk)
    assert [q["care"] for q in st.rows_of(s, st.QUOTES)] == [20, 25, 30]
    sales(s, action="set_price", item="care_plan", package="shop", price=35)
    assert [ks.care_price(ks.prices(s), k) for k in ("starter", "business", "shop")] == [20, 25, 35]
    assert "£20 starter, £25 business, £35 shop" in sales(s, action="prices")


# ---- worldwide outreach --------------------------------------------------------------

def test_local_prices_convert_from_pounds_and_round_to_friendly_numbers():
    assert world.local_price(395, "USD") == "about $499 (£395)"
    assert world.local_price(395, "GBP") == "£395"
    assert world.convert(895, "USD") == 1099 and world.convert(395, "KRW") == 690_000
    assert world.friendly(497.7) == 499 and world.friendly(691_250) == 690_000 and world.friendly(42) == 40
    for code in ("USD", "EUR", "NGN", "ZAR", "KES", "GHS", "CNY", "KRW", "CAD", "AUD", "AED", "INR"):
        assert world.RATES_FROM_GBP[code] > 0 and code in world.CURRENCIES
        assert world.local_price(395, code).endswith("(£395)")
    with pytest.raises(ValueError, match="rate"):
        world.convert(10, "XYZ")


def test_countries_map_to_currency_and_language():
    cases = {"UK": ("GB", "GBP", "en"), "Germany": ("DE", "EUR", "de"), "france": ("FR", "EUR", "fr"),
             "Spain": ("ES", "EUR", "es"), "Portugal": ("PT", "EUR", "pt"), "Italy": ("IT", "EUR", "it"),
             "Netherlands": ("NL", "EUR", "nl"), "USA": ("US", "USD", "en"), "Canada": ("CA", "CAD", "en"),
             "Nigeria": ("NG", "NGN", "en"), "South Africa": ("ZA", "ZAR", "en"), "Kenya": ("KE", "KES", "en"),
             "Ghana": ("GH", "GHS", "en"), "China": ("CN", "CNY", "zh"), "Korea": ("KR", "KRW", "ko"),
             "Australia": ("AU", "AUD", "en"), "UAE": ("AE", "AED", "ar"), "India": ("IN", "INR", "en")}
    for name, (code, currency, language) in cases.items():
        assert world.country_code(name) == code
        assert world.currency_of(code) == currency and world.language_of(code) == language
    assert world.country_code("Atlantis") == "" and world.currency_of("") == "GBP" and world.language_of("") == "en"
    assert world.currency_of("SE") == "GBP"  # no rate for kronor yet, so pounds only
    assert world.language_code(None, "KR") == "ko" and world.language_code("Chinese") == "zh"
    assert world.language_code("fr", "GB") == "fr"
    with pytest.raises(ValueError, match="Which language"):
        world.language_code("Klingon")


def test_each_country_gets_its_own_email_rules_note():
    expect = {"GB": ["PECR", "sole traders"], "FR": ["GDPR", "Germany and Austria", "contact form"],
              "DE": ["GDPR", "consent", "DM"], "US": ["CAN-SPAM", "postal address", "opt out"],
              "CA": ["CASL", "consent", "DM", "contact form"], "NG": ["NDPR"], "ZA": ["POPIA"],
              "KE": ["Data Protection Act"], "CN": ["PIPL", "don't send cold email", "Douyin", "Xiaohongshu", "WeChat"],
              "KR": ["PIPA", "don't send cold email", "Instagram", "Naver", "KakaoTalk"]}
    for code, bits in expect.items():
        note = world.compliance_note(code)
        for bit in bits:
            assert bit in note, (code, bit)
    assert world.compliance_note("") == world.compliance_note("GB")
    assert "opt-out" in world.compliance_note("BR")  # anywhere else gets the general advice
    assert [world.default_channel(c) for c in ("GB", "US", "DE", "CN", "KR", "CA")] == \
        ["email", "email", "dm", "dm", "dm", "dm"]


def test_payment_terms_are_half_and_half_never_monthly(s):
    terms = "half when we start building, half once everything's complete"
    assert world.payment_terms(50) == terms
    assert world.payment_terms(30) == "30% when we start building, the rest once everything's complete"
    sales(s, action="quote", client="Ada", package="starter")
    out = sales(s, action="quote", client="Ada", package="business", country="USA")
    assert terms in out and "£895 (about $1,099)" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Ada" / "Quote Q-0002.html").read_text(encoding="utf-8")
    assert terms in html and "about $1,099 in US dollars" in html
    for channel in ks.CHANNELS:
        body = sales(s, action="outreach", client="Ada", channel=channel).card["text"]
        assert terms in body
        assert "klarna" not in body.lower() and "monthly payment" not in body.lower()
    assert "In US dollars that's roughly: starter $499 (£395)" in sales(s, action="prices", country="US")


class FakeClaude:
    def __init__(self):
        self.asked = []
        self.messages = self

    async def create(self, **kw):
        self.asked.append(kw)
        return type("R", (), {"content": [type("B", (), {"type": "text", "text": "안녕하세요 (Korean draft)"})()]})()


def test_finder_works_worldwide_and_keeps_the_country(s, monkeypatch):
    out = finder(s, action="find", town="Lagos", country="Nigeria", kind="salons")
    assert "near Stockport" in out  # the mock map always answers Stockport; the country still sticks
    rows = st.rows_of(s, st.PROSPECTS)
    assert rows and all(r["country"] == "NG" for r in rows)
    assert kf.kind_key("salons") == "hairdressers" and kf.kind_key("barbers") == "hairdressers"
    assert [r[1] for r in finder(s, action="prospects", country="Nigeria").card["rows"]]
    with pytest.raises(ValueError, match="No prospects"):
        finder(s, action="prospects", country="Kenya")
    email = sales(s, action="outreach", client="Sal's Cafe", channel="email")
    assert "Websites start from about ₦770,000 (£395)" in email.card["text"] and "NDPR" in email
    assert email.card["text"].endswith(world.OPT_OUT) and "a web designer based in the UK" not in email.card["text"]


def test_outreach_abroad_is_translated_with_english_underneath(s, monkeypatch):
    fake = FakeClaude()
    monkeypatch.setattr(helpers, "_client", fake)
    out = sales(s, action="outreach", client="Seoul Barbers", country="South Korea")
    body = out.card["text"]
    assert out.card["title"] == "Outreach: Seoul Barbers" and "drafted a dm for Seoul Barbers (South Korea) in Korean" in out
    assert body.startswith("안녕하세요") and "English version:" in body and body.endswith(world.OPT_OUT)
    assert "KakaoTalk" in out and "about ₩690,000 (£395)" in body and "Nothing has been sent" in out
    assert "Korean" in fake.asked[0]["messages"][0]["content"] and fake.asked[0]["model"] == s.model
    us = sales(s, action="outreach", client="Austin Tacos", country="USA").card["text"]
    assert "[your postal address]" in us and "CAN-SPAM" not in us and len(fake.asked) == 1  # English: no call
    fr = sales(s, action="outreach", client="Café Lyon", country="France", language="de", channel="letter")
    assert "in German" in fr and fake.asked[-1]["messages"][0]["content"].count("German") == 1
    monkeypatch.setattr(helpers, "_client", None)
    plain = sales(s, action="outreach", client="Bar Madrid", country="Spain", channel="email")
    assert "couldn't translate it into Spanish" in plain and "English version" not in plain.card["text"]
    assert "€459" in plain.card["text"] and plain.card["text"].endswith(world.OPT_OUT)


# ---- outreach tracker ----------------------------------------------------------------

def ago(days: int) -> str:
    return (st.today() - timedelta(days=days)).isoformat()


def lead(s, name):
    return next(r for r in st.rows_of(s, st.OUTREACH) if r["name"] == name)


def outreach_files(s, name):
    return sorted(p.name for p in (memory.root(s) / "Kinetic Web Designs" / "Clients" / name).glob("Outreach*"))


def test_drafts_are_recorded_and_nobody_is_messaged_twice(s):
    finder(s, action="find", town="Stockport")
    sales(s, action="outreach", client="Joe's Barbers", contact_name="Joe", channel="email")
    row = lead(s, "Joe's Barbers")
    assert row["status"] == "drafted" and row["draft_channel"] == "email" and row["contact_name"] == "Joe"
    assert row["prospect"] == st.find_prospect(st.rows_of(s, st.PROSPECTS), "Joe's Barbers")["id"]
    said = track(s, action="mark", business="Joe's Barbers", status="contacted", channel="email")
    assert said.startswith("Noted: you messaged Joe's Barbers by email.") and "a polite follow-up" in said
    assert "a last short one on" in said
    assert lead(s, "Joe's Barbers")["messages"] == 1
    track(s, action="mark", business="Joe's Barbers", status="contacted", channel="email")  # said twice: one message
    assert lead(s, "Joe's Barbers")["messages"] == 1
    finder_row = st.find_prospect(st.rows_of(s, st.PROSPECTS), "Joe's Barbers")
    assert finder_row["status"] == "contacted" and finder_row["contacted"] == st.today().isoformat()
    again = sales(s, action="outreach", client="Joe's Barbers")
    assert isinstance(again, str) and "already messaged Joe's Barbers by email" in again and "No double messaging" in again
    assert len(outreach_files(s, "Joe's Barbers")) == 1  # no second draft
    assert "won't draft anything for them again" in track(s, action="mark", business="Bloom", status="opted out")
    with pytest.raises(ValueError, match="won't draft anything"):
        sales(s, action="outreach", client="Bloom")
    with pytest.raises(ValueError, match="shouldn't be messaged again"):
        track(s, action="mark", business="Bloom", status="contacted")
    track(s, action="mark", business="Sal's Cafe", status="not interested", date="yesterday")
    with pytest.raises(ValueError, match="won't draft anything"):
        sales(s, action="outreach", client="Sal's Cafe", channel="phone")
    assert st.find_prospect(st.rows_of(s, st.PROSPECTS), "Sal's Cafe")["status"] == "not interested"
    assert outreach_files(s, "Bloom") == [] and outreach_files(s, "Sal's Cafe") == []
    track(s, action="mark", business="Gone Garage", status="interested")
    assert "already marked interested" in sales(s, action="outreach", client="Gone Garage")
    with pytest.raises(ValueError, match="Mark it as one of"):
        track(s, action="mark", business="Gone Garage", status="maybe")
    with pytest.raises(ValueError, match="in the future"):
        track(s, action="mark", business="Gone Garage", status="replied", date="tomorrow")


def test_finder_mark_keeps_the_tracker_in_step(s):
    finder(s, action="find", town="Stockport")
    finder(s, action="mark", business="Bloom", status="contacted")
    assert lead(s, "Bloom")["status"] == "contacted" and lead(s, "Bloom")["messages"] == 1
    finder(s, action="mark", business="Sal's Cafe", status="client")
    assert lead(s, "Sal's Cafe")["status"] == "won"
    track(s, action="mark", business="Joe's Barbers", status="won")
    assert st.find_prospect(st.rows_of(s, st.PROSPECTS), "Joe's Barbers")["status"] == "client"


def test_two_follow_ups_at_three_and_seven_days_then_stop(s):
    finder(s, action="find", town="Stockport")
    sales(s, action="my_details", owner="Lee")
    sales(s, action="outreach", client="Joe's Barbers", contact_name="Joe")
    track(s, action="mark", business="Joe's Barbers", status="contacted", channel="email", date=ago(3))
    track(s, action="mark", business="Sal's Cafe", status="contacted", channel="phone", date=ago(2))
    due = track(s, action="follow_ups")
    assert "1 lead is due a follow-up: Joe's Barbers." in due and [r[0] for r in due.card["rows"]] == ["Joe's Barbers"]
    assert due.card["rows"][0][1] == "First" and "day 3 and day 7" in due
    assert "Give them until" in track(s, action="follow_up", business="Sal's Cafe")
    assert "haven't told me you've messaged Bloom" in track(s, action="follow_up", business="Bloom")
    out = track(s, action="follow_up", business="Joe's Barbers")
    body = out.card["text"]
    assert out.card["title"] == "Follow-up: Joe's Barbers" and "Nothing has been sent" in out
    assert "a polite follow-up" in out and "first of two follow-ups" in out
    assert body.startswith("Subject: Following up: Joe's Barbers's website") and "Hi Joe," in body
    assert "following up on my email from" in body and "Alfred, Kinetic Web Designs" in body and "Lee" not in body
    assert "half when we start building, half once everything's complete" in body and body.endswith(world.OPT_OUT)
    assert "klarna" not in body.lower() and "monthly payment" not in body.lower()
    assert "Outreach follow-up email " + st.today().isoformat() + ".md" in outreach_files(s, "Joe's Barbers")
    assert lead(s, "Joe's Barbers")["follow_up_drafted"] == st.today().isoformat()
    plain = track(s, action="follow_up", business="Joe's Barbers", channel="dm", price=False).card["text"]
    assert "Websites start from" not in plain and plain.endswith(world.OPT_OUT)
    said = track(s, action="mark", business="Joe's Barbers", status="contacted", channel="email")
    assert "That's their first follow-up" in said and lead(s, "Joe's Barbers")["messages"] == 2
    assert "Nobody is due a follow-up" in track(s, action="follow_ups")  # the last one waits for day 7
    wait = track(s, action="follow_up", business="Joe's Barbers")
    assert "Give them until" in wait and "their last follow-up" in wait
    assert lead(s, "Joe's Barbers")["contacted"] == ago(3)  # the first message's date
    rows = st.rows_of(s, st.OUTREACH)
    next(r for r in rows if r["name"] == "Joe's Barbers")["contacted"] = ago(7)  # four days on
    st.save(s, st.OUTREACH, rows)
    due = track(s, action="follow_ups")
    assert "Joe's Barbers (last one)" in due and due.card["rows"][0][1] == "Last"
    last = track(s, action="follow_up", business="Joe's Barbers")
    body = last.card["text"]
    assert "short last follow-up" in last and "It's their last follow-up" in last
    assert body.startswith("Subject: Last note: Joe's Barbers's website") and "One last note from me" in body
    assert "mock-up I made for you is still yours" in body and "won't message again" in body
    assert "Websites start from" not in body and body.endswith(world.OPT_OUT) and "Lee" not in body
    said = track(s, action="mark", business="Joe's Barbers", status="contacted", channel="dm")  # not the same message
    assert "three messages in all" in said and lead(s, "Joe's Barbers")["messages"] == 3 == ko.MAX_MESSAGES
    assert "Nobody is due a follow-up" in track(s, action="follow_ups")
    assert "Two follow-ups is the limit" in track(s, action="follow_up", business="Joe's Barbers")
    assert "3 messages already" in sales(s, action="outreach", client="Joe's Barbers")
    track(s, action="mark", business="Joe's Barbers", status="replied")
    assert "already replied" in track(s, action="follow_up", business="Joe's Barbers")
    track(s, action="mark", business="Joe's Barbers", status="opted out")
    with pytest.raises(ValueError, match="won't draft anything"):
        track(s, action="follow_up", business="Joe's Barbers")


def test_follow_up_due_dates_count_from_the_first_message(s):
    rows = [{"name": "A", "status": "contacted", "messages": 1, "contacted": ago(2), "last_contacted": ago(2)},
            {"name": "B", "status": "contacted", "messages": 1, "contacted": ago(3), "last_contacted": ago(3)},
            {"name": "C", "status": "contacted", "messages": 2, "contacted": ago(6), "last_contacted": ago(1)},
            {"name": "D", "status": "contacted", "messages": 2, "contacted": ago(7), "last_contacted": ago(4)},
            {"name": "E", "status": "contacted", "messages": 3, "contacted": ago(20), "last_contacted": ago(13)},
            {"name": "F", "status": "replied", "messages": 1, "contacted": ago(9), "last_contacted": ago(9)}]
    st.save(s, st.OUTREACH, [{"id": i, **r} for i, r in enumerate(rows, 1)])
    assert [r["name"] for r in ko.due_rows(s)] == ["B", "D"]  # B's first (day 3) and D's last (day 7) are due today
    assert ko.next_due(rows[0]) == st.today() + timedelta(days=1) and ko.next_due(rows[4]) is None
    assert [r["name"] for r in ko.due_rows(s, st.today() + timedelta(days=1))] == ["B", "D", "A", "C"]


def test_follow_up_abroad_is_in_their_language(s, monkeypatch):
    fake = FakeClaude()
    monkeypatch.setattr(helpers, "_client", fake)
    sales(s, action="outreach", client="Seoul Barbers", country="South Korea")
    assert lead(s, "Seoul Barbers")["country"] == "KR" and lead(s, "Seoul Barbers")["draft_channel"] == "dm"
    track(s, action="mark", business="Seoul Barbers", status="contacted", date=ago(8))
    assert lead(s, "Seoul Barbers")["channel"] == "dm"  # the channel of the draft
    out = track(s, action="follow_up", business="Seoul Barbers")
    body = out.card["text"]
    assert "follow-up dm for Seoul Barbers in Korean" in out and body.startswith("안녕하세요")
    assert "English version:" in body and "about ₩690,000 (£395)" in body and body.endswith(world.OPT_OUT)
    assert "Korean" in fake.asked[-1]["messages"][0]["content"]


def test_summary_counts_per_status_and_country(s):
    finder(s, action="find", town="Stockport")
    sales(s, action="outreach", client="Seoul Barbers", country="South Korea")
    track(s, action="mark", business="Joe's Barbers", status="contacted", channel="visit")
    track(s, action="mark", business="Bloom", status="won")
    out = track(s, action="summary")
    assert out.startswith("5 leads: 2 new, 1 drafted, 1 contacted, 1 won.")
    assert "By country: United Kingdom 4, South Korea 1." in out
    rows = {r[0]: r for r in out.card["rows"]}
    assert rows["All"][-1] == "5" and rows["South Korea"][2] == "1" and rows["United Kingdom"][1] == "2"
    listed = track(s, action="leads", country="South Korea")
    assert [r[0] for r in listed.card["rows"]] == ["Seoul Barbers"]
    assert [r[0] for r in track(s, action="leads", status="won").card["rows"]] == ["Bloom"]
    with pytest.raises(ValueError, match="No leads"):
        track(s, action="leads", status="opted out")


def test_daily_follow_up_reminder_is_said_once_a_day(s, monkeypatch):
    from datetime import datetime
    today = st.today()
    early, later = datetime(today.year, today.month, today.day, 8), datetime(today.year, today.month, today.day, 10)
    assert ko.reminder_line(s, later) == ""  # nothing due: nothing said
    st.save(s, ko.REMINDED, {})
    for name in ("Ada", "Bob"):
        track(s, action="mark", business=name, status="contacted", channel="email", date=ago(3))
    track(s, action="mark", business="Cal", status="contacted", channel="email", date=ago(2))
    assert ko.reminder_line(s, early) == ""  # not before nine
    said = ko.reminder_line(s, later)
    assert said == "Sir, 2 Kinetic leads are due a follow-up: Ada, Bob. Say \"draft the follow-ups\" when you're ready."
    assert ko.reminder_line(s, later) == ""  # once a day
    tomorrow = later + timedelta(days=1)
    assert "3 Kinetic leads are due" in ko.reminder_line(s, tomorrow)

    heard = []

    async def announce(text, kind):
        heard.append((text, kind))
        raise asyncio.CancelledError  # stop the watcher after its first heads-up

    st.save(s, ko.REMINDED, {})
    monkeypatch.setattr(ko, "REMIND_HOUR", 0)  # the watcher reads the real clock: don't wait for nine o'clock
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(ko.watch(s, announce, lambda: True), 10))  # fail, never hang
    assert heard and heard[0][1] == "sales" and "due a follow-up" in heard[0][0]


# ---- best bets, Google Places, founding clients, reviews and referrals ----------------------

def test_social_page_only_counts_as_no_website_and_ranks_first(s, monkeypatch):
    monkeypatch.setitem(globals(), "ELEMENTS", ELEMENTS + [
        {"type": "node", "id": 6, "tags": {"name": "Lily's Nails", "shop": "beauty",
                                           "website": "https://www.facebook.com/lilysnails", "phone": "0161 222"}},
        {"type": "node", "id": 7, "tags": {"name": "Ink Studio", "shop": "tattoo",
                                           "website": "https://instagram.com/inkstudio"}}])
    out = finder(s, action="find", town="Stockport", kind="mixed")
    rows = out.card["rows"]
    assert [r[1] for r in rows] == ["Lily's Nails", "Sal's Cafe", "Ink Studio", "Gone Garage", "Joe's Barbers", "Bloom"]
    assert rows[0][3] == "none" and rows[0][5] == "No website (Facebook only)" and rows[2][5] == "No website (Instagram only)"
    assert "3 with no website" in out
    lily = st.find_prospect(st.rows_of(s, st.PROSPECTS), "Lily's Nails")
    assert lily["website"] == "" and lily["facebook"] == "https://www.facebook.com/lilysnails" and "audit" not in lily
    assert "only your Facebook page" in sales(s, action="outreach", client="Lily's Nails").card["text"]
    with pytest.raises(ValueError, match="Facebook page, not a website"):
        finder(s, action="audit", url="https://m.facebook.com/somewhere")
    # a social page saved as a "website" before this counted as none is fixed on the next find
    saved = st.rows_of(s, st.PROSPECTS)
    next(r for r in saved if r["name"] == "Ink Studio").update(website="https://instagram.com/inkstudio", instagram="")
    st.save(s, st.PROSPECTS, saved)
    finder(s, action="find", town="Stockport", kind="mixed")
    assert st.find_prospect(st.rows_of(s, st.PROSPECTS), "Ink Studio")["website"] == ""


def test_rank_key_puts_no_site_and_broken_before_weakest_score():
    def p(name, website="", grade=None, score=0, **kw):
        return {"name": name, "website": website, **({"audit": {"grade": grade, "score": score}} if grade else {}), **kw}
    rows = [p("Strong", "https://a.test", "good", 92), p("Unchecked", "https://b.test"), p("Weak", "https://c.test", "weak", 20),
            p("Broken", "https://d.test", "down"), p("FB", "https://facebook.com/x"), p("Quiet"), p("Phone", phone="1"),
            p("Okay", "https://e.test", "ok", 60)]
    assert [r["name"] for r in sorted(rows, key=kf.rank_key)] == \
        ["Phone", "FB", "Quiet", "Broken", "Weak", "Okay", "Strong", "Unchecked"]  # ones you can reach first
    assert kf.social_of("https://www.facebook.com/x") == "facebook" and kf.social_of("https://notfacebook.com") == ""


PLACES_PAGES = [
    {"places": [{"id": "g1", "displayName": {"text": "Fade Room"}, "formattedAddress": "1 King St, Manchester M2 4LQ, UK",
                 "nationalPhoneNumber": "0161 555 0001", "businessStatus": "OPERATIONAL", "types": ["barber_shop"],
                 "googleMapsUri": "https://maps.google.com/?cid=1", "rating": 4.8, "userRatingCount": 120},
                {"id": "g2", "displayName": {"text": "Costa Coffee"}, "businessStatus": "OPERATIONAL"},
                {"id": "g3", "displayName": {"text": "Old Barbers"}, "businessStatus": "CLOSED_PERMANENTLY"}],
     "nextPageToken": "page2"},
    {"places": [{"id": "g4", "displayName": {"text": "Joe's Barbers"}, "websiteUri": "http://joes.test",
                 "formattedAddress": "4 High St, Manchester, UK", "businessStatus": "OPERATIONAL",
                 "types": ["hair_care", "point_of_interest"]},
                {"id": "g5", "displayName": {"text": "Snip Snip"}, "websiteUri": "https://www.instagram.com/snipsnip",
                 "formattedAddress": "9 Deansgate, Manchester, UK"}],
     "nextPageToken": "page3"},
    {"places": [{"id": "g6", "displayName": {"text": "Gone Garage"}, "websiteUri": "https://gone.test"}],
     "nextPageToken": "page4"},
    {"places": [{"id": "g7", "displayName": {"text": "Page Four"}}]},
]
places_calls = []


def places_handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "places.googleapis.com":
        body = json.loads(request.content)
        places_calls.append((dict(request.headers), body))
        if request.headers.get("x-goog-api-key") != "test-key":
            return httpx.Response(403, json={"error": {"message": "API key not valid"}})
        page = {"": 0, "page2": 1, "page3": 2, "page4": 3}[body.get("pageToken", "")]
        return httpx.Response(200, json=PLACES_PAGES[page])
    return handler(request)


def places_finder(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(places_handler)) as http:
            return await kf.run_tool("web_client_finder", args, s, http)
    return asyncio.run(go())


def test_google_places_finds_leads_with_a_minimal_field_mask_and_a_call_cap(s, monkeypatch, capsys):
    from dataclasses import replace
    places_calls.clear()
    monkeypatch.setitem(kf.places_used, "calls", 0)
    g = replace(s, google_places_key="test-key", places_max_calls=100)
    out = places_finder(g, action="find", town="Manchester", kind="barbers")
    assert len(places_calls) == 3 and not queries  # three pages at most, and no OpenStreetMap
    headers, body = places_calls[0]
    assert body == {"textQuery": "hairdressers and barbers in Manchester", "pageSize": 20}
    assert places_calls[1][1]["pageToken"] == "page2" and places_calls[2][1]["pageToken"] == "page3"
    mask = headers["x-goog-fieldmask"]
    assert mask.split(",") == [f"places.{f}" for f in ("id", "displayName", "formattedAddress", "websiteUri",
                                                       "nationalPhoneNumber", "internationalPhoneNumber", "googleMapsUri",
                                                       "businessStatus", "types", "rating", "userRatingCount")] + ["nextPageToken"]
    names = [r[1] for r in out.card["rows"]]
    assert "Costa Coffee" not in names and "Old Barbers" not in names and "Page Four" not in names
    assert names == ["Fade Room", "Snip Snip", "Gone Garage", "Joe's Barbers"]
    assert "Found on Google Maps" in out and "test-key" not in out and "test-key" not in capsys.readouterr().out
    fade = st.find_prospect(st.rows_of(s, st.PROSPECTS), "Fade Room")
    assert fade["google"] == "g1" and fade["country"] == "GB" and fade["rating"] == 4.8 and fade["kind"] == "barber shop"
    assert "Google rating: 4.8 (120 reviews)" in places_finder(g, action="prospect", business="Fade Room").card["text"]
    assert st.find_prospect(st.rows_of(s, st.PROSPECTS), "Snip Snip")["instagram"] == "https://www.instagram.com/snipsnip"
    places_finder(g, action="find", town="Manchester", kind="barbers")  # the same places again: refreshed, not doubled
    assert len(st.rows_of(s, st.PROSPECTS)) == 4
    # the cap: one call left, then nothing more until Alfred restarts
    monkeypatch.setitem(kf.places_used, "calls", 99)
    places_calls.clear()
    places_finder(g, action="find", town="Manchester", kind="barbers")
    assert len(places_calls) == 1
    out = places_finder(g, action="find", town="Stockport", kind="mixed")
    assert "JARVIS_PLACES_MAX_CALLS" in out and "OpenStreetMap instead" in out and queries  # fell back
    assert len(places_calls) == 1


def test_google_places_bad_key_falls_back_to_openstreetmap(s, monkeypatch):
    from dataclasses import replace
    monkeypatch.setitem(kf.places_used, "calls", 0)
    out = places_finder(replace(s, google_places_key="wrong"), action="find", town="Stockport", kind="mixed")
    assert "turned the key down" in out and "OpenStreetMap instead" in out and "wrong" not in out
    assert [r[1] for r in out.card["rows"]][:2] == ["Sal's Cafe", "Gone Garage"]
    queries.clear()
    finder(s, action="find", town="Stockport")  # no key: OpenStreetMap, no Google call
    assert queries and kf.places_used["calls"] == 1


def test_founding_offer_never_stacks_with_the_existing_website_discount(s):
    out = sales(s, action="quote", client="Ada", package="business", founding=True)
    q = st.rows_of(s, st.QUOTES)[0]
    assert q["total"] == 795 and q["founding_discount"] == 100 and q["rebuild_discount"] == 0
    assert "£100 founding client offer" in out
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Ada" / "Quote Q-0001.html").read_text(encoding="utf-8")
    assert "Founding client offer: £100 off" in html and "honest Google review" in html
    assert "half when we start building, half once everything" in html and "No monthly instalments" in html
    assert "https://kineticwebdesigns.co.uk/#quote" in html
    sales(s, action="quote", client="Bob", package="business", founding=True, existing_website=True)
    bob = st.rows_of(s, st.QUOTES)[1]  # 20% of £895 is £179, more than £100: the rebuild discount wins
    assert bob["rebuild_discount"] == 179 and bob["founding_discount"] == 0 and bob["total"] == 716
    sales(s, action="quote", client="Cal", package="starter", founding=True, existing_website=True)
    cal = st.rows_of(s, st.QUOTES)[2]  # no rebuild discount on a starter site: the founding offer
    assert cal["founding_discount"] == 100 and cal["rebuild_discount"] == 0 and cal["total"] == 295
    sales(s, action="quote", client="Dee", package="business", founding=True)
    with pytest.raises(ValueError, match="first 3 clients"):
        sales(s, action="quote", client="Eve", package="business", founding=True)
    sales(s, action="quote", client="Ada", package="shop", founding=True)  # Ada already has it: still fine
    assert "Quote Q-0004 is now declined." == sales(s, action="quote_status", quote="Q-0004", status="declined")
    sales(s, action="quote", client="Eve", package="business", founding=True)  # Dee declined: a place is free


def test_invoice_has_half_and_half_terms_and_the_plan_link(s):
    sales(s, action="quote", client="Sal's Cafe", package="business")
    inv(s, action="invoice", quote="Q-0001")
    html = (memory.root(s) / "Kinetic Web Designs" / "Clients" / "Sal's Cafe" / "Invoice INV-0001.html").read_text(encoding="utf-8")
    assert "Payment terms: half when we start building, half once everything&#x27;s complete" in html or \
        "Payment terms: half when we start building, half once everything's complete" in html
    assert "https://kineticwebdesigns.co.uk/#quote" in html and "klarna" not in html.lower()
    inv(s, action="invoice", quote="Q-0001", part="final")
    reminder = inv(s, action="reminder", invoice="INV-0002").card["text"]
    assert reminder.endswith("Thanks,\nAlfred, Kinetic Web Designs")


def test_review_and_referral_requests_for_won_clients(s, monkeypatch):
    from dataclasses import replace
    assert "No won clients yet" in track(s, action="ask_reviews")
    track(s, action="mark", business="Bloom", status="interested")
    assert "isn't a client yet" in track(s, action="review_request", business="Bloom")
    said = track(s, action="mark", business="Bloom", status="won")
    assert "Once their site is live" in said
    said = track(s, action="mark", business="Bloom", status="live")
    assert 'ask Bloom for a review' in said and lead(s, "Bloom")["status"] == "live"
    out = track(s, action="review_request", business="Bloom", contact_name="Bea")
    body = out.card["text"]
    assert "Subject: Could you leave Kinetic Web Designs a quick Google review?" in body and "Hi Bea," in body
    assert "[your Google review link]" in body and "JARVIS_KINETIC_REVIEW_LINK" in out and "Nothing has been sent" in out
    assert "Recommend a business to us, and when their website goes live you get a free month of hosting and care" in body
    assert body.count("Thanks,\nAlfred, Kinetic Web Designs") == 2 and "founding" not in body.lower()
    folder = memory.root(s) / "Kinetic Web Designs" / "Clients" / "Bloom"
    assert (folder / f"Review request {st.today().isoformat()}.md").exists()
    assert (folder / f"Referral note {st.today().isoformat()}.md").exists()
    assert lead(s, "Bloom")["review_asked"] == st.today().isoformat()
    # founding clients get a reminder of their agreement, with the user's own review link
    g = replace(s, kinetic_review_link="https://g.page/r/kinetic/review")
    sales(s, action="quote", client="Sal's Cafe", package="starter", founding=True)
    sales(s, action="quote_status", quote="Q-0001", status="accepted")
    for name in ("Ada", "Bob", "Cal", "Dee", "Eve", "Fay"):
        track(s, action="mark", business=name, status="won")
    track(s, action="mark", business="Fay", status="won", founding=True)
    ask = track(g, action="ask_reviews")
    names = [r[0] for r in ask.card["rows"]]
    assert len(names) == 5 and set(names[:2]) == {"Fay", "Sal's Cafe"} and "Bloom" not in names  # founding first
    assert "7 clients not asked for a Google review yet" in ask and ask.card["rows"][0][2] == "yes"
    out = track(g, action="review_request", business="Sal's Cafe")
    body = out.card["text"]
    assert "founding clients" in body and "£100 off" in body and "honest Google review" in body
    assert "permission to show the site" in body and "https://g.page/r/kinetic/review" in body
    assert "JARVIS_KINETIC_REVIEW_LINK" not in out and "founding client review reminder" in out
    assert lead(s, "Sal's Cafe")["status"] == "won" and lead(s, "Sal's Cafe")["founding"] is True
    assert "Sal's Cafe" not in [r[0] for r in track(g, action="ask_reviews", count=10).card["rows"]]
    track(s, action="mark", business="Bloom", status="opted out")
    with pytest.raises(ValueError, match="won't draft anything"):
        track(s, action="review_request", business="Bloom")
    for text in (body, out):
        assert "klarna" not in str(text).lower()
