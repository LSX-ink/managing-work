import dataclasses

import httpx
import pytest

import alfredmem
import tools
from config import Settings


class FakeWorker:
    """Stands in for the Claude Mem worker's HTTP API."""

    def __init__(self):
        self.saved = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/memory/save":
            body = __import__("json").loads(request.content)
            self.saved.append(body)
            return httpx.Response(200, json={"success": True, "id": len(self.saved)})
        if request.url.path == "/api/search":
            assert request.url.params["project"] == "alfred"
            query = request.url.params.get("query", "").lower()
            found = [{"project": s["project"], "title": s.get("title", ""), "narrative": s["text"],
                      "created_at": "2026-10-12T13:36:10.597Z"} for s in self.saved
                     if not query or query in s["text"].lower()]
            found.append({"project": "managing-work", "title": "Claude Code work", "narrative": "not Alfred's"})
            return httpx.Response(200, json={"observations": found})
        return httpx.Response(404)


@pytest.fixture
def worker(monkeypatch):
    fake = FakeWorker()
    transport = httpx.MockTransport(fake.handler)
    monkeypatch.setattr(alfredmem.httpx, "get", lambda url, **kw: httpx.Client(transport=transport).get(url, **kw))
    monkeypatch.setattr(alfredmem.httpx, "request",
                        lambda method, url, **kw: httpx.Client(transport=transport).request(method, url, **kw))
    return fake


def on() -> Settings:
    return dataclasses.replace(Settings(), alfred_mem=True)


def test_off_in_tests_by_default():
    assert not alfredmem.enabled(Settings())
    assert alfredmem.prompt_section(Settings()) == ""
    assert "turned off" in alfredmem.run_tool("long_term_memory", {"action": "recent"}, Settings())


def test_own_port_not_claude_codes():
    assert alfredmem.base_url(on()) == "http://127.0.0.1:37778"
    env = alfredmem.worker_env(on())
    assert env["CLAUDE_MEM_WORKER_PORT"] == "37778"
    assert env["CLAUDE_MEM_DATA_DIR"].endswith("alfred-mem")


def test_save_and_search_only_alfreds_memories(worker):
    s = on()
    assert alfredmem.run_tool("long_term_memory", {"action": "save", "text": "Chose the Kinetic Web Designs route",
                                                   "title": "Money plan"}, s) == "Saved to my long-term memory."
    assert worker.saved[0] == {"text": "Chose the Kinetic Web Designs route", "project": "alfred", "title": "Money plan"}
    found = alfredmem.run_tool("long_term_memory", {"action": "search", "query": "kinetic"}, s)
    assert "Money plan: Chose the Kinetic Web Designs route" in found
    assert "not Alfred's" not in found


def test_remember_turn_strips_stamps_and_skips_activate(worker):
    s = on()
    alfredmem.remember_turn(s, "(Local time: Monday 12 October, 14:00)\nMy car is due an MOT in May", "Noted, sir.")
    alfredmem.remember_turn(s, "[activate]", "Good afternoon.")
    assert len(worker.saved) == 1
    assert worker.saved[0]["text"].startswith("The user said: My car is due an MOT in May\nAlfred replied: Noted")
    assert worker.saved[0]["title"] == "My car is due an MOT in May"


def test_snapshot_goes_into_instructions(worker):
    s = on()
    alfredmem.save(s, "Likes Kaizer Chiefs", "Team")
    alfredmem.take_snapshot(s)
    assert "Team: Likes Kaizer Chiefs" in alfredmem.prompt_section(s)
    alfredmem._snapshot = ""


def test_not_installed_says_how(monkeypatch):
    monkeypatch.setattr(alfredmem, "healthy", lambda settings: False)
    monkeypatch.setattr(alfredmem, "plugin_scripts", lambda: None)
    with pytest.raises(ValueError, match="npx claude-mem install"):
        alfredmem.run_tool("long_term_memory", {"action": "recent"}, on())


def test_finds_newest_installed_plugin(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    cache = tmp_path / "plugins" / "cache" / "thedotmack" / "claude-mem"
    for version in ("13.9.0", "13.35.0", "14.0.0"):
        scripts = cache / version / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "worker-service.cjs").write_text("")
        (scripts / "bun-runner.js").write_text("")
    (cache / "14.0.0" / ".orphaned_at").write_text("")
    assert alfredmem.plugin_scripts() == cache / "13.35.0" / "scripts"


def test_always_in_front_of_alfred():
    names = [t["name"] for t in tools.client_tool_definitions(Settings())]
    assert "long_term_memory" in names
    tool = next(t for t in tools.client_tool_definitions(Settings()) if t["name"] == "long_term_memory")
    assert not tool.get("defer_loading")
