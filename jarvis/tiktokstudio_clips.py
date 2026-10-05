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
Accounts with continue_at (Clipzz: 200k) make moment videos: a viral moment cut for a minute straight from a past
stream (with stream_min_views, Clipzz: 200k, only streams watched that much; old streams are fine), starting just
before the moment kicks off. Nobody's clip is reposted: the stream's most-viewed viewer clips only mark where its
moments are, since Alfred can't watch hours of stream himself. When a posted moment video passes continue_at views, the
next minute of the same stream follows as a new video, for as long as each one keeps passing it. Continuations
are never labelled as parts: each reads as a clip on its own.
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
MOMENT_SECONDS = 62.0  # a moment video: just over a minute of the stream
LEAD_SECONDS = 3.0  # start a touch before the clip, so the moment isn't joined mid-sentence
PART_WORDS = re.compile(r"\b(?:part|pt\.?|episode|ep\.?)\s*\d+\b|\(\s*\d+\s*\)|\bcontinued\b|\bcont'?d\b", re.I)
CONTINUE_PROMPT = """A TikTok clip of {streamer} went viral: "{title}". The next video shows the minute of the stream
straight after it. Write one scroll-stopping hook for the top of that next video, under 12 words, no hashtags.
It must read as a clip on its own: never say part, continued, episode or a number in brackets.
Reply with only the hook."""
MAX_CLIPS = 6
MAX_USED = 3000
SITES = {"twitch": "twitch.tv", "kick": "kick.com"}
CHOOSE_PROMPT = """You pick the clips for the TikTok clip account @{name} ({theme}).
{replacing}What the user thought of this account's earlier videos:
{taste}
Lean towards what they approved and away from what they rejected, but stay creative: pick a fresh moment and a
new angle for the hook, never a copy of an earlier video. An X means that one moment wasn't viral or entertaining
enough: it is not a verdict on the streamer or the stream, whose other moments are still fair game.
{performance}

Candidates (id | streamer | views | seconds | title{extra}):
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
    if account.get("stream_min_views") and any(c.get("video_id") for c in found):
        try:  # moment videos only come from streams watched enough: ask Twitch how many views each stream had
            info = await twitch.video_views(http, settings, [c["video_id"] for c in found if c.get("video_id")])
            for c in found:
                if c.get("video_id") and str(c["video_id"]) in info:
                    c["stream_views"], length = info[str(c["video_id"])]
                    if c.get("vod") and length:  # so a cut never runs past the end of the stream
                        c["vod"] = (c["vod"][0], c["vod"][1], length)
        except Exception as exc:
            print(f"[jarvis] Twitch stream views: {exc}", flush=True)
    if not found and problems:
        raise ValueError(f"I couldn't reach the clips for {account['name']}: " + " ".join(problems))
    return found


def moment_line(c: dict) -> str:
    """How strongly viewers reacted to a moment: how many of them clipped it, and how watched its stream was."""
    bits = []
    if c.get("moment_clips"):
        bits.append(f"{c['moment_clips']} viewer clip{'s' if c['moment_clips'] != 1 else ''} of it, "
                    f"{c.get('moment_views', 0):,} clip views")
    if c.get("stream_views"):
        bits.append(f"stream watched {c['stream_views']:,} times")
    return "; ".join(bits)


async def choose(client, settings, account: dict, clips: list[dict], replaces: dict | None = None,
                 best: list[str] | None = None) -> tuple[list[dict], str]:
    """Claude orders the candidates and writes the hook with the user's taste and the audience's views in mind;
    (clips, "") without him."""
    if client is None or len(clips) < 1:
        return clips, ""
    moments = any(c.get("moment_clips") for c in clips)
    rows = "\n".join(f"{c['id']} | {c['broadcaster_name']} | {c.get('view_count', 0):,} | {c.get('duration', 0):.0f} | "
                     f"{cs.clean(c.get('title'), 100)}" + (f" | {moment_line(c)}" if moments else "") for c in clips[:15])
    performance = ("What kept the audience watching (this account's most-viewed posted videos): " + "; ".join(best)
                   + ". Pick moments like those.") if best else ""
    replacing = (f"This video REPLACES '{replaces.get('title')}', which the user rejected"
                 + (f" because: {replaces['reason']}" if replaces.get("reason") else "")
                 + ". Do clearly better on what was wrong.\n") if replaces else ""
    prompt = CHOOSE_PROMPT.format(name=account["name"], theme=account["theme"], replacing=replacing,
                                  taste=cs.taste_summary(account), rows=rows, performance=performance,
                                  extra=" | how viewers reacted" if moments else "")
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=800,
                                             messages=[{"role": "user", "content": prompt}])
        text = "".join(getattr(b, "text", "") for b in reply.content)
        data = cv.loads_lenient(text)
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
    """Fill a 1080x1920 screen (crop the sides), put the hook and credit on top, keep the clip's own sound.
    Stream footage is usually 720p or 1080p wide, so the crop scales it up: the same light sharpen and encoder
    settings as the studio's own videos keep it crisp and its dark game scenes free of banding."""
    fill = f"scale={cv.W}:{cv.H}:force_original_aspect_ratio=increase,crop={cv.W}:{cv.H},fps={cv.FPS},setsar=1"
    sharpen = f",{cv.SHARPEN}" if cv.SHARPEN else ""
    cv.run(["-i", str(source), "-loop", "1", "-i", str(layer), "-filter_complex",
            f"[0:v]{fill}{sharpen}[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v];[0:a]aresample=44100[a]",
            "-map", "[v]", "-map", "[a]", *cv.VIDEO_CODEC,
            "-c:a", "aac", "-b:a", cv.WORK_AUDIO, "-ar", "44100", "-ac", "2", str(out)])


def level(part: Path) -> None:
    """Bring one clip to TikTok's loudness in place, so a quiet streamer and a shouting one sit at the same volume
    in the compilation (nobody reaches for the volume between clips). Kept as it was if levelling fails."""
    out = part.with_name(f"{part.stem}-level{part.suffix}")
    try:
        cv.normalise(part, out)
        out.replace(part)
    except Exception as exc:
        out.unlink(missing_ok=True)
        print(f"[jarvis] Clip levelling skipped: {exc}", flush=True)


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


def moment_window(start: float, length: float = 0) -> tuple[float, float] | None:
    """(start, end) of a minute-long moment video in its stream, or None when the stream has no full minute left."""
    end = start + MOMENT_SECONDS
    if length:
        end = min(end, length)
    return (start, end) if end - start >= MIN_SECONDS else None


def standalone(text: str) -> str:
    """Strips any 'part 2' style label, so a continuation reads as its own clip."""
    return re.sub(r"\s{2,}", " ", PART_WORDS.sub("", text or "")).strip(" -:|,")


def moment_record(clip: dict, vod: tuple, end: float) -> dict:
    """What's kept so the next minute of the same moment can be cut later."""
    keep = ("id", "url", "title", "broadcaster_name", "channel", "platform", "view_count", "stream_views",
            "moment_clips", "moment_views")
    return {"vod": vod[0], "end": end, "length": vod[2] or 0, "clip": {k: clip.get(k) for k in keep if clip.get(k) is not None}}


def moment_key(vod_url: str, start: float, end: float | None = None) -> str:
    """Kept in the account's used list, so the same stretch of a stream is never posted twice."""
    return f"moment:{vod_url}@{int(start)}-{int(end if end is not None else start + MOMENT_SECONDS)}"


def used_stretches(vod_url: str, used) -> list[tuple[float, float]]:
    """(start, end) of every stretch of this stream already made into a video."""
    found = []
    for key in used or ():
        if str(key).startswith(f"moment:{vod_url}@"):
            span = str(key).rsplit("@", 1)[1]
            try:
                a, _, b = span.partition("-")
                found.append((float(a), float(b) if b else float(a) + MOMENT_SECONDS))
            except ValueError:
                pass
    return found


def overlaps(vod_url: str, start: float, used, end: float | None = None) -> bool:
    """True when start..end (a minute by default) shares any footage with a stretch already used."""
    end = start + MOMENT_SECONDS if end is None else end
    return any(a < end and start < b for a, b in used_stretches(vod_url, used))


async def stream_views(clip: dict, vod_lists: dict) -> int:
    """Total views of the stream a clip came from (Twitch is asked up front; Kick from its stream list)."""
    if "stream_views" in clip:
        return int(clip["stream_views"] or 0)
    if clip.get("platform") == "kick" and clip.get("channel") in vod_lists:
        return kick.vod_views(clip, vod_lists[clip["channel"]])
    return 0


MOMENT_SPAN = 60.0  # clips that start within this of each other are the same moment


async def find_moments(clips: list[dict], vod_lists: dict) -> list[dict]:
    """The viral moments in past streams, strongest first. Clips only mark where things happened: when several
    viewers clipped the same stretch of a stream, that's one moment, and the more of them (and the more their clips
    were watched) the more viral it was. Each moment starts at its earliest clip, where the action kicked off."""
    by_stream: dict[str, list] = {}
    for c in clips:
        vod = await find_vod(c, vod_lists)
        if vod:
            by_stream.setdefault(vod[0], []).append((vod, c))
    found = []
    for rows in by_stream.values():
        rows.sort(key=lambda r: r[0][1])
        group: list = []
        for vod, c in rows + [(None, None)]:
            if group and (vod is None or vod[1] - group[0][0][1] > MOMENT_SPAN):
                top = max(group, key=lambda r: r[1].get("view_count", 0))[1]
                first = group[0][0]
                views = sum(r[1].get("view_count", 0) for r in group)
                found.append({**top, "vod": (first[0], first[1], first[2]), "moment_clips": len(group),
                              "moment_views": views, "moment_score": views * (1 + 0.5 * (len(group) - 1))})
                group = []
            if vod is not None:
                group.append((vod, c))
    return sorted(found, key=lambda m: m["moment_score"], reverse=True)


async def cut_moment(clips: list[dict], vod_lists: dict, work: Path, stream_min: int = 0,
                     used=()) -> tuple[dict, Path, float, dict] | None:
    """A minute cut straight from a past stream, starting just before a viral moment: the first candidate whose
    stream is still up, was watched at least stream_min times and hasn't had this stretch posted already. A
    rejected moment only rules out that stretch: the rest of its stream stays available."""
    for i, clip in enumerate(clips[:MAX_CLIPS * 3]):
        vod = await find_vod(clip, vod_lists)
        if not vod:
            continue
        start = max(0.0, vod[1] - LEAD_SECONDS)
        window = moment_window(start, vod[2])
        if not window or overlaps(vod[0], start, used):
            continue
        if stream_min and await stream_views(clip, vod_lists) < stream_min:
            continue
        try:
            path = await asyncio.to_thread(download, vod[0], work / f"moment{i}", window)
        except Exception as exc:  # the stream is gone or blocked: try the next moment
            print(f"[jarvis] Moment cut of {clip['id']}: {exc}", flush=True)
            continue
        return clip, path, window[1] - window[0], moment_record(clip, vod, window[1])
    return None


async def continuation_hook(client, settings, prev: dict) -> str:
    clip = prev["moment"]["clip"]
    fallback = f"{clip.get('broadcaster_name', 'This streamer')} didn't stop there"  # never the earlier title again
    if client is None:
        return fallback
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=300, messages=[{"role": "user", "content":
            CONTINUE_PROMPT.format(streamer=clip.get("broadcaster_name", "a streamer"),
                                   title=prev.get("hook") or prev.get("title") or clip.get("title", ""))}])
        hook = standalone(" ".join(getattr(b, "text", "") for b in reply.content).strip().strip('"'))[:90]
        return hook if hook and hook.lower() != str(prev.get("hook") or prev.get("title") or "").lower() else fallback
    except Exception as exc:
        print(f"[jarvis] Continuation hook: {exc}", flush=True)
        return fallback


async def make_continuation(settings, account: dict, folder: Path, prev: dict, client=None) -> dict:
    """The next minute of a moment video's stream, as a new video that reads on its own."""
    moment = prev.get("moment") or {}
    window = moment_window(float(moment.get("end") or 0), float(moment.get("length") or 0)) if moment.get("vod") else None
    if not window:
        raise ValueError("That moment's stream has no full minute left, so it ends here.")
    if overlaps(moment["vod"], window[0], account.get("used_clips"), window[1]):
        raise ValueError("The next minute of that stream is already in another video, so this moment ends here.")
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        path = await asyncio.to_thread(download, moment["vod"], work / "moment", window)
    except Exception:
        _clear(work)
        raise
    clip = {k: v for k, v in moment["clip"].items() if k != "id"}  # the clip id was used by the first video
    hook = await continuation_hook(client, settings, prev)
    result = await _render(settings, folder, work, [(clip, path)], hook, prev.get("keyword") or "moment",
                           window[1] - window[0], 0, {**moment, "end": window[1]})
    result["clip_ids"].append(moment_key(moment["vod"], window[0], window[1]))
    return result


def _clear(work: Path) -> None:
    for f in work.iterdir():
        f.unlink(missing_ok=True)
    work.rmdir()


async def make(http, settings, account: dict, folder: Path, era: str, client=None, replaces: dict | None = None,
               best: list[str] | None = None) -> dict:
    """One clip video for the account. Returns what the studio needs, plus the clip ids used."""
    if not cs.allowed(account):
        raise ValueError(f"{account['name']} has no streamers who allow clipping yet. Add one with their OK, e.g. "
                         "'add xqc on Kick to Clipzz, he allows clipping'.")
    used = set(account.get("used_clips") or [])
    min_views, pad = account.get("min_views") or 0, account.get("extend") or 0
    found = viral(guard(await sources(http, settings, account, era), account), used, min_views)
    if account.get("continue_at"):  # moment accounts: old viral moments are just as good, so try a few past weeks
        for _ in range(3):
            if found:
                break
            found = viral(guard(await sources(http, settings, account, "old"), account), used, min_views)
    elif not found and era == "old":  # a quiet week; try another
        found = viral(guard(await sources(http, settings, account, era), account), used, min_views)
    vod_lists: dict = {}
    if account.get("continue_at"):  # moment videos: rank whole moments, not single clips
        found = [m for m in await find_moments(found, vod_lists)
                 if not overlaps(m["vod"][0], max(0.0, m["vod"][1] - LEAD_SECONDS), used)]
    ordered, hook = await choose(client, settings, account, found, replaces, best)
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    sources_cut, total, extended = [], 0.0, 0
    if account.get("continue_at"):  # one moment, cut straight from the stream: never a reposted clip
        cut = await cut_moment(ordered, vod_lists, work, account.get("stream_min_views") or 0, used)
        if not cut:
            _clear(work)
            bar = f" with {account['stream_min_views']:,}+ views" if account.get("stream_min_views") else ""
            raise ValueError(f"I couldn't find a viral moment in a past stream{bar} that's still online and not "
                             "posted yet. I'll look again with the next video.")
        clip, path, total, moment = cut
        hook = hook or hook_line([clip])
        result = await _render(settings, folder, work, [(clip, path)], hook, era, total, 0, moment)
        result["clip_ids"].append(moment_key(moment["vod"], moment["end"] - total, moment["end"]))
        return result
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
        _clear(work)
        need = f" with {min_views:,}+ views" if min_views else ""
        raise ValueError(f"I couldn't find enough fresh viral clips{need} to fill a minute.")
    hook = hook or hook_line([c for c, _ in sources_cut])
    return await _render(settings, folder, work, sources_cut, hook, era, total, extended, None)


async def _render(settings, folder: Path, work: Path, sources_cut: list, hook: str, era: str, total: float,
                  extended: int, moment: dict | None) -> dict:
    """Portrait, captioned, levelled and joined: the finished clip video and its notes."""
    chosen = [c for c, _ in sources_cut]
    parts = []
    for i, (clip, source) in enumerate(sources_cut):
        layer = work / f"layer{i}.png"
        await asyncio.to_thread(overlay(hook if i == 0 else clip.get("title") or hook, credit(clip)).save, layer)
        part = work / f"part{i}.mp4"
        await asyncio.to_thread(portrait, source, layer, part)
        await asyncio.to_thread(level, part)
        parts.append(part)
    names = list(dict.fromkeys(c["broadcaster_name"] for c in chosen))
    sites = list(dict.fromkeys(c.get("platform", "twitch").title() for c in chosen))
    title = cs.slug(f"{names[0]} - {hook}"[:80])
    video = folder / f"{title}.mp4"
    n = 2
    while video.exists():  # a word, not "(2)": nothing about a video should read like a part number
        word = ["again", "more", "still", "later", "after"][(n - 2) % 5] + ("" if n < 7 else " " + cs.new_id()[-4:])
        video, n = folder / f"{title} - {word}.mp4", n + 1
    await asyncio.to_thread(cv.join, parts, work / "joined.mp4")
    (work / "joined.mp4").replace(video)
    try:  # watched once like the studio's own videos: too short, silent, black or dead air
        checks = await asyncio.to_thread(cv.check_video, video)
    except Exception as exc:
        print(f"[jarvis] Quality check skipped: {exc}", flush=True)
        checks = []
    facts = await asyncio.to_thread(cv.video_facts, video)
    _clear(work)
    credits = " ".join(f"@{n}" for n in names)
    cut = "Extended cut: what happened before and after. " if extended else ""
    caption = (f"{hook} 🎮 {cut}Clips from {', '.join(names)} on {' and '.join(sites)} (all credit to {credits}). "
               "Follow for daily clips!")
    tags = [*(s.lower() for s in sites), "streamer", "clips", "viral", *[re.sub(r"\W", "", n).lower() for n in names[:2]]]
    facts_line = f"Length: {facts}\n\n" if facts else ""
    check_line = f"Quality check: {'; '.join(checks) if checks else 'passed'}\n\n"
    video.with_suffix(".md").write_text(f"# {hook}\n\n{caption}\n\n" + " ".join(f"#{t}" for t in tags) + "\n\n"
                                        + facts_line + check_line + "## Clips\n\n"
                                        + "\n".join(f"- {c.get('title', '')} ({c.get('broadcaster_name', '')}, {c.get('view_count', 0):,} views): {c.get('url', '')}"
                                                    for c in chosen) + "\n", encoding="utf-8")
    if moment:
        c = chosen[0]
        notes = (f"a minute from {c.get('broadcaster_name', 'a')}'s stream, moment '{cs.clean(c.get('title'), 80)}'"
                 + (f" ({moment_line(c)})" if moment_line(c) else ""))
    else:
        notes = f"{era} clips of {', '.join(names)}" + (", extended cut" if extended else "") + f", {total:.0f}s"
    return {"title": hook, "caption": caption, "hashtags": tags, "keyword": era, "path": video, "hook": hook,
            "notes": notes, "scenes": [{"narration": c.get("title", "")} for c in chosen],
            "clip_ids": [c["id"] for c in chosen if c.get("id")], "checks": checks, "moment": moment}
