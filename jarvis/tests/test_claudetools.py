import asyncio

import httpx
import pytest

import bots
import claudetools as ct
import omniroute
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def run(name, args, settings, http=None):
    return asyncio.run(ct.run_tool(name, args, settings, http))


DDG = """
<div class="result results_links results_links_deep web-result">
  <h2 class="result__title"><a rel="nofollow" class="result__a"
    href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.bbc.co.uk%2Fnews&amp;rut=abc">BBC <b>News</b></a></h2>
  <a class="result__snippet" href="x">The latest <b>UK</b> news.</a>
</div>
<div class="result results_links web-result">
  <h2 class="result__title"><a class="result__a" href="https://example.com/page">Example</a></h2>
  <a class="result__snippet" href="y">An example page.</a>
</div>
"""


def test_duckduckgo_results_are_unwrapped():
    found = ct.parse_ddg(DDG)
    assert found[0] == {"title": "BBC News", "url": "https://www.bbc.co.uk/news", "snippet": "The latest UK news."}
    assert found[1]["url"] == "https://example.com/page"
    assert len(ct.parse_ddg(DDG, limit=1)) == 1


def test_free_search_falls_back_to_wikipedia(s):
    def answer(request):
        if "duckduckgo" in request.url.host:
            return httpx.Response(200, text="<html>nothing</html>")
        return httpx.Response(200, json={"query": {"search": [{"title": "Ada Lovelace", "snippet": "a <b>mathematician</b>"}]}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(answer)) as http:
            return await ct.run_tool("free_web_search", {"query": "Ada Lovelace"}, s, http)

    out = asyncio.run(go())
    assert "Ada Lovelace - https://en.wikipedia.org/wiki/Ada_Lovelace" in out and "a mathematician" in out


def test_word_excel_and_powerpoint_files_are_made_and_read_back(s):
    word = run("office_file", {"action": "make_word", "title": "Plan", "text": "# Goals\n- **Win** clients\n1. Call\n"
                               "| Name | Price |\n|---|---|\n| Site | 395 |"}, s)
    assert "Made Plan.docx in Documents" in word and word.card["kind"] == "file"
    text = run("office_file", {"action": "read", "name": "plan.docx"}, s)
    assert "Goals" in text and "Win clients" in text and "Site | 395" in text

    run("office_file", {"action": "make_excel", "title": "Prices", "folder": "Work",
                        "sheets": [{"name": "Plans", "rows": [["Plan", "Price"], ["Starter", "395"]]}]}, s)
    sheet = run("office_file", {"action": "read", "name": "Prices", "folder": "Work"}, s)
    assert "[Sheet Plans]" in sheet and "Starter | 395" in sheet

    run("office_file", {"action": "make_powerpoint", "title": "Pitch",
                        "slides": [{"title": "Why us", "bullets": ["Fast", "Free care month"], "notes": "smile"}]}, s)
    deck = run("office_file", {"action": "read", "name": "Pitch.pptx"}, s)
    assert "[Slide 1] Pitch" in deck and "Why us" in deck and "Fast" in deck

    again = run("office_file", {"action": "make_word", "title": "Plan", "text": "second"}, s)
    assert "Plan (2).docx" in again  # never overwrites


def test_pdf_pages_are_read(tmp_path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.add_blank_page(200, 200)
    path = tmp_path / "x.pdf"
    with open(path, "wb") as f:
        w.write(f)
    text, total = ct.pdf_text(path.read_bytes(), "2")
    assert total == 2 and "[Page 2]" in text and "[Page 1]" not in text


def test_bad_office_action_and_missing_title(s):
    with pytest.raises(ValueError):
        run("office_file", {"action": "sing"}, s)
    with pytest.raises(ValueError):
        run("office_file", {"action": "make_word", "title": " "}, s)


def test_the_list_pops_up_and_is_in_the_bots_window(s):
    shown = run("claude_tools", {}, s)
    assert shown.card["kind"] == "showme" and "Web search" in shown
    assert any(b["key"] == "claude_tools" for b in bots.EXTRA_BOTS)
    assert ct in tools.ABILITIES


def test_the_free_ai_always_gets_the_free_web_tools():
    every = tools.client_tool_definitions(Settings())
    deferred = {t["name"] for t in every if t.get("defer_loading")}
    assert set(ct.FREE_ROUTE_TOOLS) <= deferred  # Claude finds them with tool search; he has his own web_search
    sent = omniroute.gateway_request({"model": "x", "messages": [], "tools": every}, "auto")
    names = {t["name"] for t in sent["tools"]}
    assert set(ct.FREE_ROUTE_TOOLS) <= names and omniroute.FREE_ROUTE_TOOLS == ct.FREE_ROUTE_TOOLS
