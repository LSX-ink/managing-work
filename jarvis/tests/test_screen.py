import asyncio
from dataclasses import replace

import httpx
import pytest

import screen
import tools
from brain import request_options
from config import Settings


def test_card_is_checked_and_capped():
    c = screen.card("list", "Shopping", items=[{"label": "Milk", "say": "tick off milk"}, "Eggs"],
                    buttons=[{"label": "Clear", "say": "clear the shopping list"}, {"label": "no say"}])
    assert c["id"] == "list-shopping"
    assert c["items"] == [{"label": "Milk", "done": False, "say": "tick off milk"},
                          {"label": "Eggs", "done": False, "say": ""}]
    assert c["buttons"] == [{"label": "Clear", "say": "clear the shopping list"}]
    with pytest.raises(ValueError):
        screen.card("html", "x")
    with pytest.raises(ValueError):
        screen.card("chart", "x", chart={"labels": ["a"], "values": [1, 2]})


def test_show_file_finds_it_and_blocks_escapes(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    (tmp_path / "Work" / "Payslips").mkdir(parents=True)
    (tmp_path / "Work" / "Payslips" / "June payslip.pdf").write_bytes(b"%PDF-1.4")
    shown = screen.show_file(s, "Work", "june")
    assert shown.card["mime"] == "application/pdf"
    assert shown.card["src"] == "/screen/file?path=Work/Payslips/June%20payslip.pdf"
    assert screen.memory_path(s, "Work/Payslips/June payslip.pdf").name == "June payslip.pdf"
    for bad in ("../secret.txt", "Work/../../x", ".recent-chat.json", ""):
        with pytest.raises(ValueError):
            screen.memory_path(s, bad)


def test_page_text_reads_words_not_scripts():
    title, text, image = screen.page_text(
        '<html><head><title>Big News &amp; More</title><meta property="og:image" content="https://x.test/a.jpg">'
        '<script>alert("no")</script></head><body><nav>Menu menu menu menu menu menu menu</nav>'
        '<article><p>This is the first proper paragraph of the story, long enough.</p><p>Short</p></article></body></html>')
    assert title == "Big News & More" and image == "https://x.test/a.jpg"
    assert text == "This is the first proper paragraph of the story, long enough."


def test_shown_result_pops_up_on_the_page():
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        return await tools.run_tool("show_on_screen", {"kind": "chart", "title": "Sleep", "labels": ["Mon", "Tue"],
                                                        "values": [7, 6.5], "chart_type": "line"},
                                    Settings(), None, page)

    out = asyncio.run(go())
    assert out == "It's on the screen: Sleep." and type(out) is str
    assert sent[0]["type"] == "popup" and sent[0]["card"]["chart"]["values"] == [7.0, 6.5]


def test_video_only_youtube():
    async def go(url):
        return await screen.run_tool("show_on_screen", {"kind": "video", "url": url}, Settings(), None)

    shown = asyncio.run(go("https://youtu.be/dQw4w9WgXcQ"))
    assert shown.card["src"] == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
    with pytest.raises(ValueError):
        asyncio.run(go("https://evil.test/v"))


def test_screen_file_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import server
    monkeypatch.setattr(server, "settings", replace(server.settings, memory_dir=str(tmp_path), password=""))
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "note.md").write_text("# Hi", encoding="utf-8")
    (tmp_path / "Ideas" / "page.html").write_text("<script>x</script>", encoding="utf-8")
    client = TestClient(server.app)
    r = client.get("/screen/file", params={"path": "Ideas/note.md"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    r = client.get("/screen/file", params={"path": "Ideas/page.html"})
    assert r.headers["content-type"] == "application/octet-stream" and "sandbox" in r.headers["content-security-policy"]
    assert client.get("/screen/file", params={"path": "../x"}).status_code == 404


def test_most_abilities_load_on_demand():
    opts = request_options(Settings())
    names = [t.get("name") for t in opts["tools"]]
    assert "tool_search_tool_bm25" in names and "show_on_screen" in names
    deferred = {t["name"] for t in opts["tools"] if t.get("defer_loading")}
    assert "date_time" in deferred and "todo_list" not in deferred
    assert not any(t.get("cache_control") and t.get("defer_loading") for t in opts["tools"])
    off = request_options(replace(Settings(), tool_search=False))
    assert not any(t.get("defer_loading") for t in off["tools"])
    assert "tool_search_tool_bm25" not in {t.get("name") for t in off["tools"]}


def test_extra_kinds_carry_data():
    screen.EXTRA_KINDS.add("test-board")
    try:
        c = screen.card("test-board", "Board", data={"cells": [1, 2, 3]}, checks=True)
        assert c["data"] == {"cells": [1, 2, 3]} and c["checks"] is True
        with pytest.raises(ValueError):
            screen.card("test-board", "Board", data={"x": "y" * 300_000})
    finally:
        screen.EXTRA_KINDS.discard("test-board")
