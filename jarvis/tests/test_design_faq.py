import asyncio
import json
import re

import pytest

import design_faq as df
import tools
from config import Settings
from design_contrast import AA, UI, ratio

QA = [{"question": "How much is it?", "answer": "From £395.\n\nSee https://example.com/prices."},
      {"question": "How long?", "answer": "1 to 3 weeks."}]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(df.run_tool("make_faq_section", {"name": "Lebo's Bakery", "colour": "#c2410c", **args},
                                   settings))


def read(tmp_path, file="faq.html"):
    return (tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "web" / file).read_text(encoding="utf-8")


def test_makes_block_with_schema(s, tmp_path):
    out = ask({"questions": QA, "contact_url": "/contact"}, s)
    assert "2 questions" in out
    code = read(tmp_path)
    assert code.count("<details") == 2 and "<details open>" in code and code.count("<details open>") == 1
    assert "<p>From £395.</p><p>See <a href=\"https://example.com/prices\">https://example.com/prices</a>.</p>" \
        in code
    assert 'href="/contact">Get in touch' in code and "<script>" not in code
    data = json.loads(re.search(r'ld\+json">\s*(.*?)\s*</script>', code, re.S).group(1))
    assert data["@type"] == "FAQPage" and [q["name"] for q in data["mainEntity"]] == ["How much is it?", "How long?"]
    assert data["mainEntity"][0]["acceptedAnswer"]["text"] == "From £395. See https://example.com/prices."
    assert read(tmp_path, "faq-preview.html").startswith("<!doctype html>")


def test_first_closed_and_no_contact(s, tmp_path):
    ask({"questions": QA, "first_open": False, "title": "FAQ"}, s)
    code = read(tmp_path)
    assert "<details open>" not in code and "faq-more" not in code.split("</style>")[1] and ">FAQ</h2>" in code


def test_escapes_everything(s, tmp_path):
    ask({"questions": [{"question": "<b>Q</b>", "answer": "<script>alert(1)</script> & </script>"},
                       {"question": "Q2", "answer": 'https://x.com/"onclick=1'}]}, s)
    code = read(tmp_path)
    body, ld = code.split('<script type="application/ld+json">')
    assert "<b>Q</b>" not in body and "<script>alert" not in body and "&amp;" in body
    assert '"onclick' not in body and "&quot;onclick=1" in body
    assert ld.count("</script>") == 1 and "<\\/script>" in ld


@pytest.mark.parametrize("brand", ["#fde047", "#c2410c", "#0b0b0f", "#ffffff", "#22c55e"])
def test_colours(brand):
    code = df.block("X", brand, "FAQ", [("a", "b"), ("c", "d")], True, "")
    accent = re.search(r"--faq-accent:(#\w+)", code).group(1)
    ring = re.search(r"--faq-ring:(#\w+)", code).group(1)
    assert ratio(accent, "#ffffff") >= AA and ratio(ring, "#ffffff") >= UI


@pytest.mark.parametrize("args, words", [
    ({"name": "", "questions": QA}, "business name"),
    ({"questions": QA[:1]}, "2 to 15"),
    ({"questions": QA * 8}, "2 to 15"),
    ({"questions": "nope"}, "list"),
    ({"questions": [{"question": "a"}, {"question": "b", "answer": "c"}]}, "question and an answer"),
    ({"questions": [{"question": "Same?", "answer": "a"}, {"question": "same?", "answer": "b"}]}, "twice"),
    ({"questions": [{"question": "x" * 161, "answer": "a"}, QA[0]]}, "shorter"),
    ({"questions": QA, "contact_url": "javascript:alert(1)"}, "contact link"),
])
def test_bad_input(s, args, words):
    assert words in ask(args, s)


def test_registered():
    assert df in tools.ABILITIES and [t["name"] for t in df.tool_definitions()] == ["make_faq_section"]
