import asyncio
from datetime import timedelta

import pytest

import screen
import tools
import writingincome_blog
import writingincome_book
import writingincome_money
import writingincome_newsletter
import writingincome_store as wi
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def call(mod, name):
    def run(s, action, **a):
        return mod.run_tool(name, {"action": action, **a}, s)
    return run


nl = call(writingincome_newsletter, "writingincome_newsletter")
blog = call(writingincome_blog, "writingincome_blog")
book = call(writingincome_book, "writingincome_book")
money = call(writingincome_money, "writingincome_money")

POST = ("# Baking Bread at Home\n\nBaking bread at home is easy. You need flour, water and time. Most people think it is hard. It is not.\n\n"
        "## Why bake bread\n\nHome baking bread saves money and tastes better. The smell alone is worth it for everyone in the house today.\n\n"
        "## Simple steps\n\nMix the dough. Wait. Bake it. Then eat the bread while it is warm and enjoy every single bite of it.")


def kind(shown):
    assert isinstance(shown, screen.Shown)
    return shown.card["kind"]


def data(shown):
    return shown.card["data"]


def test_registered_and_through_tools(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"writingincome_newsletter", "writingincome_blog", "writingincome_book", "writingincome_money"} <= names
    for kind_name in (wi.RESULT, wi.GUIDE, wi.CHECK, wi.BOARD, wi.METER):
        assert kind_name in screen.EXTRA_KINDS
    out = asyncio.run(tools._run_tool("writingincome_blog", {"action": "make_slug", "title": "The Best Bread Recipe"}, s, None, None))
    assert kind(out) == wi.RESULT and "best-bread-recipe" in out


def test_newsletter_calendar(s):
    assert "Planned issue 1" in nl(s, "plan_issue", title="Autumn reads", date="2099-01-10", status="drafting")
    nl(s, "plan_issue", title="Old one", date="2020-01-01", status="sent")
    cal = nl(s, "issue_calendar")
    assert kind(cal) == "table" and len(cal.card["rows"]) == 1
    assert len(nl(s, "issue_calendar", all=True).card["rows"]) == 2
    assert "ready" in nl(s, "update_issue", issue="Autumn", status="ready", subject="Hello")
    with pytest.raises(ValueError):
        nl(s, "update_issue", issue="Autumn", status="nope")
    assert "confirm" in nl(s, "remove_issue", issue="1")
    assert "Removed" in nl(s, "remove_issue", issue="1", confirmed=True)
    with pytest.raises(ValueError):
        nl(s, "plan_issue", title="")


def test_newsletter_templates_and_subjects(s):
    assert kind(nl(s, "sections_template")) == wi.GUIDE
    assert len(data(nl(s, "sections_template", kind="essay"))["sections"]) == 1
    with pytest.raises(ValueError):
        nl(s, "sections_template", kind="zzz")
    subj = nl(s, "subject_lines", topic="sourdough")
    assert subj.card["kind"] == "list" and len(subj.card["items"]) == 12
    assert subj.card["items"][0]["say"].startswith("Check this subject line")
    good = nl(s, "check_subject", subject="Three small sourdough fixes", preview="Short notes on getting a better rise this weekend.")
    assert kind(good) == wi.CHECK and data(good)["headline"] == "Looks good"
    bad = nl(s, "check_subject", subject="FREE!! Act now to WIN cash")
    assert data(bad)["headline"] != "Looks good"
    assert any(i["status"] == "fail" for i in data(bad)["items"])


def test_newsletter_logs(s):
    with pytest.raises(ValueError):
        nl(s, "subscriber_growth")
    nl(s, "log_subscribers", count=100, date="2026-01-01")
    assert "+40" in nl(s, "log_subscribers", count=140, date="2026-01-15")
    growth = nl(s, "subscriber_growth", target=200)
    assert kind(growth) == "chart" and growth.card["chart"]["values"] == [100, 140]
    assert "rough guess" in growth and "about 3 weeks" in growth
    with pytest.raises(ValueError):
        nl(s, "open_rate_report")
    assert "50.0% opened" in nl(s, "log_opens", issue="Issue 1", sent=200, opened=100, clicked=10)
    with pytest.raises(ValueError):
        nl(s, "log_opens", issue="Bad", sent=10, opened=20)
    nl(s, "log_opens", issue="Issue 2", sent=100, opened=30)
    rep = nl(s, "open_rate_report")
    assert kind(rep) == "chart" and rep.card["chart"]["values"] == [50.0, 30.0] and "Issue 1" in rep


def test_newsletter_welcome_magnets_checklist(s):
    w = nl(s, "welcome_sequence", count=3, topic="sourdough starter guide")
    assert kind(w) == wi.GUIDE and len(data(w)["sections"]) == 3 and "sourdough starter guide" in w.card["data"]["sections"][0]["heading"]
    assert "Saved" in nl(s, "welcome_edit", email_number=1, subject="Hi there", body="My own text.\n\nSecond bit.")
    assert "Hi there" in data(nl(s, "welcome_sequence"))["sections"][0]["heading"]
    with pytest.raises(ValueError):
        nl(s, "welcome_edit", email_number=1)
    assert kind(nl(s, "lead_magnet_ideas", topic="baking")) == "table"
    assert nl(s, "send_checklist").card["kind"] == "list"


def test_blog_pipeline_and_seo(s):
    assert "Added post 1" in blog(s, "add_post", title="Baking Bread", keyword="baking bread", target_words=1200)
    blog(s, "add_post", title="Old Post", status="published", date="2020-01-01")
    board = blog(s, "pipeline")
    assert kind(board) == wi.BOARD and len(data(board)["columns"]) == 3
    assert "draft" in blog(s, "update_post", post="Baking", status="drafting")
    with pytest.raises(ValueError):
        blog(s, "update_post", post="Baking", status="zzz")
    seo = blog(s, "seo_checklist", post="1")
    assert kind(seo) == wi.CHECK and len(data(seo)["items"]) == 14 and seo.card["buttons"]
    assert "Ticked" in blog(s, "seo_tick", post="1", step=2)
    assert data(blog(s, "seo_checklist", post="1"))["items"][1]["status"] == "ok"
    assert "Unticked" in blog(s, "seo_tick", post="1", step=2)
    with pytest.raises(ValueError):
        blog(s, "seo_tick", post="1", step=99)
    assert "confirm" in blog(s, "remove_post", post="Old Post")
    assert "Removed" in blog(s, "remove_post", post="Old Post", confirmed=True)


def test_blog_checkers(s):
    ok = blog(s, "check_meta", title="How to Bake Bread at Home Today", meta="x" * 130, keyword="bake bread")
    assert kind(ok) == wi.CHECK and any(i["label"] == "Suggested web address" for i in data(ok)["items"])
    long = blog(s, "check_meta", title="T" * 90, keyword="zzz")
    assert data(long)["items"][0]["status"] == "warn" and "to look at" in data(long)["headline"]
    key = blog(s, "keyword_check", text=POST, keyword="baking bread", title="Baking Bread at Home")
    assert kind(key) == wi.CHECK and data(key)["items"][0]["status"] == "ok" and data(key)["items"][1]["status"] == "ok"
    with pytest.raises(ValueError):
        blog(s, "keyword_check", text="short", keyword="x")
    hs = blog(s, "heading_structure", text=POST)
    assert kind(hs) == wi.CHECK and "Tidy" in data(hs)["headline"]
    skipped = blog(s, "heading_structure", text="# A\n\n### C\n\n## B")
    assert "look at" in data(skipped)["headline"]
    with pytest.raises(ValueError):
        blog(s, "heading_structure", text="no headings here at all")
    read = blog(s, "readability", text=POST, target_words=100)
    assert kind(read) == wi.RESULT and float(data(read)["headline"]) > 60 and "Against target" in dict(data(read)["rows"])
    assert wi.reading_ease("The cat sat on the mat. The dog ran to the man.")["ease"] > 90
    hard = wi.reading_ease("Notwithstanding organisational considerations, comprehensive administrative reorganisation necessitates deliberation.")
    assert hard["ease"] < 30 and hard["band"] == "very difficult"
    with pytest.raises(ValueError):
        blog(s, "readability", text="Hi.")
    assert wi.slugify("The Best Way to Bake Bread!") == "best-way-bake-bread"


def test_blog_targets_links_refresh(s):
    assert kind(blog(s, "word_targets")) == wi.GUIDE
    blog(s, "add_post", title="Baking Bread", target_words=1000)
    blog(s, "add_post", title="Sourdough Tips", status="draft")
    blog(s, "add_post", title="Ancient Post", status="published", date="2020-03-01")
    t = blog(s, "word_targets", post="Baking", words=250)
    assert "25%" in t
    assert "Planned a link" in blog(s, "add_link", post="Baking", to_post="Sourdough", anchor="sourdough tips")
    with pytest.raises(ValueError):
        blog(s, "add_link", post="Baking", to_post="Sourdough")
    with pytest.raises(ValueError):
        blog(s, "add_link", post="Baking", to_post="Baking")
    plan = blog(s, "link_plan")
    assert kind(plan) == wi.GUIDE and "Ancient Post" in str(data(plan)["sections"][1]["lines"]) and "Baking Bread -> Sourdough Tips" in str(data(plan)["sections"][0]["lines"])
    old = blog(s, "refresh_due")
    assert kind(old) == "table" and "Ancient Post" in str(old.card["rows"])
    assert "Marked" in blog(s, "mark_refreshed", post="Ancient")
    assert isinstance(blog(s, "refresh_due"), str) and "No published post" in blog(s, "refresh_due")
    assert "Marked" in blog(s, "mark_refreshed", post="Ancient", date=(wi.today() - timedelta(days=400)).isoformat())
    assert kind(blog(s, "refresh_due")) == "table"
    assert kind(blog(s, "make_slug", title="Baking Bread Fast")) == wi.RESULT


def test_book_tracker_and_progress(s):
    assert "Started" in book(s, "add_book", title="Ashes", target_words=60000, daily_goal=500)
    assert book(s, "list_books").card["kind"] == "table"
    assert "Chapter 1" in book(s, "log_chapter", chapter="1", words=3000, target_words=4000)
    assert "Prologue" in book(s, "log_chapter", chapter="Prologue", words=800)
    assert "3,000" in book(s, "log_chapter", chapter="1", words=3000)
    assert "Streak: 1 day." in book(s, "log_words", words=600)
    yesterday = (wi.today() - timedelta(days=1)).isoformat()
    book(s, "log_words", words=700, date=yesterday)
    assert "Streak: 2 days" in book(s, "log_words", words=100)
    assert "600 words" not in book(s, "set_daily_goal", daily_goal=1000)
    prog = book(s, "book_progress")
    assert kind(prog) == wi.METER and prog.card["data"]["rows"][0]["label"] == "Book"
    ch = book(s, "writing_chart")
    assert kind(ch) == "chart" and len(ch.card["chart"]["values"]) == 14 and ch.card["chart"]["values"][-1] == 700
    book(s, "add_book", title="Second")
    with pytest.raises(ValueError):
        book(s, "book_progress")
    assert "confirm" in book(s, "remove_book", book="Second")
    assert "Removed" in book(s, "remove_book", book="Second", confirmed=True)


def test_kdp_royalties(s):
    e = book(s, "royalty_calc", format="ebook", price=4.99, delivery_cost=0.30, copies=100)
    rows = dict(data(e)["rows"])
    assert data(e)["headline"] == "£3.19" and rows["35% royalty option"] == "£1.75"
    assert "current rates" in e and "current rates" in json_notes(e)
    p = book(s, "royalty_calc", format="paperback", price=9.99, print_cost=3.20)
    assert data(p)["headline"] == "£2.79"
    poor = book(s, "royalty_calc", format="paperback", price=4, print_cost=3.20)
    assert "doesn't cover" in " ".join(data(poor)["notes"])
    with pytest.raises(ValueError):
        book(s, "royalty_calc", format="paperback", price=9.99)
    with pytest.raises(ValueError):
        book(s, "royalty_calc", format="audio", price=9.99)
    ladder = book(s, "royalty_ladder", prices="2.99, 4.99", delivery_cost=0.2)
    assert kind(ladder) == "table" and ladder.card["rows"][1] == ["£4.99", "£1.75", "£3.29"]
    need = book(s, "copies_for_target", target=100, price=9.99, print_cost=3.20, format="paperback")
    assert data(need)["headline"] == "36"
    with pytest.raises(ValueError):
        book(s, "copies_for_target", target=100, price=3, print_cost=3.20, format="paperback")
    assert data(book(s, "copies_for_target", target=100, price=4.99, delivery_cost=0.3))["headline"] == "32"
    pg = book(s, "pages_estimate", words=55000)
    assert data(pg)["headline"] == "200 pages"


def json_notes(shown):
    return " ".join(data(shown)["notes"])


def test_book_blurb_keywords_launch(s):
    book(s, "add_book", title="Ashes")
    assert kind(book(s, "blurb_template")) == wi.GUIDE
    assert data(book(s, "blurb_template", kind="nonfiction"))["sections"][0]["heading"] == "Problem"
    text = ("A runaway blacksmith steals a map.\n\n" + "She must cross the burning quarter before dawn, or lose everything she loves. " * 6
            + "\n\nThe bestseller you have waited for.")
    chk = book(s, "check_blurb", text=text, book="Ashes")
    assert kind(chk) == wi.CHECK and "Saved" in chk and any(i["status"] == "warn" for i in data(chk)["items"])
    with pytest.raises(ValueError):
        book(s, "check_blurb", text="Too short")
    assert "1 of 7" in book(s, "keywords_set", slot=1, keyword="cosy fantasy romance")
    with pytest.raises(ValueError):
        book(s, "keywords_set", slot=8, keyword="x")
    assert "Noted 2" in book(s, "categories_set", categories="Fantasy, Romance")
    kw = book(s, "keywords_show")
    assert kind(kw) == wi.GUIDE and "cosy fantasy romance" in str(data(kw)["sections"][0]["lines"])
    lc = book(s, "launch_checklist")
    assert kind(lc) == wi.CHECK and lc.card["buttons"][0]["say"].startswith("Tick launch step 1")
    assert "Ticked" in book(s, "launch_tick", step=1)
    assert data(book(s, "launch_checklist"))["items"][0]["status"] == "ok"
    assert "Unticked" in book(s, "launch_tick", step=1)
    rr = book(s, "review_requests")
    assert kind(rr) == wi.GUIDE and "never pay" in data(rr)["note"]
    assert "GOV.UK" in json_guide(book(s, "kdp_notes"))


def json_guide(shown):
    return str(data(shown))


def test_paid_subscription_maths(s):
    r = money(s, "paid_subs_calc", subscribers=100, price=5, platform="substack", monthly_costs=10)
    assert kind(r) == wi.RESULT and data(r)["headline"] == "£395.50" and "not a promise" in r
    assert "GOV.UK" in json_notes(r)
    y = money(s, "paid_subs_calc", subscribers=10, price=50, billing="yearly", platform="none", card_pct=0, card_fixed=0)
    assert data(y)["headline"] == "£41.67"
    with pytest.raises(ValueError, match="Medium pays"):
        money(s, "paid_subs_calc", subscribers=10, price=5, platform="medium")
    with pytest.raises(ValueError):
        money(s, "paid_subs_calc", subscribers=10, price=5, platform="patreon")
    goal = money(s, "paid_goal", target=500, price=5, platform="substack")
    assert kind(goal) == wi.RESULT and int(data(goal)["headline"].replace(",", "")) == 124
    with pytest.raises(ValueError):
        money(s, "paid_goal", target=500, price=0.2, platform="substack")
    conv = money(s, "conversion_whatif", subscribers=1000, price=5, platform="substack")
    assert kind(conv) == "table" and len(conv.card["rows"]) == 5 and conv.card["rows"][0][1] == "10"
    be = money(s, "break_even", price=5, platform="ghost", monthly_costs=25)
    assert kind(be) == wi.RESULT and data(be)["headline"] == "6"
    rate = money(s, "per_word_rate", fee=150, words=1000, hours=5)
    assert "15p a word" in data(rate)["headline"] and "£30 an hour" in data(rate)["headline"]


def test_affiliate_and_pitches(s):
    a = money(s, "affiliate_disclosure", where="blog", amazon=True)
    assert kind(a) == wi.GUIDE and "Amazon Associate" in str(data(a)) and "ASA" in str(data(a))
    assert "#ad" in str(data(money(s, "affiliate_disclosure", where="social")))
    with pytest.raises(ValueError):
        money(s, "affiliate_disclosure", where="carrier pigeon")
    with pytest.raises(ValueError):
        money(s, "pitch_board")
    assert "Nothing has been sent" in money(s, "pitch_add", publication="Daily Bread", idea="Why sourdough is back", status="pitched",
                                            date=(wi.today() - timedelta(days=20)).isoformat(), fee=120)
    money(s, "pitch_add", publication="Food Weekly", idea="Winter soups")
    board = money(s, "pitch_board")
    assert kind(board) == wi.BOARD and "follow-up" in data(board)["note"] and "Nothing is ever sent" in board
    assert "accepted" in money(s, "pitch_update", pitch="sourdough", status="accepted", fee=150)
    assert "£150" in data(money(s, "pitch_board"))["note"]
    with pytest.raises(ValueError):
        money(s, "pitch_update", pitch="1", status="sent")
    assert kind(money(s, "pitch_template")) == wi.GUIDE
    assert "confirm" in money(s, "pitch_remove", pitch="2")
    assert "Removed" in money(s, "pitch_remove", pitch="2", confirmed=True)
    assert "GOV.UK" in str(data(money(s, "honest_guide")))


def test_bad_actions_and_no_promises(s):
    for mod, name in ((writingincome_newsletter, "writingincome_newsletter"), (writingincome_blog, "writingincome_blog"),
                      (writingincome_book, "writingincome_book"), (writingincome_money, "writingincome_money")):
        with pytest.raises(ValueError):
            mod.run_tool(name, {"action": "nope"}, s, None)
        assert mod.NAMES == {name}
        schema = mod.tool_definitions()[0]["input_schema"]
        assert schema["additionalProperties"] is False and set(schema["properties"]["action"]["enum"]) == set(mod.ACTIONS)
    assert "guarantee" not in json_notes(money(s, "paid_subs_calc", subscribers=5, price=5)).lower().replace("not a promise", "")
