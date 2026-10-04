"""Alfred's TikTok studio: he runs several accounts, writes and directs their videos, and posts only what you approve.

- Every morning (from JARVIS_CREATOR_HOUR, 7am by default) he makes each account's videos for the day (3 unless
  you change it), one after another, and tells you when they're waiting for you.
- Each video waits in the studio queue. Nothing posts without a tick: Approve posts it with TikTok's Content
  Posting API (to your TikTok inbox as a draft, or straight to the account; see tiktok.py). Without a connected
  TikTok app, the MP4 and its caption are saved in the Work memory folder, ready to upload by hand.
- An X (reject) marks the video rejected and straight away starts a better replacement for the same account.
- Taste: every tick and X (with the reason, if given) is remembered per account, and each new script or clip pick
  is told what the user liked and disliked, so the videos lean towards what gets ticked while staying fresh.
- Sequels: when a story reaches 50k views Alfred makes part 2, then another part at every 100k more (150k, 250k,
  350k), up to part 5, which ends the series on a shocking cliffhanger. Views are read from TikTok when the
  account is connected with the video.list permission, or you tell Alfred ("that story has 80k views").
"""

import asyncio
import time
from datetime import date, datetime

import httpx

import tiktokstudio_clips as clips
import tiktokstudio_store as cs
import tiktokstudio_video as cv
import screen
import tiktok
import twitch
from config import Settings

CHECK_SECONDS = 300
VIEWS_EVERY = 6 * 3600
FAILS_PER_DAY = 3
LAST_PART = 5
FIRST_SEQUEL_AT = 50_000
SEQUEL_STEP = 100_000
screen.EXTRA_KINDS.add("creator-studio")
_ctx: dict = {"client": None, "http": None, "announce": None, "making": False, "views_at": 0.0, "pending": []}
_tasks: set = set()  # background makes started by an X, kept so they aren't dropped mid-way


def start(settings: Settings, client, http: httpx.AsyncClient, announce) -> asyncio.Task:
    _ctx.update(client=client, http=http, announce=announce)
    return asyncio.create_task(watch(settings))


async def _say(text: str) -> None:
    if _ctx["announce"]:
        await _ctx["announce"](text, "studio")


# ---- sequels ------------------------------------------------------------------------------------------------

def views_needed(part: int) -> int:
    """Views the latest part needs before the next part is made: 50k for part 2, then +100k for each part after."""
    return FIRST_SEQUEL_AT + SEQUEL_STEP * (part - 1)


def series_views(data: dict, first_id: str) -> int:
    return max([v.get("views", 0) for v in data["videos"] if v.get("series_of", v["id"]) == first_id] or [0])


def _is_clips(data: dict, video: dict) -> bool:
    account = cs.find_account(data, video.get("account"))
    return bool(account and account.get("format") == "clips")


def sequels_due(data: dict) -> list[dict]:
    """The latest part of each story whose views have earned the next part (and which isn't made yet)."""
    due = []
    for v in data["videos"]:
        first = v.get("series_of", v["id"])
        part = v.get("part", 1)
        account = cs.find_account(data, v.get("account"))
        if v.get("status") not in ("posted", "approved") or part >= LAST_PART or _is_clips(data, v) or (
                account and account.get("off")):
            continue
        later = [w for w in data["videos"] if w.get("series_of") == first and w.get("part", 1) > part]
        if later:
            continue
        if series_views(data, first) >= views_needed(part):
            due.append(v)
    return due


def sequel_idea(data: dict, latest: dict) -> str:
    first = latest.get("series_of", latest["id"])
    parts = sorted((w for w in data["videos"] if w.get("series_of", w["id"]) == first), key=lambda w: w.get("part", 1))
    so_far = "\n".join(f"Part {w.get('part', 1)} '{w['title']}': {w.get('story', '')}" for w in parts)
    part = latest.get("part", 1) + 1
    ending = ("This is the FINAL part (5 of 5): pay off the story, then end on a shocking cliffhanger twist that "
              "leaves people desperate for more." if part == LAST_PART else
              f"End on a cliffhanger that makes people wait for part {part + 1}.")
    return (f"This is PART {part} of a series people loved. Keep the same characters, setting and voice, and "
            f"start with a one-line 'previously' recap. Put 'Part {part}' in the keyword. {ending}\nThe story so far:\n{so_far}")


# ---- making videos ------------------------------------------------------------------------------------------

def replace_idea(rejected: dict) -> str:
    """The brief for a video made after an X: it replaces the rejected one and must do better."""
    why = f" The user's reason: {rejected['reason']}." if rejected.get("reason") else ""
    hook = f" (hook: {rejected['hook']})" if rejected.get("hook") else ""
    return (f"This video REPLACES '{rejected.get('title')}'{hook}, which the user rejected.{why} Work out what was "
            "weak about it and make something clearly better and different: a stronger hook, a fresher idea and "
            "tighter pacing. Don't reuse its idea.")


async def make_one(settings: Settings, account_name: str, idea: str = "", sequel_of: dict | None = None,
                   replaces: dict | None = None, script: dict | None = None) -> dict:
    data = cs.load(settings)
    account = cs.account(data, account_name)
    if account.get("off"):
        raise ValueError(f"{account['name']} is switched off, so it makes no videos. Say 'switch {account['name']} "
                         "on' once its page is ready.")
    vid = {"id": cs.new_id(), "account": account["name"], "day": date.today().isoformat(), "status": "making",
           "title": "Being made", "made_at": time.strftime("%Y-%m-%d %H:%M"), "part": 1, "views": 0}
    if sequel_of:
        vid["part"] = sequel_of.get("part", 1) + 1
        vid["series_of"] = sequel_of.get("series_of", sequel_of["id"])
        idea = sequel_idea(data, sequel_of)
    if replaces:
        vid["replaces"] = replaces["id"]
        idea = f"{replace_idea(replaces)} {idea}".strip()
    data["videos"].append(vid)
    cs.save(settings, data)
    recent = [v["title"] for v in data["videos"] if v.get("account") == account["name"] and v.get("status") != "making"]
    try:
        folder = cs.work_folder(settings, "TikTok", account["name"])
        if account["format"] == "clips":
            return await _finish(settings, vid["id"], await make_clips(settings, data, account, folder, replaces))
        await ensure_trends(settings, account["name"])
        await ensure_lessons(settings, account["name"])
        account = cs.account(cs.load(settings), account["name"])
        result = await cv.make(_ctx["client"], _ctx["http"], settings, account, folder, idea, recent,
                               best=best_titles(data, account["name"]), taste=cs.taste_summary(account),
                               part=vid["part"], variety=variety_brief(data, account["name"]), script=script)
        fresh = cs.load(settings)  # remember the characters and threads this video added to the account's world
        cs.update_bible(cs.account(fresh, account["name"]), result.get("bible"))
        cs.save(settings, fresh)
        update = {"status": "ready", "title": result["title"], "caption": result["caption"],
                  "hashtags": result["hashtags"], "keyword": result["keyword"], "hook": result.get("hook", ""),
                  "notes": f"{account['style']} look" + (f", series {result['series']}" if result.get("series") else "")
                  + (f", editor's score {result['score']}/10" if result.get("score") else "")
                  + (f". Check before posting: {'; '.join(result['checks'])}" if result.get("checks") else ""),
                  "checks": result.get("checks", []),
                  "file": cs.relative(settings, result["path"]), "mood": result.get("mood", ""),
                  "score": result.get("score", 0), "hook_score": result.get("hook_score", 0), "retention": result.get("retention", 0),
                  "scenes": len(result["scenes"]), "pinned_comment": result.get("pinned_comment", ""),
                  "sound": result.get("sound", ""),
                  "story": " ".join(s["narration"] for s in result["scenes"])[:1500]}
    except Exception as exc:  # the network, the API or ffmpeg let us down; say so and carry on
        print(f"[jarvis] Studio video failed: {exc}", flush=True)
        update = {"status": "failed", "error": str(exc)[:300]}
    return await _finish(settings, vid["id"], update)


MAX_DRAFTS = 10


async def draft_script(settings: Settings, account_name: str, idea: str = "") -> str:
    """Write a script without filming it, so the user can read it first: filming (pictures, voices, ffmpeg) is the
    slow part, and a weak story is cheaper to catch here. make_video with the draft films it exactly as written."""
    data = cs.load(settings)
    account = cs.account(data, account_name)
    if account["format"] == "clips":
        raise ValueError(f"{account['name']} posts stream clips, so there's no script to write.")
    await ensure_trends(settings, account["name"])
    await ensure_lessons(settings, account["name"])
    data = cs.load(settings)
    account = cs.account(data, account["name"])
    recent = [v["title"] for v in data["videos"] if v.get("account") == account["name"] and v.get("status") != "making"]
    script = await cv.write_script(_ctx["client"], settings, account, cs.clean(idea, 500), recent,
                                   best_titles(data, account["name"]), cs.taste_summary(account),
                                   variety_brief(data, account["name"]))
    draft = {"id": cs.new_id(), "account": account["name"], "made_at": time.strftime("%Y-%m-%d %H:%M"), "script": script}
    data["drafts"] = [*data.get("drafts", []), draft][-MAX_DRAFTS:]
    cs.save(settings, data)
    return preview(draft)


def preview(draft: dict) -> str:
    """A draft script as the user reads it: the scores, the opening, then each scene with how it's filmed."""
    sc = draft["script"]
    scores = ", ".join(f"{k} {sc[key]}/10" for k, key in (("editor", "score"), ("hook", "hook_score"),
                                                           ("retention", "retention")) if sc.get(key))
    lines = [f"Draft {draft['id']} for {draft['account']}: \"{sc['title']}\"" + (f" ({scores})" if scores else ""),
             f"Cover: {sc.get('cover') or '-'}. Mood: {sc.get('mood') or '-'}."]
    for i, scene in enumerate(sc["scenes"], 1):
        how = [scene.get("pace", "normal")]
        if scene.get("speaker", "narrator") != "narrator":
            how.append(f"voice: {scene['speaker']}")
        if scene.get("hit"):
            how.append(f"sound: {scene['hit']}")
        lines.append(f"{i}. [{', '.join(how)}] {scene['narration']}")
    lines.append("Say 'film it' to make this video, or ask for another draft.")
    return "\n".join(lines)


def find_draft(data: dict, which: str) -> dict:
    drafts = data.get("drafts", [])
    if not drafts:
        raise ValueError("There are no draft scripts; ask for one first.")
    which = str(which or "latest").strip().lower()
    if which in ("latest", "last", "it", "that"):
        return drafts[-1]
    for d in reversed(drafts):
        if d["id"] == which or which in d["script"]["title"].lower() or which == d["account"].lower():
            return d
    raise ValueError(f"I can't find a draft called {which}.")


def variety_brief(data: dict, name: str, count: int = 3) -> str:
    """The account's last few finished videos in a line each (mood, opening line, how the story starts), so the next
    one is written to feel different instead of repeating the same mood and opening every day."""
    done = [v for v in data.get("videos", []) if v.get("account") == name and v.get("status") in ("ready", "approved", "posted")]
    lines = []
    for v in done[-count:]:
        bits = [f'"{v.get("title", "")}"']
        if v.get("mood"):
            bits.append(f"mood {v['mood']}")
        if v.get("hook"):
            bits.append(f'opened with "{v["hook"][:120]}"')
        if v.get("story"):
            bits.append(f'began: {v["story"][:140]}')
        lines.append(", ".join(bits))
    return " | ".join(lines)


async def _finish(settings: Settings, video_id: str, update: dict) -> dict:
    data = cs.load(settings)
    vid = {}
    for v in data["videos"]:
        if v["id"] == video_id:
            v.update(update)
            vid = v
    cs.save(settings, data)
    return vid


async def make_clips(settings: Settings, data: dict, account: dict, folder, replaces: dict | None = None) -> dict:
    """A clip video: new viral clips and old viral ones take turns through the day."""
    era = "new" if cs.made_today(data, account["name"]) % 2 else "old"
    try:
        result = await clips.make(_ctx["http"], settings, account, folder, era, _ctx["client"], replaces)
    except Exception as exc:
        print(f"[jarvis] Clip video failed: {exc}", flush=True)
        return {"status": "failed", "error": str(exc)[:300]}
    fresh = cs.load(settings)
    a = cs.account(fresh, account["name"])
    a["used_clips"] = (a.get("used_clips") or [])[-clips.MAX_USED:] + result["clip_ids"]
    cs.save(settings, fresh)
    return {"status": "ready", "title": result["title"], "caption": result["caption"], "hashtags": result["hashtags"],
            "keyword": era, "file": cs.relative(settings, result["path"]), "story": "",
            "hook": result.get("hook", ""), "clip_ids": result["clip_ids"], "checks": result.get("checks", []),
            "notes": result.get("notes", "")
            + (f". Check before posting: {'; '.join(result['checks'])}" if result.get("checks") else "")}


def best_titles(data: dict, account: str, n: int = 5) -> list[str]:
    """This account's most-viewed videos, e.g. 'The Last Voicemail (82,000 views)'."""
    seen = sorted((v for v in data["videos"] if v.get("account") == account and v.get("views")),
                  key=lambda v: v["views"], reverse=True)[:n]
    return [f"{v['title']} ({v['views']:,} views)" for v in seen]


async def ensure_trends(settings: Settings, account_name: str, force: bool = False) -> dict:
    """Check this week's TikTok trends for the account once a day (before its first video); keep the brief."""
    data = cs.load(settings)
    account = cs.account(data, account_name)
    trends = account.get("trends") or {}
    if not force and trends.get("day") == date.today().isoformat():
        return trends
    try:
        brief = await cv.research_trends(_ctx["client"], settings, account)
    except Exception as exc:  # no web search today: the videos still get made from what works
        print(f"[jarvis] Trends for {account_name}: {exc}", flush=True)
        return trends
    if brief:
        data = cs.load(settings)
        account = cs.account(data, account_name)
        account["trends"] = trends = {"day": date.today().isoformat(), "brief": brief}
        cs.save(settings, data)
    return trends


LESSONS_AFTER = 4  # videos with views before there's anything to learn


def viewed(data: dict, account: str) -> list[dict]:
    return [v for v in data["videos"] if v.get("account") == account and v.get("views")]


async def ensure_lessons(settings: Settings, account_name: str, force: bool = False) -> dict:
    """Once a day, work out from this account's view counts what its best videos share; the writer follows it."""
    data = cs.load(settings)
    account = cs.account(data, account_name)
    lessons = account.get("lessons") or {}
    videos = viewed(data, account["name"])
    if len(videos) < LESSONS_AFTER or (not force and lessons.get("day") == date.today().isoformat()):
        return lessons
    try:
        brief = await cv.learn_lessons(_ctx["client"], settings, account, videos)
    except Exception as exc:  # no lessons today: the writer still has the trends and the best titles
        print(f"[jarvis] Lessons for {account_name}: {exc}", flush=True)
        return lessons
    if brief:
        data = cs.load(settings)
        account = cs.account(data, account_name)
        account["lessons"] = lessons = {"day": date.today().isoformat(), "brief": brief, "videos": len(videos)}
        cs.save(settings, data)
    return lessons


async def make_in_background(settings: Settings, jobs: list[tuple]) -> None:
    """Make the jobs one after another: (account, idea, sequel_of[, replaces]). Jobs that arrive while a video is
    being made wait their turn."""
    _ctx["pending"].extend(jobs)
    if _ctx["making"]:
        return
    _ctx["making"] = True
    made = []
    try:
        while _ctx["pending"]:
            made.append(await make_one(settings, *_ctx["pending"].pop(0)))
    finally:
        _ctx["making"] = False
        _ctx["pending"].clear()
    ready = [v for v in made if v["status"] == "ready"]
    if ready:
        names = ", ".join(f"{v['title']}" + (f" (part {v['part']})" if v.get("part", 1) > 1 else "") for v in ready)
        await _say(f"{len(ready)} new TikTok video{'s' if len(ready) != 1 else ''} ready for you to approve: {names}.")
    elif made:
        await _say(f"I couldn't finish the TikTok video: {made[-1].get('error', 'something went wrong')}.")


def clips_blocked(settings: Settings, account: dict) -> str:
    """Why a clip account can't make videos yet ('' when it can): no streamer has allowed clipping, or only Twitch
    streamers have and there are no Twitch keys. Kick needs no keys."""
    if not cs.allowed(account):
        return (f"{account['name']} has no streamers who allow clipping yet; tell Alfred who does "
                "(e.g. 'add xqc on Kick to Clipzz, he allows clipping').")
    if not cs.allowed(account, "kick") and not twitch.configured(settings):
        return twitch.setup_line()
    return ""


def todays_jobs(settings: Settings, data: dict, today: date) -> list[tuple[str, str, None]]:
    jobs = []
    for a in data["accounts"]:
        if a.get("off"):
            continue  # switched off until the user sets that page up
        fails = sum(1 for v in data["videos"] if v.get("account") == a["name"] and v.get("day") == today.isoformat()
                    and v.get("status") == "failed")
        missing = a.get("per_day", 3) - cs.made_today(data, a["name"], today)
        if a.get("format") == "clips" and clips_blocked(settings, a):
            continue  # nothing to find clips with yet; the studio card says what's needed
        if fails < FAILS_PER_DAY:
            jobs += [(a["name"], "", None)] * max(0, missing)
    return jobs


async def refresh_views(settings: Settings) -> None:
    """Read view counts for posted videos from TikTok (accounts connected with the video.list permission)."""
    data = cs.load(settings)
    changed = False
    for a in data["accounts"]:
        if not tiktok.connected(settings, a["name"]):
            continue
        try:
            found = await tiktok.video_views(_ctx["http"], settings, a["name"])
        except Exception as exc:
            print(f"[jarvis] TikTok views for {a['name']}: {exc}", flush=True)
            continue
        for v in data["videos"]:
            if v.get("account") != a["name"] or v.get("status") != "posted":
                continue
            views = tiktok.match_views(found, v)
            if views is not None and views != v.get("views"):
                v["views"], changed = views, True
    if changed:
        cs.save(settings, data)


async def watch(settings: Settings) -> None:
    """Make the day's videos and any sequels that views have earned."""
    await asyncio.sleep(20)
    while True:
        try:
            if settings.creator_daily and datetime.now().hour >= settings.creator_hour and not _ctx["making"]:
                if time.time() - _ctx["views_at"] > VIEWS_EVERY:
                    _ctx["views_at"] = time.time()
                    await refresh_views(settings)
                data = cs.load(settings)
                jobs = [] if data.get("paused") else [(v["account"], "", v) for v in sequels_due(data)] + todays_jobs(settings, data, date.today())
                if jobs:
                    await make_in_background(settings, jobs)
        except Exception as exc:
            print(f"[jarvis] Studio: {exc}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


# ---- approving and posting ----------------------------------------------------------------------------------

async def approve(settings: Settings, ref: str) -> str:
    data = cs.load(settings)
    v = cs.find_video(data, ref, waiting=True)
    can_post = tiktok.configured(settings) and tiktok.connected(settings, v["account"])
    if v.get("status") not in cs.WAITING and not (v.get("status") == "approved" and can_post):
        raise ValueError(f"'{v.get('title')}' is {v.get('status')}, so there's nothing to approve.")
    account = cs.find_account(data, v["account"])
    if account and not v.get("liked"):  # a tick teaches Alfred what the user likes
        v["liked"] = True
        cs.remember(account, v, True)
    path = screen.memory_path(settings, v["file"])
    caption = f"{v.get('caption', '')}\n\n" + " ".join(f"#{t}" for t in v.get("hashtags", []))
    if can_post:
        try:
            sent = await tiktok.post(_ctx["http"] or httpx.AsyncClient(timeout=60), settings, v["account"], path, caption.strip())
        except ValueError as exc:
            v["status"], v["error"] = "failed_post", str(exc)[:300]
            cs.save(settings, data)
            raise
        v.update(status="posted", publish_id=sent["publish_id"], mode=sent["mode"], posted_at=time.strftime("%Y-%m-%d %H:%M"))
        cs.save(settings, data)
        if sent["mode"] == "draft":
            return (f"Sent '{v['title']}' to {v['account']}'s TikTok inbox. Open TikTok, tap the notification, "
                    "tick AI-generated content and press Post.")
        return f"Posted '{v['title']}' to {v['account']} on TikTok."
    v.update(status="approved", posted_at=time.strftime("%Y-%m-%d %H:%M"))
    cs.save(settings, data)
    return (f"Approved '{v['title']}'. It's saved in {path.parent.name} with its caption, ready to upload to "
            f"{v['account']} by hand. {tiktok.setup_line()}")


async def reject(settings: Settings, ref: str, reason: str = "") -> str:
    """An X: the video is rejected (never posted), remembered as a dislike, and a better one is started at once."""
    data = cs.load(settings)
    v = cs.find_video(data, ref, waiting=True)
    if v.get("status") not in cs.WAITING:
        raise ValueError(f"'{v.get('title')}' is {v.get('status')}, so there's nothing to reject.")
    reason = cs.clean(reason, 300)
    v.update(status="rejected", reason=reason, rejected_at=time.strftime("%Y-%m-%d %H:%M"))
    account = cs.find_account(data, v["account"])
    if account:
        cs.remember(account, v, False, reason)
    cs.save(settings, data)
    said = f"Rejected '{v['title']}'; it won't be posted and the file stays in the folder."
    if data.get("paused"):
        return said + " Content making is paused, so I won't make a replacement until you say resume."
    if account is None or _ctx["client"] is None:
        return said + " I can't start a replacement until the studio is running; restart Alfred."
    task = asyncio.create_task(make_in_background(settings, [(account["name"], "", None, dict(v))]))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return said + f" I'm already making a better one for {account['name']}; I'll tell you when it's ready."


skip = reject  # the old Skip button and "skip that one" mean an X now


def set_views(settings: Settings, ref: str, views) -> str:
    data = cs.load(settings)
    v = cs.find_video(data, ref)
    v["views"] = max(0, int(float(str(views).lower().replace(",", "").replace("k", "e3").replace("m", "e6"))))
    if v.get("status") == "ready":
        v["status"] = "approved"  # it's clearly out there
    cs.save(settings, data)
    part = v.get("part", 1)
    need = views_needed(part)
    if part >= LAST_PART:
        return f"Noted {v['views']:,} views. That was the final part."
    if series_views(data, v.get("series_of", v["id"])) >= need:
        return f"Noted {v['views']:,} views on '{v['title']}'. That earns part {part + 1}; I'll make it shortly."
    return f"Noted {v['views']:,} views. Part {part + 1} comes at {need:,}."


# ---- the studio card ---------------------------------------------------------------------------------------

def set_paused(settings: Settings, paused: bool) -> str:
    """Pause or resume all content making: no daily videos, sequels or replacements while paused."""
    data = cs.load(settings)
    data["paused"] = paused
    cs.save(settings, data)
    if not paused:
        return "Content making is back on. The daily videos pick up from the next check."
    dropped = len(_ctx["pending"])
    _ctx["pending"].clear()
    return ("Content making is paused: no new videos, sequels or replacements until you say resume."
            + (" The one I'm making now will finish." if _ctx["making"] else "")
            + (f" I dropped {dropped} waiting in line." if dropped else "")
            + " Videos already waiting for approval stay there.")


def studio_card(settings: Settings, data: dict, focus: str = "") -> dict:
    live = [v for v in data["videos"] if v.get("status") in ("making", "ready", "failed_post", "failed")]
    done = [v for v in data["videos"] if v.get("status") in ("posted", "approved", "rejected")][-8:]
    videos = []
    for v in (live + done)[-30:]:
        row = {k: v.get(k) for k in ("id", "account", "title", "status", "part", "views", "caption", "error", "mode",
                                     "score", "hook_score", "mood", "sound", "pinned_comment")}
        row["hashtags"] = " ".join(f"#{t}" for t in v.get("hashtags", []))
        if v.get("file"):
            row["src"] = f"/screen/file?path={screen.quote(v['file'])}"
        videos.append(row)
    accounts = [{"name": a["name"], "style": a["style"], "format": a["format"], "per_day": a.get("per_day", 3),
                 "off": bool(a.get("off")),
                 "theme": a["theme"], "connected": tiktok.connected(settings, a["name"]),
                 "lessons": bool((a.get("lessons") or {}).get("brief"))} for a in data["accounts"]]
    return screen.card("creator-studio", "TikTok studio", "creator-studio",
                       buttons=[{"label": "Make one now", "say": "Make a TikTok video now."}],
                       data={"accounts": accounts, "videos": videos, "configured": tiktok.configured(settings),
                             "setup": " ".join([tiktok.setup_line(), *dict.fromkeys(
                                 filter(None, (clips_blocked(settings, a) for a in data["accounts"] if a["format"] == "clips")))]),
                             "focus": focus, "making": _ctx["making"], "paused": bool(data.get("paused"))})


def queue(settings: Settings) -> list[dict]:
    """The videos waiting for a tick or an X, oldest first, for the HUD: each with a URL the browser can play."""
    data = cs.load(settings)
    rows = []
    for v in data["videos"]:
        if v.get("status") not in cs.WAITING or not v.get("file"):
            continue
        cover = str(v["file"]).rsplit(".", 1)[0] + ".png"
        try:
            has_cover = screen.memory_path(settings, cover).is_file()
        except ValueError:
            has_cover = False
        rows.append({"id": v["id"], "account": v["account"], "title": v.get("title", ""),
                     "kind": "clip" if _is_clips(data, v) else "story", "created": v.get("made_at") or v.get("day"),
                     "video_url": f"/screen/file?path={screen.quote(v['file'])}",
                     "thumb_url": f"/screen/file?path={screen.quote(cover)}" if has_cover else None})
    return rows


def studio(settings: Settings) -> screen.Shown:
    data = cs.load(settings)
    waiting = sum(1 for v in data["videos"] if v.get("status") == "ready")
    said = (f"{waiting} video{'s' if waiting != 1 else ''} waiting for your approval." if waiting else
            "Nothing is waiting for approval right now.")
    return screen.Shown(said + (" I'm making one now." if _ctx["making"] else ""), studio_card(settings, data))


# ---- accounts ----------------------------------------------------------------------------------------------

FIELDS = ("theme", "style", "format", "series", "per_day", "voice", "accent", "streamers", "category", "min_views", "extend",
          "off")


def add_account(settings: Settings, args: dict) -> str:
    data = cs.load(settings)
    if len(data["accounts"]) >= cs.MAX_ACCOUNTS:
        raise ValueError("That's the most accounts Alfred can run.")
    if cs.find_account(data, args.get("account")) and cs.find_account(data, args.get("account"))["name"].lower() == cs.clean(args.get("account")).lstrip("@").lower():
        raise ValueError("There's already an account with that name.")
    a = cs.new_account(args.get("account"), **{k: args.get(k) for k in FIELDS if args.get(k) is not None})
    data["accounts"].append(a)
    cs.save(settings, data)
    return (f"Added {a['name']}: {a['theme']}, in the {a['style']} look, {a['per_day']} videos a day. "
            "Connect it to TikTok from the studio card when you're ready.")


def update_account(settings: Settings, args: dict) -> str:
    data = cs.load(settings)
    a = cs.account(data, args.get("account"))
    fresh = cs.new_account(cs.clean(args.get("new_name")) or a["name"], used_clips=a.get("used_clips"), taste=a.get("taste"),
                           **{k: args.get(k) if args.get(k) is not None else a.get(k) for k in FIELDS})
    old = a["name"]
    a.update(fresh)
    if old != a["name"]:
        for v in data["videos"]:
            if v.get("account") == old:
                v["account"] = a["name"]
        tokens = tiktok.tokens(settings)
        if old in tokens:
            tokens[a["name"]] = tokens.pop(old)
            tiktok.save_tokens(settings, tokens)
    cs.save(settings, data)
    return (f"Updated {a['name']}: {a['theme']}; {a['style']} look; {a['per_day']} a day"
            + ("; switched off, so it makes no videos." if a.get("off") else "."))


def remove_account(settings: Settings, args: dict) -> str:
    data = cs.load(settings)
    a = cs.account(data, args.get("account"))
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {a['name']} (its videos stay in the folder), then call again with confirmed."
    data["accounts"].remove(a)
    cs.save(settings, data)
    tiktok.disconnect(settings, a["name"])
    return f"Removed {a['name']}. Its videos are still in the folder."


def name_ideas(args: dict) -> str:
    theme = cs.clean(args.get("theme"), 300) or "short AI story videos"
    return (f"INSTRUCTION for Alfred: suggest 10 flashy, current, Gen Z style TikTok account names for: {theme}. "
            "Think lower case with a dot or underscore (like lowkey.lore, mindglitch.fyi, karma.receipts), slang "
            "that's current, short, easy to say and to search, 20 characters or fewer, no real brands or people. "
            "Show them on screen as a list with show_on_screen, each with a four-word vibe, and say your top pick "
            "aloud. Remind the user to check the name is free on TikTok.")


async def profile_kit(settings: Settings, http: httpx.AsyncClient, args: dict) -> screen.Shown:
    """A profile picture made in the account's look, plus a bio for Alfred to write."""
    account = cs.account(cs.load(settings), args.get("account"))
    picture = await cv.fetch_picture(http, f"a striking, simple profile picture icon for a TikTok account about "
                                           f"{account['theme']}", account["style"], 7, (1024, 1024))
    if picture is None:
        raise ValueError("I couldn't make the profile picture just now; try again in a minute.")
    path = cs.work_folder(settings, "TikTok", account["name"]) / "Profile picture.png"
    await asyncio.to_thread(picture.save, path)
    said = (f"Profile picture for {account['name']} saved in its folder. INSTRUCTION for Alfred: also write a TikTok "
            f"bio for {account['name']} ({account['theme']}): under 80 characters, one emoji, a reason to follow "
            "and a line that invites comments. Show it with show_on_screen as text and read it aloud.")
    return screen.Shown(said, screen.file_card(settings, path))


# ---- the tool ---------------------------------------------------------------------------------------------

ACTIONS = ["studio", "make_video", "approve", "reject", "skip", "pause", "resume", "set_views", "accounts", "add_account", "update_account",
           "remove_account", "name_ideas", "profile_kit", "trends", "connect", "setup", "bible", "lessons",
           "draft_script"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "tiktok_studio",
        "description": "Alfred's TikTok studio: he runs several TikTok accounts, each with its own theme and look, "
                       "and writes and directs their videos himself (script, AI pictures, voice, 1 minute or longer). "
                       "Each day it makes every account's videos (3 each by default) and queues them; nothing posts "
                       "until the user ticks it. studio shows the queue with play, a tick (approve) and an X "
                       "(reject). make_video (account, optional idea) starts one now in the background. approve "
                       "(video) posts it: 'post that one', 'tick it', 'I like the lowkey.lore video'. reject (video, "
                       "optional reason) is the X: 'reject that one', 'X it', 'no', 'I don't like the lowkey.lore "
                       "video' (video: lowkey.lore), 'that clip is boring' (reason: boring); it never posts, Alfred "
                       "learns from it and at once makes a better replacement for the same account. skip means "
                       "reject. pause stops all content making (no daily videos, sequels or replacements): 'pause "
                       "making content', 'stop making videos'; resume turns it back on. Every tick and X is remembered per account and steers the next videos. video is an "
                       "id, part of a title, an account name, or 'latest' (the newest waiting video). set_views (video, views e.g. 80k) records views: 50k earns part 2, then every "
                       "100k more another part up to part 5, which ends on a shocking cliffhanger. accounts lists "
                       "them. add_account (account name, theme, style noir/explainer/drama/cinematic, format "
                       "story/facts/clips, series, per_day, voice e.g. en-GB-RyanNeural, accent colour; clip accounts: "
                       "streamers, category, min_views, extend). Clip accounts like Clipzz post viral Twitch or Kick "
                       "clips, old and new, filling the phone screen, a minute or more, the streamer credited, and "
                       "only from streamers who allow clipping (allows_clipping). n3on.vault is N3on's clip page "
                       "(Kick, and Twitch when set up): clips with 100k+ views, each extended by about 30 seconds "
                       "before and after from the stream. update_account "
                       "(account, new_name or any field; off true switches an account off so it makes no videos at "
                       "all, off false switches it back on: 'switch karma.receipts on'). Only lowkey.lore is on "
                       "until the user sets the other pages up. remove_account (account, confirmed). name_ideas (theme) for "
                       "flashy Gen Z account names. profile_kit (account) makes a profile picture and a bio. trends (account, refresh) shows this "
                       "week's TikTok trends for its niche (checked daily before the first video and used in every "
                       "script, with the account's best-performing videos) so you can plan what to post next. connect (account) gives the TikTok login link. setup explains "
                       "what auto-posting needs. bible (account) shows the account's story bible: its recurring "
                       "characters (with their fixed looks), world and open story threads, which every new video "
                       "builds on so series stay consistent. lessons (account, refresh) shows what the account's view "
                       "counts say works (what its best videos share), learnt daily once 4 videos have views and "
                       "followed by every new script.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "Account name, e.g. lowkey.lore."},
                "idea": {"type": "string", "description": "make_video or draft_script: a story idea or topic to use."},
                "draft": {"type": "string", "description": "make_video: film this draft script (its id, title, or "
                          "'latest') instead of writing a new one. draft_script writes a script to read before "
                          "filming, which saves the slow part when the story isn't right."},
                "video": {"type": "string", "description": "Video id, part of its title, its account, or 'latest'."},
                "reason": {"type": "string", "description": "reject: what the user didn't like, in their words."},
                "views": {"type": "string", "description": "set_views: e.g. 80000 or 80k."},
                "new_name": {"type": "string"},
                "theme": {"type": "string"},
                "style": {"type": "string", "enum": list(cs.STYLES)},
                "format": {"type": "string", "enum": list(cs.FORMATS)},
                "series": {"type": "array", "items": {"type": "string"}},
                "per_day": {"type": "integer", "description": "Videos a day for this account, 0 to 6."},
                "voice": {"type": "string", "description": "A Microsoft neural voice, e.g. en-US-AndrewNeural."},
                "accent": {"type": "string", "description": "Keyword colour for the explainer look, e.g. #ff4d6d."},
                "streamers": {"type": "array", "description": "Clip accounts: the streamers to clip (the full list). "
                              "Set allows_clipping true only when the user says that streamer allows clipping; "
                              "Alfred never clips anyone without it.",
                              "items": {"type": "object", "properties": {
                                  "name": {"type": "string"}, "platform": {"type": "string", "enum": list(cs.PLATFORMS)},
                                  "allows_clipping": {"type": "boolean"}}, "required": ["name"]}},
                "category": {"type": "string", "description": "Clip accounts: Twitch category, e.g. Just Chatting."},
                "min_views": {"type": "integer", "description": "Clip accounts: only clips with at least this many views."},
                "extend": {"type": "integer", "description": "Clip accounts: seconds of the stream added before and after each clip (0 = plain clips)."},
                "off": {"type": "boolean", "description": "update_account: true switches the account off (no videos), false back on."},
                "confirmed": {"type": "boolean"},
                "refresh": {"type": "boolean", "description": "trends or lessons: check again now."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"tiktok_studio"}


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if http is not None and _ctx["http"] is None:
        _ctx["http"] = http
    if action == "studio":
        return studio(settings)
    if action == "draft_script":
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        return await draft_script(settings, args.get("account"), args.get("idea") or "")
    if action == "make_video" and args.get("draft"):
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        data = cs.load(settings)
        draft = find_draft(data, args["draft"])
        data["drafts"] = [d for d in data["drafts"] if d["id"] != draft["id"]]
        cs.save(settings, data)
        job = (draft["account"], "", None, None, draft["script"])
        if _ctx["making"]:
            _ctx["pending"].append(job)
            return f"I'm making another video right now; \"{draft['script']['title']}\" is next in line."
        asyncio.create_task(make_in_background(settings, [job]))
        return f"Filming \"{draft['script']['title']}\" now, exactly as drafted. I'll tell you when it's ready to approve."
    if action == "make_video":
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        data = cs.load(settings)
        account = cs.account(data, args.get("account"))
        if _ctx["making"]:
            _ctx["pending"].append((account["name"], cs.clean(args.get("idea"), 500), None))
            return f"I'm making another video right now; {account['name']}'s is next in line."
        asyncio.create_task(make_in_background(settings, [(account["name"], cs.clean(args.get("idea"), 500), None)]))
        return (f"I'm writing and directing a new video for {account['name']} now. It takes a few minutes; "
                "I'll tell you when it's ready to approve.")
    if action in ("pause", "resume"):
        return set_paused(settings, action == "pause")
    if action == "approve":
        return await approve(settings, args.get("video") or args.get("account"))
    if action in ("reject", "skip"):
        return await reject(settings, args.get("video") or args.get("account"), args.get("reason") or "")
    if action == "set_views":
        return set_views(settings, args.get("video"), args.get("views") or 0)
    if action == "accounts":
        data = cs.load(settings)
        rows = [[a["name"], a["style"], a["format"], "off" if a.get("off") else str(a.get("per_day", 3)),
                 "yes" if tiktok.connected(settings, a["name"]) else "no"] for a in data["accounts"]]
        return screen.Shown(f"Alfred runs {len(rows)} account{'s' if len(rows) != 1 else ''}: "
                            + ", ".join(r[0] for r in rows) + ".",
                            screen.card("table", "TikTok accounts", "creator-accounts",
                                        columns=["Account", "Look", "Format", "A day", "Connected"], rows=rows))
    if action == "add_account":
        return add_account(settings, args)
    if action == "update_account":
        return update_account(settings, args)
    if action == "remove_account":
        return remove_account(settings, args)
    if action == "name_ideas":
        return name_ideas(args)
    if action == "trends":
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        account = cs.account(cs.load(settings), args.get("account"))
        trends = await ensure_trends(settings, account["name"], force=bool(args.get("refresh")))
        best = best_titles(cs.load(settings), account["name"])
        text = (trends.get("brief") or "I couldn't check the trends just now.") + (
            "\n\nBest so far: " + "; ".join(best) if best else "")
        return screen.Shown(f"This week's trends for {account['name']}. INSTRUCTION for Alfred: sum them up in two "
                            "sentences and suggest the next three video ideas.",
                            screen.card("text", f"Trends: @{account['name']}", f"creator-trends-{account['name']}",
                                        text=text, buttons=[{"label": "Make one from this",
                                                             "say": f"Make a TikTok video now for {account['name']} using this week's trends."}]))
    if action == "lessons":
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        account = cs.account(cs.load(settings), args.get("account"))
        lessons = await ensure_lessons(settings, account["name"], force=bool(args.get("refresh")))
        have = len(viewed(cs.load(settings), account["name"]))
        text = lessons.get("brief") or (f"Only {have} of {account['name']}'s videos have view counts so far. I start "
                                        f"learning from them at {LESSONS_AFTER}.")
        return screen.Shown(f"What's working on {account['name']}. INSTRUCTION for Alfred: sum it up in two sentences.",
                            screen.card("text", f"What's working: @{account['name']}", f"creator-lessons-{account['name']}",
                                        text=text))
    if action == "bible":
        account = cs.account(cs.load(settings), args.get("account"))
        text = cs.bible_summary(account)
        return screen.Shown(f"The story bible for {account['name']}. INSTRUCTION for Alfred: sum it up in two sentences.",
                            screen.card("text", f"Story bible: @{account['name']}", f"creator-bible-{account['name']}", text=text))
    if action == "profile_kit":
        return await profile_kit(settings, _ctx["http"] or http, args)
    if action == "connect":
        account = cs.account(cs.load(settings), args.get("account"))
        if not tiktok.configured(settings):
            return tiktok.setup_line()
        return (f"Tell the user to press Connect beside {account['name']} on the TikTok studio card and log in to "
                "that TikTok account.")
    if action == "setup":
        return tiktok.setup_line() + (" It's set up." if tiktok.configured(settings) else "")
    raise ValueError(f"Unknown studio action: {action}")
