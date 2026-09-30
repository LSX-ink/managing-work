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
6. Video: ffmpeg (bundled by imageio-ffmpeg) gives each shot its own camera move, a soft swish on each cut, matches the scene to its
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
# who speaks a scene when it is a character's own line of dialogue, not the narrator
SPEAKERS = {"woman": "en-GB-SoniaNeural", "man": "en-US-GuyNeural", "old man": "en-GB-ThomasNeural",
            "old woman": "en-US-AriaNeural", "child": "en-US-AnaNeural"}
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
What this account's own view counts say works (follow these lessons): {lessons}
Your last few videos on this account (make today's clearly different from them: another mood, another kind of
opening line, another setting and point of view; a sequel keeps its story but still changes the mood or angle): {variety}
What's trending on TikTok for this niche right now (ride these where they fit, never copy anyone): {trends}
Story bible for this account (its recurring world: bring characters back where they fit, keep their looks
exactly the same, pay off or deepen open threads, and add new ones freely):
{bible}
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
- "pace" for each scene is how Alfred reads it, like a voice actor: "slow" for reveals, dread and the last line,
  "fast" for panic, chases and escalating lists, "normal" otherwise. Vary it; most scenes are normal.
- "speaker" for each scene is "narrator", or, when the whole scene is one character saying a line out loud (a
  voicemail, a scream, a whisper), who says it. For a named character (from the story bible or this video) put
  their name, so they keep the same voice in every video; otherwise "woman", "man", "old man", "old woman" or
  "child". Use a character voice for 1 to 3 lines that hit hard; everything else is the narrator.
- "bible": what this video adds to the story bible: characters it uses (name, look, notes, and voice_type:
  "woman", "man", "old man", "old woman" or "child"), threads it opens
  (open questions or mysteries to pay off in later videos), threads it closes, and the world in one line if it
  is new or has grown. Use {{}} for nothing.
- keyword: 1 to 3 words shown big at the top (e.g. ADHD, Letter "M", Unsent Letter #4).
- caption: one or two lines for the post, ending with a question. hashtags: 4 to 6, lower case, without #.
- cover: 2 to 5 punchy words shown big on screen over the first scene and on the cover (for example "SHE NEVER
  CALLED BACK"); it teases the story without giving the twist away and is not the same as the first spoken line.
- pinned_comment: the first comment to pin under the video, written as the account: a question or a small
  extra clue that gets people arguing their theories in the comments (under 150 characters).
- ambience: the quiet sound of the story's world under the voice: "rain", "wind", "city", "room", "night" or
  "none" (for explainers and anything without a place).
- mood: 2 or 3 words for the backing music (for example "tense slow piano", "eerie ambient", "upbeat hype").
- sound: one trending TikTok sound from the trends above that fits this story (name and artist), or a style of
  sound to search for if none fits. The user adds it in the TikTok app when posting.

Reply with ONLY this JSON:
{{"pitches": [{{"idea": "...", "score": 0}}], "title": "...", "keyword": "...", "series": "...", "character": "...",
  "hook": "...", "cover": "...", "caption": "...", "hashtags": ["..."], "mood": "...", "sound": "...", "pinned_comment": "...", "ambience": "none",
  "bible": {{"world": "...", "characters": [{{"name": "...", "look": "...", "notes": "...", "voice_type": "woman"}}], "threads_opened": ["..."], "threads_closed": ["..."]}},
  "scenes": [{{"text": "...", "narration": "...", "picture": "...", "closeup": "...", "pace": "normal", "speaker": "narrator"}}]}}"""

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


HOOK_PROMPT = """You write the first line of TikTok stories. Here is a finished script:
{script}

The first spoken line right now is: "{first}"

Write 8 alternative first lines for the SAME story, each a different technique: in medias res action, a shocking
specific detail, a direct question to the viewer, a confession, a countdown or number, a forbidden or secret angle,
a contradiction, and a line of dialogue. Each must be under 14 words, sayable in under 2 seconds, specific (names,
numbers, objects), and must flow straight into the second line: "{second}". No clickbait the story doesn't pay off.
Then score each one AND the current line 1 to 10 on "would I stop scrolling". Reply with ONLY this JSON:
{{"hooks": [{{"line": "...", "score": 0}}], "current": 0}}"""


RETENTION_PROMPT = """You are TikTok's retention analyst. Here is a finished script, one scene per line
(number | on-screen line | narration):
{scenes}

Watch it in your head like a viewer with their thumb over the screen. For every scene from 2 onwards, score 1 to
10 how sure you are they keep watching through it. Find the ONE scene where most people would swipe away (a
slow bit, a summary, a repeat, a lull after the hook, a line that tells instead of shows) and rewrite it so it
raises the stakes, reveals something, or opens a new question, keeping the same story, character and length and
flowing from the scene before into the scene after. Reply with ONLY this JSON:
{{"scores": [0], "weakest": 2, "why": "one short reason", "text": "new on-screen line under 12 words",
"narration": "new narration, one or two short sentences", "after": 0}}
"scores" lists scenes 2 onwards in order, "weakest" is the scene number and "after" your score for the rewrite."""


LESSONS_PROMPT = """You are the analyst for the TikTok account @{name} ({theme}). Here is every video with a view
count, one per line (views | title | first line | mood | scenes | editor's score | hook score | part | posted):
{rows}

Compare the top third with the bottom third. What do the winners share that the losers don't: the kind of first
line, the topic, the character, the mood, length, series parts, posting time? Reply with 3 to 6 short, concrete
lessons the writer must follow next time (for example "open on a named person mid-action, not a question"), each
backed by the numbers. Plain text, one lesson per line, under 900 characters. No preamble."""


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


async def learn_lessons(client, settings: Settings, account: dict, videos: list[dict]) -> str:
    """Short lessons from which of this account's videos got the most views, for the writer to follow."""
    rows = "\n".join(" | ".join(str(x) for x in (
        v.get("views", 0), v.get("title", ""), v.get("hook", ""), v.get("mood", "") or "-", v.get("scenes") or "-",
        v.get("score") or "-", v.get("hook_score") or "-", v.get("part", 1), v.get("posted_at") or v.get("made_at") or "-"))
        for v in sorted(videos, key=lambda v: v.get("views", 0), reverse=True))
    reply = await client.messages.create(model=settings.model, max_tokens=1500, messages=[
        {"role": "user", "content": LESSONS_PROMPT.format(name=account["name"], theme=account["theme"], rows=rows)}])
    return cs.clean("".join(getattr(b, "text", "") for b in reply.content), 1000)


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
        "mood": cs.clean(data.get("mood"), 80),
        "cover": cs.clean(data.get("cover"), 60),
        "ambience": str(data.get("ambience") or "").lower().strip() if str(data.get("ambience") or "").lower().strip()
        in AMBIENCE else "",
        "pinned_comment": cs.clean(data.get("pinned_comment"), 200),
        "sound": cs.clean(data.get("sound"), 200),
        "score": _score(data.get("score")),
        "bible": data.get("bible") if isinstance(data.get("bible"), dict) else {},
        "scenes": [{"text": cs.clean(s.get("text") or s.get("narration"), 120),
                    "narration": cs.clean(s.get("narration") or s.get("text"), 400),
                    "picture": cs.clean(s.get("picture") or s.get("text"), 300),
                    "closeup": cs.clean(s.get("closeup"), 300),
                    "pace": str(s.get("pace") or "").lower() if str(s.get("pace") or "").lower() in PACES else "normal",
                    "speaker": cs.clean(s.get("speaker"), 40).lower() or "narrator"}
                   for s in scenes[:14]],
    }


def _score(value) -> int:
    try:
        return max(0, min(10, round(float(value))))
    except (TypeError, ValueError):
        return 0


async def write_script(client, settings: Settings, account: dict, idea: str = "", recent: list[str] | None = None,
                       best: list[str] | None = None, taste: str = "", variety: str = "") -> dict:
    prompt = SCRIPT_PROMPT.format(variety=variety or "none yet",
        taste=taste or cs.taste_summary(account), bible=cs.bible_summary(account),
        name=account["name"], theme=account["theme"], format=cs.FORMATS[account["format"]],
        series=", ".join(account.get("series") or []) or "none yet; pick a catchy repeatable one",
        look=cs.STYLES[account["style"]], recent="; ".join((recent or [])[-30:]) or "none yet",
        best="; ".join(best or []) or "no view counts yet",
        trends=(account.get("trends") or {}).get("brief") or "not checked yet; use what you know works",
        lessons=(account.get("lessons") or {}).get("brief") or "not enough views yet",
        idea=f"Today's idea from the user: {idea}" if idea else "Pick today's idea yourself.")
    reply = await client.messages.create(model=settings.model, max_tokens=6000,
                                         messages=[{"role": "user", "content": prompt}])
    draft = parse_script("".join(getattr(b, "text", "") for b in reply.content))
    edited = await edit_script(client, settings, prompt, draft)
    return await fix_retention(client, settings, await pick_hook(client, settings, edited))


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
    edited["bible"] = edited["bible"] or draft["bible"]
    for key in ("cover", "mood", "sound", "pinned_comment", "ambience"):
        edited[key] = edited[key] or draft[key]
    return edited


async def pick_hook(client, settings: Settings, script: dict) -> dict:
    """Pits 8 new opening lines against the current one and keeps whichever stops the scroll best."""
    first, second = script["scenes"][0]["narration"], script["scenes"][1]["narration"]
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=2000, messages=[
            {"role": "user", "content": HOOK_PROMPT.format(first=first, second=second, script=json.dumps(
                [s["narration"] for s in script["scenes"]], ensure_ascii=False))}])
        match = re.search(r"\{.*\}", "".join(getattr(b, "text", "") for b in reply.content), re.S)
        data = json.loads(match.group(0)) if match else {}
    except Exception as exc:  # the API, or JSON that didn't parse: the current hook stands
        print(f"[jarvis] Hook test skipped: {exc}", flush=True)
        return script
    hooks = [(_score(h.get("score")), cs.clean(h.get("line"), 160)) for h in data.get("hooks") or []
             if isinstance(h, dict) and cs.clean(h.get("line"))]
    if not hooks:
        return script
    score, line = max(hooks, key=lambda h: h[0])
    if score <= _score(data.get("current")):
        return {**script, "hook_score": _score(data.get("current"))}
    opening = {**script["scenes"][0], "narration": line, "text": cs.clean(line, 120)}
    return {**script, "scenes": [opening, *script["scenes"][1:]], "hook": line, "hook_score": score,
            "old_hook": first}


async def fix_retention(client, settings: Settings, script: dict) -> dict:
    """Finds the scene viewers would most likely swipe away on and rewrites it, if the rewrite scores higher."""
    scenes = script["scenes"]
    if len(scenes) < 3:
        return script
    rows = "\n".join(f"{i} | {s['text']} | {s['narration']}" for i, s in enumerate(scenes, 1))
    try:
        reply = await client.messages.create(model=settings.model, max_tokens=1500, messages=[
            {"role": "user", "content": RETENTION_PROMPT.format(scenes=rows)}])
        match = re.search(r"\{.*\}", "".join(getattr(b, "text", "") for b in reply.content), re.S)
        data = json.loads(match.group(0)) if match else {}
        weakest = int(data.get("weakest"))
    except Exception as exc:  # the API, or JSON that didn't parse: the script stands
        print(f"[jarvis] Retention pass skipped: {exc}", flush=True)
        return script
    scores = [_score(x) for x in data.get("scores") or [] if isinstance(x, (int, float, str))]
    narration = cs.clean(data.get("narration"), 400)
    if not 2 <= weakest <= len(scenes) or not narration:
        return script
    before = scores[weakest - 2] if len(scores) >= weakest - 1 else 0
    after = _score(data.get("after"))
    if after <= before:
        return {**script, "retention": min(scores) if scores else 0}
    fixed = {**scenes[weakest - 1], "narration": narration, "text": cs.clean(data.get("text"), 120) or cs.clean(narration, 120)}
    scores[weakest - 2] = after
    return {**script, "scenes": [*scenes[:weakest - 1], fixed, *scenes[weakest:]], "retention": min(scores),
            "retention_fix": f"scene {weakest} rewritten ({before} to {after}/10): {cs.clean(data.get('why'), 160)}"}


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


HOOK_TEXT_Y = 190  # the top of the frame: clear of the captions, the drama box and TikTok's own buttons


def with_hook_text(im: Image.Image, text: str, accent, style: str = "") -> Image.Image:
    """Big on-screen hook text for the first scene and the cover: what makes a scroller stop before the voice
    lands. Explainer frames already open on a big headline, so they're left alone."""
    text = cs.clean(text, 60)
    if not text or style == "explainer":
        return im
    im = im.copy()
    draw = ImageDraw.Draw(im, "RGBA")
    font = ac.font(84)
    lines = wrap(draw, text.upper(), font, 900)[:3]
    tall = sum(draw.textbbox((0, 0), l, font=font, stroke_width=5)[3] + 8 for l in lines)
    draw.rectangle((0, HOOK_TEXT_Y - 50, W, HOOK_TEXT_Y + tall + 60), fill=(0, 0, 0, 90))
    y = centred(draw, HOOK_TEXT_Y, " ".join(lines), font, (255, 255, 255), width=900, gap=8, stroke=5)
    draw.rectangle((W // 2 - 90, y + 24, W // 2 + 90, y + 34), fill=accent)
    return im


def with_part_badge(im: Image.Image, part: int, accent) -> Image.Image:
    """A "PART 2" tag in the top corner of every scene of a sequel, so viewers know to look for part 1."""
    if part < 2:
        return im
    im = im.copy()
    draw = ImageDraw.Draw(im)
    font = ac.font(44)
    label = f"PART {part}"
    box = draw.textbbox((0, 0), label, font=font)
    draw.rounded_rectangle((60, 60, 60 + box[2] - box[0] + 48, 60 + box[3] - box[1] + 34), 14, fill=accent)
    draw.text((84, 72 - box[1]), label, font=font, fill=(0, 0, 0))
    return im


FRAMES = {"drama": drama_frame, "noir": noir_frame, "explainer": explainer_frame, "cinematic": cinematic_frame}


def frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    return FRAMES.get(account.get("style"), noir_frame)(picture, account, script, scene)


# ---- 4. voice ----------------------------------------------------------------------------------------------

PACES = {"slow": "-6%", "normal": "+6%", "fast": "+16%"}  # the free voice's speaking rate for each scene pace


async def narrate(http: httpx.AsyncClient, settings: Settings, text: str, voice: str, target: Path,
                  words: list | None = None, pace: str = "normal") -> bool:
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
            talk = edge_tts.Communicate(text, name, rate=PACES.get(pace, "+6%"), boundary="WordBoundary")
        except TypeError:  # an older edge-tts without word timings
            talk = edge_tts.Communicate(text, name, rate=PACES.get(pace, "+6%"))
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


WHOOSH = ("anoisesrc=d=0.45:c=pink:a=0.6:r=44100,highpass=f=350,lowpass=f=4200,"
          "afade=t=in:d=0.18,afade=t=out:st=0.18:d=0.27,volume=0.9,aformat=channel_layouts=stereo")


# The loop: the last scene ends on a short, slow settle into the video's very first frame, so when TikTok replays
# it the cut back to the start is seamless and the video feels like it never ended (rewatches push it out further).
LOOP_SECONDS = 0.8
LOOP_MOTION = ("1+0.04*(1-on/{n})", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")  # ends at zoom 1, where scene 1 starts


def render_scene(stills, audio: Path | None, seconds: float, out: Path, captions: Path | None = None, move: int = 0,
                 whoosh: bool = False, loop_to: Path | None = None) -> None:
    """One scene: its shots one after another (each with its own camera move), the captions on top, the voice under it,
    and (whoosh) a soft swish as it cuts in. loop_to (the last scene only) adds a short tail settling into that picture,
    the opening frame, so the video loops seamlessly."""
    stills = [stills] if isinstance(stills, (str, Path)) else list(stills)
    frames = max(1, round(seconds * FPS))
    split = [frames] if len(stills) == 1 else [round(frames * 0.55), frames - round(frames * 0.55)]
    motions = [MOTIONS[(move + i) % len(MOTIONS)] for i in range(len(stills))]
    if loop_to is not None:
        tail = max(1, round(LOOP_SECONDS * FPS))
        stills, split, motions = [*stills, loop_to], [*split, tail], [*motions, LOOP_MOTION]
        frames += tail
    inputs, chains = [], []
    for i, (image, n, (z, x, y)) in enumerate(zip(stills, split, motions)):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
        chains.append(f"[{i}:v]scale={int(W * 1.2)}:{int(H * 1.2)},zoompan=z='{z.format(n=max(1, n))}':d=1:"
                      f"x='{x.format(n=max(1, n))}':y='{y}':s={W}x{H}:fps={FPS},trim=end_frame={n},"
                      f"setpts=PTS-STARTPTS,setsar=1[s{i}]")
    k = len(stills)
    chains.append("".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[vc]")
    inputs += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    video = "[vc]"
    if captions:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(captions)]
        chains.append(f"[{k + 1}:v]format=rgba,setpts=PTS-STARTPTS[cap];[vc][cap]overlay=0:{CAPTION_Y}:eof_action=pass[vo]")
        video = "[vo]"
    chains.append(f"{video}format=yuv420p[v]")
    if whoosh:
        inputs += ["-f", "lavfi", "-i", WHOOSH]
        chains.append(f"[{k}:a]aresample=44100,aformat=channel_layouts=stereo[vo1];"
                      f"[vo1][{k + 1 + bool(captions)}:a]amix=inputs=2:duration=first:normalize=0,apad[a]")
    else:
        chains.append(f"[{k}:a]apad,aresample=44100[a]")
    run([*inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-frames:v", str(frames), "-t", f"{frames / FPS:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])


def music_for(folder: Path, mood: str = "") -> Path | None:
    """A backing track the user dropped in: the account's own Music folder first, then TikTok/Music for all accounts.
    Tracks whose name or subfolder matches the story's mood (Music/tense/..., "eerie piano.mp3") win."""
    tracks = []
    for place in (folder / "Music", folder.parent / "Music"):
        if place.is_dir():
            tracks = [p for p in place.rglob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".aac", ".ogg")]
            if tracks:
                break
    if not tracks:
        return None
    wanted = set(re.findall(r"[a-z]{3,}", mood.lower()))

    def fit(track: Path) -> int:
        return len(wanted & set(re.findall(r"[a-z]{3,}", " ".join(track.parts[-3:]).lower())))

    best = max(fit(t) for t in tracks)
    return random.choice([t for t in tracks if fit(t) == best])


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


# a quiet bed of room tone under the whole video, made by ffmpeg itself (no files needed): the scene's world
AMBIENCE = {
    "rain": "anoisesrc=c=pink:a=0.5,highpass=f=400,lowpass=f=6000,volume=0.38",
    "wind": "anoisesrc=c=brown:a=0.6,lowpass=f=500,tremolo=f=0.15:d=0.7,volume=0.25",
    "city": "anoisesrc=c=pink:a=0.4,bandpass=f=300:width_type=o:w=3,volume=0.45",
    "room": "anoisesrc=c=brown:a=0.3,lowpass=f=200,volume=0.4",
    "night": "anoisesrc=c=brown:a=0.3,lowpass=f=150,volume=0.55,aecho=0.8:0.6:600:0.3",
}


def add_ambience(video: Path, kind: str, out: Path) -> None:
    """Mix the chosen room tone quietly under the voice, fading in and out."""
    seconds = audio_seconds(video)
    run(["-i", str(video), "-f", "lavfi", "-t", f"{seconds:.3f}", "-i", f"{AMBIENCE[kind]},aresample=44100",
         "-filter_complex",
         f"[1:a]afade=t=in:d=1.5,afade=t=out:st={max(0.0, seconds - 2):.2f}:d=2[amb];"
         "[0:a][amb]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{seconds:.3f}",
         "-movflags", "+faststart", str(out)])


def join(parts: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)])
    listing.unlink(missing_ok=True)


async def make(client, http: httpx.AsyncClient, settings: Settings, account: dict, folder: Path,
               idea: str = "", recent: list[str] | None = None, script: dict | None = None,
               best: list[str] | None = None, taste: str = "", part: int = 1, variety: str = "") -> dict:
    """Write, picture, voice and render one video into folder. Returns the script plus the MP4 path."""
    script = script or await write_script(client, settings, account, idea, recent, best, taste, variety)
    cast = cs.assign_voices(account, script.get("bible"))  # named characters keep one voice across every video
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    seed = random.randint(1, 10**6)
    who = f"{script['character']}. " if script.get("character") else ""
    scenes = script["scenes"]
    pictures = await asyncio.gather(*(fetch_picture(http, who + s["picture"], account["style"], seed) for s in scenes))
    closeups = await asyncio.gather(*(fetch_picture(http, who + s["closeup"], account["style"], seed + 7)
                                      if s.get("closeup") else _none() for s in scenes))
    retried = await asyncio.gather(*(fetch_picture(http, who + s["picture"], account["style"], seed + 13)
                                     if p is None else _none() for s, p in zip(scenes, pictures)))
    pictures = [p or r for p, r in zip(pictures, retried)]
    missing = sum(p is None for p in pictures)
    pictures, closeups = fill_gaps(list(pictures), list(closeups))
    captions = captions_on(account)
    accent = ac.hex_colour(account.get("accent"), "#e8c547")
    shots, voices = [], []
    for i, (scene, picture, closeup) in enumerate(zip(scenes, pictures, closeups)):
        shown = {**scene, "captions": captions}
        opener = script.get("cover", "") if i == 0 else ""

        def draw_still(pic, path):
            still_image = with_hook_text(frame(pic, account, script, shown), opener, accent, account.get("style", ""))
            with_part_badge(still_image, part, accent).save(path)
        still = work / f"scene{i}.png"
        await asyncio.to_thread(draw_still, picture or blank_picture(), still)
        mine = [still]
        if closeup is not None:
            second = work / f"scene{i}b.png"
            await asyncio.to_thread(draw_still, closeup, second)
            mine.append(second)
        voice, words = work / f"scene{i}.mp3", []
        speaks = cast.get(scene.get("speaker", "")) or SPEAKERS.get(scene.get("speaker", ""), account.get("voice", ""))
        has_voice = await narrate(http, settings, scene["narration"], speaks, voice, words,
                                   scene.get("pace", "normal"))
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
        loop_to = shots[0][0] if i == len(shots) - 1 and i > 0 and account.get("loop", True) is not False else None
        await asyncio.to_thread(render_scene, mine, voice, seconds, part, track, i,
                                i > 0 and account.get("sfx", True) is not False, loop_to)
        parts.append(part)
    name = cs.slug(f"{script['title']}")
    video = folder / f"{name}.mp4"
    n = 2
    while video.exists():
        video, n = folder / f"{name} ({n}).mp4", n + 1
    await asyncio.to_thread(join, parts, work / "joined.mp4")
    if script.get("ambience") in AMBIENCE and account.get("ambience", True) is not False:
        try:
            await asyncio.to_thread(add_ambience, work / "joined.mp4", script["ambience"], work / "amb.mp4")
            (work / "amb.mp4").replace(work / "joined.mp4")
        except Exception as exc:
            print(f"[jarvis] Ambience skipped: {exc}", flush=True)
    track = music_for(folder, script.get("mood", ""))
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
    if script.get("sound"):
        lines += [f"Sound to add in TikTok: {script['sound']}", ""]
    if script.get("pinned_comment"):
        lines += [f"Pin this comment: {script['pinned_comment']}", ""]
    if script.get("hook_score"):
        lines += [f"Hook score: {script['hook_score']}/10"
                  + (f" (beat the first draft: \"{script['old_hook']}\")" if script.get("old_hook") else ""), ""]
    if script.get("retention_fix"):
        lines += [f"Retention pass: {script['retention_fix']}", ""]
    lines += ["## Script", ""]
    lines += [f"{i}. {s['narration']}" for i, s in enumerate(scenes, 1)]
    video.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {**script, "path": video, "missing_pictures": missing,
            "music": track.name if track else ""}


def fill_gaps(pictures: list, closeups: list) -> tuple[list, list]:
    """Scenes whose picture never came: use the scene's own close-up, else a mirrored, tighter crop of the nearest
    scene's picture, so a video never cuts to a blank gradient while other pictures exist."""
    for i, picture in enumerate(pictures):
        if picture is not None:
            continue
        if closeups[i] is not None:
            pictures[i], closeups[i] = closeups[i], None
            continue
        near = sorted((abs(j - i), j) for j, p in enumerate(pictures) if p is not None and j != i)
        if near:
            src = pictures[near[0][1]]
            w, h = src.size
            pictures[i] = ImageOps.mirror(src.crop((w // 8, h // 8, w - w // 8, h - h // 8)).resize((w, h)))
    return pictures, closeups


async def _none():
    return None
