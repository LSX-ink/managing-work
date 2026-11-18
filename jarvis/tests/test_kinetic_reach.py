import asyncio
import json
import subprocess
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

import kinetic_briefing as kb
import kinetic_find as kf
import kinetic_outreach as ko
import kinetic_reach as kr
import kinetic_sales as ks
import kinetic_site as ksite
import kinetic_store as st
import kinetic_video as kv
import kinetic_world as world
import memory
import tools
import tts
import videojoin
from config import Settings
from test_kinetic import handler, queries

TERMS = "half when we start building, half once everything's complete"
AUDIT = {"url": "http://joes.test", "score": 22, "grade": "weak", "booking": False, "date": "2026-10-01",
         "problems": [{"points": 20, "problem": "No padlock (no HTTPS)", "why": "Browsers say Not secure."},
                      {"points": 20, "problem": "Not made for phones", "why": "Tiny on phones."},
                      {"points": 10, "problem": "Slow to load (4.2s)", "why": "People leave."}]}
LEADS = [
    {"id": 1, "name": "Fade Room", "kind": "barber shop", "town": "Stockport", "website": "", "phone": "0161 555 0001",
     "address": "9 King St, Stockport", "lat": 53.4100, "lon": -2.1500, "country": "GB", "status": "new"},
    {"id": 2, "name": "Snip Snip", "kind": "hairdresser", "town": "Stockport", "website": "",
     "instagram": "https://instagram.com/snipsnip", "address": "2 Mill Lane, Stockport", "lat": 53.4300,
     "lon": -2.1500, "country": "GB", "status": "new"},
    {"id": 3, "name": "Close Cuts", "kind": "hairdresser", "town": "Stockport", "website": "",
     "address": "11 King St, Stockport", "lat": 53.4110, "lon": -2.1500, "country": "GB", "status": "new"},
    {"id": 4, "name": "Sam's Cafe", "kind": "cafe", "town": "Stockport", "website": "", "address": "1 Bridge St",
     "lat": 53.4105, "lon": -2.1490, "country": "GB", "status": "new"},
    {"id": 5, "name": "Joe's Barbers", "kind": "hairdresser", "town": "Stockport", "website": "http://joes.test",
     "address": "4 High St, Stockport", "country": "GB", "status": "new", "audit": AUDIT},
    {"id": 6, "name": "Kurz Friseur", "kind": "hairdresser", "town": "Berlin", "website": "https://kurz.test",
     "country": "DE", "status": "new", "audit": AUDIT},
    {"id": 7, "name": "Seoul Cuts", "kind": "hairdresser", "town": "Seoul", "website": "", "country": "KR",
     "status": "new"},
    {"id": 8, "name": "Northern Plumbing Ltd", "kind": "plumber", "town": "Leeds", "website": "https://np.test",
     "country": "GB", "status": "new", "audit": AUDIT},
]


@pytest.fixture
def s(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    st.save(s, st.PROSPECTS, json.loads(json.dumps(LEADS)))
    return s


def sales(s, **args):
    return asyncio.run(ks.run_tool("web_design_sales", args, s))


def reach(s, **args):
    return asyncio.run(kr.run_tool("web_design_reach", args, s))


def kinetic(s, *parts) -> Path:
    return memory.root(s) / st.FOLDER / Path(*parts)


def message_part(text: str) -> str:
    """A DM or WhatsApp message without its opt-out line."""
    return text.rsplit("\n\n", 1)[0]


# ---- A + B + C: problem first, see your design before you pay, the channel by lead type -------------------

def test_biggest_problem_in_plain_words():
    assert kf.biggest_problem(LEADS[0])["label"] == "no website"
    assert "only your Instagram page" in kf.biggest_problem(LEADS[1])["line"]
    joe = kf.biggest_problem(LEADS[4])
    assert joe["label"] == "broken on phones" and joe["line"].startswith("Your website (joes.test) is hard to use")
    shop = {**LEADS[4], "name": "Pipe Co", "kind": "plumber", "audit": {**AUDIT, "problems": AUDIT["problems"][2:]}}
    assert kf.biggest_problem(shop)["label"] == "slow on phones"
    salon = {**shop, "kind": "hairdresser"}  # people book a hairdresser: no online booking comes first
    assert kf.biggest_problem(salon)["label"] == "no online booking"
    down = {**shop, "audit": {"grade": "down", "problems": []}}
    assert kf.biggest_problem(down)["line"].startswith("I tried your website (joes.test) and it won't load")
    assert kf.biggest_problem({**shop, "audit": {"grade": "good", "problems": [], "booking": True}}) == {}


def test_no_website_leads_get_a_short_dm_and_whatsapp(s):
    out = sales(s, action="outreach", client="Snip Snip")
    dm = kinetic(s, "Clients", "Snip Snip", f"Outreach dm {st.today().isoformat()}.md").read_text(encoding="utf-8")
    wa = kinetic(s, "Clients", "Snip Snip", f"Outreach whatsapp {st.today().isoformat()}.md").read_text(encoding="utf-8")
    assert "drafted a dm for Snip Snip" in out and "also a WhatsApp message" in out and "Nothing has been sent" in out
    for text in (dm.strip(), wa.strip()):
        msg = message_part(text)
        assert len(msg) <= ks.DM_LIMIT and text.endswith(world.OPT_OUT)
        assert msg.index("only your Instagram page") < msg.index("So I made you this") < msg.index(st.PREVIEW)
        assert "Snip Snip home page mock-up.html" in msg and TERMS in msg and msg.endswith("Alfred, Kinetic Web Designs")
        assert "klarna" not in text.lower() and "monthly" not in text.lower()
    assert wa.startswith("Hi there! It's Alfred from Kinetic Web Designs.")
    assert "WhatsApp message:" in out.card["text"] and ko.STATUSES and \
        next(r for r in st.rows_of(s, st.OUTREACH) if r["name"] == "Snip Snip")["draft_channel"] == "dm"
    long = {**LEADS[0], "id": 9, "name": "The Traditional Gentlemen's Barbershop & Grooming"}
    st.save(s, st.PROSPECTS, st.rows_of(s, st.PROSPECTS) + [long])
    body = sales(s, action="outreach", client="9").card["text"]
    assert len(message_part(body.split("\n\n----------")[0])) <= ks.DM_LIMIT and st.PREVIEW in body


def test_weak_website_gets_email_and_phone_where_cold_email_is_fine(s):
    out = sales(s, action="outreach", client="Northern Plumbing Ltd")
    email, script = out.card["text"].split("\n\n----------\nPhone script:\n\n")
    assert email.startswith("Subject: I made this for Northern Plumbing Ltd\n\nHi there,\n\nYour website (np.test) is "
                            "hard to use on a phone")
    assert email.index("So I made you this") < email.index(st.PREVIEW) and TERMS in email
    assert script.startswith("Phone script for Northern Plumbing Ltd") and st.PREVIEW in script
    assert "drafted an email" in out and "also a Phone script" not in out


def test_sole_traders_and_no_cold_email_countries_get_phone_and_dm(s):
    uk = sales(s, action="outreach", client="Joe's Barbers")  # a UK sole trader: PECR, so no cold email
    assert "drafted a phone script for Joe's Barbers" in uk and "Instagram DM:" in uk.card["text"]
    assert "Subject:" not in uk.card["text"] and "PECR" in uk
    de = sales(s, action="outreach", client="Kurz Friseur")
    assert "drafted a phone script for Kurz Friseur (Germany)" in de and "Subject:" not in de.card["text"]
    kr_ = sales(s, action="outreach", client="Seoul Cuts")  # no WhatsApp where texts need consent
    assert "drafted a dm for Seoul Cuts (South Korea)" in kr_ and "WhatsApp" not in kr_.card["text"]
    assert world.lead_channels("GB", False, "Bloom Ltd") == ["email", "phone"]
    assert world.lead_channels("DE", False, "Kurz GmbH") == ["phone", "dm"]
    assert world.lead_channels("US", True) == ["dm", "whatsapp"]


def test_see_your_design_before_you_pay_is_everywhere(s):
    for channel in ks.CHANNELS:
        assert st.PREVIEW in sales(s, action="outreach", client="Ada", channel=channel).card["text"]
        st.save(s, st.OUTREACH, [])
    sales(s, action="quote", client="Ada", package="starter")
    html = kinetic(s, "Clients", "Ada", "Quote Q-0001.html").read_text(encoding="utf-8")
    assert f"<b>{st.PREVIEW}</b>" in html
    sales(s, action="outreach", client="Fade Room")
    asyncio.run(ko.run_tool("web_design_outreach", {"action": "mark", "business": "Fade Room", "status": "contacted",
                                                    "date": (st.today() - timedelta(days=3)).isoformat()}, s))
    follow = asyncio.run(ko.run_tool("web_design_outreach", {"action": "follow_up", "business": "Fade Room"}, s))
    assert st.PREVIEW in follow.card["text"] and follow.card["text"].endswith(world.OPT_OUT)


# ---- A: the 30-second mock-up video ------------------------------------------------------------------

@pytest.fixture
def fake_video(monkeypatch):
    seen = {"ffmpeg": [], "said": [], "recorded": []}
    monkeypatch.setattr(kv, "missing", lambda: "")

    def record(html, into, seconds=kv.SECONDS):
        seen["recorded"].append((Path(html).name, seconds))
        clip = Path(into) / "page.webm"
        clip.write_bytes(b"webm")
        return clip

    def run(args):
        seen["ffmpeg"].append(args)
        Path(args[-1]).write_bytes(b"mp4")

    async def synthesize(http, settings, text):
        seen["said"].append(text)
        return b"mp3"
    monkeypatch.setattr(kv, "record", record)
    monkeypatch.setattr(videojoin, "run", run)
    monkeypatch.setattr(tts, "synthesize", synthesize)
    return seen


def test_outreach_makes_a_30_second_vertical_video(s, fake_video):
    v = replace(s, kinetic_video=True, elevenlabs_api_key="test-voice-key")
    out = sales(v, action="outreach", client="Fade Room")
    path = kinetic(v, "Mockups", "Fade Room", "Fade Room mock-up video.mp4")
    assert path.read_bytes() == b"mp4" and fake_video["recorded"] == [("index.html", 30)]
    assert "Attach this video too: Kinetic Web Designs/Mockups/Fade Room/Fade Room mock-up video.mp4" in out
    assert "test-voice-key" not in out
    dm = message_part(out.card["text"].split("\n\n----------")[0])
    assert "a 30-second video of it" in dm and len(dm) <= ks.DM_LIMIT
    said = fake_video["said"][0]
    assert said.startswith("Hi, Fade Room. I searched for Fade Room online and couldn't find a website") and \
        st.PREVIEW in said and "From Kinetic Web Designs." in said
    args = fake_video["ffmpeg"][0]
    graph = args[args.index("-filter_complex") + 1]
    assert "scale=1080:1920" in graph and "pad=1080:1920" in graph and args[args.index("-t") + 1] == "30"
    assert "voice.mp3" in " ".join(args) and "libx264" in args
    email = sales(v, action="outreach", client="Northern Plumbing Ltd", channel="email").card["text"]
    assert "There's a 30-second video of it on a phone too (Northern Plumbing Ltd mock-up video.mp4)." in email


def test_video_is_optional_and_degrades_to_one_line(s, fake_video, monkeypatch):
    v = replace(s, kinetic_video=True)
    sales(v, action="outreach", client="Fade Room", video=False)
    assert not fake_video["recorded"] and not kinetic(v, "Mockups", "Fade Room", "Fade Room mock-up video.mp4").exists()
    monkeypatch.setattr(kv, "missing", lambda: "ffmpeg isn't installed")
    out = sales(v, action="outreach", client="Close Cuts")
    assert "No video this time: ffmpeg isn't installed." in out and "Attach this video" not in out
    assert "30-second" not in out.card["text"]
    off = sales(s, action="outreach", client="Sam's Cafe")  # JARVIS_KINETIC_VIDEO off: no video, no note
    assert "video" not in str(off).lower()


def test_video_action_on_its_own_and_silent_without_a_voice_key(s, fake_video, monkeypatch):
    out = reach(s, action="video", client="Joe's Barbers")
    assert "Joe's Barbers mock-up video.mp4" in out and "silent" in out and not fake_video["said"]
    args = fake_video["ffmpeg"][0]
    assert "anullsrc=r=44100:cl=stereo" in args
    assert kv.video_file("A" * 80).endswith(" mock-up video.mp4") and len(kv.video_file("A" * 80)) < 60

    def broken(html, into, seconds=30):
        raise ValueError("I couldn't start a browser to record it (no Edge)")
    monkeypatch.setattr(kv, "record", broken)
    assert reach(s, action="video", client="Fade Room") == \
        "No video this time: I couldn't start a browser to record it (no Edge)."


def test_recording_uses_a_headless_phone_sized_browser(tmp_path, monkeypatch):
    import sys
    import types
    launched, contexts = [], []

    class Page:
        video = types.SimpleNamespace(path=lambda: str(tmp_path / "rec.webm"))

        def goto(self, url):
            assert url.startswith("file://")

        def wait_for_timeout(self, ms):
            pass

        def evaluate(self, js):
            return 3000 if "scrollHeight" in js else None

    class Context:
        def new_page(self):
            return Page()

        def close(self):
            pass

    class Engine:
        def new_context(self, **kw):
            contexts.append(kw)
            return Context()

        def close(self):
            pass

    class Chromium:
        def launch(self, channel=None, headless=False):
            launched.append((channel, headless))
            if channel == "msedge":
                raise RuntimeError("Edge isn't installed")
            return Engine()

    class PW:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: PW()
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    page = tmp_path / "index.html"
    page.write_text("<html></html>")
    assert kv.record(page, tmp_path) == tmp_path / "rec.webm"
    assert launched == [("msedge", True), ("chrome", True)]  # Edge, then Chrome; always headless
    assert contexts[0]["viewport"] == {"width": 540, "height": 960} and contexts[0]["is_mobile"]
    assert contexts[0]["record_video_size"] == {"width": 1080, "height": 1920}


# ---- D: one trade a week ---------------------------------------------------------------------------------

def finder(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await kf.run_tool("web_client_finder", args, s, http)
    return asyncio.run(go())


def test_trade_of_the_week_builds_one_base_and_reuses_it(s, monkeypatch):
    assert "no trade of the week yet" in reach(s, action="trade_of_week")
    out = reach(s, action="trade_of_week", trade="barbers")
    assert st.trade_of_week(s) == {"label": "barbers", "kind": "hairdressers", "trade": "hairdresser",
                                   "set": st.today().isoformat()}
    assert "This week is barbers. I made its base mock-up design" in out
    base = kinetic(s, "Trade bases", "hairdresser base.html")
    assert base.exists() and kr.NAME in base.read_text(encoding="utf-8")
    preview = kinetic(s, "Trade bases", "hairdresser base preview.html").read_text(encoding="utf-8")
    assert "Your Business" in preview and "KWD" not in preview
    assert "already made" in reach(s, action="trade_of_week", trade="barbers")
    assert "This week's trade is barbers" in reach(s, action="trade_of_week")

    calls = []
    real = ks.mockup_html
    monkeypatch.setattr(ks, "mockup_html", lambda *a, **k: calls.append(a) or real(*a, **k))
    made = sales(s, action="mockup", client="Fade Room")
    assert "from the barbers base design" in made and not calls  # swapped in, not generated again
    html = kinetic(s, "Mockups", "Fade Room", "index.html").read_text(encoding="utf-8")
    assert "Fade Room" in html and 'href="tel:01615550001"' in html and "9 King St, Stockport" in html
    assert " in Stockport" in html and "KWD" not in html and "+99999999999" not in html
    assert ks.TRADE_LOOKS["hairdresser"][3] in html  # the trade palette when their colours aren't known
    rows = st.rows_of(s, st.PROSPECTS)
    next(r for r in rows if r["name"] == "Close Cuts").update(colours={"brand": "#123456"}, phone="",
                                                               services=["Fades"])
    st.save(s, st.PROSPECTS, rows)
    sales(s, action="mockup", client="Close Cuts", services=["Skin fades", "Beard trims"])
    html = kinetic(s, "Mockups", "Close Cuts", "index.html").read_text(encoding="utf-8")
    assert "#123456" in html and "Skin fades" in html and "Beard trims" in html and "Wedding hair" not in html
    assert 'href="#contact">Get in touch' in html and "KWD" not in html
    # finder and outreach default to the trade of the week
    queries.clear()
    monkeypatch.setattr(memory, "check_public", lambda url: asyncio.sleep(0))
    found = finder(s, action="find", town="Stockport")
    assert "(this week's trade, barbers)" in found and 'nwr["shop"="hairdresser"]' in queries[0]
    assert 'amenity"="cafe' not in queries[0]
    st.save(s, st.PROSPECTS, json.loads(json.dumps(LEADS)))
    first = sales(s, action="outreach")
    assert first.card["title"] == "Outreach: Fade Room"  # the best new barber lead
    assert "Done: no trade of the week" in reach(s, action="trade_of_week", trade="none")
    assert st.trade_of_week(s) == {}
    with pytest.raises(ValueError, match="Pick one trade"):
        reach(s, action="trade_of_week", trade="businesses")


def test_trade_base_takes_a_saved_design_system(s):
    folder = kinetic(s, "stripe.com")
    folder.mkdir(parents=True)
    (folder / "tokens.json").write_text(json.dumps({"color": {"brand": {"$value": "#635bff"}},
                                                    "fontFamily": {"primary": {"$value": ["Inter", "sans-serif"]}}}))
    reach(s, action="trade_of_week", trade="cafes", style_from="stripe.com")
    sales(s, action="mockup", client="Sam's Cafe")
    html = kinetic(s, "Mockups", "Sam's Cafe", "index.html").read_text(encoding="utf-8")
    assert "#635bff" in html and "Inter, sans-serif" in html and "Sam&#x27;s Cafe" in html


# ---- C: the walk-in route ------------------------------------------------------------------------------

def test_walk_in_route_orders_no_website_leads_by_nearest_neighbour(s):
    reach(s, action="trade_of_week", trade="barbers")
    out = reach(s, action="walk_in_route", town="Stockport")
    names = [r[1] for r in out.card["rows"]]
    assert names == ["Fade Room", "Close Cuts", "Snip Snip"]  # no cafe, no website-owners, nearest next
    assert out.card["rows"][1][4] == "0.1 km" and out.card["rows"][2][3] == "Instagram only, no website"
    md = kinetic(s, "Walk-in routes", f"Stockport walk-in route {st.today().isoformat()}.md").read_text(encoding="utf-8")
    assert md.count(st.PREVIEW) == 3 and md.count("So I made you this") == 3 and TERMS in md
    assert "https://www.google.com/maps/dir/53.41,-2.15/53.411,-2.15/53.43,-2.15" in md
    assert kinetic(s, "Mockups", "Snip Snip", "Snip Snip home page mock-up.html").exists()
    assert {r["name"]: r["draft_channel"] for r in st.rows_of(s, st.OUTREACH)}["Close Cuts"] == "visit"
    every = reach(s, action="walk_in_route", town="Stockport", trade="cafes")
    assert [r[1] for r in every.card["rows"]] == ["Sam's Cafe"]


def test_walk_in_route_by_address_without_map_positions(s):
    rows = st.rows_of(s, st.PROSPECTS)
    for r in rows:
        r.pop("lat", None), r.pop("lon", None)
    rows += [{"id": 20 + i, "name": f"Shop {i}", "kind": "shop", "town": "Stockport", "website": "",
              "address": f"{i} Zed Road, Stockport", "status": "new"} for i in range(1, 12)]
    st.save(s, st.PROSPECTS, rows)
    out = reach(s, action="walk_in_route", town="Stockport")
    assert len(out.card["rows"]) == 10 and "sorted by street" not in str(out)
    md = next(kinetic(s, "Walk-in routes").glob("*.md")).read_text(encoding="utf-8")
    assert "sorted by street" in md and "google.com/maps" not in md
    assert kr.route([{"name": "B", "address": "12 King St"}, {"name": "A", "address": "2 King St"},
                     {"name": "C", "address": "1 Abbey Rd"}])[0][0]["name"] == "C"
    with pytest.raises(ValueError, match="Ask me to find some there first"):
        reach(s, action="walk_in_route", town="Nowhere")


def test_reach_is_registered():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert "web_design_reach" in names and kr in tools.ABILITIES


# ---- E: five numbers in the morning briefing --------------------------------------------------------------

def test_briefing_shows_five_numbers_with_conversion_and_the_step_to_fix(s, monkeypatch):
    today = st.today()
    monday = today - timedelta(days=today.weekday())
    last = (monday - timedelta(days=3)).isoformat()
    this = today.isoformat()
    rows = []
    for i in range(100):  # 100 first messages last week, all with a mock-up, 3 replies
        hist = [{"date": last, "status": "contacted", "channel": "email"}]
        if i < 3:
            hist.append({"date": last, "status": "replied"})
        rows.append({"id": i + 1, "name": f"Lead {i}", "status": "replied" if i < 3 else "contacted", "messages": 1,
                     "contacted": last, "last_contacted": last, "mockup": True, "history": hist})
    for i in range(95):  # 95 this week, no replies yet
        rows.append({"id": 100 + i, "name": f"New {i}", "status": "contacted", "messages": 1, "contacted": this,
                     "last_contacted": this, "mockup": i < 90,
                     "history": [{"date": this, "status": "contacted", "channel": "dm"}]})
    st.save(s, st.OUTREACH, rows)
    st.save(s, st.INVOICES, [{"id": 1, "number": "INV-0001", "client": "Lead 0", "total": 197.5, "status": "paid",
                              "paid_on": last, "due": last}])
    answers = {"AS this_week FROM briefs": [{"n": 2, "this_week": 1}],
               "AS this_week FROM payments": [{"kind": "payment", "status": "succeeded", "n": 1, "this_week": 0},
                                              {"kind": "refund", "status": "succeeded", "n": 4, "this_week": 4}]}
    seen = []

    def run(cmd, **kw):
        seen.append(cmd[-1])
        rows_ = next((r for k, r in answers.items() if k in cmd[-1]), [])
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps([{"results": rows_, "success": True}]), stderr="")
    monkeypatch.setattr(ksite.subprocess, "run", run)
    monkeypatch.setattr(ksite.shutil, "which", lambda name: "npx")
    b = kb.gather(s)
    assert all("'" not in c for c in seen) and any("GROUP BY kind, status" in c for c in seen)
    nums = b["numbers"]
    assert nums["last"] == {"messages": 100, "replies": 3, "mockups": 100, "briefs": 1, "payments": 1}
    assert nums["this"] == {"messages": 95, "replies": 0, "mockups": 90, "briefs": 1, "payments": 0}
    full = kb.full_text(s, b)
    for bit in ("## Your five numbers", "| Messages sent | 95 | 100 |", "| Mock-ups sent | 90 (95%) | 100 (100%) |",
                "| Replies | 0 (0%) | 3 (3%) |", "| Briefs | 1 (-) | 1 (33%) |",
                "| Deposits and payments | 0 (0%) | 1 (100%) |",
                "Target each week: 100 messages, 10 replies, 3 briefs, 1 client."):
        assert bit in full, bit
    assert "Fix this step (replies): open with their single biggest problem" in full  # 3 replies from 195 is the weakest
    assert "This week so far: 95 messages sent, 0 replies, 1 brief, 0 payments. The step to fix is replies." in \
        kb.short_text(s, b)


def test_briefing_numbers_without_the_website(s, monkeypatch):
    def missing(cmd, **kw):
        raise FileNotFoundError
    monkeypatch.setattr(ksite.subprocess, "run", missing)
    monkeypatch.setattr(ksite.shutil, "which", lambda name: "npx")
    b = kb.gather(s)
    assert b["numbers"]["this"]["briefs"] is None
    full = kb.full_text(s, b)
    assert "| Briefs | couldn't check | couldn't check |" in full
    assert "Fix this step (messages): send more first messages" in full


def test_asian_countries_have_currency_language_and_rules():
    import kinetic_world as w
    assert w.local_price(395, w.currency_of("JP")).startswith("about ¥")
    assert w.local_price(395, w.currency_of("TH")).startswith("about ฿")
    assert w.language_code("", "VN") == "vi" and w.language_code("", "HK") == "zh-hant"
    assert w.language_code("chinese") == "zh"
    assert not w.cold_email_ok("JP") and not w.cold_email_ok("VN") and w.cold_email_ok("SG")
    assert w.lead_channels("JP", True) == ["dm"]
    assert "Japan" in w.compliance_note("JP")
    assert w.country_code("the Philippines") == "PH" and w.country_code("Saudi Arabia") == "SA"
    assert all(w.COUNTRIES[c][1] in w.RATES_FROM_GBP for c in ("JP", "TH", "SG", "MY", "PH", "ID", "VN", "HK", "TW",
                                                               "PK", "BD", "LK", "SA"))
