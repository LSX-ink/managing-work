import json
import sys

import pytest

import mcpbridge
import tools
from config import Settings

# A tiny MCP server: answers initialize, lists two tools and runs them, one message per line like the real ones.
FAKE = r'''
import json, os, sys
for line in sys.stdin:
    msg = json.loads(line)
    if "id" not in msg:
        continue
    method, ident = msg["method"], msg["id"]
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake"}}
    elif method == "tools/list":
        result = {"tools": [
            {"name": "ask", "description": "Answer a question.",
             "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
            {"name": "shot", "description": "A picture.", "inputSchema": {"type": "object", "properties": {}}}]}
    elif method == "tools/call" and msg["params"]["name"] == "ask":
        q = msg["params"]["arguments"]["query"]
        result = {"content": [{"type": "text", "text": f"answer to {q} with key {os.environ['FAKE_KEY'][:3]}"}]}
    elif method == "tools/call":
        result = {"content": [{"type": "image", "data": "aGk=", "mimeType": "image/png"}]}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}) + "\n")
    sys.stdout.flush()
'''


@pytest.fixture
def claude_app(tmp_path, monkeypatch):
    script = tmp_path / "fake_mcp.py"
    script.write_text(FAKE)
    config = tmp_path / "claude_desktop_config.json"
    config.write_text(json.dumps({"mcpServers": {
        "perplexity": {"command": sys.executable, "args": [str(script)], "env": {"FAKE_KEY": "pplx-secret-123"}},
        "remote": {"url": "https://example.com/mcp"}}}))
    monkeypatch.setenv("JARVIS_MCP_CONFIG", str(config))
    yield config
    mcpbridge.stop_all()


def run(**args):
    return mcpbridge.run_tool("mcp_bridge", args, Settings())


def test_registered_and_deferred():
    defs = [t for t in tools.client_tool_definitions(Settings()) if t["name"] == "mcp_bridge"]
    assert len(defs) == 1 and defs[0].get("defer_loading")
    assert mcpbridge in tools.ABILITIES


def test_reads_the_claude_app_list(claude_app):
    found = mcpbridge.load_config()
    assert list(found) == ["perplexity", "remote", "higgsfield"]
    assert found["remote"]["args"] == ["-y", "mcp-remote", "https://example.com/mcp"]  # online ones via mcp-remote
    assert found["higgsfield"]["args"][-1] == "https://mcp.higgsfield.ai/mcp"
    assert "perplexity (starts when needed)" in run(action="servers")


def test_lists_and_calls_tools(claude_app):
    listing = run(action="tools", server="Perplexity")
    assert "- ask: Answer a question." in listing and "query* (string)" in listing
    assert run(action="call", server="perplexity", tool="ask", arguments={"query": "why"}) == "answer to why with key ppl"
    assert "perplexity (running)" in run(action="servers")
    picture = run(action="call", server="perplexity", tool="shot")
    assert picture[0]["type"] == "image" and picture[0]["source"]["data"] == "aGk="
    assert "Restarted perplexity: 2 tools" in run(action="restart", server="perplexity")


def test_clear_errors(claude_app, monkeypatch):
    with pytest.raises(ValueError, match="no MCP called 'nope'.*perplexity"):
        run(action="tools", server="nope")
    with pytest.raises(ValueError, match="no tool 'fly'"):
        run(action="call", server="perplexity", tool="fly")
    monkeypatch.setenv("JARVIS_MCP_CONFIG", str(claude_app.parent / "missing.json"))
    assert run(action="servers") == "MCPs Alfred can use: higgsfield (starts when needed)"
    monkeypatch.setenv("JARVIS_MCP", "false")
    assert "switched off" in run(action="servers")


def test_api_keys_never_echoed():
    server = mcpbridge.Server("x", {"command": "x", "args": [], "env": {"KEY": "pplx-secret-123"}})
    server.errors = ["bad key pplx-secret-123"]
    assert "pplx-secret-123" not in server.last_error() and "***" in server.last_error()


def test_a_server_that_wont_start(tmp_path, monkeypatch):
    config = tmp_path / "c.json"
    config.write_text(json.dumps({"mcpServers": {"broken": {"command": str(tmp_path / "no-such-program")}}}))
    monkeypatch.setenv("JARVIS_MCP_CONFIG", str(config))
    with pytest.raises(ValueError, match="couldn't start the broken MCP"):
        run(action="tools", server="broken")


class FakeHiggsfield:
    """Answers jobs_wait like Higgsfield: still running until the `done_on`th ask."""

    name = "higgsfield"

    def __init__(self, done_on=3, structured=True):
        self.done_on, self.structured, self.asks = done_on, structured, []

    def request(self, method, params, timeout):
        self.asks.append(params)
        state = {"all_terminal": len(self.asks) >= self.done_on, "poll_after_seconds": 4,
                 "jobs": [{"index": 0, "status": "completed" if len(self.asks) >= self.done_on else "in_progress"}]}
        if self.structured:
            return {"structuredContent": state, "content": [{"type": "text", "text": "status"}]}
        return {"content": [{"type": "text", "text": json.dumps(state)}]}


@pytest.mark.parametrize("structured", [True, False])
def test_waits_for_higgsfield_jobs_in_one_call(structured):
    server, naps = FakeHiggsfield(structured=structured), []
    result = mcpbridge.wait_for_jobs(server, {"jobs": [{"index": 0, "job_id": "x"}], "timeout_seconds": 0},
                                     sleep=naps.append)
    assert len(server.asks) == 3 and naps == [4.0, 4.0]
    assert all(a["arguments"]["timeout_seconds"] == 15 for a in server.asks)
    assert mcpbridge.wait_state(result)[0] is True


def test_higgsfield_wait_gives_up_at_the_limit():
    server = FakeHiggsfield(done_on=99)
    result = mcpbridge.wait_for_jobs(server, {"jobs": []}, limit=0, sleep=lambda s: None)
    assert len(server.asks) == 1 and mcpbridge.wait_state(result)[0] is False


def test_unreadable_wait_answer_is_returned_as_is():
    assert mcpbridge.wait_state({"content": [{"type": "text", "text": "not json"}]}) is None
    assert mcpbridge.wait_state({"structuredContent": {"jobs": []}}) is None


def test_run_tool_routes_higgsfield_jobs_wait(monkeypatch):
    server = FakeHiggsfield(done_on=2)
    server.tools = [{"name": "jobs_wait"}]
    monkeypatch.setattr(mcpbridge, "get_server", lambda name: server)
    monkeypatch.setattr(mcpbridge.time, "sleep", lambda s: None)
    out = run(action="call", server="higgsfield", tool="jobs_wait", arguments={"jobs": [{"index": 0, "job_id": "x"}]})
    assert len(server.asks) == 2 and out == "status"
