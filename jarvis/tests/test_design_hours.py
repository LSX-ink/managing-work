import asyncio
import json
import re

import pytest
from PIL import Image

import design_hours as dh
import tools
from config import Settings

HOURS = {"Mon-Fri": "7:30am-4pm", "Sat": "8-2", "Sun": "closed"}


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dh.run_tool("make_opening_hours", args, settings))


@pytest.mark.parametrize("text, spans", [
    ("9am-5:30pm", [(540, 1050)]), ("10-4", [(600, 960)]), ("9-5:30", [(540, 1050)]),
    ("9-12, 1-5", [(540, 720), (780, 1020)]), ("17:30-23:00", [(1050, 1380)]), ("12-2", [(720, 840)]),
    ("noon to 6pm", [(720, 1080)]), ("9am-midnight", [(540, 1440)]), ("midnight-6am", [(0, 360)]),
    ("Closed", []), ("24 hours", [(0, 1440)]),
])
def test_spans(text, spans):
    assert dh.spans_of(text) == spans


@pytest.mark.parametrize("key, days", [
    ("Mon-Fri", [0, 1, 2, 3, 4]), ("Sat & Sun", [5, 6]), ("Fri-Mon", [4, 5, 6, 0]), ("Tues, Thursday", [1, 3]),
    ("wednesday", [2]), ("Mon and Wed", [0, 2]),
])
def test_days(key, days):
    assert dh.days_of(key) == days


def test_words():
    assert dh.words([(540, 720), (780, 1050)]) == "9am – noon, 1pm – 5:30pm"
    assert dh.words([]) == "Closed" and dh.words([(0, 1440)]) == "Open 24 hours"


def test_files_and_schema(s, tmp_path):
    out = ask({"name": "Lebo's Bakery", "colour": "#fde047", "hours": HOURS, "website": "lebosbakery.co.uk"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web"
    assert "Sat 8am – 2pm" in out and "Sun Closed" in out
    page = (folder / "hours.html").read_text()
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
    assert data["@type"] == "LocalBusiness" and data["url"] == "https://lebosbakery.co.uk"
    specs = data["openingHoursSpecification"]
    weekday = next(x for x in specs if x["opens"] == "07:30")
    assert weekday["closes"] == "16:00" and len(weekday["dayOfWeek"]) == 5
    assert {"dayOfWeek": ["https://schema.org/Saturday"], "opens": "08:00", "closes": "14:00",
            "@type": "OpeningHoursSpecification"} in specs
    assert not any("Sunday" in d for x in specs for d in x["dayOfWeek"])  # closed days are left out
    assert 'data-day="0"><th scope="row">Sunday' in page and "Lebo&#x27;s Bakery" in page
    sign = Image.open(folder / "hours-sign.png")
    assert sign.size == (round(148 * dh.MM) + 2 * dh.BLEED, round(210 * dh.MM) + 2 * dh.BLEED)
    assert (folder / "hours-sign.pdf").read_bytes().startswith(b"%PDF")


def test_name_cannot_break_out_of_the_data():
    page = dh.web_block("</script><script>alert(1)</script>", "#000000", dh.week_of({"Mon": "9-5"}), "")
    assert page.count("</script") == 2  # only the two real closing tags; the name can't end the data early


@pytest.mark.parametrize("args, words", [
    ({"colour": "#000", "hours": HOURS}, "business name"),
    ({"name": "X", "colour": "#000"}, "by day"),
    ({"name": "X", "colour": "#000", "hours": {"Funday": "9-5"}}, "don't know the day"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "5pm-9am"}}, "before the opening"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "9-1, 12-5pm"}}, "overlap"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "25:00-26:00"}}, "isn't a real time"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "soonish"}}, "couldn't read"),
    ({"name": "X", "colour": "#000", "hours": {"Mon-Fri": "9-5", "Fri": "9-3"}}, "given twice"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "closed"}}, "Every day is closed"),
    ({"name": "X", "colour": "#000", "hours": {"Mon": "9-5"}, "website": "javascript:x"}, "isn't a web address"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dh in tools.ABILITIES and [t["name"] for t in dh.tool_definitions()] == ["make_opening_hours"]
