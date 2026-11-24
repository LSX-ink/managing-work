import subprocess

import askclaude


def test_asks_claude_read_only_and_reads_the_answer(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="ChefMotso's website is chefmotso.com.", stderr="")

    monkeypatch.setattr(askclaude, "claude_command", lambda: "claude")
    monkeypatch.setattr(askclaude, "background", lambda s, q: "")
    monkeypatch.setattr(askclaude.subprocess, "run", fake_run)
    out = askclaude.ask(None, "What is ChefMotso's website?")
    assert out == "Claude says: ChefMotso's website is chefmotso.com."
    cmd = seen["cmd"]
    assert cmd[cmd.index("--allowedTools") + 1] == "Read,Grep,Glob,WebSearch,WebFetch"
    assert "Edit" in cmd[cmd.index("--disallowedTools") + 1] and "Bash" in cmd[cmd.index("--disallowedTools") + 1]
    assert "Do not change anything" in cmd[cmd.index("-p") + 1]


def test_no_claude_or_turned_off(monkeypatch):
    monkeypatch.setattr(askclaude, "claude_command", lambda: None)
    assert askclaude.ask(None, "hi") == askclaude.MISSING
    monkeypatch.setenv("JARVIS_ASK_CLAUDE", "false")
    assert askclaude.ask(None, "hi") == askclaude.OFF


def test_is_a_tool_alfred_always_has():
    import tools
    assert askclaude in tools.ALWAYS_LOADED and askclaude in tools.ABILITIES
