"""Repurpose part 4: the cross-platform tracker (which version of each video is on which platform, typed in by the
user) with gaps and stats, and evergreen re-post reminders.

Everything is stored in repurpose.json in the memory folder. Nothing is fetched from any platform, nothing is posted,
and the dates are whatever the user says.
"""

import calendar
import csv
from datetime import date, timedelta

import homestore as hs
import repurpose_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.add("repurpose-matrix")

ACTIONS = ["version_log", "version_edit", "version_remove", "tracker_show", "video_versions", "gaps", "platforms_set",
           "tracker_stats", "tracker_export", "evergreen_mark", "evergreen_due", "evergreen_list", "evergreen_done",
           "evergreen_remove"]
STATUSES = ["planned", "draft", "scheduled", "posted"]
SOON = 14


def _platform(saved: dict, name) -> str:
    known = saved["platforms"] or store.PLATFORMS
    return hs.find(known + store.PLATFORMS, hs.need(name, "platform", 40)) or hs.clean(name, 40)


def _status(value, default: str = "posted") -> str:
    text = hs.clean(value).lower() or default
    if text not in STATUSES:
        raise ValueError("The status must be one of " + ", ".join(STATUSES) + ".")
    return text


def _versions(n: int) -> str:
    return f"{n} version{'s' * (n != 1)}"


def _mine(saved: dict, video: str) -> list[dict]:
    return [v for v in saved["versions"] if v["video"].lower() == video.lower()]


def _describe(v: dict) -> str:
    return f"{v['platform']} {v['status']}{' on ' + v['date'] if v['date'] else ''}"


# ---- Versions --------------------------------------------------------------------------------------

def version_log(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    video = store.video(settings, args, saved)
    platform = _platform(saved, args.get("platform"))
    status = _status(args.get("status"))
    day = store.parse_date(args.get("date"), today)
    row = next((v for v in _mine(saved, video) if v["platform"] == platform and v["status"] != "posted"), None)
    if row is None:
        row = {"id": saved["next_id"], "video": video, "platform": platform, "format": "", "date": day,
               "status": status, "url": "", "note": ""}
        store.put(saved["versions"], row)
        saved["next_id"] += 1
    row.update({"status": status, "date": day})
    for key in ("format", "url", "note"):
        if args.get(key):
            row[key] = hs.clean(args[key], 200)
    store.save(settings, saved)
    return f"Noted: {video} on {platform} is {status} ({day}). {_versions(len(_mine(saved, video)))} of it now."


def _by_id(saved: dict, args: dict) -> dict:
    n = int(hs.number(args.get("id"), "version number", 1, 1_000_000))
    row = next((v for v in saved["versions"] if v["id"] == n), None)
    if row is None:
        raise ValueError(f"I don't have version number {n}. Ask for the video's versions to see the numbers.")
    return row


def version_edit(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    row = _by_id(saved, args)
    if args.get("status"):
        row["status"] = _status(args["status"])
    if args.get("date"):
        row["date"] = store.parse_date(args["date"], today)
    for key in ("format", "url", "note"):
        if args.get(key) is not None:
            row[key] = hs.clean(args[key], 200)
    store.save(settings, saved)
    return f"Updated version {row['id']}: {row['video']}, {_describe(row)}."


def version_remove(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    row = _by_id(saved, args)
    if not args.get("confirmed"):
        return store.confirm_needed(f"version {row['id']} ({row['video']} on {row['platform']})")
    saved["versions"].remove(row)
    store.save(settings, saved)
    return f"Removed version {row['id']}."


def video_versions(settings: Settings, args: dict, today: date) -> screen.Shown:
    saved = store.load(settings)
    video = store.video(settings, args, saved)
    rows = _mine(saved, video)
    if not rows:
        raise ValueError(f"I have no versions of {video} yet.")
    table = [[str(v["id"]), v["platform"], v["format"] or "-", v["status"], v["date"], v["url"] or v["note"] or "-"]
             for v in sorted(rows, key=lambda v: v["date"])]
    return screen.Shown(f"{video} has {len(rows)} versions.",
                        screen.card("table", f"Versions of {video}", "repurpose-versions",
                                    columns=["#", "Where", "Format", "Status", "Date", "Link or note"], rows=table))


# ---- Tracker, gaps and stats -----------------------------------------------------------------------

def _platforms(saved: dict) -> list[str]:
    return saved["platforms"] or store.PLATFORMS


def tracker_show(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    saved = store.load(settings)
    videos = list(dict.fromkeys(v["video"] for v in saved["versions"]))
    if not videos:
        return "Nothing is tracked yet. Tell me where you posted a video."
    platforms = _platforms(saved)
    rows = []
    for video in videos[-25:]:
        cells = []
        for p in platforms:
            hit = [v for v in _mine(saved, video) if v["platform"] == p]
            status = max((v["status"] for v in hit), key=STATUSES.index) if hit else ""
            cells.append({"status": status, "say": f"Show the versions of {video}." if hit else f"Log a {p} version of {video}."})
        rows.append({"video": video, "cells": cells})
    return screen.Shown(f"{len(videos)} videos tracked across {len(platforms)} places.",
                        screen.card("repurpose-matrix", "Cross-platform tracker", "repurpose-matrix",
                                    data={"platforms": platforms, "rows": rows}))


def gaps(settings: Settings, args: dict, today: date) -> screen.Shown:
    saved = store.load(settings)
    videos = [store.video(settings, args, saved)] if args.get("video") else list(dict.fromkeys(v["video"] for v in saved["versions"]))
    if not videos:
        raise ValueError("Nothing is tracked yet.")
    platforms, rows = _platforms(saved), []
    for video in videos:
        mine = _mine(saved, video)
        posted = {v["platform"] for v in mine if v["status"] == "posted"}
        planned = {v["platform"] for v in mine if v["status"] != "posted"} - posted
        missing = [p for p in platforms if p not in posted and p not in planned]
        rows.append([video, ", ".join(sorted(posted)) or "-", ", ".join(sorted(planned)) or "-", ", ".join(missing) or "none"])
    return screen.Shown(f"Gaps for {len(videos)} video{'s' if len(videos) != 1 else ''}.",
                        screen.card("table", "Where is it missing?", "repurpose-gaps", columns=["Video", "Posted", "Planned", "Missing"], rows=rows))


def platforms_set(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    given = args.get("platforms")
    given = given.split(",") if isinstance(given, str) else given or []
    saved["platforms"] = list(dict.fromkeys(hs.clean(p, 40) for p in given if hs.clean(p)))[:12]
    store.save(settings, saved)
    return "Tracking " + ", ".join(_platforms(saved)) + "."


def tracker_stats(settings: Settings, args: dict, today: date) -> screen.Shown:
    saved = store.load(settings)
    posted = [v for v in saved["versions"] if v["status"] == "posted"]
    if not posted:
        raise ValueError("No posted versions are tracked yet.")
    videos = {v["video"] for v in posted}
    per = {}
    for v in posted:
        per[v["platform"]] = per.get(v["platform"], 0) + 1
    rows = [[p, str(n)] for p, n in sorted(per.items(), key=lambda x: -x[1])]
    average = len(posted) / len(videos)
    return screen.Shown(f"{len(posted)} posted versions of {len(videos)} videos, {average:.1f} per video.",
                        screen.card("chart", "Versions posted per platform", "repurpose-stats",
                                    chart={"type": "bar", "labels": [r[0] for r in rows], "values": [int(r[1]) for r in rows], "unit": ""}))


def tracker_export(settings: Settings, args: dict, today: date) -> screen.Shown:
    saved = store.load(settings)
    if not saved["versions"]:
        raise ValueError("Nothing is tracked yet.")
    path = store.folder(settings) / "repurpose-tracker.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "video", "platform", "format", "status", "date", "url", "note"])
        for v in saved["versions"]:
            writer.writerow([v["id"], v["video"], v["platform"], v["format"], v["status"], v["date"], v["url"], v["note"]])
    return screen.Shown(f"Exported {len(saved['versions'])} versions to {path.name}.", screen.file_card(settings, path))


# ---- Evergreen -------------------------------------------------------------------------------------

def add_months(day: date, months: int) -> date:
    m = day.month - 1 + months
    year, month = day.year + m // 12, m % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _due(item: dict) -> date:
    return add_months(date.fromisoformat(item["last"]), item["months"])


def evergreen_mark(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    video = store.video(settings, args, saved)
    months = int(hs.number(args.get("months") or 6, "months between re-posts", 1, 36))
    last = store.parse_date(args.get("date"), today)
    if video not in saved["evergreen"] and len(saved["evergreen"]) >= 200:
        raise ValueError("That list is full; remove something first.")
    saved["evergreen"][video] = {"months": months, "last": last, "note": hs.clean(args.get("note"), 150)}
    store.save(settings, saved)
    return f"{video} is evergreen: I'll flag it for a re-post {months} months after {last}, on {_due(saved['evergreen'][video])}."


def _evergreen_rows(saved: dict, today: date) -> list[list[str]]:
    rows = []
    for video, item in sorted(saved["evergreen"].items(), key=lambda kv: _due(kv[1])):
        due = _due(item)
        state = "overdue" if due < today else "due soon" if due <= today + timedelta(days=SOON) else "later"
        rows.append([video, due.isoformat(), state, item["note"] or "-"])
    return rows


def evergreen_list(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    rows = _evergreen_rows(store.load(settings), today)
    if not rows:
        return "No evergreen videos yet."
    return screen.Shown(f"{len(rows)} evergreen video{'s' if len(rows) != 1 else ''}.",
                        screen.card("table", "Evergreen re-posts", "repurpose-evergreen", columns=["Video", "Re-post on", "State", "Note"], rows=rows))


def evergreen_due(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    rows = [r for r in _evergreen_rows(store.load(settings), today) if r[2] != "later"]
    if not rows:
        return "Nothing is due for a re-post in the next two weeks."
    items = [{"label": f"{r[0]}: {r[2]}, {r[1]}", "say": f"I re-posted {r[0]} today."} for r in rows]
    return screen.Shown(f"{len(rows)} to re-post. Tap one once you've done it.",
                        screen.card("list", "Time to re-post", "repurpose-due", items=items))


def evergreen_done(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    key = hs.find(saved["evergreen"], hs.need(args.get("video"), "video", 80))
    if key is None:
        raise ValueError("That isn't marked evergreen.")
    saved["evergreen"][key]["last"] = store.parse_date(args.get("date"), today)
    store.save(settings, saved)
    return f"Noted the re-post of {key}. Next one {_due(saved['evergreen'][key])}."


def evergreen_remove(settings: Settings, args: dict, today: date) -> str:
    saved = store.load(settings)
    key = hs.find(saved["evergreen"], hs.need(args.get("video"), "video", 80))
    if key is None:
        raise ValueError("That isn't marked evergreen.")
    if not args.get("confirmed"):
        return store.confirm_needed(f"the evergreen reminder for {key}")
    del saved["evergreen"][key]
    store.save(settings, saved)
    return f"Removed the evergreen reminder for {key}."


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "repurpose_tracker",
        "description": "Track where each video's versions are posted (typed in by the user; nothing is fetched or "
                       "posted). action: version_log (video, platform, status planned/draft/scheduled/posted, date, "
                       "format, url, note) / version_edit (id, ...) / version_remove (id, confirmed only after yes) / "
                       "video_versions (video); tracker_show = video by platform grid / gaps (video) = where it's "
                       "missing / platforms_set (platforms) / tracker_stats / tracker_export = CSV file; "
                       "evergreen_mark (video, months, date, note) = re-post reminder / evergreen_due / "
                       "evergreen_list / evergreen_done (video, date) / evergreen_remove (video, confirmed only "
                       "after yes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "video": {"type": "string"},
                "platform": {"type": "string"},
                "platforms": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": STATUSES},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday or a weekday."},
                "format": {"type": "string"},
                "url": {"type": "string", "description": "A link the user typed; it is only stored."},
                "note": {"type": "string"},
                "id": {"type": "integer"},
                "months": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"repurpose_tracker"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    found = {"version_log": version_log, "version_edit": version_edit, "version_remove": version_remove,
             "tracker_show": tracker_show, "video_versions": video_versions, "gaps": gaps,
             "platforms_set": platforms_set, "tracker_stats": tracker_stats, "tracker_export": tracker_export,
             "evergreen_mark": evergreen_mark, "evergreen_due": evergreen_due, "evergreen_list": evergreen_list,
             "evergreen_done": evergreen_done, "evergreen_remove": evergreen_remove}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args, today or hs.today())
