import asyncio
import json
from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest

import kinetic_find as kf
import kinetic_invoices as ki
import kinetic_sales as ks
import kinetic_store as st
import freelance_store
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
    return ks.run_tool("web_design_sales", args, s)


def inv(s, **args):
    return ki.run_tool("web_design_invoices", args, s)


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


def test_outreach_drafts_are_never_sent(s):
    finder(s, action="find", town="Stockport")
    sales(s, action="my_details", owner="Lee", phone="07000 000000")
    email = sales(s, action="outreach", client="Joe's Barbers", contact_name="Joe")
    body = email.card["text"]
    assert body.startswith("Subject: A quick idea for Joe's Barbers") and "Hi Joe," in body
    assert "No padlock" in body and "no thanks" in body and "Lee" in body
    assert "Nothing has been sent" in email and "sole traders" in email
    none = sales(s, action="outreach", client="Sal's Cafe", channel="phone").card["text"]
    assert "couldn't find a website" in none and "0161 000 0000" in none
    assert sales(s, action="outreach", client="Bloom", channel="visit").card["text"].startswith("Walk-in script")
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
    assert {"web_client_finder", "web_design_sales", "web_design_invoices"} <= names
