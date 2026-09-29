import asyncio
import csv

import pytest

import digitalproducts_copy as dc
import digitalproducts_ideas as di
import digitalproducts_make as dm
import digitalproducts_sell as ds
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def idea(s, **a):
    return di.run_tool("digitalproducts_catalogue", a, s, None)


def make(s, **a):
    return dm.run_tool("digitalproducts_make", a, s, None)


def cp(s, **a):
    return dc.run_tool("digitalproducts_copy", a, s, None)


def sell(s, **a):
    return ds.run_tool("digitalproducts_launch", a, s, None)


def card(x):
    assert isinstance(x, screen.Shown) and x.card
    return x.card


def plan(s, name="Weekly Reset Planner", **a):
    a.setdefault("format", "printable planner")
    a.setdefault("price", 4)
    a.setdefault("audience", "busy parents")
    return idea(s, action="product_plan", name=name, **a)


def files(s, tmp_path):
    return sorted(p.name for p in (tmp_path / "digitalproducts" / "files").rglob("*") if p.is_file())


# ---- Catalogue tool: ideas and validator ----

def test_idea_add_list_edit_remove(s):
    assert "idea 1" in idea(s, action="idea_add", idea="Meal planner", niche="cooking")
    assert card(idea(s, action="idea_list"))["kind"] == "list"
    idea(s, action="idea_edit", id=1, idea="Weekly meal planner", format="printable planner")
    assert "Weekly meal" in card(idea(s, action="idea_list"))["items"][0]["label"]
    assert "confirm" in idea(s, action="idea_remove", id=1)
    idea(s, action="idea_remove", id=1, confirmed=True)
    assert card(idea(s, action="idea_list"))["items"][0]["label"] == "Nothing yet"


def test_brainstorm_returns_ten_savable_ideas(s):
    c = card(idea(s, action="idea_brainstorm", niche="gardening"))
    assert len(c["items"]) == 10 and "gardening" in c["items"][0]["label"] and c["items"][0]["say"]


def test_validate_and_tick(s):
    idea(s, action="idea_add", idea="Habit sheet")
    c = card(idea(s, action="idea_validate", id=1))
    assert len(c["items"]) == 8 and not any(i["done"] for i in c["items"])
    out = idea(s, action="validate_tick", id=1, items=[1, 2, 3])
    assert "3 of 8" in out and sum(i["done"] for i in card(out)["items"]) == 3
    assert "2 of 8" in idea(s, action="validate_tick", id=1, items=[3], done=False)


def test_idea_rank(s):
    idea(s, action="idea_add", idea="A")
    idea(s, action="idea_add", idea="B")
    idea(s, action="validate_tick", id=2, items=[1, 2])
    rows = card(idea(s, action="idea_rank"))["rows"]
    assert rows[0][1] == "B"


def test_product_plan_from_idea_and_show(s):
    idea(s, action="idea_add", idea="Budget sheet", format="budget sheet")
    out = idea(s, action="product_plan", idea_id=1, price=3.5)
    assert card(out)["kind"] == "table" and "Budget sheet" in out
    assert idea(s, action="idea_list").startswith("No product ideas")
    shown = idea(s, action="product_show", product="budget")
    assert any("budget_sheet_make" in r[1] for r in card(shown)["rows"])


def test_product_plan_needs_format(s):
    with pytest.raises(ValueError):
        idea(s, action="product_plan", name="Thing")


def test_catalogue_status_edit_remove(s):
    plan(s)
    plan(s, name="Study Checklist", format="checklist", status="idea")
    idea(s, action="status_set", product="Weekly", status="listed")
    c = card(idea(s, action="catalogue_show"))
    assert c["kind"] == "digitalproducts-catalogue" and screen.card is not None
    cols = {col["status"]: col["items"] for col in c["data"]["columns"]}
    assert cols["listed"][0]["name"] == "Weekly Reset Planner" and cols["idea"][0]["say"]
    idea(s, action="product_edit", product=1, price=5, audience="students", benefits=["Simple"])
    assert "£5.00" in idea(s, action="product_show", product=1)
    assert "confirm" in idea(s, action="product_remove", product=1)
    idea(s, action="product_remove", product=1, confirmed=True)
    assert len(card(idea(s, action="catalogue_show"))["data"]["columns"][2]["items"]) == 0


def test_bad_status_and_missing_product(s):
    plan(s)
    with pytest.raises(ValueError):
        idea(s, action="status_set", product=1, status="sold")
    with pytest.raises(ValueError):
        idea(s, action="product_show", product="nothing here")


def test_catalogue_export_and_stats(s, tmp_path):
    plan(s)
    out = idea(s, action="catalogue_export")
    assert card(out)["kind"] == "file"
    rows = list(csv.reader(open(tmp_path / "digitalproducts" / "catalogue" / "catalogue.csv")))
    assert rows[1][1] == "Weekly Reset Planner"
    assert card(idea(s, action="catalogue_stats"))["chart"]["values"] == [0, 1, 0, 0]


def test_version_log_and_list(s):
    plan(s)
    idea(s, action="version_log", product=1, change="Added A5 pages")
    idea(s, action="version_log", product=1, change="Fixed typo", version="v1.1")
    c = card(idea(s, action="version_list", product="Weekly"))
    assert [r[1] for r in c["rows"]] == ["v1.0", "v1.1"]


# ---- Make tool ----

def test_planners_all_styles(s, tmp_path):
    for style in ("weekly", "daily", "monthly"):
        out = make(s, action="planner_make", style=style, month=2, year=2027)
        assert card(out)["kind"] == "file"
    text = (tmp_path / "digitalproducts" / "files" / "monthly-planner.html").read_text()
    assert "February 2027" in text and "<table>" in text
    assert make(s, action="planner_make", style="weekly", pdf=True) and any(f.endswith(".pdf") for f in files(s, tmp_path))
    with pytest.raises(ValueError):
        make(s, action="planner_make", style="yearly")


def test_checklist_worksheet_habit_budget(s, tmp_path):
    make(s, action="checklist_make", title="Moving Day", items=["Boxes", "Keys"])
    make(s, action="worksheet_make", title="Goal Worksheet", items=["What is my goal?"])
    make(s, action="habit_tracker_make", month=2, year=2027, items=["Read", "Walk"])
    make(s, action="budget_sheet_make")
    names = files(s, tmp_path)
    assert {"moving-day.html", "goal-worksheet.html", "monthly-budget-sheet.html"} <= set(names)
    assert "Boxes" in (tmp_path / "digitalproducts/files/moving-day.html").read_text()
    habit = next(n for n in names if n.startswith("habit-tracker"))
    assert "<th>28</th>" in (tmp_path / "digitalproducts/files" / habit).read_text()
    assert "<th>29</th>" not in (tmp_path / "digitalproducts/files" / habit).read_text()


def test_html_is_escaped(s, tmp_path):
    make(s, action="checklist_make", title="A", items=["<script>x</script>"])
    assert "<script>x" not in (tmp_path / "digitalproducts/files/a.html").read_text()


def test_ebook_csv_prompts_course(s, tmp_path):
    make(s, action="ebook_skeleton", title="Calm Mornings", items=["Wake up", "Move"], words=500, audience="tired people")
    text = (tmp_path / "digitalproducts/files/calm-mornings-skeleton.md").read_text()
    assert "## Chapter 2: Move" in text and "500 words" in text
    make(s, action="csv_template", kind="content calendar")
    rows = list(csv.reader(open(tmp_path / "digitalproducts/files/content-calendar-template.csv")))
    assert rows[0][0] == "Date" and len(rows) == 4
    make(s, action="csv_template", items=["A", "B"], title="custom", rows=1)
    with pytest.raises(ValueError):
        make(s, action="csv_template", kind="nonsense")
    make(s, action="prompt_pack", topic="baking", count=12)
    pack = (tmp_path / "digitalproducts/files/baking-prompt-pack.md").read_text()
    assert "12." in pack and "baking" in pack and "test each prompt" in pack
    out = make(s, action="course_outline", title="Sketching", count=4, minutes=10)
    assert "40 minutes" in out


def test_wallpapers_and_cover(s, tmp_path):
    out = make(s, action="wallpaper_make", title="Night Sky", count=2, palette="mono", size="phone")
    assert card(out)["kind"] == "file"
    from PIL import Image
    imgs = sorted((tmp_path / "digitalproducts/files/night-sky").glob("*.png"))
    assert len(imgs) == 2 and Image.open(imgs[0]).size == (1170, 2532)
    make(s, action="cover_make", title="Calm Mornings: a gentle guide", subtitle="Ten small habits", palette="ocean")
    cover = Image.open(tmp_path / "digitalproducts/files/calm-mornings-a-gentle-guide-cover.png")
    assert cover.size == (1600, 2000)
    with pytest.raises(ValueError):
        make(s, action="wallpaper_make", palette="neon")


def test_files_show_pdf_remove_and_attach(s, tmp_path):
    plan(s)
    make(s, action="checklist_make", title="Start Here", items=["One"], product="Weekly")
    rows = card(idea(s, action="product_show", product=1))["rows"]
    assert dict(rows)["Files"] == "start-here.html"
    assert len(card(make(s, action="files_list"))["items"]) == 1
    assert card(make(s, action="file_show", name="start-here"))["kind"] == "file"
    assert card(make(s, action="file_pdf", name="start-here"))["mime"] == "application/pdf"
    make(s, action="ebook_skeleton", title="Book")
    assert make(s, action="file_pdf", name="book-skeleton.md").card["name"].endswith(".pdf")
    make(s, action="csv_template", kind="budget")
    with pytest.raises(ValueError):
        make(s, action="file_pdf", name="budget-template.csv")
    assert "confirm" in make(s, action="file_remove", name="start-here.html")
    make(s, action="file_remove", name="start-here.html", confirmed=True)
    assert "start-here.html" not in files(s, tmp_path)


# ---- Copy tool ----

def test_listing_draft_show_check_export(s, tmp_path):
    plan(s, keywords=["weekly planner"], benefits=["Room to write", "Prints on A4"])
    out = cp(s, action="listing_draft", product="Weekly")
    body = card(out)["text"]
    assert "TITLE OPTIONS" in body and "Room to write" in body and "FAQ" in body and "TAGS" in body
    assert "similar products sell for" in out
    assert card(cp(s, action="listing_show", product=1))["kind"] == "text"
    assert "No files attached" in str(card(cp(s, action="listing_check", product=1))["items"])
    assert card(cp(s, action="listing_export", product=1))["kind"] == "file"
    assert (tmp_path / "digitalproducts/listings/weekly-reset-planner-listing.md").exists()


def test_listing_check_flags_risky_claims(s):
    plan(s, benefits=["Guaranteed to make money fast"])
    cp(s, action="listing_draft", product=1)
    labels = " ".join(i["label"] for i in card(cp(s, action="listing_check", product=1))["items"])
    assert "guaranteed" in labels.lower() and "make money" in labels


def test_listing_show_without_draft(s):
    plan(s)
    with pytest.raises(ValueError):
        cp(s, action="listing_show", product=1)


def test_titles_tags_cover_faq(s):
    plan(s, keywords=["meal plan"])
    assert len(card(cp(s, action="title_options", product=1))["items"]) >= 2
    tags = card(cp(s, action="tags_make", product=1))["items"]
    assert 3 <= len(tags) <= 13
    ideas = card(cp(s, action="cover_ideas", product=1))
    assert len(ideas["items"]) == 7 and ideas["buttons"]
    assert "Q:" in card(cp(s, action="faq_draft", product=1))["text"]


def test_licences(s, tmp_path):
    for kind in ("personal", "commercial", "teacher"):
        assert "not legal advice" in card(cp(s, action="licence_terms", kind=kind))["text"]
    assert card(cp(s, action="licence_file", kind="commercial"))["kind"] == "file"
    assert (tmp_path / "digitalproducts/licences/commercial-licence.md").exists()
    with pytest.raises(ValueError):
        cp(s, action="licence_terms", kind="free for all")


def test_customer_faq_bank_and_reply(s):
    cp(s, action="customer_faq_add", question="Can I print it more than once?", answer="Yes, for yourself.")
    cp(s, action="customer_faq_add", question="What size is the file?", answer="A4 and Letter.")
    assert len(card(cp(s, action="customer_faq_list"))["items"]) == 2
    assert "A4 and Letter" in cp(s, action="customer_faq_find", question="which size is it")
    assert "Nothing in your FAQ" in cp(s, action="customer_faq_find", question="zebra")
    reply = cp(s, action="customer_reply", message="Hello, can I print this again?", customer="Sam")
    assert "Hi Sam" in card(reply)["text"] and "Yes, for yourself" in card(reply)["text"]
    assert "[your answer here]" in card(cp(s, action="customer_reply", message="zebra?"))["text"]
    assert "confirm" in cp(s, action="customer_faq_remove", id=1)
    cp(s, action="customer_faq_remove", id=1, confirmed=True)
    assert len(card(cp(s, action="customer_faq_list"))["items"]) == 1


def test_update_and_thanks_notes(s):
    plan(s)
    idea(s, action="version_log", product=1, change="new A5 pages")
    assert "new A5 pages" in card(cp(s, action="update_note", product=1))["text"]
    assert "Thank you for buying" in card(cp(s, action="thanks_note", product=1))["text"]


# ---- Launch tool ----

def test_bundle_make_list_remove(s):
    plan(s, price=4)
    plan(s, name="Study Checklist", format="checklist", price=2)
    out = sell(s, action="bundle_make", name="Starter", products=["Weekly", "Study"], price=5)
    assert "£6.00" in out and "similar products sell for" in out
    rows = card(out)["rows"]
    assert any(r[0] == "15% off" for r in rows) and rows[-1] == ["Your bundle price", "£5.00"]
    assert card(sell(s, action="bundle_list"))["rows"][0][0] == "Starter"
    with pytest.raises(ValueError):
        sell(s, action="bundle_make", name="Solo", products=["Weekly"])
    assert "confirm" in sell(s, action="bundle_remove", name="Starter")
    sell(s, action="bundle_remove", name="Starter", confirmed=True)
    assert sell(s, action="bundle_list").startswith("No bundles")


def test_price_tiers(s):
    plan(s, price=4)
    c = card(sell(s, action="price_tiers", product=1))
    assert c["kind"] == "digitalproducts-tiers" and [t["price"] for t in c["data"]["tiers"]] == ["£4.00", "£6.50", "£9.50"]
    assert card(sell(s, action="price_tiers", price=10))["data"]["tiers"][0]["price"] == "£10.00"
    with pytest.raises(ValueError):
        sell(s, action="price_tiers")


def test_comps(s):
    plan(s, price=4)
    assert "No similar prices" in sell(s, action="comps_show")
    for p in (3, 5, 7):
        sell(s, action="comps_add", price=p, product="Weekly", note="found by me")
    out = sell(s, action="comps_show", product="Weekly")
    assert "middle £5.00" in out and "Yours is £4.00" in out
    assert "confirm" in sell(s, action="comps_remove", id=2)
    sell(s, action="comps_remove", id=2, confirmed=True)
    assert "2 similar" in sell(s, action="comps_show")


def test_launch_checklist(s):
    plan(s)
    out = sell(s, action="launch_start", product="Weekly")
    items = card(out)["items"]
    assert len(items) >= 12 and items[0]["say"] and not any(i["done"] for i in items)
    ticked = sell(s, action="launch_tick", product=1, items=[1, 2])
    assert sum(i["done"] for i in card(ticked)["items"]) == 2
    untick = sell(s, action="launch_tick", product=1, items=[1], done=False)
    assert sum(i["done"] for i in card(untick)["items"]) == 1
    assert "1 of" in sell(s, action="launch_show", product=1)
    assert "confirm" in sell(s, action="launch_remove", product=1)
    sell(s, action="launch_remove", product=1, confirmed=True)
    with pytest.raises(ValueError):
        sell(s, action="launch_show", product=1)


def test_refund_text_has_gov_note(s):
    assert "GOV.UK" in card(sell(s, action="refund_text"))["text"]


# ---- Registry ----

def test_unknown_actions(s):
    for mod, name in ((di, "digitalproducts_catalogue"), (dm, "digitalproducts_make"), (dc, "digitalproducts_copy"),
                      (ds, "digitalproducts_launch")):
        with pytest.raises(ValueError):
            mod.run_tool(name, {"action": "nope"}, s, None)


def test_all_actions_are_wired_and_registered():
    total = 0
    for mod in (di, dm, dc, ds):
        (tool,) = mod.tool_definitions()
        assert tool["input_schema"]["additionalProperties"] is False
        assert set(tool["input_schema"]["properties"]["action"]["enum"]) == set(mod.ACTIONS)
        assert mod in tools.ABILITIES and tool["name"] in mod.NAMES
        total += len(mod.ACTIONS)
    assert total >= 50
    assert "digitalproducts-catalogue" in screen.EXTRA_KINDS and "digitalproducts-tiers" in screen.EXTRA_KINDS


def test_through_tools_run_tool(s):
    out = asyncio.run(tools._run_tool("digitalproducts_catalogue", {"action": "idea_brainstorm", "niche": "yoga"}, s, None))
    assert isinstance(out, screen.Shown) and out.card["kind"] == "list"
