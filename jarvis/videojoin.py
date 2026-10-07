"""Join video clips into one film: Higgsfield (or any) clips, files in the memory folders or web links, made the
same size and frame rate, joined with hard cuts or crossfades, with narration and music laid over the whole timeline.
The film is saved into a memory folder and plays on Alfred's screen.

last_frame grabs a clip's final frame as a picture, so the next generated clip can start from it (image-to-video,
or Seedance's video extension) and the shots flow on from each other instead of looking patched together.
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx

import media_common as mc
import memory
import screen
from config import Settings
from tiktokstudio_store import slug
from tiktokstudio_video import audio_seconds, ffmpeg

NAMES = {"join_video_clips"}
ACTIONS = ["join", "last_frame"]
DEFAULT_FOLDER = "Work/Films"
MAX_CLIPS = 40
MAX_DOWNLOAD = 500 * 1024 * 1024
FADE_SECONDS = 0.5
MUSIC_FADE = 2.0
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def tool_definitions() -> list[dict]:
    return [{
        "name": "join_video_clips",
        "description": "Join video clips into one seamless film and play it on the screen: 'stitch those Higgsfield "
                       "clips into one video', 'put the narration and music over it'. join takes clips in order "
                       "(web links from Higgsfield, or files in the memory folders like Work/Films/shot1.mp4), makes "
                       "them one size and frame rate, joins them with hard cuts or crossfades, and lays audio tracks "
                       "(narration, music; links or files) over the whole film, saving it to a memory folder. "
                       "last_frame (clip) saves a clip's final frame as a picture: use it as the start image of "
                       "the next generated clip so each shot carries on from the last one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "clips": {"type": "array", "items": {"type": "string"},
                          "description": "join: the clips in order (links or memory-folder files)."},
                "clip": {"type": "string", "description": "last_frame: the clip (link or file)."},
                "audio": {"type": "array", "description": "join: tracks laid over the whole film.",
                          "items": {"type": "object", "properties": {
                              "source": {"type": "string", "description": "A link or memory-folder file."},
                              "volume": {"type": "number", "description": "1 = as is (default); music ~0.3."},
                              "start": {"type": "number", "description": "Seconds into the film (default 0)."},
                              "loop": {"type": "boolean", "description": "Repeat to fill the film (music)."}},
                              "required": ["source"]}},
                "transition": {"type": "string", "enum": ["cut", "crossfade"], "description": "Default cut."},
                "fade_seconds": {"type": "number", "description": f"Crossfade length (default {FADE_SECONDS})."},
                "keep_clip_sound": {"type": "boolean", "description": "Keep the clips' own sound (default true)."},
                "size": {"type": "string", "description": "e.g. 1080x1920; default the first clip's size."},
                "fps": {"type": "number", "description": "Default the first clip's frame rate."},
                "name": {"type": "string", "description": "The film's file name."},
                "folder": {"type": "string", "description": f"Memory folder to save in (default {DEFAULT_FOLDER})."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run(args: list[str]) -> None:
    done = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if done.returncode:
        lines = [l for l in done.stderr.splitlines() if l.strip()]
        raise ValueError(f"ffmpeg couldn't make the film: {(lines[0] if lines else 'unknown error')[:300]}")


def probe(path: Path) -> dict:
    """A clip's size, frame rate, length and whether it has sound."""
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    video = re.search(r"Stream #\S+.*?: Video: .*?(\d{2,5})x(\d{2,5}).*?(?:([\d.]+) fps|([\d.]+) tbr)", out)
    if not video:
        raise ValueError(f"{path.name} isn't a video I can read.")
    return {"w": int(video[1]), "h": int(video[2]), "fps": float(video[3] or video[4] or 30),
            "seconds": audio_seconds(path), "sound": bool(re.search(r"Stream #\S+.*?: Audio:", out))}


def fetch(settings: Settings, source: str, into: Path, http: httpx.Client | None) -> Path:
    """A clip or track: downloaded if it's a link, otherwise a file in the memory folders."""
    source = str(source or "").strip()
    if not source:
        raise ValueError("One of the clips or tracks is empty.")
    if source.startswith(("http://", "https://")):
        name = Path(urlparse(source).path).name or "clip.mp4"
        parts = into / ".parts"  # downloads wait here and are cleared once the film is made
        parts.mkdir(parents=True, exist_ok=True)
        target = parts / f"{len(list(parts.iterdir()))}-{slug(Path(name).stem, 'part')}{Path(name).suffix.lower() or '.mp4'}"
        client = http or httpx.Client(timeout=120, follow_redirects=True)
        try:
            with client.stream("GET", source, follow_redirects=True) as reply:
                reply.raise_for_status()
                size = 0
                with target.open("wb") as out:
                    for chunk in reply.iter_bytes():
                        size += len(chunk)
                        if size > MAX_DOWNLOAD:
                            raise ValueError("That clip is too big to download (over 500 MB).")
                        out.write(chunk)
        except httpx.HTTPError as exc:
            raise ValueError(f"I couldn't download {name}: {exc}") from None
        finally:
            if http is None:
                client.close()
        return target
    root = mc.base(settings).resolve()
    path = (root / source.replace("\\", "/")).resolve()
    if root not in path.parents:
        raise ValueError(f"{source} isn't in the memory folders.")
    if not path.is_file():
        matches = [p for p in mc.all_files(settings) if p.name.lower() == Path(source).name.lower()]
        if not matches:
            raise ValueError(f"I can't find {source} in the memory folders.")
        path = max(matches, key=lambda p: p.stat().st_mtime)
    return path


def film_filter(facts: list[dict], w: int, h: int, fps: float, crossfade: bool, fade: float, keep_sound: bool,
                tracks: list[dict], total: float) -> str:
    """The filter graph: each clip fitted to w x h at fps, joined, then the extra tracks mixed over the film."""
    n = len(facts)
    chains = []
    for i, f in enumerate(facts):
        chains.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
                      f"setsar=1,trim=duration={f['seconds']:.3f},setpts=PTS-STARTPTS,fps={fps:g},format=yuv420p[v{i}]")
        sound = f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo," if keep_sound and f["sound"] else \
            "anullsrc=r=44100:cl=stereo,"
        chains.append(f"{sound}atrim=duration={f['seconds']:.3f},asetpts=PTS-STARTPTS[a{i}]")
    if n == 1:
        chains.append("[v0]null[vj];[a0]anull[aj]")
    elif crossfade:
        at, video, sound = 0.0, "[v0]", "[a0]"
        for i in range(1, n):
            at += facts[i - 1]["seconds"] - fade
            chains.append(f"{video}[v{i}]xfade=transition=fade:duration={fade:g}:offset={at:.3f}[vx{i}]")
            chains.append(f"{sound}[a{i}]acrossfade=d={fade:g}[ax{i}]")
            video, sound = f"[vx{i}]", f"[ax{i}]"
        chains.append(f"{video}null[vj];{sound}anull[aj]")
    else:
        chains.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vj][aj]")
    mixes = ["[aj]"]
    for j, t in enumerate(tracks):
        k = n + j
        delay = round(float(t.get("start") or 0) * 1000)
        tail = f",afade=t=out:st={max(0.0, total - MUSIC_FADE):.3f}:d={MUSIC_FADE}" if t.get("loop") else ""
        chains.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo,volume={float(t.get('volume') or 1):g},"
                      f"adelay={delay}|{delay},atrim=duration={total:.3f}{tail}[t{j}]")
        mixes.append(f"[t{j}]")
    if tracks:
        chains.append("".join(mixes) + f"amix=inputs={len(mixes)}:duration=first:normalize=0[af]")
    else:
        chains.append("[aj]anull[af]")
    return ";".join(chains)


def join(settings: Settings, args: dict, http=None) -> screen.Shown:
    clips = [c for c in args.get("clips") or [] if str(c).strip()]
    if not clips:
        raise ValueError("Which clips should I join? Give me them in order.")
    if len(clips) > MAX_CLIPS:
        raise ValueError(f"That's a lot of clips: I can join up to {MAX_CLIPS} at once.")
    folder = memory.folder(settings, args.get("folder") or DEFAULT_FOLDER, create=True)
    paths = [fetch(settings, c, folder, http) for c in clips]
    facts = [probe(p) for p in paths]
    if any(f["seconds"] <= 0 for f in facts):
        raise ValueError("One of the clips has no length I can read.")
    if args.get("size"):
        match = re.fullmatch(r"\s*(\d{2,4})\s*[x×]\s*(\d{2,4})\s*", str(args["size"]))
        if not match:
            raise ValueError("Give the size like 1080x1920.")
        w, h = int(match[1]), int(match[2])
    else:
        w, h = facts[0]["w"], facts[0]["h"]
    w, h = w - w % 2, h - h % 2  # the H.264 encoder needs even sizes
    fps = min(max(float(args.get("fps") or facts[0]["fps"] or 30), 12), 60)
    crossfade = args.get("transition") == "crossfade" and len(facts) > 1
    fade = min(max(float(args.get("fade_seconds") or FADE_SECONDS), 0.1), 2.0)
    if crossfade:
        fade = min(fade, min(f["seconds"] for f in facts) / 2)
    total = sum(f["seconds"] for f in facts) - (fade * (len(facts) - 1) if crossfade else 0)
    tracks = [t for t in args.get("audio") or [] if isinstance(t, dict) and str(t.get("source", "")).strip()]
    track_paths = [fetch(settings, t["source"], folder, http) for t in tracks]
    name = slug(args.get("name") or "film", "film")
    out = folder / f"{name}.mp4"
    number = 2
    while out.exists():
        out, number = folder / f"{name} {number}.mp4", number + 1
    inputs = [x for p in paths for x in ("-i", str(p))]
    for t, p in zip(tracks, track_paths):
        inputs += (["-stream_loop", "-1"] if t.get("loop") else []) + ["-i", str(p)]
    graph = film_filter(facts, w, h, fps, crossfade, fade, args.get("keep_clip_sound", True) is not False, tracks,
                        total)
    run([*inputs, "-filter_complex", graph, "-map", "[vj]", "-map", "[af]", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", f"{fps:g}",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    for part in (folder / ".parts").glob("*") if (folder / ".parts").exists() else []:
        part.unlink(missing_ok=True)
    minutes, seconds = divmod(round(total), 60)
    said = (f"Joined {len(facts)} clips into {out.name} ({minutes}:{seconds:02d}, {w}x{h}"
            f"{', crossfaded' if crossfade else ''}), saved in {mc.rel(settings, folder)}. Playing it now.")
    return screen.Shown(said, screen.file_card(settings, out))


def last_frame(settings: Settings, args: dict, http=None) -> str:
    folder = memory.folder(settings, args.get("folder") or DEFAULT_FOLDER, create=True)
    clip = fetch(settings, args.get("clip", ""), folder, http)
    seconds = probe(clip)["seconds"]
    out = folder / f"{slug(clip.stem, 'clip')} last frame.png"
    run(["-ss", f"{max(0.0, seconds - 0.1):.3f}", "-i", str(clip), "-frames:v", "1", "-update", "1", str(out)])
    if clip.parent.name == ".parts":
        clip.unlink(missing_ok=True)
    if not out.exists():
        raise ValueError("I couldn't grab the last frame of that clip.")
    return (f"Saved the last frame of {clip.name} as {mc.rel(settings, out)}. Upload it as the start image of the "
            "next clip so the shot carries straight on.")


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "join":
        return join(settings, args)
    if action == "last_frame":
        return last_frame(settings, args)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
