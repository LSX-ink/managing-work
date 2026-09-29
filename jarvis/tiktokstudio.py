"""Alfred's TikTok studio: he runs several accounts, writes and directs their videos, and posts only what you approve.

- Every morning (from JARVIS_CREATOR_HOUR, 7am by default) he makes each account's videos for the day (3 unless
  you change it), one after another, and tells you when they're waiting for you.
- Each video waits in the studio queue. One tap on Approve posts it with TikTok's Content Posting API (to your
  TikTok inbox as a draft, or straight to the account; see tiktok.py). Without a connected TikTok app, the MP4
  and its caption are saved in the Work memory folder, ready to upload by hand.
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
_ctx: dict = {"client": None, "http": None, "announce": None, "making": False, "views_at": 0.0}


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
        if v.get("status") not in ("posted", "approved") or part >= LAST_PART or _is_clips(data, v):
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

async def make_one(settings: Settings, account_name: str, idea: str = "", sequel_of: dict | None = None) -> dict:
    data = cs.load(settings)
    account = cs.account(data, account_name)
    vid = {"id": cs.new_id(), "account": account["name"], "day": date.today().isoformat(), "status": "making",
           "title": "Being made", "made_at": time.strftime("%Y-%m-%d %H:%M"), "part": 1, "views": 0}
    if sequel_of:
        vid["part"] = sequel_of.get("part", 1) + 1
        vid["series_of"] = sequel_of.get("series_of", sequel_of["id"])
        idea = sequel_idea(data, sequel_of)
    data["videos"].append(vid)
    cs.save(settings, data)
    recent = [v["title"] for v in data["videos"] if v.get("account") == account["name"] and v.get("status") != "making"]
    try:
        folder = cs.work_folder(settings, "TikTok", account["name"])
        if account["format"] == "clips":
            return await _finish(settings, vid["id"], await make_clips(settings, data, account, folder))
        await ensure_trends(settings, account["name"])
        account = cs.account(cs.load(settings), account["name"])
        result = await cv.make(_ctx["client"], _ctx["http"], settings, account, folder, idea, recent,
                               best=best_titles(data, account["name"]))
        update = {"status": "ready", "title": result["title"], "caption": result["caption"],
                  "hashtags": result["hashtags"], "keyword": result["keyword"],
                  "file": cs.relative(settings, result["path"]),
                  "story": " ".join(s["narration"] for s in result["scenes"])[:1500]}
    except Exception as exc:  # the network, the API or ffmpeg let us down; say so and carry on
        print(f"[jarvis] Studio video failed: {exc}", flush=True)
        update = {"status": "failed", "error": str(exc)[:300]}
    return await _finish(settings, vid["id"], update)


async def _finish(settings: Settings, video_id: str, update: dict) -> dict:
    data = cs.load(settings)
    vid = {}
    for v in data["videos"]:
        if v["id"] == video_id:
            v.update(update)
            vid = v
    cs.save(settings, data)
    return vid


async def make_clips(settings: Settings, data: dict, account: dict, folder) -> dict:
    """A clip video: new viral clips and old viral ones take turns through the day."""
    era = "new" if cs.made_today(data, account["name"]) % 2 else "old"
    try:
        result = await clips.make(_ctx["http"], settings, account, folder, era)
    except Exception as exc:
        print(f"[jarvis] Clip video failed: {exc}", flush=True)
        return {"status": "failed", "error": str(exc)[:300]}
    fresh = cs.load(settings)
    a = cs.account(fresh, account["name"])
    a["used_clips"] = (a.get("used_clips") or [])[-clips.MAX_USED:] + result["clip_ids"]
    cs.save(settings, fresh)
    return {"status": "ready", "title": result["title"], "caption": result["caption"], "hashtags": result["hashtags"],
            "keyword": era, "file": cs.relative(settings, result["path"]), "story": ""}


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


async def make_in_background(settings: Settings, jobs: list[tuple[str, str, dict | None]]) -> None:
    if _ctx["making"]:
        return
    _ctx["making"] = True
    made = []
    try:
        for account, idea, sequel in jobs:
            made.append(await make_one(settings, account, idea, sequel))
    finally:
        _ctx["making"] = False
    ready = [v for v in made if v["status"] == "ready"]
    if ready:
        names = ", ".join(f"{v['title']}" + (f" (part {v['part']})" if v.get("part", 1) > 1 else "") for v in ready)
        await _say(f"{len(ready)} new TikTok video{'s' if len(ready) != 1 else ''} ready for you to approve: {names}.")
    elif made:
        await _say(f"I couldn't finish the TikTok video: {made[-1].get('error', 'something went wrong')}.")


def todays_jobs(settings: Settings, data: dict, today: date) -> list[tuple[str, str, None]]:
    jobs = []
    for a in data["accounts"]:
        fails = sum(1 for v in data["videos"] if v.get("account") == a["name"] and v.get("day") == today.isoformat()
                    and v.get("status") == "failed")
        missing = a.get("per_day", 3) - cs.made_today(data, a["name"], today)
        if a.get("format") == "clips" and not twitch.configured(settings):
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
                jobs = [(v["account"], "", v) for v in sequels_due(data)] + todays_jobs(settings, data, date.today())
                if jobs:
                    await make_in_background(settings, jobs)
        except Exception as exc:
            print(f"[jarvis] Studio: {exc}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


# ---- approving and posting ----------------------------------------------------------------------------------

async def approve(settings: Settings, ref: str) -> str:
    data = cs.load(settings)
    v = cs.find_video(data, ref)
    can_post = tiktok.configured(settings) and tiktok.connected(settings, v["account"])
    if v.get("status") not in ("ready", "failed_post") and not (v.get("status") == "approved" and can_post):
        raise ValueError(f"'{v.get('title')}' is {v.get('status')}, so there's nothing to approve.")
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


def skip(settings: Settings, ref: str) -> str:
    data = cs.load(settings)
    v = cs.find_video(data, ref)
    v["status"] = "skipped"
    cs.save(settings, data)
    return f"Skipped '{v['title']}'. The file stays in the folder."


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

def studio_card(settings: Settings, data: dict, focus: str = "") -> dict:
    live = [v for v in data["videos"] if v.get("status") in ("making", "ready", "failed_post", "failed")]
    done = [v for v in data["videos"] if v.get("status") in ("posted", "approved")][-8:]
    videos = []
    for v in (live + done)[-30:]:
        row = {k: v.get(k) for k in ("id", "account", "title", "status", "part", "views", "caption", "error", "mode")}
        row["hashtags"] = " ".join(f"#{t}" for t in v.get("hashtags", []))
        if v.get("file"):
            row["src"] = f"/screen/file?path={screen.quote(v['file'])}"
        videos.append(row)
    accounts = [{"name": a["name"], "style": a["style"], "format": a["format"], "per_day": a.get("per_day", 3),
                 "theme": a["theme"], "connected": tiktok.connected(settings, a["name"])} for a in data["accounts"]]
    return screen.card("creator-studio", "TikTok studio", "creator-studio",
                       buttons=[{"label": "Make one now", "say": "Make a TikTok video now."}],
                       data={"accounts": accounts, "videos": videos, "configured": tiktok.configured(settings),
                             "setup": tiktok.setup_line() + ("" if twitch.configured(settings) or not any(
                                 a["format"] == "clips" for a in data["accounts"]) else " " + twitch.setup_line()), "focus": focus, "making": _ctx["making"]})


def studio(settings: Settings) -> screen.Shown:
    data = cs.load(settings)
    waiting = sum(1 for v in data["videos"] if v.get("status") == "ready")
    said = (f"{waiting} video{'s' if waiting != 1 else ''} waiting for your approval." if waiting else
            "Nothing is waiting for approval right now.")
    return screen.Shown(said + (" I'm making one now." if _ctx["making"] else ""), studio_card(settings, data))


# ---- accounts ----------------------------------------------------------------------------------------------

FIELDS = ("theme", "style", "format", "series", "per_day", "voice", "accent", "streamers", "category")


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
    fresh = cs.new_account(cs.clean(args.get("new_name")) or a["name"], used_clips=a.get("used_clips"),
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
    return f"Updated {a['name']}: {a['theme']}; {a['style']} look; {a['per_day']} a day."


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

ACTIONS = ["studio", "make_video", "approve", "skip", "set_views", "accounts", "add_account", "update_account",
           "remove_account", "name_ideas", "profile_kit", "trends", "connect", "setup"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "tiktok_studio",
        "description": "Alfred's TikTok studio: he runs several TikTok accounts, each with its own theme and look, "
                       "and writes and directs their videos himself (script, AI pictures, voice, 1 minute or longer). "
                       "Each day it makes every account's videos (3 each by default) and queues them; nothing posts "
                       "until the user approves. studio shows the queue with play, Approve and Skip. make_video "
                       "(account, optional idea) starts one now in the background. approve / skip (video: id, title "
                       "or 'latest'). set_views (video, views e.g. 80k) records views: 50k earns part 2, then every "
                       "100k more another part up to part 5, which ends on a shocking cliffhanger. accounts lists "
                       "them. add_account (account name, theme, style noir/explainer/drama/cinematic, format "
                       "story/facts/clips, series, per_day, voice e.g. en-GB-RyanNeural, accent colour; clip accounts: "
                       "streamers, category). Clip accounts like Clipzz post viral Twitch clips, old and new, filling "
                       "the phone screen, a minute or more, the streamer credited. update_account "
                       "(account, new_name or any field). remove_account (account, confirmed). name_ideas (theme) for "
                       "flashy Gen Z account names. profile_kit (account) makes a profile picture and a bio. trends (account, refresh) shows this "
                       "week's TikTok trends for its niche (checked daily before the first video and used in every "
                       "script, with the account's best-performing videos) so you can plan what to post next. connect (account) gives the TikTok login link. setup explains "
                       "what auto-posting needs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "account": {"type": "string", "description": "Account name, e.g. lowkey.lore."},
                "idea": {"type": "string", "description": "make_video: a story idea or topic to use."},
                "video": {"type": "string", "description": "Video id, part of its title, or 'latest'."},
                "views": {"type": "string", "description": "set_views: e.g. 80000 or 80k."},
                "new_name": {"type": "string"},
                "theme": {"type": "string"},
                "style": {"type": "string", "enum": list(cs.STYLES)},
                "format": {"type": "string", "enum": list(cs.FORMATS)},
                "series": {"type": "array", "items": {"type": "string"}},
                "per_day": {"type": "integer", "description": "Videos a day for this account, 0 to 6."},
                "voice": {"type": "string", "description": "A Microsoft neural voice, e.g. en-US-AndrewNeural."},
                "accent": {"type": "string", "description": "Keyword colour for the explainer look, e.g. #ff4d6d."},
                "streamers": {"type": "array", "items": {"type": "string"},
                              "description": "Clip accounts: Twitch streamers to take clips from (best: ones who allow clipping). Empty: the category's top clips."},
                "category": {"type": "string", "description": "Clip accounts: Twitch category, e.g. Just Chatting."},
                "confirmed": {"type": "boolean"},
                "refresh": {"type": "boolean", "description": "trends: check again now."},
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
    if action == "make_video":
        if _ctx["client"] is None:
            raise ValueError("The studio isn't running; restart Alfred.")
        data = cs.load(settings)
        account = cs.account(data, args.get("account"))
        if _ctx["making"]:
            return "I'm already making a video; I'll tell you when it's ready, then ask again."
        asyncio.create_task(make_in_background(settings, [(account["name"], cs.clean(args.get("idea"), 500), None)]))
        return (f"I'm writing and directing a new video for {account['name']} now. It takes a few minutes; "
                "I'll tell you when it's ready to approve.")
    if action == "approve":
        return await approve(settings, args.get("video"))
    if action == "skip":
        return skip(settings, args.get("video"))
    if action == "set_views":
        return set_views(settings, args.get("video"), args.get("views") or 0)
    if action == "accounts":
        data = cs.load(settings)
        rows = [[a["name"], a["style"], a["format"], str(a.get("per_day", 3)),
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
