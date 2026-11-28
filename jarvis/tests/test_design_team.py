import asyncio
import re

import pytest

import design_team as dt
import tools
from config import Settings
from design_contrast import AA, ratio

PEOPLE = [{"name": "Lebo Mokoena", "role": "Head baker", "photo": "/img/lebo.webp", "bio": "Since 2011.",
           "url": "https://instagram.com/lebo", "link_text": "Instagram"},
          {"name": "Sam Patel", "role": "Cake designer"},
          {"name": "Ama", "role": "Pastry chef", "photo": "https://x.com/a.jpg", "alt": "Ama smiling in the kitchen"}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dt.run_tool("make_team_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                         "people": PEOPLE, **args}, settings))


def read(tmp_path, file="team.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_team(s, tmp_path):
    out = ask({"intro": "Hello."}, s)
    assert "3 people" in out and "Sam Patel has initials" in out and "agreed to show" in out
    code = read(tmp_path)
    assert code.count('<li class="tm-card">') == 3 and "<h3>Lebo Mokoena</h3>" in code
    assert '<img class="tm-photo" src="/img/lebo.webp" alt="Lebo Mokoena, Head baker" width="600"' in code
    assert 'alt="Ama smiling in the kitchen"' in code
    assert '<span class="tm-photo tm-initials" aria-hidden="true">SP' in code
    assert ('<a class="tm-link" href="https://instagram.com/lebo" target="_blank" rel="noopener">Instagram'
            '<span class="tm-sr"> (Lebo Mokoena)</span></a>') in code
    assert "repeat(3, minmax(0, 1fr))" in code and "<script" not in code
    assert read(tmp_path, "team-preview.html").startswith("<!doctype html>")


def test_one_person_and_columns(s, tmp_path):
    out = ask({"people": PEOPLE[:1]}, s)
    assert "1 person" in out and "initials" not in out
    assert "repeat(1, minmax(0, 1fr))" in read(tmp_path)
    ask({"people": [{"name": f"P{i}", "role": "R"} for i in range(5)]}, s)
    assert "repeat(3, minmax(0, 1fr))" in read(tmp_path)
    ask({"people": [{"name": f"P{i}", "role": "R"} for i in range(8)]}, s)
    assert "repeat(4, minmax(0, 1fr))" in read(tmp_path)


@pytest.mark.parametrize("bad, msg", [
    ({"people": []}, "1 to 8"),
    ({"people": PEOPLE * 3}, "1 to 8"),
    ({"people": [{"name": "A"}]}, "needs a name and a role"),
    ({"people": [{"name": "A", "role": "B", "photo": "a.jpg"}]}, "photo"),
    ({"people": [{"name": "A", "role": "B", "url": "javascript:x"}]}, "isn't one I can use"),
    ({"people": [{"name": "A", "role": "B", "bio": "x" * 300}]}, "under 220"),
    ({"people": [{"name": "A", "role": "B"}, {"name": "a", "role": "C"}]}, "same name"),
])
def test_rejects(s, bad, msg):
    out = ask(bad, s)
    assert msg in out and "Made a" not in out


def test_escapes(s, tmp_path):
    ask({"people": [{"name": "<b>A</b>", "role": "<i>x</i>"}]}, s)
    code = read(tmp_path)
    assert "&lt;b&gt;A&lt;/b&gt;" in code and "<i>x" not in code


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dt.block({"name": "X", "brand": brand, "title": "T", "intro": "", "people": [
        {"name": "A", "role": "B", "photo": "", "alt": "", "initials": "A", "bio": "", "url": "", "link_text": ""}]})
    get = lambda k: re.search(rf"--tm-{k}:(#[0-9a-f]{{6}})", code).group(1)  # noqa: E731
    assert ratio(get("accent"), "#ffffff") >= AA and ratio(get("letters"), get("tint")) >= AA


def test_registered():
    assert dt in tools.ABILITIES and [t["name"] for t in dt.tool_definitions()] == ["make_team_section"]
