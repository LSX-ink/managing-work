import subprocess

import askclaude


def _fake(monkeypatch, reply="Done."):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return subprocess.CompletedProcess(cmd, 0, stdout=reply, stderr="")

    monkeypatch.setattr(askclaude, "claude_command", lambda: "claude")
    monkeypatch.setattr(askclaude, "background", lambda s, q: "")
    monkeypatch.setattr(askclaude.subprocess, "run", fake_run)
    return seen


def arg(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def test_ask_is_read_only(monkeypatch):
    seen = _fake(monkeypatch, "ChefMotso's website is chefmotso.com.")
    assert askclaude.ask(None, "What is ChefMotso's website?") == "Claude says: ChefMotso's website is chefmotso.com."
    cmd = seen["cmd"]
    assert arg(cmd, "--allowedTools") == "Read,Grep,Glob,WebSearch,WebFetch"
    assert "Edit" in arg(cmd, "--disallowedTools") and "Bash" in arg(cmd, "--disallowedTools")
    assert "Do not change anything" in arg(cmd, "-p")


def test_change_can_edit_but_outward_commands_are_blocked(monkeypatch):
    seen = _fake(monkeypatch, "I changed the heading.\nNEEDS YES: deploy chefmotso.com with the new heading")
    out = askclaude.ask(None, "change the ChefMotso heading", "change")
    cmd = seen["cmd"]
    assert "Edit" in arg(cmd, "--allowedTools") and "Bash" in arg(cmd, "--allowedTools")
    assert "Bash(*wrangler*)" in arg(cmd, "--disallowedTools") and "Bash(*git push*)" in arg(cmd, "--disallowedTools")
    prompt = arg(cmd, "-p")
    assert "Do NOT do anything outward-facing" in prompt and "passwords" in prompt and "Vera" in prompt
    assert "NEEDS YES: deploy chefmotso.com" in out and "read the NEEDS YES action back" in out


def test_outward_needs_the_users_yes(monkeypatch):
    seen = _fake(monkeypatch, "Deployed.")
    assert "need the user's yes" in askclaude.ask(None, "deploy chefmotso.com", "outward")
    assert "cmd" not in seen
    assert askclaude.ask(None, "deploy chefmotso.com", "outward", user_said_yes=True) == "Claude says: Deployed."
    assert "wrangler" not in arg(seen["cmd"], "--disallowedTools")
    assert "said yes to it" in arg(seen["cmd"], "-p")


def test_no_claude_or_turned_off(monkeypatch):
    monkeypatch.setattr(askclaude, "claude_command", lambda: None)
    assert askclaude.ask(None, "hi") == askclaude.MISSING
    monkeypatch.setenv("JARVIS_ASK_CLAUDE", "false")
    assert askclaude.ask(None, "hi") == askclaude.OFF


def test_is_a_tool_alfred_always_has():
    import tools
    assert askclaude in tools.ALWAYS_LOADED and askclaude in tools.ABILITIES
