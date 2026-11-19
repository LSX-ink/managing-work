import asyncio
import re

import pytest

import design_testimonials as dt
import tools
from config import Settings
from design_contrast import AA, UI, ratio

REVIEWS = [{"quote": "Best sourdough in town.", "reviewer": "Sarah K.", "source": "Google review"},
           {"quote": "Great cake. " * 40, "reviewer": "Tom R.", "stars": 4.5},
           {"quote": "\"Lovely coffee.\"", "reviewer": "Amira", "stars": 4}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dt.run_tool("make_testimonials_section", {"name": "Lebo's Bakery", "colour": "#c2410c",
                                                                 **args}, settings))


def read(tmp_path, file="testimonials.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_makes_section(s, tmp_path):
    out = ask({"reviews": REVIEWS, "summary": "4.9 from 120 Google reviews", "reviews_url": "https://g.page/x"}, s)
    assert "3 reviews" in out and "1 long review gets a 'Read more'" in out and "really wrote" in out
    code = read(tmp_path)
    assert code.count('<figure class="t-card">') == 3 and "Rated 4.5 out of 5" in code and "Rated 4 out of 5" in code
    assert "“Best sourdough in town.”" in code and "“Lovely coffee.”" in code and '"Lovely' not in code
    assert '4.9 from 120 Google reviews <a href="https://g.page/x">See all reviews</a>' in code
    assert "<summary>Read more" in code and "Tom R.'s review" in code
    assert "<script" not in code and "ld+json" not in code  # no self-serving review stars for Google
    assert read(tmp_path, "testimonials-preview.html").startswith("<!doctype html>")


def test_long_review_cut_at_sentence_and_kept_whole(s, tmp_path):
    ask({"reviews": REVIEWS[1:2]}, s)
    code = read(tmp_path)
    first = re.search(r"<p>“(.*?)<span class=\"t-dots\">", code).group(1)
    rest = re.search(r"</summary><p>(.*?)”</p>", code).group(1)
    assert first.endswith("Great cake.") and (first + " " + rest).split() == ("Great cake. " * 40).split()


@pytest.mark.parametrize("rating, gold", [(5, 5), (4.5, 4), (1, 1), (3.5, 3)])
def test_stars(rating, gold):
    svg = dt.stars_svg(rating, "u")
    assert svg.count(f'fill="{dt.GOLD}"') == gold and ("url(#u-h" in svg) == (rating % 1 != 0)
    assert svg.count("<path") == 5 and 'aria-hidden="true"' in svg


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = dt.block("X", brand, "T", "", "", [])
    accent = re.search(r"--t-accent:(#\w+)", code).group(1)
    mark = re.search(r"--t-mark:(#\w+)", code).group(1)
    assert ratio(accent, "#ffffff") >= AA and ratio(mark, "#ffffff") >= UI


def test_escapes(s, tmp_path):
    ask({"reviews": [{"quote": "<script>alert(1)</script>", "reviewer": "<b>Bo</b>", "source": "<i>x</i>"}],
         "title": "A & B"}, s)
    code = read(tmp_path)
    assert "<script>" not in code and "<b>Bo" not in code and "<i>x" not in code and "A &amp; B" in code


@pytest.mark.parametrize("args, words", [
    ({"name": "", "reviews": REVIEWS}, "business name"),
    ({"reviews": []}, "1 to 9"),
    ({"reviews": REVIEWS * 4}, "1 to 9"),
    ({"reviews": [{"quote": "Nice"}]}, "reviewer's name"),
    ({"reviews": [{"quote": "Nice", "reviewer": "A", "stars": 6}]}, "1 to 5"),
    ({"reviews": [{"quote": "Nice", "reviewer": "A", "stars": 4.2}]}, "in halves"),
    ({"reviews": [{"quote": "x " * 700, "reviewer": "A"}]}, "very long"),
    ({"reviews": REVIEWS, "reviews_url": "javascript:alert(1)"}, "all reviews"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert dt in tools.ABILITIES and [t["name"] for t in dt.tool_definitions()] == ["make_testimonials_section"]
