"""Clip accounts (like Clipzz): viral Twitch clips, cropped to fill a phone screen, joined to a minute or more.

Twitch clips last 60 seconds at most, so each video joins a streamer's top clips (most-viewed first) until it
passes a minute, and tops it up with other streamers' clips from the same window if needed. The account's videos
alternate between new viral clips (the last week) and old viral ones (a random week from the last few years).
Every clip keeps its sound; the streamer is credited on screen and in the caption, and a hook line sits at the top.
Clips are downloaded with yt-dlp and cut with ffmpeg.
"""

import asyncio
import re
from pathlib import Path

from PIL import Image, ImageDraw

import artstudio_common as ac
import tiktokstudio_store as cs
import tiktokstudio_video as cv
import twitch

MIN_SECONDS = 61.0
MAX_CLIPS = 6
MAX_USED = 3000


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


def download(url: str, target: Path) -> Path:
    import yt_dlp
    with yt_dlp.YoutubeDL({"outtmpl": str(target.with_suffix(".%(ext)s")), "format": "best[ext=mp4]/best",
                           "quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
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


async def make(http, settings, account: dict, folder: Path, era: str) -> dict:
    """One clip video for the account. Returns what the studio needs, plus the clip ids used."""
    if not twitch.configured(settings):
        raise ValueError(twitch.setup_line())
    used = set(account.get("used_clips") or [])
    clips = await twitch.top_clips(http, settings, era, account.get("streamers") or None,
                                   account.get("category") or "Just Chatting")
    chosen = pick(clips, used)
    if not chosen and era == "old":  # a quiet week; try another
        chosen = pick(await twitch.top_clips(http, settings, era, account.get("streamers") or None,
                                             account.get("category") or "Just Chatting"), used)
    if not chosen:
        raise ValueError("I couldn't find enough fresh viral clips to fill a minute.")
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    hook = hook_line(chosen)
    parts = []
    for i, clip in enumerate(chosen):
        source = await asyncio.to_thread(download, clip["url"], work / f"clip{i}")
        layer = work / f"layer{i}.png"
        await asyncio.to_thread(overlay(hook if i == 0 else clip.get("title") or hook,
                                        f"twitch.tv/{clip['broadcaster_name']}").save, layer)
        part = work / f"part{i}.mp4"
        await asyncio.to_thread(portrait, source, layer, part)
        parts.append(part)
    names = list(dict.fromkeys(c["broadcaster_name"] for c in chosen))
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
    caption = f"{hook} 🎮 Clips from {', '.join(names)} on Twitch (all credit to {credits}). Follow for daily clips!"
    tags = ["twitch", "streamer", "clips", "viral", *[re.sub(r"\W", "", n).lower() for n in names[:2]]]
    video.with_suffix(".md").write_text(f"# {hook}\n\n{caption}\n\n" + " ".join(f"#{t}" for t in tags) + "\n\n## Clips\n\n"
                                        + "\n".join(f"- {c['title']} ({c['broadcaster_name']}, {c.get('view_count', 0):,} views): {c['url']}"
                                                    for c in chosen) + "\n", encoding="utf-8")
    return {"title": hook, "caption": caption, "hashtags": tags, "keyword": era, "path": video,
            "scenes": [{"narration": c["title"]} for c in chosen], "clip_ids": [c["id"] for c in chosen]}
