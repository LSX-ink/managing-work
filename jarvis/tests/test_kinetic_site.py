import asyncio
import json
import subprocess
from dataclasses import replace
from email.message import EmailMessage

import pytest

import alfred_mail
import helpers
import kinetic_site as ksite
import kinetic_store as st
import memory
import tools
from config import Settings

NOW = 1_800_000_000_000
BRIEFS = [
    {"id": 7, "created_at": NOW, "name": "Ada Lovelace", "business": "Ada's Salon", "email": "ada@salon.test",
     "phone": "0161 111 1111", "data": json.dumps({"what": "Hair salon", "currentSite": "", "look": "Calm and pink",
                                                   "when": "Next month", "package": "Business website", "estimate": "£895",
                                                   "colours": {"main": "#c58b9b", "background": "", "accent": ""}})},
    {"id": 6, "created_at": NOW - 86_400_000, "name": "Bob Jones", "business": "Bob's Plumbing", "email": "bob@plumb.test",
     "phone": None, "data": json.dumps({"what": "Plumber", "currentSite": "bobsplumbing.test", "look": "Bold",
                                        "package": "Online shop"})},
]
calls = []


def fake_run(answers, code=0, stderr=""):
    def run(cmd, **kw):
        calls.append((cmd, kw))
        sql = cmd[-1]
        rows = next((rows for key, rows in answers.items() if key in sql), [])
        out = rows if isinstance(rows, str) else json.dumps([{"results": rows, "success": True, "meta": {}}])
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr=stderr)
    return run


ANSWERS = {
    "FROM signups WHERE marketing": [{"step": 0, "stopped": None, "n": 2}, {"step": 1, "stopped": None, "n": 3},
                                     {"step": 4, "stopped": "done", "n": 1}, {"step": 2, "stopped": "brief", "n": 1}],
    "AS opted_in FROM signups": [{"total": 12, "today": 2, "week": 5, "opted_in": 7}],
    "FROM briefs ORDER BY": BRIEFS,
    "FROM briefs": [{"total": 2, "today": 1, "week": 2}],
}


@pytest.fixture(autouse=True)
def wrangler(monkeypatch):
    calls.clear()
    monkeypatch.setattr(ksite.subprocess, "run", fake_run(ANSWERS))
    monkeypatch.setattr(ksite.shutil, "which", lambda name: "npx")


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def site(s, **args):
    return asyncio.run(ksite.run_tool("kinetic_site", args, s))


def test_queries_go_through_wrangler_read_only():
    rows = ksite.wrangler("SELECT COUNT(*) AS total FROM briefs")
    cmd, kw = calls[0]
    assert cmd[:8] == ["npx", "--yes", "wrangler", "d1", "execute", "kinetic-db", "--remote", "--json"]
    assert cmd[8] == "--command" and kw["timeout"] == ksite.TIMEOUT and rows == [{"total": 2, "today": 1, "week": 2}]
    for bad in ("DELETE FROM signups", "SELECT * FROM signups; DROP TABLE signups", "SELECT \"x\" FROM briefs",
                "SELECT name FROM briefs WHERE name = 'a'", "SELECT 1 FROM x %PATH%", "SELECT 1\nFROM x",
                "SELECT replace(email, 1, 2) FROM signups"):
        with pytest.raises(ValueError, match="read-only"):
            ksite.wrangler(bad)
    assert len(calls) == 1


def test_wrangler_problems_are_plain_and_never_echo_output(monkeypatch):
    monkeypatch.setattr(ksite.subprocess, "run", fake_run({"": "secret-token-123"}, 1, "You are not logged in. "
                                                                                     "Run wrangler login. CF_API_TOKEN=abc"))
    with pytest.raises(ValueError, match="npx wrangler login") as e:
        ksite.wrangler("SELECT 1 FROM briefs")
    assert "abc" not in str(e.value) and "secret" not in str(e.value)
    monkeypatch.setattr(ksite.subprocess, "run", fake_run({"": '{"error": {"text": "no such table: briefs"}}'}, 1))
    with pytest.raises(ValueError, match="migrations"):
        ksite.wrangler("SELECT 1 FROM briefs")

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])
    monkeypatch.setattr(ksite.subprocess, "run", slow)
    with pytest.raises(ValueError, match="too long"):
        ksite.wrangler("SELECT 1 FROM briefs")
    monkeypatch.setattr(ksite.subprocess, "run", fake_run({"": "Notice: update available\n[{\"results\": [{\"n\": 1}]}]"}))
    assert ksite.wrangler("SELECT 1 AS n FROM briefs") == [{"n": 1}]


def test_signups_briefs_and_summary(s):
    assert site(s, action="signups") == ("On kineticwebdesigns.co.uk: 12 sign-ups in all, 2 today and 5 in the last 7 "
                                         "days; 7 ticked the box for tips, offers and news.")
    today, week = ksite._since()
    assert f"created_at >= {today}" in calls[0][0][-1] and f"created_at >= {week}" in calls[0][0][-1] and week < today
    out = site(s, action="briefs", count=50)
    assert "2 briefs in all, 1 today" in out and "latest is from Ada Lovelace at Ada's Salon" in out
    assert "Business website, estimate £895, wants it Next month, look: Calm and pink" in out
    assert "LIMIT 10" in calls[-1][0][-1]  # count is capped
    assert out.card["rows"][1][2] == "Bob Jones (Bob's Plumbing)"
    assert out.card["buttons"][0]["say"] == "Reply to brief 7 with a mock-up and quote."
    both = site(s, action="summary")
    assert "12 sign-ups" in both and "2 briefs" in both and both.card["rows"][3][0] == "Brief 7: Ada's Salon"


def test_series_counts_each_email_and_who_stopped(s):
    out = site(s, action="series")
    assert out.startswith("7 opted-in sign-ups in the follow-up series. 5 still going (2 waiting for the first email, "
                          "3 had email 1). Stopped: 1 finished all four, 1 sent a brief.")
    assert "WHERE marketing = 1 GROUP BY drip_step, drip_stopped" in calls[0][0][-1]
    rows = dict((r[0], r[1]) for r in out.card["rows"])
    assert rows["Had email 1 (day 2: A quick look at what we build)"] == "3" and rows["Stopped: sent a brief"] == "1"


def test_reply_to_brief_makes_mockup_quote_and_unsent_draft(s):
    out = site(s, action="reply_to_brief")
    drafts = alfred_mail._load_drafts(s)
    assert len(drafts) == 1 and drafts[0]["to"] == "ada@salon.test" and drafts[0]["status"] == "draft"
    body = drafts[0]["body"]
    assert body.startswith("Hi Ada,") and "half when we start building, half once everything's complete" in body
    assert "klarna" not in body.lower() and "monthly payment" not in body.lower() and "£895" in body
    assert "Kinetic Web Designs/Mockups/Ada's Salon/index.html" in out and "Clients/Ada's Salon/Quote Q-0001.html" in out
    assert body.endswith("Kind regards,\nKinetic Web Designs")
    assert "NOT been sent" in out and "confirmed true" in out and out.card["buttons"][0]["say"] == "Yes, send email draft 1."
    root = memory.root(s) / "Kinetic Web Designs"
    assert (root / "Mockups" / "Ada's Salon" / "index.html").exists()
    assert (root / "Clients" / "Ada's Salon" / "Quote Q-0001.html").exists()
    q = st.rows_of(s, st.QUOTES)[0]
    assert q["package"] == "business" and q["rebuild_discount"] == 0
    site(s, action="reply_to_brief", brief="bob@plumb.test")
    bob = st.rows_of(s, st.QUOTES)[1]
    assert bob["client"] == "Bob's Plumbing" and bob["package"] == "shop" and bob["rebuild_discount"] > 0  # has a site
    assert site(s, action="reply_to_brief", brief="6").startswith("For Bob Jones")
    with pytest.raises(ValueError, match="can't find a recent brief"):
        site(s, action="reply_to_brief", brief="Nobody")
    assert all(d["status"] == "draft" for d in alfred_mail._load_drafts(s))  # nothing is ever sent


def test_new_brief_email_is_announced(s):
    s = replace(s, alfred_email_address="alfredw.lsx@gmail.com", alfred_email_app_password="x")
    msg = EmailMessage()
    msg["From"] = "Kinetic Web Designs <hello@kineticwebdesigns.co.uk>"
    msg["Subject"] = "New website brief: Ada's Salon"
    msg.uid = 9
    assert alfred_mail.announcement(s, msg) == ("Sir, new website brief from Ada's Salon. Want me to draft a reply with "
                                                "a mock-up?")
    other = EmailMessage()
    other["From"] = "Shop <news@shop.test>"
    other["Subject"] = "Your order"
    other.uid = 10
    assert "new email from Shop" in alfred_mail.announcement(s, other)


def test_ad_plan_for_salons_in_the_us(s):
    out = site(s, action="ad_plan", trade="salons", countries=["USA"])
    path = memory.root(s) / "Kinetic Web Designs" / "Ads" / f"Ad plan hairdressers United States {st.today().isoformat()}.md"
    plan = path.read_text(encoding="utf-8")
    assert "Use the salon or barbershop site video" in plan and "'salon site video.mp4'" in plan and "couldn't find it" in plan
    assert "United States: start at about $6 (£5) to about $13 (£10) a day for 7 days" in plan
    assert "Hair salons" in plan and "#salonowner" in plan and "about $499" not in plan.split("## Caption")[0]
    assert "Websites from $499" in plan and "half when we start building, half once everything's complete" in plan
    assert "Commercial Music Library" in plan and "Alfred can't launch or pay for ads" in plan
    assert "Meta Ads Manager" in out and "Kinetic Web Designs/Ads/" in out and not calls  # no database needed


def test_ad_plan_uses_saved_videos_and_translates(s, monkeypatch):
    from test_kinetic import FakeClaude
    vids = memory.root(s) / "Kinetic Web Designs" / "Videos"
    vids.mkdir(parents=True)
    (vids / "Kinetic main ad.mp4").write_bytes(b"x")
    (vids / "Barber site video.mp4").write_bytes(b"x")
    fake = FakeClaude()
    monkeypatch.setattr(helpers, "_client", fake)
    out = site(s, action="ad_plan", trade="barbers", countries="France, Ireland", platform="tiktok", daily_budget=8)
    assert "Kinetic Web Designs/Videos/Barber site video.mp4" in out
    plan = (memory.root(s) / "Kinetic Web Designs" / "Ads" /
            f"Ad plan hairdressers France, Ireland {st.today().isoformat()}.md").read_text(encoding="utf-8")
    assert "In French:" in plan and "€459" in plan and "France: about €9 (£8) a day for 7 days" in plan
    assert len(fake.asked) == 1 and "French" in fake.asked[0]["messages"][0]["content"]  # Ireland is English
    broad = site(s, action="ad_plan", trade="small businesses")
    assert "main Kinetic ad (Kinetic Web Designs/Videos/Kinetic main ad.mp4)" in broad
    with pytest.raises(ValueError, match="don't know the country"):
        site(s, action="ad_plan", trade="cafes", countries=["Atlantis"])


def test_kinetic_site_is_registered():
    assert ksite in tools.ABILITIES and ksite.NAMES == {t["name"] for t in ksite.tool_definitions()}
    assert "Klarna" in ksite.tool_definitions()[0]["description"]
