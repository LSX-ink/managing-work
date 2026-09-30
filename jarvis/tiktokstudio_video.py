"""Alfred as author and director: writes a short vertical video, pictures it, voices it and cuts it to an MP4.

1. Script: Claude pitches five different ideas, picks the strongest and writes it as a story (hook in the first
   2 seconds, stakes, escalation, a twist, an ending that loops back to the start), in the account's theme,
   format and series, avoiding titles it used before and leaning towards what the user ticked, away from what
   they X-ed. A second pass, a tough editor, scores the draft and rewrites it tighter.
2. Pictures: two shots per scene (the main shot and a close-up) from Pollinations (free, no key), in the
   account's look, with the main character described the same way every time. If a picture can't be fetched,
   a plain dark frame is used so the video still gets made.
3. Frames: each picture is laid out in the account's style with Pillow (noir card, black explainer or
   cinematic), with the line for that scene written small on screen.
4. Voice: ElevenLabs when its key is set, otherwise Microsoft's free neural voices (edge-tts). No voice at all
   still makes a captioned video.
5. Captions: big word-by-word captions timed to the voice, the spoken word lit in the account's colour.
6. Video: ffmpeg (bundled by imageio-ffmpeg) gives each shot its own camera move, matches the scene to its
   narration and joins the scenes into one 1080x1920 MP4. A backing track dropped into the TikTok/Music folder
   (or the account's own Music folder) plays quietly underneath, dipping when Alfred speaks.
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
import tiktokstudio_store as cs
import tts
from config import Settings

W, H = 1080, 1920
FPS = 30
MIN_LENGTH = 61.0  # every video lasts at least a minute (TikTok's Creator Rewards only pays for 1 minute or more)
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
SCRIPT_PROMPT = """You are Alfred, the author and director of the TikTok account @{name}: a master storyteller with a
wild imagination, and one of the best short-form video makers on TikTok.
The account's theme: {theme}
Format: {format}
Series this account runs: {series}
Look: {look}

Write ONE new video for today. It must last at least one minute, ideally 65 to 90 seconds: 170 to 230 spoken words in total. {idea}
Titles already used (never repeat or closely copy these): {recent}
What did best on this account so far (do more of what works): {best}
What's trending on TikTok for this niche right now (ride these where they fit, never copy anyone): {trends}
What the user ticked and X-ed on this account (lean towards what they approved and away from what they rejected,
but be creative: a fresh idea in the spirit of the approved ones, never a copy):
{taste}

Imagination first:
- Before writing, pitch 5 wildly different ideas for today: a different premise, point of view, setting or genre
  twist each time. Skip the obvious first idea everyone would make. Score each 1 to 10 for how hard it stops the
  scroll, how original it is, its emotional punch and how much people will want to rewatch and share it, then
  write the best one.

Storytelling:
- The first line is the hook and must land in under 2 seconds: drop straight into the action or a line that
  shocks, and open a question the viewer has to see answered. Never open with a greeting, "Have you ever" or
  "In a world".
- One main character with a name, something they want and something at stake. Show, don't tell: concrete
  sensory details (a sound, a smell, one strange object) instead of summaries.
- Every scene raises the stakes or reveals something new. Re-hook every 3 or 4 scenes with a turn ("but that
  wasn't the strange part").
- Land a twist that changes what the start meant, then end on a line that loops back to the first line, so a
  rewatch feels new and people comment their theories.
- Write for the ear: short sentences, varied rhythm, present tense for stories, no filler, no cliches
  ("little did she know", "and that's when everything changed").

Rules:
- 10 to 14 scenes. Each scene has one short on-screen line (under 12 words) and the narration Alfred reads
  (one or two short sentences).
- Everything must be original, kind, and safe for TikTok: no real people, no brands, no medical or money
  promises, nothing hateful or sexual. For psychology, say "some people" and "often", never diagnose.
- "character": the main character described once in 15 to 30 words (age, face, hair, clothes), so every picture
  shows the same person. Leave it empty if there is no recurring person.
- "picture" is the main shot of the scene and "closeup" a second, different shot of the same moment (a detail,
  hands, an object, the eyes, another angle), each 10 to 25 words, for an image generator. No text in pictures.
- keyword: 1 to 3 words shown big at the top (e.g. ADHD, Letter "M", Unsent Letter #4).
- caption: one or two lines for the post, ending with a question. hashtags: 4 to 6, lower case, without #.

Reply with ONLY this JSON:
{{"pitches": [{{"idea": "...", "score": 0}}], "title": "...", "keyword": "...", "series": "...", "character": "...",
  "hook": "...", "caption": "...", "hashtags": ["..."],
  "scenes": [{{"text": "...", "narration": "...", "picture": "...", "closeup": "..."}}]}}"""

EDITOR_PROMPT = """You are the toughest short-form story editor on TikTok. A writer was given this brief:

<brief>
{brief}
</brief>

Here is their draft:
{draft}

Score the draft 1 to 10 on each of: hook (does the first line stop the scroll in 2 seconds), curiosity (is there a
question we must see answered), stakes, escalation, vivid specific details, twist, ending that loops back, and
spoken rhythm. Then rewrite it so every score would be 9 or 10: sharpen the hook, cut every weak, vague or generic
line, add specific details, make the twist land harder and the last line pay off the first. Keep the idea, the
character and the JSON shape, keep all the brief's rules and keep it 65 to 90 seconds (170 to 230 spoken words).
Add "scores" (your scores for the ORIGINAL draft) and "score" (1 to 10, your honest score for YOUR rewrite).
Reply with ONLY the JSON."""


TRENDS_PROMPT = """Search the web for what is trending on TikTok THIS WEEK for an account about: {theme}.
Find: 5 trending topics or story angles, 5 hashtags that are growing, video formats and hooks getting high
engagement (first-line styles, series, lengths, posting times), and 3 trending sounds that fit. Then reply with a
short plain-text brief (under 1200 characters) Alfred can use to plan the next videos. No links, no preamble."""


async def research_trends(client, settings: Settings, account: dict) -> str:
    """A short brief of this week's TikTok trends in the account's niche, found with Claude's web search."""
    import brain
    new_web = settings.model.startswith(brain._NEW_WEB_TOOLS)
    tool = {"type": "web_search_20260209" if new_web else "web_search_20250305", "name": "web_search", "max_uses": 5}
    messages = [{"role": "user", "content": TRENDS_PROMPT.format(theme=account["theme"])}]
    for _ in range(3):  # a long search can pause; carry on where it stopped
        reply = await client.messages.create(model=settings.model, max_tokens=3000, messages=messages, tools=[tool])
        if reply.stop_reason != "pause_turn":
            break
        messages = [*messages, {"role": "assistant", "content": reply.content}]
    text = "".join(getattr(b, "text", "") for b in reply.content if getattr(b, "type", "") == "text")
    return cs.clean(text, 1500)


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
        "character": cs.clean(data.get("character"), 300),
        "score": _score(data.get("score")),
        "scenes": [{"text": cs.clean(s.get("text") or s.get("narration"), 120),
                    "narration": cs.clean(s.get("narration") or s.get("text"), 400),
                    "picture": cs.clean(s.get("picture") or s.get("text"), 300),
                    "closeup": cs.clean(s.get("closeup"), 300)} for s in scenes[:14]],
    }


def _score(value) -> int:
    try:
        return max(0, min(10, round(float(value))))
    except (TypeError, ValueError):
        return 0


async def write_script(client, settings: Settings, account: dict, idea: str = "", recent: list[str] | None = None,
                       best: list[str] | None = None, taste: str = "") -> dict:
    prompt = SCRIPT_PROMPT.format(
        taste=taste or cs.taste_summary(account),
        name=account["name"], theme=account["theme"], format=cs.FORMATS[account["format"]],
        series=", ".join(account.get("series") or []) or "none yet; pick a catchy repeatable one",
        look=cs.STYLES[account["style"]], recent="; ".join((recent or [])[-30:]) or "none yet",
        best="; ".join(best or []) or "no view counts yet",
        trends=(account.get("trends") or {}).get("brief") or "not checked yet; use what you know works",
        idea=f"Today's idea from the user: {idea}" if idea else "Pick today's idea yourself.")
    reply = await client.messages.create(model=settings.model, max_tokens=6000,
                                         messages=[{"role": "user", "content": prompt}])
    draft = parse_script("".join(getattr(b, "text", "") for b in reply.content))
    return await edit_script(client, settings, prompt, draft)


async def edit_script(client, settings: Settings, brief: str, draft: dict) -> dict:
    """A second pass by a tough editor: scores the draft and rewrites it tighter. If the edit fails, the draft stands."""
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=6000, messages=[
            {"role": "user", "content": EDITOR_PROMPT.format(brief=brief, draft=json.dumps(draft, ensure_ascii=False))}])
        edited = parse_script("".join(getattr(b, "text", "") for b in reply.content))
    except Exception as exc:  # the API, or JSON the editor mangled
        print(f"[jarvis] Script edit skipped: {exc}", flush=True)
        return draft
    if len(edited["scenes"]) < max(2, len(draft["scenes"]) // 2):
        return draft  # the editor cut too much
    edited["character"] = edited["character"] or draft["character"]
    return edited


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
    if not scene.get("captions"):
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
    if not scene.get("captions"):
        centred(draw, 1470, scene["text"], ac.font(50), (250, 250, 250), width=880)
    centred(draw, 1760, f"@{account['name']}", ac.font(26), (110, 110, 110))
    return im


def cinematic_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    im = ImageOps.fit(picture, (W, H))
    shade = Image.linear_gradient("L").resize((W, H)).point(lambda v: max(0, v - 90) * 2)
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, shade.point(lambda v: min(200, v)))
    draw = ImageDraw.Draw(im)
    if not scene.get("captions"):
        centred(draw, 1420, scene["text"], ac.font(54), (255, 255, 255), width=900, stroke=3)
    centred(draw, 1780, f"@{account['name']}", ac.font(28), (200, 200, 200))
    return im


def drama_frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    im = ImageOps.fit(picture, (W, H))
    draw = ImageDraw.Draw(im, "RGBA")
    centred(draw, 900, account["name"], ac.font(44), (255, 255, 255, 45))  # faint watermark, like the page
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

async def narrate(http: httpx.AsyncClient, settings: Settings, text: str, voice: str, target: Path,
                  words: list | None = None) -> bool:
    """Save the narration as an MP3; False when no voice is available. With the free voice, words (if given) is
    filled with (start, end, word) timings in seconds, for the captions."""
    audio = await tts.synthesize(http, settings, text) if settings.elevenlabs_api_key and not voice else None
    if audio:
        target.write_bytes(audio)
        return True
    try:
        import edge_tts
        name = voice or settings.creator_voice or DEFAULT_VOICE
        try:
            talk = edge_tts.Communicate(text, name, rate="+6%", boundary="WordBoundary")
        except TypeError:  # an older edge-tts without word timings
            talk = edge_tts.Communicate(text, name, rate="+6%")
        with open(target, "wb") as out:
            async for chunk in talk.stream():
                if chunk.get("type") == "audio":
                    out.write(chunk["data"])
                elif chunk.get("type") == "WordBoundary" and words is not None:
                    start = chunk["offset"] / 1e7
                    words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
        return target.exists() and target.stat().st_size > 0
    except Exception as exc:  # no internet, or edge-tts missing
        print(f"[jarvis] Story voice failed: {exc}", flush=True)
        return False


# ---- 4b. captions ------------------------------------------------------------------------------------------
# Big word-by-word captions, the TikTok way: two or three words at a time in the lower third, the word being
# spoken lit up in the account's colour. Timed from the voice's word timings, or spread over the scene if there
# are none. Drama-style accounts keep their headline box instead.

CAPTION_Y, CAPTION_H = 1260, 420


def captions_on(account: dict) -> bool:
    return account.get("style") != "drama" and account.get("captions", True) is not False


def estimate_words(text: str, seconds: float, start: float = 0.1) -> list[tuple[float, float, str]]:
    """Spread the words over the time they're spoken, longer words taking longer."""
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 2 for w in words]
    step, t, out = max(0.1, seconds - start) / sum(weights), start, []
    for w, k in zip(words, weights):
        out.append((t, t + k * step, w))
        t += k * step
    return out


def chunks(words: list[tuple[float, float, str]], size: int = 3) -> list[list[tuple[float, float, str]]]:
    """Group words into short caption lines, breaking after punctuation."""
    out, line = [], []
    for w in words:
        line.append(w)
        if len(line) >= size or re.search(r"[.,!?;:…]$", w[2]):
            out.append(line)
            line = []
    return out + ([line] if line else [])


def caption_image(line: list[str], lit: int, accent) -> Image.Image:
    im = Image.new("RGBA", (W, CAPTION_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    size = 86
    font = ac.font(size)
    words = [w.upper() for w in line]
    space = draw.textlength(" ", font=font)
    while size > 44 and sum(draw.textlength(w, font=font) for w in words) + space * (len(words) - 1) > W - 120:
        size -= 6
        font = ac.font(size)
        space = draw.textlength(" ", font=font)
    x = (W - (sum(draw.textlength(w, font=font) for w in words) + space * (len(words) - 1))) / 2
    for i, w in enumerate(words):
        draw.text((x, CAPTION_H / 2 - size / 2), w, font=font, fill=accent if i == lit else (255, 255, 255),
                  stroke_width=7, stroke_fill=(0, 0, 0))
        x += draw.textlength(w, font=font) + space
    return im


def caption_track(words: list[tuple[float, float, str]], seconds: float, accent, work: Path, tag: str) -> Path | None:
    """A list of caption images with how long each shows, for ffmpeg's concat reader; None when there's nothing to say."""
    if not words:
        return None
    blank = work / f"{tag}-blank.png"
    Image.new("RGBA", (W, CAPTION_H), (0, 0, 0, 0)).save(blank)
    entries, t, n = [], 0.0, 0
    for line in chunks(words):
        for i, (start, end, _) in enumerate(line):
            start = min(max(start, t), seconds)
            if start - t > 0.02:
                entries.append((blank, start - t))
                t = start
            nxt = line[i + 1][0] if i + 1 < len(line) else end + 0.12
            until = min(max(nxt, start + 0.08), seconds)
            if until <= t:
                continue
            path = work / f"{tag}-{n}.png"
            caption_image([w[2] for w in line], i, accent).save(path)
            entries.append((path, until - t))
            t, n = until, n + 1
    if not n:
        return None
    if seconds - t > 0.02:
        entries.append((blank, seconds - t))
    listing = work / f"{tag}.txt"
    text = "".join(f"file '{p.name}'\nduration {d:.3f}\n" for p, d in entries)
    listing.write_text(text + f"file '{entries[-1][0].name}'\n", encoding="utf-8")  # the reader needs the last one twice
    return listing


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


def fit_to_length(voiced: list[float], length: float = MIN_LENGTH, gap: float = 0.35) -> list[float]:
    """Seconds per scene: each narration plus a short pause, and if that comes to under a minute the spare time is
    shared out so each picture holds a little longer. Longer stories keep their natural length."""
    base = [v + gap for v in voiced]
    spare = length - sum(base)
    if spare > 0:
        base = [b + spare / len(base) for b in base]
    frames = [round(b * FPS) for b in base]
    if spare > 0:
        frames[-1] += round(length * FPS) - sum(frames)
    return [f / FPS for f in frames]


MOTIONS = [  # a different camera move on each shot keeps the eye busy: push in, pull out, drift left, drift right
    ("min(1+on*0.0007,1.12)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("max(1.12-on*0.0007,1)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("1.12", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    ("1.12", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
]


def render_scene(stills, audio: Path | None, seconds: float, out: Path, captions: Path | None = None, move: int = 0) -> None:
    """One scene: its shots one after another (each with its own camera move), the captions on top, the voice under it."""
    stills = [stills] if isinstance(stills, (str, Path)) else list(stills)
    frames = max(1, round(seconds * FPS))
    split = [frames] if len(stills) == 1 else [round(frames * 0.55), frames - round(frames * 0.55)]
    inputs, chains = [], []
    for i, (image, n) in enumerate(zip(stills, split)):
        z, x, y = MOTIONS[(move + i) % len(MOTIONS)]
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
        chains.append(f"[{i}:v]scale={int(W * 1.2)}:{int(H * 1.2)},zoompan=z='{z}':d=1:x='{x.format(n=max(1, n))}':"
                      f"y='{y}':s={W}x{H}:fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,setsar=1[s{i}]")
    k = len(stills)
    chains.append("".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[vc]")
    inputs += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    video = "[vc]"
    if captions:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(captions)]
        chains.append(f"[{k + 1}:v]format=rgba,setpts=PTS-STARTPTS[cap];[vc][cap]overlay=0:{CAPTION_Y}:eof_action=pass[vo]")
        video = "[vo]"
    chains.append(f"{video}format=yuv420p[v];[{k}:a]apad,aresample=44100[a]")
    run([*inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-frames:v", str(frames), "-t", f"{frames / FPS:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])


def music_for(folder: Path) -> Path | None:
    """A backing track the user dropped in: the account's own Music folder first, then TikTok/Music for all accounts."""
    tracks = []
    for place in (folder / "Music", folder.parent / "Music"):
        if place.is_dir():
            tracks = [p for p in place.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".aac", ".ogg")]
            if tracks:
                break
    return random.choice(tracks) if tracks else None


def add_music(video: Path, track: Path, out: Path) -> None:
    """Lay the track quietly under the voice, dipping further whenever Alfred speaks, and fade it out at the end."""
    seconds = audio_seconds(video)
    run(["-i", str(video), "-stream_loop", "-1", "-i", str(track), "-filter_complex",
         "[0:a]asplit[v1][v2];[1:a]aresample=44100,volume=0.25[m];"
         "[m][v1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];"
         f"[duck]afade=t=out:st={max(0.0, seconds - 2.5):.2f}:d=2.5[bed];"
         "[v2][bed]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{seconds:.3f}",
         "-movflags", "+faststart", str(out)])


def join(parts: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)])
    listing.unlink(missing_ok=True)


async def make(client, http: httpx.AsyncClient, settings: Settings, account: dict, folder: Path,
               idea: str = "", recent: list[str] | None = None, script: dict | None = None,
               best: list[str] | None = None, taste: str = "") -> dict:
    """Write, picture, voice and render one video into folder. Returns the script plus the MP4 path."""
    script = script or await write_script(client, settings, account, idea, recent, best, taste)
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    seed = random.randint(1, 10**6)
    who = f"{script['character']}. " if script.get("character") else ""
    scenes = script["scenes"]
    pictures = await asyncio.gather(*(fetch_picture(http, who + s["picture"], account["style"], seed) for s in scenes))
    closeups = await asyncio.gather(*(fetch_picture(http, who + s["closeup"], account["style"], seed + 7)
                                      if s.get("closeup") else _none() for s in scenes))
    captions = captions_on(account)
    accent = ac.hex_colour(account.get("accent"), "#e8c547")
    shots, voices = [], []
    for i, (scene, picture, closeup) in enumerate(zip(scenes, pictures, closeups)):
        shown = {**scene, "captions": captions}
        still = work / f"scene{i}.png"
        await asyncio.to_thread(lambda: frame(picture or blank_picture(), account, script, shown).save(still))
        mine = [still]
        if closeup is not None:
            second = work / f"scene{i}b.png"
            await asyncio.to_thread(lambda: frame(closeup, account, script, shown).save(second))
            mine.append(second)
        voice, words = work / f"scene{i}.mp3", []
        has_voice = await narrate(http, settings, scene["narration"], account.get("voice", ""), voice, words)
        seconds = await asyncio.to_thread(audio_seconds, voice) if has_voice else 0
        shots.append(mine)
        voices.append((voice, seconds, words) if seconds > 0.3 else (None, reading_seconds(scene["narration"]), []))
    lengths = fit_to_length([v[1] for v in voices])
    parts = []
    for i, (mine, (voice, spoken, words), seconds) in enumerate(zip(shots, voices, lengths)):
        track = None
        if captions:
            timed = words or estimate_words(scenes[i]["narration"], spoken)
            track = await asyncio.to_thread(caption_track, timed, seconds, accent, work, f"cap{i}")
        part = work / f"scene{i}.mp4"
        await asyncio.to_thread(render_scene, mine, voice, seconds, part, track, i)
        parts.append(part)
    name = cs.slug(f"{script['title']}")
    video = folder / f"{name}.mp4"
    n = 2
    while video.exists():
        video, n = folder / f"{name} ({n}).mp4", n + 1
    await asyncio.to_thread(join, parts, work / "joined.mp4")
    track = music_for(folder)
    if track:
        try:
            await asyncio.to_thread(add_music, work / "joined.mp4", track, work / "scored.mp4")
            (work / "scored.mp4").replace(work / "joined.mp4")
        except Exception as exc:  # a track ffmpeg can't read: keep the voice-only cut
            print(f"[jarvis] Backing track skipped: {exc}", flush=True)
    (work / "joined.mp4").replace(video)
    (work / "scene0.png").replace(video.with_suffix(".png"))  # the cover picture
    for f in work.iterdir():
        f.unlink(missing_ok=True)
    work.rmdir()
    tags = " ".join(f"#{t}" for t in script["hashtags"])
    lines = [f"# {script['title']}", "", f"{script['caption']}", "", tags, ""]
    if script.get("score"):
        lines += [f"Editor's score: {script['score']}/10", ""]
    lines += ["## Script", ""]
    lines += [f"{i}. {s['narration']}" for i, s in enumerate(scenes, 1)]
    video.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {**script, "path": video, "missing_pictures": sum(p is None for p in pictures),
            "music": track.name if track else ""}


async def _none():
    return None
