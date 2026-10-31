import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

import bots
import higgsfield_guide as hg
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def run(mod, args, settings):
    return asyncio.run(mod.run_tool(next(iter(mod.NAMES)), args, settings))


def test_registered_with_alfred():
    assert bots in tools.ABILITIES and higgsfield_guide_in_tools()
    names = {t["name"] for m in (bots, hg) for t in m.tool_definitions()}
    assert names == bots.NAMES | hg.NAMES


def higgsfield_guide_in_tools():
    return hg in tools.ABILITIES


def test_bot_list_has_hq_agents_and_the_checker(s):
    out = run(bots, {"action": "list"}, s)
    assert out.card["kind"] == "showme"
    labels = [i["label"] for sec in out.card["data"]["sections"] for i in sec["items"]]
    assert any("Video quality checker" in x for x in labels)
    assert any("Higgsfield guide" in x for x in labels)
    assert any("Hawk" in x for x in labels) and any("Vera" in x for x in labels)  # straight from the HQ roster
    assert all(i.get("say") for sec in out.card["data"]["sections"] for i in sec["items"])


def test_find_bot():
    assert bots.find("hawk")["key"] == "scout"
    assert bots.find("video_qc")["name"] == "Video quality checker"
    with pytest.raises(ValueError):
        bots.find("nobody")


def test_run_hq_agent_without_hq_running(s, monkeypatch):
    monkeypatch.setattr(bots, "HQ_URL", "http://127.0.0.1:9")
    out = run(bots, {"action": "run", "bot": "hawk"}, s)
    assert "isn't running" in out


def make_project(tmp_path, code=0, result=None, approve=False):
    root = tmp_path / "lowkey-lore-ref"
    (root / "pipeline").mkdir(parents=True)
    vdir = root / "videos" / "03-dam"
    (vdir / "qc").mkdir(parents=True)
    (vdir / "lowkey-lore-dam.mp4").write_bytes(b"x")
    result = result if result is not None else {"sha": "abc", "passed_automatic": code == 0, "fails": [],
                                                "warnings": [], "review": [], "duration": 80.0, "loudness": -14.0}
    # A stand-in qc.py with the real one's contract: writes qc/result.json, exits 0 pass / 1 fail.
    (root / "pipeline" / "qc.py").write_text(
        "import json, sys, pathlib\n"
        "v = pathlib.Path(sys.argv[1])\n"
        f"(v / 'qc' / 'result.json').write_text(json.dumps({result!r}))\n"
        f"print('QC done')\nsys.exit({code})\n")
    if approve:
        (vdir / "qc" / "approval.json").write_text(json.dumps({"sha": result["sha"]}))
    return root, vdir


def test_check_video_pass_and_approved(tmp_path, monkeypatch):
    root, vdir = make_project(tmp_path, approve=True)
    monkeypatch.setenv("JARVIS_LORE_PROJECT", str(root))
    out = bots.check_video("dam")
    assert "PASSED" in out and "ready to send" in out
    assert out.card["title"] == "Video check: PASSED"


def test_check_video_newest_and_waiting_for_review(tmp_path, monkeypatch):
    root, vdir = make_project(tmp_path)
    monkeypatch.setenv("JARVIS_LORE_PROJECT", str(root))
    out = bots.check_video("")
    assert "03-dam: PASSED" in out and "visual review" in out


def test_check_video_fail_lists_findings(tmp_path, monkeypatch):
    root, _ = make_project(tmp_path, code=1, result={"sha": "abc", "passed_automatic": False,
                                                     "fails": ["frozen picture from 87.37s"], "warnings": [], "review": []})
    monkeypatch.setenv("JARVIS_LORE_PROJECT", str(root))
    out = bots.check_video("03")
    assert "FAILED" in out and "frozen picture" in out and "remade" in out


def test_check_video_error(tmp_path, monkeypatch):
    root, _ = make_project(tmp_path, code=2, result={})
    monkeypatch.setenv("JARVIS_LORE_PROJECT", str(root))
    assert "ERROR" in bots.check_video("dam")


def test_check_video_no_checker(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_LORE_PROJECT", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="can't find the video checker"):
        bots.check_video("")


def test_lint_pass_means_no_fail_items(tmp_path, monkeypatch):
    root, vdir = make_project(tmp_path)
    (vdir / "scene.py").write_text("")
    monkeypatch.setattr(bots, "blender_running", lambda: False)
    fake = tmp_path / "blender.py"
    # Stand-in Blender: writes lint.json with a review item only, exits 0 like the real one.
    fake.write_text("import json, sys, pathlib\n"
                    "v = pathlib.Path(sys.argv[sys.argv.index('--video') + 1])\n"
                    "(v / 'qc' / 'lint.json').write_text(json.dumps([{'kind': 'coplanar', 'severity': 'review', 'note': 'n'}]))\n")
    monkeypatch.setattr(bots, "_run", lambda cmd, cwd, sec: _real_run([sys.executable, str(fake)] + cmd[1:], cwd, sec))
    state, lines = bots.lint_scene(root, vdir)
    assert state == "pass" and "REVIEW coplanar" in lines[0]


_real_run = bots._run


def test_lint_refuses_while_rendering(tmp_path, monkeypatch):
    root, vdir = make_project(tmp_path)
    monkeypatch.setattr(bots, "blender_running", lambda: True)
    state, lines = bots.lint_scene(root, vdir)
    assert state == "error" and "already running" in lines[0]


# Higgsfield guide ------------------------------------------------------------------------------------------------

def test_features_window(s):
    out = run(hg, {"action": "features"}, s)
    assert out.card["kind"] == "showme"
    titles = [sec["title"] for sec in out.card["data"]["sections"]]
    assert titles == hg.GROUPS
    assert "Dubbing" in out and "Start and end frame" in out


def test_every_plan_step_is_a_feature():
    for _, steps in hg.VIDEO_PLANS.values():
        assert all(k in hg.BY_KEY for k, _ in steps)
    assert all(k in hg.BY_KEY for k, _ in hg.SITE_STEPS)


def test_lore_plan_starts_with_seamless_opening(s):
    out = run(hg, {"action": "video_plan", "kind": "lore", "topic": "the dam"}, s)
    assert "for the dam" in out and "END frame" in out and "draft" in out.lower()
    out = run(hg, {"action": "video_plan", "kind": "kinetic"}, s)
    assert "Kinetic" in out


def test_site_plan_keeps_real_photos(s):
    out = run(hg, {"action": "site_plan", "business": "Ash Lodge"}, s)
    assert "Never invent interiors" in out


def test_feature_lookup(s):
    assert "Dubbing" in run(hg, {"action": "feature", "name": "dubbing"}, s)
    assert "Kling" in run(hg, {"action": "feature", "name": "kling3_0"}, s)
    with pytest.raises(ValueError):
        run(hg, {"action": "feature", "name": "teleport"}, s)


def test_cost_uses_free_get_cost_only(s, monkeypatch):
    calls = []

    def fake(tool, arguments):
        calls.append((tool, arguments))
        return '{"credits": 10}'

    monkeypatch.setattr(hg, "_call", fake)
    out = run(hg, {"action": "cost", "model": "kling3_0", "duration": 5}, s)
    assert "10 credits" in out and "Nothing was made" in out
    assert calls[0][0] == "generate_video" and calls[0][1]["params"]["get_cost"] is True


def test_rules_include_no_ai_cutaway(s):
    assert "cutaway" in run(hg, {"action": "rules"}, s)


def test_hud_has_bots_buttons():
    page = (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="hud-bots"' in page and 'id="bots-fab"' in page and 'id="higgsfield-fab"' in page
    assert "/static/bots.js" in page
    js = (Path(__file__).resolve().parents[1] / "frontend" / "bots.js").read_text(encoding="utf-8")
    assert "Show my bots" in js and "Show the Higgsfield features" in js


def test_tool_descriptions_fit():
    for m in (bots, hg):
        for t in m.tool_definitions():
            assert len(t["description"]) < 1500
            assert os.path.basename(m.__file__)
