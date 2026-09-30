"""Clip accounts (like Clipzz and n3on.vault): viral Twitch and Kick clips, cropped to fill a phone screen, a minute
or more.

Only streamers who allow clipping are ever clipped: each clip account lists its streamers, each with an
allows_clipping flag, and every clip found is checked against that list before it's used.
Twitch clips last 60 seconds at most, so a Clipzz video joins a streamer's top clips (most-viewed first) until it
passes a minute, and tops it up with other allowed streamers' clips if needed. Videos alternate between new viral
clips (the last week) and old viral ones (a random week from the last few years on Twitch, all time on Kick).
Accounts with min_views (n3on.vault: 100k) only take clips with at least that many views. Accounts with extend
(n3on.vault: 30) make an extended cut: the same moment cut again from the stream's VOD with 30 seconds before and
after, when the clip's place in the stream is known; otherwise the plain clip is used.
When Claude is available he orders the candidates and writes the hook, leaning towards what the user ticked and
away from what they X-ed. Every clip keeps its sound; the streamer is credited on screen and in the caption.
Clips are downloaded with yt-dlp and cut with ffmpeg; a clip id is never used twice on the same account.
"""

import asyncio
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

import artstudio_common as ac
import kick
import tiktokstudio_store as cs
import tiktokstudio_video as cv
import twitch

MIN_SECONDS = 61.0
MAX_CLIPS = 6
MAX_USED = 3000
SITES = {"twitch": "twitch.tv", "kick": "kick.com"}
CHOOSE_PROMPT = """You pick the clips for the TikTok clip account @{name} ({theme}).
{replacing}What the user thought of this account's earlier videos:
{taste}
Lean towards what they approved and away from what they rejected, but stay creative: pick a fresh moment and a
new angle for the hook, never a copy of an earlier video.

Candidate clips (id | streamer | views | seconds | title):
{rows}

Reply with ONLY this JSON: {{"order": ["the best clip id first", "..."], "hook": "one scroll-stopping line for the
top of the video, under 12 words, no hashtags"}}"""


def pick(clips: list[dict], used: set[str], length: float = MIN_SECONDS) -> list[dict]:
    """The clips for one video: the top streamer's best unused clips, topped up from others, until past length."""
    fresh = [c for c in clips if c.get("id") not in used and c.get("duration")]
    if not fresh:
        return []
    star = fresh[0]["broadcaster_name"]
    chosen = [c for c in fresh if c["broadcaster_name"] == star][:MAX_CLIPS]
    for c in fresh:
        if sum(x["duration"] for x in chosen) >= length or len(chosen) >= MAX_CLIPS:
            break
        if c not in chosen:
            chosen.append(c)
    total = 0.0
    for i, c in enumerate(chosen):
        total += c["duration"]
        if total >= length:
            return chosen[:i + 1]
    return []


# ---- only streamers who allow clipping -----------------------------------------------------------------------

def guard(clips: list[dict], account: dict) -> list[dict]:
    """Drop every clip whose streamer hasn't allowed clipping on that platform."""
    ok = {(p, n.lower()) for p in cs.PLATFORMS for n in cs.allowed(account, p)}
    return [c for c in clips if (c.get("platform", "twitch"), str(c.get("channel") or c.get("broadcaster_login")
                                                                   or c.get("broadcaster_name") or "").lower()) in ok]


def viral(clips: list[dict], used: set[str], min_views: int = 0) -> list[dict]:
    """Unused clips with at least min_views, most-viewed first."""
    return sorted((c for c in clips if c.get("id") not in used and c.get("duration")
                   and c.get("view_count", 0) >= min_views), key=lambda c: c.get("view_count", 0), reverse=True)


def extension(offset: float, seconds: float, pad: float = 30, length: float = 0) -> tuple[float, float]:
    """(start, end) in the stream: the clip plus pad seconds either side, kept inside the stream."""
    start, end = max(0.0, offset - pad), offset + seconds + pad
    return start, min(end, length) if length else end


async def sources(http, settings, account: dict, era: str) -> list[dict]:
    """Viral clips from every allowed streamer on every platform Alfred can reach; a clear message if none."""
    found, problems = [], []
    for slug in cs.allowed(account, "kick"):
        try:
            await kick.check_channel(http, settings, slug)
            found += await asyncio.to_thread(kick.top_clips, slug, era)
        except Exception as exc:  # no network, or Kick said no
            problems.append(f"Kick ({slug}): {str(exc)[:160]}")
    names = cs.allowed(account, "twitch")
    if names and not twitch.configured(settings):
        problems.append(twitch.setup_line())
    elif names:
        try:
            for c in await twitch.top_clips(http, settings, era, names, account.get("category") or "Just Chatting"):
                c = {**c, "platform": "twitch"}
                if c.get("video_id") and c.get("vod_offset") is not None:
                    c["vod"] = (f"https://www.twitch.tv/videos/{c['video_id']}", float(c["vod_offset"]), 0.0)
                found.append(c)
        except Exception as exc:
            problems.append(f"Twitch: {str(exc)[:160]}")
    if not found and problems:
        raise ValueError(f"I couldn't reach the clips for {account['name']}: " + " ".join(problems))
    return found


async def choose(client, settings, account: dict, clips: list[dict], replaces: dict | None = None) -> tuple[list[dict], str]:
    """Claude orders the candidates and writes the hook with the user's taste in mind; (clips, "") without him."""
    if client is None or len(clips) < 1:
        return clips, ""
    rows = "\n".join(f"{c['id']} | {c['broadcaster_name']} | {c.get('view_count', 0):,} | {c.get('duration', 0):.0f} | "
                     f"{cs.clean(c.get('title'), 100)}" for c in clips[:15])
    replacing = (f"This video REPLACES '{replaces.get('title')}', which the user rejected"
                 + (f" because: {replaces['reason']}" if replaces.get("reason") else "")
                 + ". Do clearly better on what was wrong.\n") if replaces else ""
    prompt = CHOOSE_PROMPT.format(name=account["name"], theme=account["theme"], replacing=replacing,
                                  taste=cs.taste_summary(account), rows=rows)
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=800,
                                             messages=[{"role": "user", "content": prompt}])
        text = "".join(getattr(b, "text", "") for b in reply.content)
        data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    except Exception as exc:  # Claude is busy: fall back to most-viewed first
        print(f"[jarvis] Clip choice: {exc}", flush=True)
        return clips, ""
    by_id = {c["id"]: c for c in clips}
    first = [by_id.pop(str(i)) for i in data.get("order") or [] if str(i) in by_id]
    return first + [c for c in clips if c["id"] in by_id], cs.clean(data.get("hook"), 90)


# ---- cutting --------------------------------------------------------------------------------------------------

def overlay(hook: str, credit: str) -> Image.Image:
    """A see-through layer: the hook in a white box at the top and the streamer credit near the bottom."""
    im = Image.new("RGBA", (cv.W, cv.H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font = ac.font(52)
    lines = cv.wrap(draw, hook, font, 900)[:3]
    tall = sum(draw.textbbox((0, 0), l, font=font)[3] + 10 for l in lines)
    draw.rounded_rectangle((60, 170, cv.W - 60, 210 + tall), radius=18, fill=(255, 255, 255, 240))
    y = 190
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        draw.text(((cv.W - (box[2] - box[0])) / 2, y), line, font=font, fill=(10, 10, 10))
        y += box[3] - box[1] + 10
    small = ac.font(38)
    box = draw.textbbox((0, 0), credit, font=small, stroke_width=3)
    draw.text(((cv.W - (box[2] - box[0])) / 2, 1640), credit, font=small, fill=(255, 255, 255),
              stroke_width=3, stroke_fill=(0, 0, 0))
    return im


def download(url: str, target: Path, section: tuple[float, float] | None = None) -> Path:
    """A clip, or with section (start, end) just that part of a stream's VOD."""
    import yt_dlp
    opts = {"outtmpl": str(target.with_suffix(".%(ext)s")), "format": "best[ext=mp4]/best",
            "quiet": True, "no_warnings": True, "noplaylist": True}
    if section:
        from yt_dlp.utils import download_range_func
        opts.update(download_ranges=download_range_func(None, [section]), force_keyframes_at_cuts=True,
                    ffmpeg_location=cv.ffmpeg())
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    found = sorted(target.parent.glob(target.stem + ".*"))
    if not found:
        raise RuntimeError(f"The clip at {url} didn't download.")
    return found[0]


def portrait(source: Path, layer: Path, out: Path) -> None:
    """Fill a 1080x1920 screen (crop the sides), put the hook and credit on top, keep the clip's own sound."""
    fill = f"scale={cv.W}:{cv.H}:force_original_aspect_ratio=increase,crop={cv.W}:{cv.H},fps={cv.FPS},setsar=1"
    cv.run(["-i", str(source), "-loop", "1", "-i", str(layer), "-filter_complex",
            f"[0:v]{fill}[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v];[0:a]aresample=44100[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])


def hook_line(clips: list[dict]) -> str:
    title = re.sub(r"\s+", " ", clips[0].get("title") or "").strip()
    return title[:80] or f"{clips[0]['broadcaster_name']} went viral for this"


def credit(clip: dict) -> str:
    return f"{SITES.get(clip.get('platform', 'twitch'), 'twitch.tv')}/{clip.get('channel') or clip['broadcaster_name']}"


async def find_vod(clip: dict, vod_lists: dict) -> tuple[str, float, float] | None:
    """Where the clip sits in its stream: Twitch says so; for Kick, match the clip to the channel's past streams."""
    if clip.get("vod"):
        return clip["vod"]
    if clip.get("platform") != "kick":
        return None
    slug = clip["channel"]
    if slug not in vod_lists:
        try:
            vod_lists[slug] = await asyncio.to_thread(kick.vods, slug)
        except Exception as exc:
            print(f"[jarvis] Kick streams for {slug}: {exc}", flush=True)
            vod_lists[slug] = []
    return kick.vod_offset(clip, vod_lists[slug])


async def cut_extended(clip: dict, pad: float, vod_lists: dict, target: Path) -> tuple[Path, float, bool]:
    """(file, seconds, extended?): the clip cut again from its stream with pad seconds either side, or the plain clip."""
    vod = await find_vod(clip, vod_lists)
    if vod:
        start, end = extension(vod[1], clip["duration"], pad, vod[2])
        try:
            return await asyncio.to_thread(download, vod[0], target, (start, end)), end - start, True
        except Exception as exc:  # the VOD is gone or blocked: the plain clip still makes a video
            print(f"[jarvis] Extended cut of {clip['id']}: {exc}", flush=True)
    return await asyncio.to_thread(download, clip["url"], target), clip["duration"], False


async def make(http, settings, account: dict, folder: Path, era: str, client=None, replaces: dict | None = None) -> dict:
    """One clip video for the account. Returns what the studio needs, plus the clip ids used."""
    if not cs.allowed(account):
        raise ValueError(f"{account['name']} has no streamers who allow clipping yet. Add one with their OK, e.g. "
                         "'add xqc on Kick to Clipzz, he allows clipping'.")
    used = set(account.get("used_clips") or [])
    min_views, pad = account.get("min_views") or 0, account.get("extend") or 0
    found = viral(guard(await sources(http, settings, account, era), account), used, min_views)
    if not found and era == "old":  # a quiet week; try another
        found = viral(guard(await sources(http, settings, account, era), account), used, min_views)
    ordered, hook = await choose(client, settings, account, found, replaces)
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    sources_cut, total, extended, vod_lists = [], 0.0, 0, {}
    if pad:  # extended cuts: one moment is usually a minute and a half on its own
        for i, clip in enumerate(ordered[:MAX_CLIPS]):
            path, seconds, longer = await cut_extended(clip, pad, vod_lists, work / f"clip{i}")
            sources_cut.append((clip, path))
            total, extended = total + seconds, extended + longer
            if total >= MIN_SECONDS:
                break
    else:
        for i, clip in enumerate(pick(ordered, used)):
            sources_cut.append((clip, await asyncio.to_thread(download, clip["url"], work / f"clip{i}")))
            total += clip["duration"]
    if total < MIN_SECONDS:
        for f in work.iterdir():
            f.unlink(missing_ok=True)
        work.rmdir()
        need = f" with {min_views:,}+ views" if min_views else ""
        raise ValueError(f"I couldn't find enough fresh viral clips{need} to fill a minute.")
    chosen = [c for c, _ in sources_cut]
    hook = hook or hook_line(chosen)
    parts = []
    for i, (clip, source) in enumerate(sources_cut):
        layer = work / f"layer{i}.png"
        await asyncio.to_thread(overlay(hook if i == 0 else clip.get("title") or hook, credit(clip)).save, layer)
        part = work / f"part{i}.mp4"
        await asyncio.to_thread(portrait, source, layer, part)
        parts.append(part)
    names = list(dict.fromkeys(c["broadcaster_name"] for c in chosen))
    sites = list(dict.fromkeys(c.get("platform", "twitch").title() for c in chosen))
    title = cs.slug(f"{names[0]} - {hook}"[:80])
    video = folder / f"{title}.mp4"
    n = 2
    while video.exists():
        video, n = folder / f"{title} ({n}).mp4", n + 1
    await asyncio.to_thread(cv.join, parts, work / "joined.mp4")
    (work / "joined.mp4").replace(video)
    for f in work.iterdir():
        f.unlink(missing_ok=True)
    work.rmdir()
    credits = " ".join(f"@{n}" for n in names)
    cut = "Extended cut: what happened before and after. " if extended else ""
    caption = (f"{hook} 🎮 {cut}Clips from {', '.join(names)} on {' and '.join(sites)} (all credit to {credits}). "
               "Follow for daily clips!")
    tags = [*(s.lower() for s in sites), "streamer", "clips", "viral", *[re.sub(r"\W", "", n).lower() for n in names[:2]]]
    video.with_suffix(".md").write_text(f"# {hook}\n\n{caption}\n\n" + " ".join(f"#{t}" for t in tags) + "\n\n## Clips\n\n"
                                        + "\n".join(f"- {c['title']} ({c['broadcaster_name']}, {c.get('view_count', 0):,} views): {c['url']}"
                                                    for c in chosen) + "\n", encoding="utf-8")
    notes = f"{era} clips of {', '.join(names)}" + (", extended cut" if extended else "") + f", {total:.0f}s"
    return {"title": hook, "caption": caption, "hashtags": tags, "keyword": era, "path": video, "hook": hook,
            "notes": notes, "scenes": [{"narration": c["title"]} for c in chosen], "clip_ids": [c["id"] for c in chosen]}
