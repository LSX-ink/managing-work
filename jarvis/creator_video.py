"""Alfred as author and director: writes a short vertical video, pictures it, voices it and cuts it to an MP4.

1. Script: Claude writes the title, hook, scenes (on-screen line + narration + a picture description), caption
   and hashtags as JSON, in the account's theme, format and series, avoiding titles it used before.
2. Pictures: one per scene from Pollinations (free, no key), in the account's look. If a picture can't be
   fetched, a plain dark frame is used so the video still gets made.
3. Frames: each picture is laid out in the account's style with Pillow (noir card, black explainer or
   cinematic), with the line for that scene written small on screen.
4. Voice: ElevenLabs when its key is set, otherwise Microsoft's free neural voices (edge-tts). No voice at all
   still makes a captioned video.
5. Video: ffmpeg (bundled by imageio-ffmpeg) gives each frame a slow push-in, matches it to its narration and
   joins the scenes into one 1080x1920 MP4.
"""

import asyncio
import json
import random
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import artstudio_common as ac
import creator_store as cs
import tts
from config import Settings

W, H = 1080, 1920
FPS = 30
PICTURE_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
DEFAULT_VOICE = "en-GB-RyanNeural"
LOOKS = {
    "noir": ("black and white photograph, moody, cinematic close-up, deep shadows, high contrast, film grain, "
             "shallow depth of field, no text"),
    "explainer": ("minimal flat vector illustration, one simple faceless cartoon figure in beige and brown, "
                  "plain solid pure black background, centred, clean lines, no text, no words"),
    "drama": ("photorealistic cinematic still, expressive emotional faces, luxury home or everyday setting, "
              "natural light, shot on a phone, vertical, no text"),
    "cinematic": "cinematic film still, dramatic lighting, rich colour, vertical composition, no text",
}
SCRIPT_PROMPT = """You are Alfred, the author and director of the TikTok account @{name}.
The account's theme: {theme}
Format: {format}
Series this account runs: {series}
Look: {look}

Write ONE new video for today, 35 to 55 seconds long when read aloud. {idea}
Titles already used (never repeat or closely copy these): {recent}

Rules:
- Stop the scroll in the first line: the hook is a bold claim, a question or a cliffhanger.
- 5 to 8 scenes. Each scene has one short on-screen line (under 12 words) and the narration Alfred reads
  (one or two short sentences). The last scene lands the twist or the takeaway and invites a follow.
- Everything must be original, kind, and safe for TikTok: no real people, no brands, no medical or money
  promises, nothing hateful or sexual. For psychology, say "some people" and "often", never diagnose.
- "picture" describes what the camera sees in that scene in 10 to 25 words, for an image generator. No text in
  the picture. Keep the same main character described the same way in every scene.
- keyword: 1 to 3 words shown big at the top (e.g. ADHD, Letter "M", Unsent Letter #4).
- caption: one or two lines for the post, ending with a question. hashtags: 4 to 6, lower case, without #.

Reply with ONLY this JSON:
{{"title": "...", "keyword": "...", "series": "...", "hook": "...", "caption": "...", "hashtags": ["..."],
  "scenes": [{{"text": "...", "narration": "...", "picture": "..."}}]}}"""


# ---- 1. script ---------------------------------------------------------------------------------------------

def parse_script(text: str) -> dict:
    """The script JSON from Claude's reply (code fences and chatter around it are fine)."""
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        raise ValueError("The script came back without any JSON.")
    data = json.loads(match.group(0))
    scenes = [s for s in data.get("scenes") or [] if isinstance(s, dict) and cs.clean(s.get("narration") or s.get("text"))]
    if len(scenes) < 2:
        raise ValueError("The script needs at least two scenes.")
    tags = [re.sub(r"[^\w]", "", str(t)).lower() for t in data.get("hashtags") or []]
    return {
        "title": cs.clean(data.get("title"), 90) or "Untitled",
        "keyword": cs.clean(data.get("keyword"), 40),
        "series": cs.clean(data.get("series"), 60),
        "hook": cs.clean(data.get("hook"), 200),
        "caption": cs.clean(data.get("caption"), 1500),
        "hashtags": [t for t in tags if t][:8],
        "scenes": [{"text": cs.clean(s.get("text") or s.get("narration"), 120),
                    "narration": cs.clean(s.get("narration") or s.get("text"), 400),
                    "picture": cs.clean(s.get("picture") or s.get("text"), 300)} for s in scenes[:10]],
    }


async def write_script(client, settings: Settings, account: dict, idea: str = "", recent: list[str] | None = None) -> dict:
    prompt = SCRIPT_PROMPT.format(
        name=account["name"], theme=account["theme"], format=cs.FORMATS[account["format"]],
        series=", ".join(account.get("series") or []) or "none yet; pick a catchy repeatable one",
        look=cs.STYLES[account["style"]], recent="; ".join((recent or [])[-30:]) or "none yet",
        idea=f"Today's idea from the user: {idea}" if idea else "Pick today's idea yourself.")
    reply = await client.messages.create(model=settings.model, max_tokens=4000,
                                         messages=[{"role": "user", "content": prompt}])
    text = "".join(getattr(b, "text", "") for b in reply.content)
    return parse_script(text)


# ---- 2. pictures -------------------------------------------------------------------------------------------

async def fetch_picture(http: httpx.AsyncClient, description: str, style: str, seed: int, size=(1024, 1024)) -> Image.Image | None:
    prompt = f"{description}. {LOOKS.get(style, LOOKS['cinematic'])}"
    url = PICTURE_URL.format(prompt=quote(prompt[:900]), w=size[0], h=size[1], seed=seed)
    for _ in range(2):
        try:
            resp = await http.get(url, timeout=120, follow_redirects=True)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                from io import BytesIO
                return Image.open(BytesIO(resp.content)).convert("RGB")
        except (httpx.HTTPError, OSError):
            pass
    return None


def blank_picture(size=(1024, 1024)) -> Image.Image:
    """A soft dark gradient, used when a picture can't be fetched."""
    im = Image.linear_gradient("L").resize(size).point(lambda v: 20 + v // 5)
    return Image.merge("RGB", (im, im, im))


# ---- 3. frames ---------------------------------------------------------------------------------------------

def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def centred(draw, y: int, text: str, font, fill, width: int = 900, gap: int = 10, stroke: int = 0) -> int:
    """Draw wrapped centred text from y down; returns the y below it."""
    for line in wrap(draw, text, font, width):
        box = draw.textbbox((0, 0), line, font=font, stroke_width=stroke)
        draw.text(((W - (box[2] - box[0])) / 2, y), line, font=font, fill=fill, stroke_width=stroke,
                  stroke_fill="black")
        y += box[3] - box[1] + gap
    return y


def grain(im: Image.Image, amount: int = 18, seed: int = 0) -> Image.Image:
    noise = Image.effect_noise((W // 2, H // 2), amount).resize((W, H)).convert("RGB")
    return Image.blend(im, noise, 0.06)


def noir_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    grey = ImageOps.grayscale(picture).convert("RGB")
    bg = ImageOps.fit(grey, (W, H)).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.38)
    draw = ImageDraw.Draw(bg)
    card, top, left = 640, 560, (W - 640) // 2 - 70
    # a record peeking out from behind the card, like an album sleeve
    cx, cy, r = left + card - 20, top + card // 2, card // 2 - 10
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(12, 12, 12))
    for ring in range(r - 12, 60, -14):
        draw.ellipse((cx - ring, cy - ring, cx + ring, cy + ring), outline=(34, 34, 34), width=2)
    draw.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), fill=(200, 200, 200))
    draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(10, 10, 10))
    bg.paste(ImageEnhance.Contrast(ImageOps.fit(grey, (card, card))).enhance(1.15), (left, top))
    draw.rectangle((left, top, left + card - 1, top + card - 1), outline=(235, 235, 235), width=2)
    y = centred(draw, top + card + 40, script["title"], ac.font(40), (240, 240, 240))
    centred(draw, y + 2, f"@{account['name']}", ac.font(30), (150, 150, 150))
    centred(draw, 1480, scene["text"], ac.font(46), (255, 255, 255), width=860, stroke=2)
    return grain(bg)


def explainer_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    im = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(im)
    accent = ac.hex_colour(account.get("accent"), "#e8c547")
    keyword = script["keyword"] or script["title"]
    y = centred(draw, 250, f"“{keyword.upper()}”" if '"' not in keyword else keyword, ac.font(72), accent)
    centred(draw, y + 14, script["hook"] or script["title"], ac.font(34), (190, 190, 190), width=820)
    art = ImageOps.fit(picture, (860, 860))
    # blend the picture's own dark background into the page
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).ellipse((-120, -120, 980, 980), fill=255)
    im.paste(art, ((W - 860) // 2, 560), mask.filter(ImageFilter.GaussianBlur(60)))
    centred(draw, 1470, scene["text"], ac.font(50), (250, 250, 250), width=880)
    centred(draw, 1760, f"@{account['name']}", ac.font(26), (110, 110, 110))
    return im


def cinematic_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    im = ImageOps.fit(picture, (W, H))
    shade = Image.linear_gradient("L").resize((W, H)).point(lambda v: max(0, v - 90) * 2)
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, shade.point(lambda v: min(200, v)))
    draw = ImageDraw.Draw(im)
    centred(draw, 1420, scene["text"], ac.font(54), (255, 255, 255), width=900, stroke=3)
    centred(draw, 1780, f"@{account['name']}", ac.font(28), (200, 200, 200))
    return im


def drama_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    im = ImageOps.fit(picture, (W, H))
    draw = ImageDraw.Draw(im, "RGBA")
    centred(draw, 900, account["name"], ac.font(44), (255, 255, 255, 70))  # faint watermark, like the page
    font = ac.font(50)
    lines = wrap(draw, scene["text"], font, 860)
    tall = sum(draw.textbbox((0, 0), l, font=font)[3] + 12 for l in lines)
    top = 1330
    draw.rectangle((70, top - 26, W - 70, top + tall + 20), fill=(255, 255, 255, 245))
    draw.rectangle((W - 90, top - 26, W - 70, top + tall + 20), fill=(250, 215, 0, 255))  # the yellow edge
    draw.rectangle((70, top + tall + 14, W - 70, top + tall + 20), fill=(250, 215, 0, 255))
    centred(draw, top, scene["text"], font, (10, 10, 10), width=860, gap=12)
    return im


FRAMES = {"drama": drama_frame, "noir": noir_frame, "explainer": explainer_frame, "cinematic": cinematic_frame}


def frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    return FRAMES.get(account.get("style"), noir_frame)(picture, account, script, scene)


# ---- 4. voice ----------------------------------------------------------------------------------------------

async def narrate(http: httpx.AsyncClient, settings: Settings, text: str, voice: str, target: Path) -> bool:
    """Save the narration as an MP3; False when no voice is available."""
    audio = await tts.synthesize(http, settings, text) if settings.elevenlabs_api_key and not voice else None
    if audio:
        target.write_bytes(audio)
        return True
    try:
        import edge_tts
        await edge_tts.Communicate(text, voice or settings.creator_voice or DEFAULT_VOICE, rate="+6%").save(str(target))
        return target.exists() and target.stat().st_size > 0
    except Exception as exc:  # no internet, or edge-tts missing
        print(f"[jarvis] Story voice failed: {exc}", flush=True)
        return False


# ---- 5. video ----------------------------------------------------------------------------------------------

def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def audio_seconds(path: Path) -> float:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else 0.0


def reading_seconds(text: str) -> float:
    return max(2.5, len(text.split()) / 2.6 + 0.8)


def run(args: list[str]) -> None:
    done = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"ffmpeg failed: {done.stderr[-400:]}")


def render_scene(image: Path, audio: Path | None, seconds: float, out: Path) -> None:
    frames = max(1, round(seconds * FPS))
    zoom = (f"scale={int(W * 1.2)}:{int(H * 1.2)},zoompan=z='min(1+on*0.00045,1.08)':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p")
    inputs = ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
    inputs += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    run([*inputs, "-filter_complex", f"[0:v]{zoom}[v];[1:a]apad,aresample=44100[a]", "-map", "[v]", "-map", "[a]",
         "-frames:v", str(frames), "-t", f"{frames / FPS:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])


def join(parts: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)])
    listing.unlink(missing_ok=True)


async def make(client, http: httpx.AsyncClient, settings: Settings, account: dict, folder: Path,
               idea: str = "", recent: list[str] | None = None, script: dict | None = None) -> dict:
    """Write, picture, voice and render one video into folder. Returns the script plus the MP4 path."""
    script = script or await write_script(client, settings, account, idea, recent)
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    seed = random.randint(1, 10**6)
    pictures = await asyncio.gather(*(fetch_picture(http, s["picture"], account["style"], seed) for s in script["scenes"]))
    parts = []
    for i, (scene, picture) in enumerate(zip(script["scenes"], pictures)):
        still = work / f"scene{i}.png"
        await asyncio.to_thread(lambda: frame(picture or blank_picture(), account, script, scene).save(still))
        voice = work / f"scene{i}.mp3"
        has_voice = await narrate(http, settings, scene["narration"], account.get("voice", ""), voice)
        seconds = (await asyncio.to_thread(audio_seconds, voice)) + 0.35 if has_voice else 0
        seconds = seconds if seconds > 0.5 else reading_seconds(scene["narration"])
        part = work / f"scene{i}.mp4"
        await asyncio.to_thread(render_scene, still, voice if has_voice else None, seconds, part)
        parts.append(part)
    name = cs.slug(f"{script['title']}")
    video = folder / f"{name}.mp4"
    n = 2
    while video.exists():
        video, n = folder / f"{name} ({n}).mp4", n + 1
    await asyncio.to_thread(join, parts, work / "joined.mp4")
    (work / "joined.mp4").replace(video)
    (work / "scene0.png").replace(video.with_suffix(".png"))  # the cover picture
    for f in work.iterdir():
        f.unlink(missing_ok=True)
    work.rmdir()
    tags = " ".join(f"#{t}" for t in script["hashtags"])
    lines = [f"# {script['title']}", "", f"{script['caption']}", "", tags, "", "## Script", ""]
    lines += [f"{i}. {s['narration']}" for i, s in enumerate(script["scenes"], 1)]
    video.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {**script, "path": video, "missing_pictures": sum(p is None for p in pictures)}
