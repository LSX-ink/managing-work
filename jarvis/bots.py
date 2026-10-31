"""Alfred's bots: every bot we build, in one place, so Alfred can list them, show them on the HUD and run them.

The owner (31 Oct 2026): "all bots made also be put into Alfred ... and the HUD". The BOTS chip on the HUD (or
"show my bots") opens a window with every bot: the LSX HQ agents (hq/agents.py), the lowkey.lore video quality
checker on the PC, the Higgsfield guide (higgsfield_guide.py) and Alfred's own studio bots. New bots go in EXTRA_BOTS
(or the HQ roster), and they appear here on their own.

Running a bot:
- an HQ agent: asks the HQ office (http://127.0.0.1:8341, JARVIS_HQ_URL) to run it now, same as its RUN button
- video_qc: runs the lowkey.lore checker (pipeline/qc.py, and the Blender scene lint when asked) on the PC
  (JARVIS_LORE_PROJECT, the lowkey-lore-ref folder) and reports pass or fail with the checker's own findings
- the rest: Alfred's own tools, so the window's button just asks Alfred
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

import screen
from config import Settings

NAMES = {"alfred_bots"}
ACTIONS = ["list", "run", "check_video"]
KIND = "showme"
screen.EXTRA_KINDS.add(KIND)
HQ_URL = os.getenv("JARVIS_HQ_URL", "http://127.0.0.1:8341").rstrip("/")
QC_SECONDS = 1800  # the checker reads every frame of a 75-second 1080x1920 video
LINT_SECONDS = 1200
MAX_OUT = 3000

# Bots that aren't HQ agents. say: the line the window's button sends to Alfred.
EXTRA_BOTS = [
    {"key": "video_qc", "name": "Video quality checker", "emoji": "🎞️", "group": "lowkey.lore",
     "job": "Lints the Blender scene, then checks every frame of a finished lowkey.lore video for glitches "
            "(clipping, popping, camera snaps, things spinning on the spot, sound levels). Failures go back to be remade.",
     "say": "Run the video quality checker on the latest lowkey.lore video"},
    {"key": "higgsfield", "name": "Higgsfield guide", "emoji": "✨", "group": "Videos and websites",
     "job": "Knows every Higgsfield feature and plans how to use it for the lore videos, Kinetic reels and websites, "
            "with credit costs checked first.",
     "say": "Show the Higgsfield features"},
    {"key": "tiktok_studio", "name": "TikTok studio", "emoji": "🎬", "group": "lowkey.lore",
     "job": "Writes, voices and builds TikTok videos, and learns from every rejection.",
     "say": "Open the TikTok studio"},
    {"key": "design_audit", "name": "Design checker", "emoji": "📐", "group": "Kinetic Web Designs",
     "job": "Audits a website's design, contrast and speed with every design skill.",
     "say": "Audit the design of a website"},
    {"key": "instagram_dms", "name": "Instagram replies", "emoji": "📨", "group": "Kinetic Web Designs",
     "job": "Answers Instagram DMs from people who message Kinetic first.",
     "say": "How are the Instagram DM replies going?"},
]


def hq_bots() -> list[dict]:
    """The LSX HQ agents, straight from the roster, so a new agent shows up here too."""
    try:
        from hq.agents import roster
    except Exception:  # noqa: BLE001 - HQ is optional on a fresh install
        return []
    return [{"key": a.key, "name": f"{a.name} ({a.title})", "emoji": a.emoji, "group": f"LSX HQ · {a.division}",
             "job": a.job, "say": f"Run the HQ agent {a.key}", "hq": True} for a in roster()]


def all_bots() -> list[dict]:
    return EXTRA_BOTS + hq_bots()


def find(name: str) -> dict:
    q = (name or "").strip().lower()
    if not q:
        raise ValueError("Which bot?")
    bots = all_bots()
    for b in bots:
        if q == b["key"] or q == b["name"].lower():
            return b
    for b in bots:
        if q in b["name"].lower() or q in b["key"]:
            return b
    raise ValueError(f"I haven't got a bot called {name}. I have: " + ", ".join(b["name"] for b in bots))


def show_list() -> screen.Shown:
    bots = all_bots()
    groups: dict[str, list] = {}
    for b in bots:
        groups.setdefault(b["group"], []).append(
            {"label": f"{b['emoji']} {b['name']}", "note": b["job"], "say": b["say"], "action": "Run"})
    sections = [{"type": "list", "title": g, "items": items} for g, items in groups.items()]
    text = f"I have {len(bots)} bots:\n" + "\n".join(f"- {b['name']}: {b['job']}" for b in bots)
    return screen.Shown(text, screen.card(KIND, "Alfred's bots", "alfred-bots", data={"sections": sections}, buttons=[
        {"label": "Check a video", "say": "Run the video quality checker on the latest lowkey.lore video"},
        {"label": "Higgsfield", "say": "Show the Higgsfield features"},
        {"label": "HQ", "say": "Show me the LSX HQ dashboard"},
    ]))


# The video quality checker -------------------------------------------------------------------------------------
# lowkey-lore-ref (on the PC Desktop): videos\NN-slug\ holds each video; pipeline\qc.py checks the finished mp4
# (exit 0 pass, 1 fail, anything else an error) and writes videos\NN-slug\qc\result.json and report.md. The scene
# lint runs inside Blender (scene.py ... --lint) and writes qc\lint.json; it passes when no item has severity "fail"
# (Blender exits 0 either way). Never lint while a render is running: two Blenders have crashed EEVEE.

def project_dir() -> Path:
    return Path(os.getenv("JARVIS_LORE_PROJECT", "").strip()
                or Path.home() / "OneDrive" / "Desktop" / "lowkey-lore-ref")


def blender_exe() -> str:
    return os.getenv("JARVIS_BLENDER", "").strip() or r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def project_python(root: Path) -> str:
    """The project's own venv Python (it has numpy, scipy, soundfile, imageio-ffmpeg), else this one."""
    for exe in (root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"):
        if exe.exists():
            return str(exe)
    return sys.executable


def find_video(root: Path, name: str = "") -> Path:
    """A video's folder (videos/NN-slug) by number, slug or path; the newest finished one when no name is given."""
    videos = root / "videos"
    if name:
        p = Path(name).expanduser()
        if p.is_file():
            p = p.parent
        if p.is_dir():
            return p
        q = name.strip().lower().replace(" ", "-")
        for d in sorted(videos.glob("*")) if videos.is_dir() else []:
            if d.is_dir() and (d.name.lower() == q or d.name.lower().startswith(q + "-") or q in d.name.lower()):
                return d
        raise ValueError(f"I couldn't find a lowkey.lore video called {name}.")
    done = [(max(m.stat().st_mtime for m in d.glob("*.mp4")), d) for d in (videos.glob("*") if videos.is_dir() else [])
            if d.is_dir() and any(d.glob("*.mp4"))]
    if not done:
        raise ValueError("I couldn't find a finished lowkey.lore video.")
    return max(done)[1]


def blender_running() -> bool:
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq blender.exe"], capture_output=True, text=True,
                                 timeout=15).stdout
        else:
            out = subprocess.run(["pgrep", "-l", "blender"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "blender" in out.lower()


def _run(cmd: list[str], cwd: Path, seconds: int) -> tuple[int, str]:
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=seconds,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"It took longer than {seconds // 60} minutes, so I stopped it."
    except OSError as exc:
        return 127, f"I couldn't start it: {exc}"
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


def _tail(text: str) -> str:
    return text if len(text) <= MAX_OUT else "…" + text[-MAX_OUT:]


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lint_scene(root: Path, vdir: Path) -> tuple[str, list[str]]:
    """("pass" | "fail" | "error", lines) from the Blender scene lint."""
    if blender_running():
        return "error", ["Blender is already running (a render?), so I didn't lint: two Blenders crash EEVEE."]
    scene = vdir / "scene.py"
    if not scene.exists():
        return "error", [f"There's no scene.py in {vdir.name}."]
    before = time.time()
    rel = vdir.relative_to(root) if vdir.is_relative_to(root) else vdir
    code, out = _run([blender_exe(), "-b", "-P", str(rel / "scene.py"), "--", "--video", str(rel), "--lint"],
                     root, LINT_SECONDS)
    report = vdir / "qc" / "lint.json"
    items = _json(report) if report.exists() and report.stat().st_mtime >= before - 1 else None
    if code != 0 or items is None:
        return "error", ["The scene lint crashed or wrote no lint.json."] + _tail(out).splitlines()[-15:]
    fails = [i for i in items if i.get("severity") == "fail"]
    lines = [f"{i.get('severity', '').upper()} {i.get('kind', '')}: {i.get('note', '')}"
             f" ({i.get('t0', '?')}s-{i.get('t1', '?')}s)" for i in items]
    return ("fail" if fails else "pass"), lines


def qc_video(root: Path, vdir: Path) -> tuple[str, list[str], dict]:
    """("pass" | "fail" | "error", lines, result.json) from qc.py."""
    qc = root / "pipeline" / "qc.py"
    if not qc.exists():
        raise ValueError(f"I can't find the video checker at {qc}. Set JARVIS_LORE_PROJECT to the lowkey-lore-ref folder.")
    code, out = _run([project_python(root), str(qc), str(vdir)], root, QC_SECONDS)
    result = _json(vdir / "qc" / "result.json") or {}
    if code not in (0, 1):
        return "error", ["The checker hit an error (a missing mp4, mix.wav or pause.json, or ffmpeg failed)."] + \
            _tail(out).splitlines()[-15:], result
    lines = [f"FAIL {f}" for f in result.get("fails", [])] + [f"WARN {w}" for w in result.get("warnings", [])] + \
        [f"REVIEW {r}" for r in result.get("review", [])]
    if not lines:
        lines = [ln for ln in out.splitlines() if ln.startswith("QC ")][-3:]
    return ("pass" if code == 0 else "fail"), lines, result


def approved(vdir: Path, result: dict) -> bool:
    """Same rule as qc.gate: the automatic QC passed and the visual approval is for this exact file."""
    ok = _json(vdir / "qc" / "approval.json") or {}
    return bool(result.get("passed_automatic")) and bool(result.get("sha")) and ok.get("sha") == result.get("sha")


def check_video(video: str = "", lint: bool = False) -> screen.Shown:
    root = project_dir()
    if not (root / "pipeline" / "qc.py").exists():
        raise ValueError(f"I can't find the video checker in {root}. Set JARVIS_LORE_PROJECT to the lowkey-lore-ref folder.")
    vdir = find_video(root, video)
    sections, steps = [], []
    if lint:
        state, lines = lint_scene(root, vdir)
        steps.append(("Scene lint", state))
        sections.append({"type": "list", "title": f"Scene lint · {state.upper()}",
                         "items": [{"label": ln} for ln in lines[:40]] or [{"label": "Nothing found."}]})
    state, lines, result = qc_video(root, vdir)
    steps.append(("Quality check", state))
    sections.append({"type": "list", "title": f"Quality check · {state.upper()}",
                     "items": [{"label": ln} for ln in lines[:40]] or [{"label": "No problems found."}]})
    facts = [[k, str(result[k])] for k in ("duration", "loudness", "true_peak") if k in result]
    if facts:
        sections.append({"type": "table", "title": "Numbers", "columns": ["", ""], "rows": facts})
    passed = all(s == "pass" for _, s in steps)
    signed = approved(vdir, result)
    verdict = "PASSED" if passed else ("ERROR" if any(s == "error" for _, s in steps) else "FAILED")
    head = f"{vdir.name}: {verdict}" + (" and visually approved, ready to send." if passed and signed else
                                        ", waiting for the visual review (qc.py --approve)." if passed else ".")
    sections.insert(0, {"type": "text", "text": head})
    text = head + "\n" + "\n".join(f"{n}: {s}" for n, s in steps)
    if not passed:
        text += "\nIt goes back to be remade; nothing that failed is sent.\n" + "\n".join(lines[:10])
    return screen.Shown(text, screen.card(KIND, f"Video check: {verdict}", "alfred-bots-qc",
                                          data={"sections": sections}, buttons=[
                                              {"label": "Lint + check", "say": f"Lint and check the lowkey.lore video {vdir.name}"}]))


async def run_hq(key: str, http: httpx.AsyncClient | None) -> str:
    client = http or httpx.AsyncClient()
    try:
        r = await client.post(f"{HQ_URL}/api/run/{key}", timeout=15)
    except httpx.HTTPError:
        return "The LSX HQ office isn't running on this PC, so I couldn't start that agent."
    finally:
        if http is None:
            await client.aclose()
    if r.status_code >= 400:
        return f"HQ said no ({r.status_code}): {r.text[:200]}"
    return "Started. Its result shows in the HQ feed."


async def run_bot(name: str, settings: Settings, http) -> str | screen.Shown:
    bot = find(name)
    if bot["key"] == "video_qc":
        return await asyncio.to_thread(check_video, "")
    if bot["key"] == "higgsfield":
        import higgsfield_guide
        return higgsfield_guide.show_features()
    if bot.get("hq"):
        return f"{bot['name']}: " + await run_hq(bot["key"], http)
    return f"{bot['name']} is one of my own tools. {bot['job']} Just ask: \"{bot['say']}\"."


def tool_definitions() -> list[dict]:
    return [{
        "name": "alfred_bots",
        "description": "Every bot the user has (the LSX HQ agents like Hawk, Vera and Iris, the lowkey.lore video "
                       "quality checker, the Higgsfield guide, the TikTok studio and more), shown as a window on the "
                       "HUD. 'show my bots', 'what bots have I got', 'run Hawk', 'check this video'. list: all bots; "
                       "run (bot): run one now; check_video (optional video, else the newest; lint true to lint the "
                       "Blender scene first): quality-check a lowkey.lore video on the PC. A failed video must not be sent or posted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "bot": {"type": "string", "description": "run: the bot's name or key, e.g. hawk, scout, video_qc."},
                "video": {"type": "string", "description": "check_video: the video's number, name or folder "
                                                           "(e.g. 03 or dam); leave out for the newest."},
                "lint": {"type": "boolean", "description": "check_video: also run the Blender scene lint first "
                                                           "(not while a render is running)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "list":
        return show_list()
    if action == "run":
        return await run_bot(args.get("bot") or "", settings, http)
    if action == "check_video":
        return await asyncio.to_thread(check_video, args.get("video") or "", bool(args.get("lint")))
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
