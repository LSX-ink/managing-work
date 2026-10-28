"""The dashboard (owner, 27 Oct 2026: "can claude have a better dashboard?" ... "all 3"): one live page, on the PC in
LSX HQ and on the phone through Alfred's private link, with two tabs.

Business: today's Instagram DMs (with a Sent button that records it for the follow-ups), Instagram messages that need
the owner, follow-ups due, mock-ups made today, this week's numbers against the target funnel, and health.
Claude: what Claude is working on now, what's finished (with links) and what's waiting for the owner, from
claude-work.json, which Claude keeps up to date with `python -m hq.dashboard ...` (see the bottom of this file).

Read-only except the Sent button, which only marks the lead as messaged; nothing is ever sent from here."""

import json
import re
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

import psutil

DM_FOLDER = Path.home() / "OneDrive" / "Desktop" / "Instagram DMs"
LIVE_M = Path(r"C:\Users\Thato\kinetic-repo\kinetic-live\m")
SITE = "https://kineticwebdesigns.co.uk/m/"
WORK_FILE = "claude-work.json"
MAX_DONE = 40


# ---- business --------------------------------------------------------------------------------------

def dm_file(day: date, folder: Path = DM_FOLDER) -> Path | None:
    """Today's DM list: the newest rebuild ("everything + 3D", then "new designs") when there is one, else the morning list."""
    for name in (f"Instagram DMs {day.isoformat()} (everything + 3D).md", f"Instagram DMs {day.isoformat()} (new designs).md",
                 f"Instagram DMs {day.isoformat()}.md"):
        if (folder / name).exists():
            return folder / name
    return None


def parse_dms(text: str) -> list[dict]:
    """Each "## n. Name (Town)" section: name, town, @handle, mock-up link and the DM itself."""
    out = []
    for sec in re.split(r"\n## \d+\. ", "\n" + text)[1:]:
        head = sec.splitlines()[0]
        m = re.match(r"(.*) \((.*)\)$", head)
        name, town = (m.groups() if m else (head, ""))
        ig = re.search(r"Instagram: @(\S+)", sec)
        link = re.search(r"Mock-up[^:]*: (https?://\S+)", sec)
        dm = re.search(r"```\n(.*?)\n```", sec, re.S)
        if dm:
            out.append({"name": name.strip(), "town": town, "instagram": ig.group(1) if ig else "",
                        "link": link.group(1) if link else "", "dm": dm.group(1)})
    return out


def messaged_today(settings, day: date) -> set[str]:
    import kinetic_store as st
    names = set()
    for r in st.rows_of(settings, st.OUTREACH):
        for h in r.get("history") or []:
            if h.get("status") == "contacted" and h.get("date") == day.isoformat():
                names.add(r["name"].lower())
    return names


def mark_sent(settings, name: str) -> str:
    """The Sent button: the lead is marked messaged by DM today, so its follow-ups are tracked."""
    import kinetic_outreach
    return kinetic_outreach.mark(settings, {"business": name, "status": "contacted", "channel": "dm"})


def mockups_today(day: date, live: Path = LIVE_M) -> list[dict]:
    out = []
    if live.exists():
        for d in live.iterdir():
            page = d / "index.html"
            if page.exists() and date.fromtimestamp(page.stat().st_mtime) == day and not d.name.startswith("_"):
                out.append({"name": d.name, "link": f"{SITE}{d.name}/", "at": datetime.fromtimestamp(page.stat().st_mtime).strftime("%H:%M")})
    return sorted(out, key=lambda m: m["at"], reverse=True)


def health_now() -> list[dict]:
    disk = shutil.disk_usage(Path.home().anchor or "/")
    mem = psutil.virtual_memory().percent
    return [{"name": "Drive", "ok": disk.free > 10 * 2**30, "text": f"{disk.free / 2**30:.0f} GB free"},
            {"name": "Memory", "ok": mem < 92, "text": f"{mem:.0f}% used"}]


def business(settings, day: date | None = None) -> dict:
    import instagram_dms
    import kinetic_briefing
    import kinetic_outreach
    day = day or date.today()
    f = dm_file(day)
    dms = parse_dms(f.read_text(encoding="utf-8")) if f else []
    sent = messaged_today(settings, day)
    for d in dms:
        d["sent"] = d["name"].lower() in sent
    try:
        nums = kinetic_briefing.numbers(settings, {}, day)  # the website's briefs need wrangler: shown as unknown
    except Exception:  # noqa: BLE001 - a bad tracker file mustn't blank the page
        nums = {}
    try:
        needs = instagram_dms.load_state(settings).get("needs_you", [])[-10:][::-1]
    except Exception:  # noqa: BLE001
        needs = []
    due = [{"name": r["name"], "channel": r.get("channel") or "", "messages": r.get("messages", 0)}
           for r in kinetic_outreach.due_rows(settings, day)]
    return {"dms": dms, "dm_file": f.name if f else "", "needs_you": needs, "follow_ups": due,
            "mockups": mockups_today(day), "numbers": nums, "target": kinetic_briefing.TARGET, "health": health_now()}


# ---- Claude's work ----------------------------------------------------------------------------------

def load_work(folder: Path) -> dict:
    try:
        w = json.loads((folder / WORK_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        w = {}
    w.setdefault("now", {})
    w.setdefault("done", [])
    w.setdefault("waiting", [])
    return w


def save_work(folder: Path, w: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    w["done"] = w["done"][:MAX_DONE]
    w["updated"] = datetime.now().isoformat(timespec="minutes")
    (folder / WORK_FILE).write_text(json.dumps(w, indent=1, ensure_ascii=False), encoding="utf-8")


def work_update(folder: Path, action: str, title: str = "", link: str = "", detail: str = "") -> dict:
    """now: what Claude is on (with progress in detail); done: a finished item (newest first); wait: something the
    owner needs to do; clear-wait: drop a waiting item by title; idle: nothing running."""
    w = load_work(folder)
    stamp = datetime.now().strftime("%d %b %H:%M")
    if action == "now":
        w["now"] = {"title": title, "detail": detail, "since": stamp}
    elif action == "idle":
        w["now"] = {}
    elif action == "done":
        w["done"].insert(0, {"title": title, "link": link, "detail": detail, "at": stamp})
        if w["now"].get("title") == title:
            w["now"] = {}
    elif action == "wait":
        w["waiting"] = [x for x in w["waiting"] if x["title"] != title] + [{"title": title, "link": link, "detail": detail, "since": stamp}]
    elif action == "clear-wait":
        w["waiting"] = [x for x in w["waiting"] if x["title"] != title]
    else:
        raise ValueError("now, idle, done, wait or clear-wait")
    save_work(folder, w)
    return w


if __name__ == "__main__":  # python -m hq.dashboard now|idle|done|wait|clear-wait "title" [link] [detail]
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import memory
    from config import Settings
    a = sys.argv[1:] + ["", "", ""]
    work_update(memory.root(Settings()) / "LSX HQ", a[0], a[1], a[2], a[3])
    print("ok")
