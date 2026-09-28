import asyncio
import json
from datetime import date

import pytest
from PIL import ImageFont

import docs_tools as dt
import docs_tools_forms as forms
import docs_tools_sheets as sheets
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def doc(s, **args):
    return dt.run_tool("document", args, s)


def history(s, **args):
    return dt.run_tool("document_history", args, s)


def sheet(s, **args):
    return sheets.run_tool("spreadsheet", args, s)


def text_of(s, rel):
    return (dt.memory.root(s) / rel).read_text(encoding="utf-8")


BODY = "Intro with **bold**.\n\n## Day 1\n\n- walk\n\n## Day 2\n\nRest."


def test_new_document_pops_up_in_documents(s):
    out = doc(s, action="new", title="Trip plan", text=BODY)
    assert out.card["kind"] == "file" and out.card["src"] == "/screen/file?path=Documents/Trip%20plan.md"
    assert text_of(s, "Documents/Trip plan.md").startswith("# Trip plan\n\nIntro")
    again = doc(s, action="new", title="Trip plan", text="x", folder="Work/Plans")
    assert "Work/Plans/Trip%20plan.md" in again.card["src"]
    with pytest.raises(ValueError):
        doc(s, action="new", title="", text="x")


def test_add_and_replace_sections(s):
    doc(s, action="new", title="Trip", text=BODY)
    out = doc(s, action="add", name="trip", heading="day 1", text="- swim")
    assert out.card["kind"] == "file"
    doc(s, action="replace_section", name="trip", heading="Day 2", text="Fly home.")
    doc(s, action="add", name="trip", heading="Packing", text="Passport")
    doc(s, action="add", name="trip", text="The end.")
    assert text_of(s, "Documents/Trip.md") == ("# Trip\n\nIntro with **bold**.\n\n## Day 1\n\n- walk\n- swim\n\n"
                                               "## Day 2\n\nFly home.\n\n## Packing\n\nPassport\n\nThe end.\n")
    with pytest.raises(ValueError):
        doc(s, action="replace_section", name="trip", heading="Nope", text="x")


def test_show_reads_it_aloud_and_pops_it_up(s):
    doc(s, action="new", title="Poem", text="Roses are red.")
    out = doc(s, action="show", name="poem")
    assert "Roses are red." in out and out.card["name"] == "Poem.md"
    with pytest.raises(ValueError):
        doc(s, action="show", name="missing")


def test_word_count(s):
    doc(s, action="new", title="Essay", text=" ".join(["word"] * 460))
    out = doc(s, action="word_count", name="essay")
    assert out.startswith("Essay has 461 words, about 2 minutes to read")
    assert out.card["kind"] == "table" and ["Words", "461"] in out.card["rows"]


def test_find_replace_confirms_big_changes(s):
    doc(s, action="new", title="Notes", text="cat " * 25)
    out = doc(s, action="find_replace", name="notes", find="CAT", replace_with="dog")
    assert "25 times" in out and not hasattr(out, "card") and "cat" in text_of(s, "Documents/Notes.md")
    out = doc(s, action="find_replace", name="notes", find="cat", replace_with="dog", confirmed=True)
    assert out == "Replaced 25 times in Notes." and out.card["kind"] == "file"
    assert "cat" not in text_of(s, "Documents/Notes.md")
    assert "isn't in" in doc(s, action="find_replace", name="notes", find="zebra", replace_with="x")


def test_contents_from_headings_replaces_old_one(s):
    doc(s, action="new", title="Guide", text="Intro.\n\n## Setup\n\n### Windows\n\n## Use")
    doc(s, action="contents", name="guide")
    out = doc(s, action="contents", name="guide")
    assert out.card["kind"] == "file"
    assert text_of(s, "Documents/Guide.md") == ("# Guide\n\n## Contents\n\n- Setup\n  - Windows\n- Use\n\nIntro.\n\n"
                                                "## Setup\n\n### Windows\n\n## Use\n")


def test_markdown_to_html_escapes_everything():
    page = dt.to_html("# Hi <b>\n\nA **b** *i* [ok](https://x.test/?a=1&b=2) [bad](javascript:alert(1))\n\n- one\n1. two",
                      "T<")
    assert "<h1>Hi &lt;b&gt;</h1>" in page and "<title>T&lt;</title>" in page
    assert "<strong>b</strong> <em>i</em>" in page and '<a href="https://x.test/?a=1&amp;b=2">ok</a>' in page
    assert "javascript" in page and 'href="javascript' not in page
    assert "<ul>\n<li>one</li>\n</ul>\n<ol>\n<li>two</li>\n</ol>" in page and "<script" not in page


def test_export_html_and_pdf(s):
    doc(s, action="new", title="Report", text="Hello **world**.\n\n- a\n- b\n\n" + "words " * 2000)
    out = doc(s, action="export_html", name="report")
    assert "Report.html" in out and out.card["kind"] == "file"
    assert text_of(s, "Documents/Report.html").startswith("<!doctype html>")
    out = doc(s, action="export_pdf", name="report")
    assert out.card["mime"] == "application/pdf"
    data = (dt.memory.root(s) / "Documents" / "Report.pdf").read_bytes()
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page") >= 3  # two pages and the page list


def test_pdf_with_old_bitmap_font(monkeypatch):
    monkeypatch.setattr(dt, "FONT_FILES", {False: ("nope.ttf",), True: ("nope.ttf",)})
    monkeypatch.setattr(ImageFont, "load_default", lambda size=None: ImageFont.load_default_imagefont())
    assert dt.to_pdf("# Title\n\n- bullet • €5 and £5").startswith(b"%PDF")


def test_compare_documents(s):
    doc(s, action="new", title="One", text="same\nold line")
    doc(s, action="new", title="Two", text="same\nnew line")
    out = doc(s, action="compare", name="one", other="two")
    assert out.card["kind"] == "text" and "-old line" in out.card["text"] and "+new line" in out.card["text"]
    assert "2 lines added and 2 taken away" in out  # the titles differ too
    doc(s, action="new", title="One", text="same\nold line", folder="Work")
    assert doc(s, action="compare", name="one", folder="Documents", other="one", other_folder="Work") == \
        "One and One are the same."


def test_versions_and_restore(s):
    doc(s, action="new", title="Plan", text="first")
    assert "no earlier versions" in history(s, action="versions", name="plan")
    doc(s, action="replace_section", name="plan", heading="Plan", text="second")
    out = history(s, action="versions", name="plan")
    assert out.card["kind"] == "list" and out.card["items"][0]["say"] == "Restore version 1 of Plan.md."
    assert "Not restored" in history(s, action="restore", name="plan", version=1)
    assert "second" in text_of(s, "Documents/Plan.md")
    out = history(s, action="restore", name="plan", version=1, confirmed=True)
    assert out.card["kind"] == "file" and text_of(s, "Documents/Plan.md") == "# Plan\n\nfirst\n"
    assert len(dt.versions(dt.memory.root(s) / "Documents" / "Plan.md")) == 2
    with pytest.raises(ValueError):
        history(s, action="restore", name="plan", version=9, confirmed=True)
    # hidden from the pop-up file server and from document search
    with pytest.raises(ValueError):
        dt.screen.memory_path(s, "Documents/.versions/Plan.md/x.md")


def test_versions_are_capped(s):
    doc(s, action="new", title="Busy", text="0")
    for i in range(dt.MAX_VERSIONS + 5):
        doc(s, action="add", name="busy", text=str(i))
    assert len(dt.versions(dt.memory.root(s) / "Documents" / "Busy.md")) == dt.MAX_VERSIONS


def test_templates(s):
    assert "no templates" in history(s, action="templates")
    doc(s, action="new", title="Thanks", text="Dear {{ name }}, thanks for the {{gift}}.")
    out = history(s, action="save_template", name="thanks", template="Thank you note")
    assert "blanks for gift, name" in out and out.card["kind"] == "file"
    listed = history(s, action="templates")
    assert listed.card["items"][0]["say"] == "Make a new document from the Thank you note template."
    out = history(s, action="from_template", template="thank you", title="Thanks Gran", values={"Name": "Gran"})
    assert "Still blank: gift" in out and out.card["kind"] == "file"
    assert text_of(s, "Documents/Thanks Gran.md") == "# Thanks\n\nDear Gran, thanks for the {{gift}}.\n"
    with pytest.raises(ValueError):
        doc(s, action="show", name="thank you note")  # document search skips templates
    assert "Templates" not in doc(s, action="show", name="thanks").card["src"]


def test_letter(s):
    out = forms.letter(s, {"sender": "Thato\n1 High St", "recipient": "Council\nTown Hall", "subject": "Parking permit",
                           "greeting": "Dear Sir or Madam,", "body": "Please renew my permit.", "name": "Thato"},
                       date(2026, 9, 28))
    assert out.card["mime"] == "application/pdf" and "Letters" in out.card["src"]
    md = text_of(s, "Documents/Letters/Letter - Parking permit.md")
    assert "28 September 2026" in md and "Yours faithfully,\n\nThato" in md and "**Parking permit**" in md
    assert (dt.memory.root(s) / "Documents" / "Letters" / "Letter - Parking permit.pdf").read_bytes()[:4] == b"%PDF"


def test_cv_builder(s):
    assert "empty" in forms.run_tool("document_forms", {"action": "cv_show"}, s)
    forms.run_tool("document_forms", {"action": "cv_section", "name": "Thato Lesufi", "section": "profile",
                                      "text": "Reliable and friendly."}, s)
    forms.run_tool("document_forms", {"action": "cv_section", "section": "skills", "text": "- Excel"}, s)
    out = forms.run_tool("document_forms", {"action": "cv_section", "section": "skills", "text": "- Driving",
                                            "append": True}, s)
    assert out.card["mime"] == "application/pdf"
    assert json.loads((dt.memory.root(s) / "cv.json").read_text())["skills"] == "- Excel\n- Driving"
    out = forms.run_tool("document_forms", {"action": "cv_show"}, s)
    assert "Still to fill in: experience, education" in out
    md = text_of(s, "Documents/CV/Thato Lesufi CV.md")
    assert md.startswith("# Thato Lesufi\n\n## Profile\n\nReliable") and "## Skills\n\n- Excel\n- Driving" in md
    with pytest.raises(ValueError):
        forms.run_tool("document_forms", {"action": "cv_section", "section": "hobbies", "text": "x"}, s)


def test_invoice_numbers_and_vat(s):
    args = {"recipient": "Bob Ltd\n1 Road", "items": [{"description": "Cleaning", "quantity": 2, "price": 15},
                                                      {"description": "Travel", "price": 4.5}], "vat": True}
    out = forms.invoice(s, args, date(2026, 9, 28))
    assert out == "Invoice INV-0001 for £41.40 is ready, with a PDF. It's on the screen."
    assert out.card["mime"] == "application/pdf"
    md = text_of(s, "Documents/Invoices/INV-0001 Bob Ltd.md")
    assert "Cleaning: 2 x £15.00 = **£30.00**" in md and "VAT at 20%: £6.90" in md and "Payment due: 28 October 2026" in md
    out = forms.invoice(s, {**args, "vat": False}, date(2026, 9, 28))
    assert out.startswith("Invoice INV-0002 for £34.50")
    book = json.loads((dt.memory.root(s) / "invoices.json").read_text())
    assert book["next"] == 3 and [i["total"] for i in book["issued"]] == [41.4, 34.5]
    with pytest.raises(ValueError):
        forms.invoice(s, {"recipient": "x", "items": []})


def test_spreadsheet_rows(s):
    out = sheet(s, action="create", name="Spend", columns=["Item", "Category", "Cost"])
    assert out.card["kind"] == "table" and out.card["columns"] == ["#", "Item", "Category", "Cost"]
    sheet(s, action="add_row", name="spend", values={"item": "Milk", "category": "Food", "cost": "£1.20"})
    sheet(s, action="add_row", name="spend", values={"Item": "Bus, return", "Category": "Travel", "Cost": "2.50"})
    out = sheet(s, action="update_cell", name="spend", row=1, column="cost", value="1.30")
    assert out.card["rows"][0] == ["1", "Milk", "Food", "1.30"] and out.card["rows"][1][1] == "Bus, return"
    assert "Not deleted" in sheet(s, action="delete_row", name="spend", row=1)
    out = sheet(s, action="delete_row", name="spend", row=1, confirmed=True)
    assert out.card["rows"] == [["1", "Bus, return", "Travel", "2.50"]]
    assert "1 rows" in sheet(s, action="show", name="spend")
    with pytest.raises(ValueError):
        sheet(s, action="update_cell", name="spend", row=5, column="cost", value="1")
    with pytest.raises(ValueError):
        sheet(s, action="add_row", name="spend", values={"colour": "red"})
    assert "Not restored" in history(s, action="restore", name="spend")
    back = history(s, action="restore", name="spend", version=1, confirmed=True)
    assert back.card["kind"] == "table" and len(back.card["rows"]) == 2


def filled(s):
    sheet(s, action="create", name="Spend", columns=["Item", "Category", "Cost"])
    for row in [("Milk", "Food", "£1.20"), ("Bus", "Travel", "2.50"), ("Bread", "food", "1,000"), ("Gift", "", "n/a")]:
        sheet(s, action="add_row", name="spend", values=dict(zip(["Item", "Category", "Cost"], row)))


def test_spreadsheet_maths(s):
    filled(s)
    out = sheet(s, action="totals", name="spend", column="cost")
    assert out.startswith("Spend (4 rows). Cost: total 1,003.70, average 334.57, lowest 1.20, highest 1,000, 3 values")
    assert out.card["rows"] == [["Cost", "1,003.70", "334.57", "1.20", "1,000", "3"]]
    out = sheet(s, action="group_totals", name="spend", group_by="category", column="cost")
    assert out.card["kind"] == "documents-summary"
    assert out.card["data"]["rows"] == [["Food", "1,001.20"], ["Travel", "2.50"], ["(blank)", "0"], ["Total", "1,003.70"]]
    assert out.card["data"]["chart"]["values"] == [1001.2, 2.5, 0]
    counted = sheet(s, action="group_totals", name="spend", group_by="category")
    assert counted.card["data"]["columns"] == ["Category", "Count"]
    with pytest.raises(ValueError):
        sheet(s, action="totals", name="spend", column="item")


def test_sort_and_filter_into_new_sheet(s):
    filled(s)
    out = sheet(s, action="sort_filter", name="spend", sort_by="cost", descending=True, new_name="Big first")
    assert [r[1] for r in out.card["rows"]] == ["Bread", "Bus", "Milk", "Gift"]
    out = sheet(s, action="sort_filter", name="spend", filter_column="cost", filter_op="greater", filter_value="2")
    assert [r[1] for r in out.card["rows"]] == ["Bus", "Bread"]
    assert (dt.memory.root(s) / "Documents" / "Big first.csv").is_file()
    out = sheet(s, action="sort_filter", name="spend", filter_column="category", filter_op="equals", filter_value="FOOD",
                sort_by="item")
    assert [r[1] for r in out.card["rows"]] == ["Bread", "Milk"]
    with pytest.raises(ValueError):
        sheet(s, action="sort_filter", name="spend")


def test_tools_are_registered_and_deferred():
    names = [t["name"] for m in (dt, forms, sheets) for t in m.tool_definitions()]
    assert set(names) == dt.NAMES | forms.NAMES | sheets.NAMES and len(names) == 4
    for m in (dt, forms, sheets):
        assert m in tools.ABILITIES and m not in tools.ALWAYS_LOADED
        for t in m.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False


def test_runs_through_tools(tmp_path, monkeypatch):
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        s = Settings(memory_dir=str(tmp_path))
        return await tools.run_tool("document", {"action": "new", "title": "Hi", "text": "there"}, s, None, page)

    assert asyncio.run(go()) == "Wrote Hi in Documents. It's on the screen."
    assert sent[0]["type"] == "popup" and sent[0]["card"]["name"] == "Hi.md"
