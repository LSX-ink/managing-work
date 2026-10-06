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
5. Captions: big word-by-word captions timed to the voice, the spoken word lit in the account's colour and the
   scene's key words ("punch") drawn bigger.
6. Video: ffmpeg (bundled by imageio-ffmpeg) gives each shot its own camera move, a soft swish on each cut (or
   the scene's sound effect: boom, heartbeat, buzz, glitch, sting), matches the scene to its
   narration and joins the scenes into one 1080x1920 MP4. A backing track dropped into the TikTok/Music folder
   (or the account's own Music folder) plays quietly underneath, dipping when Alfred speaks.
"""

import asyncio
import json
import math
import random
import re
import subprocess
import time
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
    "lore": ("hyper-detailed cinematic film still, photorealistic, moody low-key lighting, deep teal shadows and warm "
             "amber highlights, volumetric light, rain or haze in the air, sharp focus on the subject, intricate "
             "textures, shot on 35mm anamorphic lens, shallow depth of field, vertical 9:16 composition, no text"),
}
# Each look's narrator when the account names none: lore's is a warm, natural storyteller, far less robotic than
# the older voices (it falls back to DEFAULT_VOICE if the voice service doesn't know it).
STYLE_VOICES = {"lore": "en-US-AndrewMultilingualNeural"}
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
How the biggest videos in this style work (lore-style TikToks with 50,000+ likes, studied for what makes people
stay, rewatch and argue in the comments; borrow the techniques, never the stories or the words): {viral}
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

Make viewers think:
- Plant one small, fair clue early that most people miss the first time and that the twist proves right, so a
  rewatch rewards them.
- Leave one question honestly open at the end (who, why, or what happens next) that has more than one good answer,
  so people argue their theory in the comments instead of just reacting.
- Once in the middle, turn it on the viewer for a second ("you've done this too"), so the story is about them.
- The caption's question asks for their theory or what they'd do, never "did you like it".

Rules:
- 10 to 14 scenes. Each scene has one short on-screen line (under 12 words) and the narration Alfred reads
  (one or two short sentences).
- Everything must be original, kind, and safe for TikTok: no real people, no brands, no medical or money
  promises, nothing hateful or sexual. For psychology, say "some people" and "often", never diagnose.
- "character": the main character described once in 15 to 30 words (age, face, hair, clothes), so every picture
  shows the same person. Leave it empty if there is no recurring person.
- "picture" is the main shot of the scene and "closeup" a second, different shot of the same moment (a detail,
  hands, an object, the eyes, another angle), each 10 to 25 words, for an image generator. No text in pictures.
  "detail" is an optional third shot (a wide establishing shot, an insert of a clue, a reaction): give one on most
  scenes, so the picture changes every 2 seconds and nobody gets bored. Describe every shot like a film still: the
  light, the setting, textures and the emotion on the face, never a vague summary.
- "pace" for each scene is how Alfred reads it, like a voice actor: "slow" for reveals, dread and the last line,
  "fast" for panic, chases and escalating lists, "normal" otherwise. Vary it; most scenes are normal.
- "speaker" for each scene is "narrator", or, when the whole scene is one character saying a line out loud (a
  voicemail, a scream, a whisper), who says it. For a named character (from the story bible or this video) put
  their name, so they keep the same voice in every video; otherwise "woman", "man", "old man", "old woman" or
  "child". Use a character voice for 1 to 3 lines that hit hard; everything else is the narrator.
- "hit" for each scene is a sound effect as it starts, only where the story earns it (at most 3 per video):
  "boom" (a reveal or twist), "heartbeat" (dread, someone hiding), "buzz" (a phone vibrating, a message),
  "glitch" (something wrong, a memory breaking), "sting" (a realisation, a clue), or "none".
- "punch" for each scene is the 1 or 2 words of its narration that carry the scene (the number, the name, the
  twist word), copied exactly; the captions draw them bigger. Leave it empty for a scene with no stand-out word.
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
- teaser: the number of one later scene (3 or later) whose picture flashes on screen for under a second before
  the first line, like the biggest lore videos that open on the answer and then rewind: the most striking,
  most puzzling moment, never the twist itself, so viewers have to stay to see how it gets there. 0 for none.
- clue: the number of the scene that plants the small clue the twist proves right. As the twist lands, that
  scene's closeup flashes back on screen for a split second, so viewers realise it was there all along and rewatch
  to catch it. 0 if there is no planted clue.
- mood: 2 or 3 words for the backing music (for example "tense slow piano", "eerie ambient", "upbeat hype").
- sound: one trending TikTok sound from the trends above that fits this story (name and artist), or a style of
  sound to search for if none fits. The user adds it in the TikTok app when posting.

Reply with ONLY this JSON:
{{"pitches": [{{"idea": "...", "score": 0}}], "title": "...", "keyword": "...", "series": "...", "character": "...",
  "hook": "...", "cover": "...", "caption": "...", "hashtags": ["..."], "mood": "...", "sound": "...", "pinned_comment": "...", "ambience": "none", "teaser": 0, "clue": 0,
  "bible": {{"world": "...", "characters": [{{"name": "...", "look": "...", "notes": "...", "voice_type": "woman"}}], "threads_opened": ["..."], "threads_closed": ["..."]}},
  "scenes": [{{"text": "...", "narration": "...", "picture": "...", "closeup": "...", "detail": "...", "pace": "normal", "speaker": "narrator", "punch": ["..."], "hit": "none"}}]}}"""

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


VIRAL_PROMPT = """Search the web for TikTok videos with 50,000 or more likes in the same style as this account: {theme}.
Look at {look}
Find 5 to 8 of the most-liked recent ones in this style (lore, mysteries, unsolved stories, eerie history, dark
what-ifs) and study how they hold people: the exact kind of first line and first 2 seconds, how they re-hook in
the middle, the pacing and length, the narration voice, the on-screen text, the pictures and editing, and how they
end so viewers think, rewatch and comment their theories. Then reply with a plain-text playbook (under 1500
characters) of 6 to 10 concrete techniques Alfred should copy the method of, never the story, each one line, with
roughly how many likes the videos using it had. No links, no creator names, no preamble."""

VIRAL_DAYS = 3  # how often the viral study is redone: the top videos in a niche change slowly, and searches cost


async def study_viral(client, settings: Settings, account: dict) -> str:
    """A playbook of what the most-liked TikToks in this account's style do, found with Claude's web search."""
    return await _search_brief(client, settings, VIRAL_PROMPT.format(
        theme=account["theme"], look=cs.STYLES.get(account.get("style"), "")), 2000)


async def _search_brief(client, settings: Settings, prompt: str, limit: int) -> str:
    import brain
    new_web = settings.model.startswith(brain._NEW_WEB_TOOLS)
    tool = {"type": "web_search_20260209" if new_web else "web_search_20250305", "name": "web_search", "max_uses": 5}
    messages = [{"role": "user", "content": prompt}]
    for _ in range(3):  # a long search can pause; carry on where it stopped
        reply = await client.messages.create(model=settings.model, max_tokens=3000, messages=messages, tools=[tool])
        if reply.stop_reason != "pause_turn":
            break
        messages = [*messages, {"role": "assistant", "content": reply.content}]
    text = "".join(getattr(b, "text", "") for b in reply.content if getattr(b, "type", "") == "text")
    return cs.clean(text, limit)


async def research_trends(client, settings: Settings, account: dict) -> str:
    """A short brief of this week's TikTok trends in the account's niche, found with Claude's web search."""
    return await _search_brief(client, settings, TRENDS_PROMPT.format(theme=account["theme"]), 1500)


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

def loads_lenient(text: str):
    """JSON from Claude's reply, repaired when it's slightly broken: an unescaped quote or a line break inside a
    line of narration, a trailing comma, or a reply cut off near the end. Raises ValueError when nothing usable."""
    start = (text or "").find("{")
    if start < 0:
        raise ValueError("The script came back without any JSON.")
    end = text.rfind("}")
    try:
        return json.loads(text[start:end + 1], strict=False)  # strict=False allows raw line breaks in strings
    except ValueError:
        pass
    try:
        import json_repair  # handles stray quotes, missing commas and truncated output
    except ImportError:
        raise ValueError("The script's JSON is broken and the repair tool isn't installed: run "
                         ".venv\\Scripts\\python.exe -m pip install -r requirements.txt, then restart Alfred.") from None
    data = json_repair.loads(text[start:])
    if not isinstance(data, dict) or not data:
        raise ValueError("The script's JSON couldn't be repaired.")
    return data


def parse_script(text: str) -> dict:
    """The script JSON from Claude's reply (code fences and chatter around it are fine)."""
    data = loads_lenient(text)
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
        "teaser": _teaser(data.get("teaser")),
        "clue": _teaser(data.get("clue")),
        "bible": data.get("bible") if isinstance(data.get("bible"), dict) else {},
        "scenes": [{"text": cs.clean(s.get("text") or s.get("narration"), 120),
                    "narration": cs.clean(s.get("narration") or s.get("text"), 400),
                    "picture": cs.clean(s.get("picture") or s.get("text"), 300),
                    "closeup": cs.clean(s.get("closeup"), 300),
                    "detail": cs.clean(s.get("detail"), 300),
                    "pace": str(s.get("pace") or "").lower() if str(s.get("pace") or "").lower() in PACES else "normal",
                    "speaker": cs.clean(s.get("speaker"), 40).lower() or "narrator",
                    "punch": punch_words(s.get("punch")),
                    "hit": str(s.get("hit") or "").lower().strip() if str(s.get("hit") or "").lower().strip() in HITS
                    else ""}
                   for s in scenes[:14]],
    }


def _teaser(value) -> int:
    try:
        return max(0, min(14, int(value)))
    except (TypeError, ValueError):
        return 0


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
        viral=(account.get("viral") or {}).get("brief") or "not studied yet; use what you know the biggest lore videos do",
        idea=(f"Today's idea from the user: {idea}. Where it sets a length, style or wording rule (e.g. 'six lines', "
              "'no dashes'), follow it over the defaults in this brief.") if idea else "Pick today's idea yourself.")
    draft = await _script_reply(client, settings, prompt)
    edited = await edit_script(client, settings, prompt, draft)
    return await fix_retention(client, settings, await pick_hook(client, settings, edited))


def _keep_broken(settings: Settings, text: str) -> None:
    """Saves an unreadable script reply (Memory/TikTok/broken-scripts) so the fault can be looked at later."""
    try:
        folder = Path(settings.memory_dir) / "TikTok" / "broken-scripts"
        folder.mkdir(parents=True, exist_ok=True)
        for old in sorted(folder.glob("*.txt"))[:-19]:  # keep the newest 20
            old.unlink()
        (folder / f"{time.strftime('%Y-%m-%d %H-%M-%S')}.txt").write_text(text or "(empty reply)", encoding="utf-8")
    except OSError:
        pass


async def _script_reply(client, settings: Settings, prompt: str) -> dict:
    """Writes the script; when the JSON can't be read even after repair, Claude gets one go at fixing it,
    then the script is written afresh, before giving up."""
    error = None
    for _ in range(2):
        reply = await client.messages.create(model=settings.model, max_tokens=8000,
                                             messages=[{"role": "user", "content": prompt}])
        text = "".join(getattr(b, "text", "") for b in reply.content)
        try:
            return parse_script(text)
        except ValueError as exc:
            error = exc
            _keep_broken(settings, text)
            print(f"[jarvis] Script JSON unreadable ({exc}); asking for a fixed copy", flush=True)
        try:
            fixed = await client.messages.create(model=settings.model, max_tokens=8000, messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": text or "{}"},
                {"role": "user", "content": f"That JSON doesn't parse ({error}). Send the same script again as "
                                            "valid JSON only: escape every double quote inside text with a "
                                            "backslash, no line breaks inside strings, and nothing before or "
                                            "after the JSON."}])
            return parse_script("".join(getattr(b, "text", "") for b in fixed.content))
        except ValueError as exc:
            error = exc
    raise ValueError("I wrote the script four times but couldn't read it back, so nothing was filmed. Try again, "
                     f"perhaps with a different idea. (Last fault: {error})")


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
    for key in ("cover", "mood", "sound", "pinned_comment", "ambience", "teaser", "clue"):
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
        data = loads_lenient(match.group(0)) if match else {}
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
        data = loads_lenient(match.group(0)) if match else {}
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

FLAT_SPREAD = 4  # even a dark night shot varies more than this in brightness; a blank or solid fill (give or take
# compression noise) doesn't
SHAPE_SLACK = 0.1  # how far off the asked-for shape a picture may be before it's a "busy, try later" card


def usable_picture(picture: Image.Image, size) -> bool:
    """False for what the free picture service sends when it's struggling: a blank or solid-colour picture, or a
    small square notice card in place of the tall shot asked for. Either would sit on screen for seconds."""
    from PIL import ImageStat
    want, got = size[0] / size[1], picture.width / picture.height
    if abs(got - want) / want > SHAPE_SLACK:
        return False
    return max(ImageStat.Stat(picture.convert("L").resize((64, 64))).stddev) >= FLAT_SPREAD


async def fetch_picture(http: httpx.AsyncClient, description: str, style: str, seed: int, size=(1024, 1024)) -> Image.Image | None:
    prompt = f"{description}. {LOOKS.get(style, LOOKS['cinematic'])}"
    url = PICTURE_URL.format(prompt=quote(prompt[:900]), w=size[0], h=size[1], seed=seed)
    for _ in range(2):
        try:
            resp = await http.get(url, timeout=120, follow_redirects=True)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                from io import BytesIO
                picture = Image.open(BytesIO(resp.content)).convert("RGB")
                if usable_picture(picture, size):
                    return picture
                print("[jarvis] Picture came back blank or the wrong shape; asking again", flush=True)
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


FRAMES = {"drama": drama_frame, "noir": noir_frame, "explainer": explainer_frame, "cinematic": cinematic_frame,
          "lore": cinematic_frame}


# full-screen looks fill the whole 9:16 phone screen, so their pictures are asked for tall (same pixel budget as
# a square): the whole composition shows, sharper, instead of a square cropped to its middle and blown up 1.9x.
# The card looks (noir, explainer) frame a square picture, so they keep asking for squares.
TALL_PICTURE = (864, 1536)
TALL_STYLES = ("cinematic", "drama", "lore")
FULL_HD_STYLES = ("lore",)
THREE_SHOT_STYLES = ("lore",)  # a third shot per scene: the picture changes about every 2 seconds  # asked for at the phone's full 1080x1920, so fine detail survives the zoom


def picture_size(account: dict) -> tuple[int, int]:
    if account.get("style") in FULL_HD_STYLES:
        return (W, H)
    return TALL_PICTURE if account.get("style") in TALL_STYLES else (1024, 1024)


def frame(picture: Image.Image, account: dict, script: dict, scene: dict) -> Image.Image:
    return FRAMES.get(account.get("style"), noir_frame)(picture, account, script, scene)


# ---- 4. voice ----------------------------------------------------------------------------------------------

PACES = {"slow": "-6%", "normal": "+6%", "fast": "+16%"}  # the free voice's speaking rate for each scene pace


async def narrate(http: httpx.AsyncClient, settings: Settings, text: str, voice: str, target: Path,
                  words: list | None = None, pace: str = "normal", narrator: str = "") -> bool:
    """Save the narration as an MP3; False when no voice is available. With the free voice, words (if given) is
    filled with (start, end, word) timings in seconds, for the captions."""
    audio = await tts.synthesize(http, settings, text) if settings.elevenlabs_api_key and not voice else None
    if audio:
        target.write_bytes(audio)
        return True
    name = voice or narrator or settings.creator_voice or DEFAULT_VOICE  # an account's own voice wins
    for attempt in dict.fromkeys([name, DEFAULT_VOICE]):  # a voice the service doesn't know falls back to the default
        try:
            import edge_tts
            try:
                talk = edge_tts.Communicate(text, attempt, rate=PACES.get(pace, "+6%"), boundary="WordBoundary")
            except TypeError:  # an older edge-tts without word timings
                talk = edge_tts.Communicate(text, attempt, rate=PACES.get(pace, "+6%"))
            if words is not None:
                words.clear()
            with open(target, "wb") as out:
                async for chunk in talk.stream():
                    if chunk.get("type") == "audio":
                        out.write(chunk["data"])
                    elif chunk.get("type") == "WordBoundary" and words is not None:
                        start = chunk["offset"] / 1e7
                        words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
            if target.exists() and target.stat().st_size > 0:
                return True
        except Exception as exc:  # no internet, edge-tts missing, or an unknown voice
            print(f"[jarvis] Story voice {attempt} failed: {exc}", flush=True)
    return False


# ---- 4b. captions ------------------------------------------------------------------------------------------
# Big word-by-word captions, the TikTok way: two or three words at a time in the lower third, the word being
# spoken lit up in the account's colour. Timed from the voice's word timings, or spread over the scene if there
# are none. Drama-style accounts keep their headline box instead.

# TikTok's own buttons run down the right edge and its caption text covers the bottom ~420px, so captions sit
# above that and are kept SAFE_SIDE px in from both sides (centred, so they never hide under the like button).
CAPTION_Y, CAPTION_H = 1120, 420
SAFE_SIDE, SAFE_BOTTOM = 170, 1500


PUNCH_SCALE = 1.3  # how much bigger the scene's key words are drawn
LIT_SCALE = 1.12  # the word being spoken pops up a little as it's said, so the captions bounce along with the voice


def bare(word: str) -> str:
    """A word as it's compared: lower case, without the punctuation around it."""
    return re.sub(r"^[^\w#]+|[^\w%]+$", "", str(word).lower())


def punch_words(value) -> list[str]:
    """The scene's key words from the script: at most two, each one plain word."""
    items = value if isinstance(value, list) else str(value or "").split(",")
    out = []
    for item in items:
        for w in str(item).split():
            w = bare(w)[:30]
            if w and w not in out and len(out) < 2:
                out.append(w)
    return out


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


def caption_image(line: list[str], lit: int, accent, punch=()) -> Image.Image:
    """One caption line. The word being spoken is lit in the accent colour; the scene's key words ("punch") are
    drawn bigger and always in the accent colour, so they land even before they're said. Kept inside TikTok's safe
    zone: it shrinks to fit, and long words that still don't fit wrap onto a second row."""
    im = Image.new("RGBA", (W, CAPTION_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    words = [w.upper() for w in line]
    big = [bare(w) in punch for w in line]
    scale = [PUNCH_SCALE if b else (LIT_SCALE if i == lit else 1.0) for i, b in enumerate(big)]
    room = W - 2 * SAFE_SIDE

    def layout(size, rows):
        fonts = [ac.font(size * k) for k in scale]
        widths = [draw.textlength(w, font=f) for w, f in zip(words, fonts)]
        space = draw.textlength(" ", font=ac.font(size))
        totals = [sum(widths[a:b]) + space * (b - a - 1) for a, b in rows]
        return fonts, widths, space, totals
    size, rows = 86, [(0, len(words))]
    fonts, widths, space, totals = layout(size, rows)
    while size > 56 and max(totals) > room:
        size -= 6
        fonts, widths, space, totals = layout(size, rows)
    if max(totals) > room and len(words) > 1:  # two rows, split where the rows come out most even
        cut = min(range(1, len(words)), key=lambda c: abs(sum(widths[:c]) - sum(widths[c:])))
        rows = [(0, cut), (cut, len(words))]
        fonts, widths, space, totals = layout(size, rows)
    while size > 30 and max(totals) > room:
        size -= 4
        fonts, widths, space, totals = layout(size, rows)
    step = size * PUNCH_SCALE * 1.05
    first = CAPTION_H / 2 + size * 0.4 - step * (len(rows) - 1) / 2
    for r, ((a, b), total) in enumerate(zip(rows, totals)):
        x, baseline = (W - total) / 2, first + r * step
        for i in range(a, b):
            top = baseline - size * scale[i] * 0.8
            draw.text((x, top), words[i], font=fonts[i], fill=accent if i == lit or big[i] else (255, 255, 255),
                      stroke_width=9 if big[i] else 7, stroke_fill=(0, 0, 0))
            x += widths[i] + space
    return with_shadow(im)


SHADOW_DROP, SHADOW_BLUR, SHADOW_ALPHA = 6, 6, 0.6


def with_shadow(im: Image.Image) -> Image.Image:
    """A soft drop shadow under the caption, so white words stay readable over a bright sky or a white wall."""
    shade = im.getchannel("A").point(lambda a: int(a * SHADOW_ALPHA))
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 255), (0, SHADOW_DROP), shade.crop((0, 0, im.width, im.height - SHADOW_DROP)))
    return Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)), im)


POP_SECONDS, POP_SCALE = 2 / FPS, 0.86


def popped(image: Image.Image) -> Image.Image:
    """The caption shrunk a little about its centre: shown for a couple of frames before the full size, it makes
    each new line snap onto the screen the way TikTok's own captions do."""
    small = image.resize((round(image.width * POP_SCALE), round(image.height * POP_SCALE)), Image.LANCZOS)
    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    canvas.paste(small, ((image.width - small.width) // 2, (image.height - small.height) // 2))
    return canvas


def caption_track(words: list[tuple[float, float, str]], seconds: float, accent, work: Path, tag: str,
                  punch=()) -> Path | None:
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
            image = caption_image([w[2] for w in line], i, accent, punch)
            image.save(path)
            if i == 0 and until - t > 3 * POP_SECONDS:  # a fresh line pops in: two frames a touch smaller first
                pop = work / f"{tag}-{n}-pop.png"
                popped(image).save(pop)
                entries.append((pop, POP_SECONDS))
                t += POP_SECONDS
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


def video_facts(path: Path) -> str:
    """The finished video's length and file size for its notes, e.g. "1:04, 38.2 MB" ('' if it can't be read),
    so it's clear at a glance it clears TikTok's 1-minute mark and how big an upload it is."""
    try:
        seconds, size = audio_seconds(path), path.stat().st_size
    except Exception:
        return ""
    if seconds <= 0:
        return ""
    whole = round(seconds)
    return f"{whole // 60}:{whole % 60:02d}, {size / 1_000_000:.1f} MB"


DEAD_AIR_DB, DEAD_AIR_SECONDS = -50, 2.0  # quieter than this for this long counts as dead air
FREEZE_SECONDS = 3.0  # a picture that doesn't change at all for this long reads as a stalled video
LATE_START_SECONDS = 0.8  # silence this long at the very start loses the viewers who decide in the first second
DIM_LUMA = 45  # average brightness (16 = black, 235 = white) below this looks murky on a phone screen


def check_video(path: Path) -> list[str]:
    """Watch the finished video once before it's offered for approval, the way an editor would: too short for
    TikTok's 1-minute payouts, no sound at all, stretches of black screen, a picture frozen still, a picture too dark
    overall, a silent opening, or dead air (viewers swipe away from silence, from a picture that looks stuck and from murk). Returns the problems found."""
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path), "-vf", f"blackdetect=d=1.0:pix_th=0.06,freezedetect=n=0.001:d={FREEZE_SECONDS},"
                          "signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG",
                          "-af", f"volumedetect,silencedetect=n={DEAD_AIR_DB}dB:d={min(LATE_START_SECONDS, DEAD_AIR_SECONDS)}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    problems = []
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    seconds = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else 0.0
    if seconds < MIN_LENGTH - 0.5:
        problems.append(f"only {seconds:.0f} seconds long; TikTok pays for 1 minute or more")
    loudest = re.search(r"max_volume: (-?[\d.]+|-inf) dB", out)
    if not loudest or loudest[1] == "-inf" or float(loudest[1]) < -50:
        problems.append("there's no sound")
    else:
        gaps = [(float(a), float(d)) for a, d in re.findall(
            r"silence_start: (-?[\d.]+).*?silence_duration: ([\d.]+)", out, re.S)]
        opened = [float(a) for a in re.findall(r"silence_start: (-?[\d.]+)", out)]
        if len(opened) > len(gaps):  # still silent when the video ends, so ffmpeg never closes the gap
            gaps.append((opened[-1], max(0.0, seconds - opened[-1])))
        if gaps and gaps[0][0] <= 0.05:
            problems.append(f"the first {gaps[0][1]:.1f} seconds are silent; start the voice straight away to hook viewers")
        quiet = [d for _, d in gaps if d >= DEAD_AIR_SECONDS]
        if quiet:
            problems.append(f"{sum(quiet):.0f} seconds of dead air (silence of {DEAD_AIR_SECONDS:g}s or more)")
    black = sum(float(d) for d in re.findall(r"black_duration:([\d.]+)", out))
    if black >= 1.0:
        problems.append(f"{black:.0f} seconds of black screen")
    starts = [float(t) for t in re.findall(r"freeze_start: ([\d.]+)", out)]
    still = sum(float(d) for d in re.findall(r"freeze_duration: ([\d.]+)", out))
    if len(starts) > len(re.findall(r"freeze_end:", out)):  # still frozen when the video ends
        still += max(0.0, seconds - starts[-1])
    luma = [float(v) for v in re.findall(r"signalstats\.YAVG=([\d.]+)", out)]
    if luma and sum(luma) / len(luma) < DIM_LUMA and black < seconds / 2:
        problems.append("the picture is very dark overall; brighten it so it doesn't look murky on a phone")
    if still:
        problems.append(f"{still:.0f} seconds where the picture is frozen still ({FREEZE_SECONDS:g}s or more)")
    return problems


def reading_seconds(text: str) -> float:
    return max(2.5, len(text.split()) / 2.6 + 0.8)


def run(args: list[str]) -> None:
    done = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"ffmpeg failed: {done.stderr[-400:]}")


# the voice service leaves up to a second of silence after the last word; cut it back to a short breath so the
# pause between scenes is the one we choose (fit_to_length's gap), not dead air that makes viewers swipe
TAIL_TRIM = "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse"


def trim_tail(voice: Path) -> None:
    """Trim the silence after the last spoken word, in place. Word timings are untouched (only the end moves)."""
    out = voice.with_name(f"{voice.stem}-trim{voice.suffix}")
    run(["-i", str(voice), "-af", TAIL_TRIM, str(out)])
    if audio_seconds(out) > 0.3:  # never swap in an empty file
        out.replace(voice)
    else:
        out.unlink(missing_ok=True)


# and a little silence before the first word too: the scene should start talking the moment it cuts in
HEAD_TRIM = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04"


def trim_head(voice: Path) -> float:
    """Trim the silence before the first spoken word, in place. Returns the seconds removed, so the word timings
    (measured from the old start) can be moved earlier by the same amount."""
    before = audio_seconds(voice)
    out = voice.with_name(f"{voice.stem}-head{voice.suffix}")
    run(["-i", str(voice), "-af", HEAD_TRIM, str(out)])
    after = audio_seconds(out)
    if after <= 0.3:  # never swap in an empty file
        out.unlink(missing_ok=True)
        return 0.0
    out.replace(voice)
    return max(0.0, before - after)


def shift_words(words: list, by: float) -> None:
    """Move word timings earlier by `by` seconds, in place (never before 0)."""
    words[:] = [(max(0.0, a - by), max(0.0, b - by), w) for a, b, w in words]


# the breath after each scene and its share of any spare time follow the scene's pace: a fast scene snaps to the
# next, a slow one lingers on its picture, so padding a short story out to a minute doesn't flatten its rhythm
PACE_GAPS = {"fast": 0.2, "normal": 0.35, "slow": 0.6}
PACE_HOLD = {"fast": 0.5, "normal": 1.0, "slow": 1.6}
# The hook gets none of the spare time, and the two scenes after it only a little: the biggest videos move fastest at
# the start, where people decide whether to swipe, and spend their slack later once the story has them.
OPENING_HOLD = (0.0, 0.35, 0.6)
OPENING_FROM = 6  # only on a full-length story: with a handful of scenes, holding the opening back stretches the rest


def fit_to_length(voiced: list[float], length: float = MIN_LENGTH, gap: float = 0.35,
                  paces: list[str] | None = None) -> list[float]:
    """Seconds per scene: each narration plus a short pause, and if that comes to under a minute the spare time is
    shared out so each picture holds a little longer (slow scenes more, fast ones less, and the opening scenes least
    of all, so the video starts fast). Longer stories keep their natural length."""
    paces = paces or ["normal"] * len(voiced)
    base = [v + (PACE_GAPS.get(p, gap) if p != "normal" else gap) for v, p in zip(voiced, paces)]
    spare = length - sum(base)
    if spare > 0:
        opening = OPENING_HOLD if len(paces) >= OPENING_FROM else ()
        weights = [PACE_HOLD.get(p, 1.0) * (opening[i] if i < len(opening) else 1.0) for i, p in enumerate(paces)]
        base = [b + spare * w / sum(weights) for b, w in zip(base, weights)]
    frames = [round(b * FPS) for b in base]
    if spare > 0:
        frames[-1] += round(length * FPS) - sum(frames)
    return [f / FPS for f in frames]


MOTIONS = [  # a different camera move on each shot keeps the eye busy: push in, pull out, drift left, drift right
    ("min(1+on*{r},1.12)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("max(1.12-on*{r},1)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    ("1.12", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    ("1.12", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
]


WHOOSH = ("anoisesrc=d=0.45:c=pink:a=0.6:r=44100,highpass=f=350,lowpass=f=4200,"
          "afade=t=in:d=0.18,afade=t=out:st=0.18:d=0.27,volume=0.9,aformat=channel_layouts=stereo")
# The camera follows the scene's pace: a slow creep for reveals and dread, a quick push for panic.
PUSH_RATE = {"slow": 0.0004, "normal": 0.0007, "fast": 0.0014}
SHAKE_HITS = ("boom", "glitch")  # these hits jolt the camera for a moment as the scene cuts in
DIP_SECONDS = 0.3  # a slow scene (a reveal, dread) rises out of black instead of hard-cutting in: a beat to breathe
HIT_LOOKS = {  # and some hit the eye too, for the first fraction of a second: a white flash, a colour-split glitch
    "boom": "fade=t=in:st=0:d=0.18:color=white",
    "glitch": "rgbashift=rh=-18:bh=18:gv=6:enable='lt(t,0.25)',noise=alls=40:allf=t:enable='lt(t,0.25)'",
    "sting": "fade=t=in:st=0:d=0.1:color=white",
}
SHAKE = (",scale={w}:{h},crop={W}:{H}:x='(iw-{W})/2+22*sin(n*2.7)*max(0,1-n/10)'"
         ":y='(ih-{H})/2+16*cos(n*3.1)*max(0,1-n/10)'")


# A light sharpen after the pictures are scaled up and panned, so AI art (made at 1024px) doesn't look soft
# on a 1080x1920 phone screen; mild enough not to add halos or crunch the noise.
SHARPEN = "unsharp=5:5:0.7:5:5:0.0"
# A soft vignette that darkens the corners a touch, pulling the eye to the middle of the frame where the subject
# and the captions are (applied under the captions, so they stay clean white).
VIGNETTE = "vignette=angle=PI/7"
# A living film texture for looks that should feel like a movie, not a slideshow: grain that moves every frame and
# light that breathes very gently, so even a still picture never reads as frozen (under the captions, which stay clean).
ATMOSPHERES = {
    "film": "noise=alls=9:allf=t+u,eq=eval=frame:brightness='0.018*sin(2*PI*t*0.6)'",
}
STYLE_ATMOSPHERE = {"lore": "film"}


# A colour grade for the whole video, picked from the script's mood, so a horror story looks cold and a memory
# looks warm (applied under the captions, so they stay clean white).
GRADES = {
    "cold": "colorbalance=bs=0.10:bm=0.06:rs=-0.05:rh=-0.04,eq=saturation=0.85:contrast=1.06",
    "warm": "colorbalance=rs=0.08:rm=0.05:bs=-0.06:bh=-0.04,eq=saturation=1.05",
    "vivid": "eq=saturation=1.3:contrast=1.08",
    "faded": "eq=saturation=0.6:contrast=0.92:brightness=0.02",
}
GRADE_WORDS = {
    "cold": ("eerie", "tense", "dark", "horror", "creepy", "dread", "ominous", "suspense", "cold", "mystery", "thriller"),
    "warm": ("warm", "nostalgic", "romantic", "hopeful", "tender", "cozy", "sweet", "love"),
    "vivid": ("upbeat", "hype", "energetic", "fun", "happy", "bright", "party", "playful"),
    "faded": ("sad", "melancholy", "lonely", "grief", "memory", "somber", "bittersweet"),
}


def grade_for(mood: str, account: dict | None = None) -> str:
    """The grade's name for this mood ('' for none); an account can pin one with grade: 'cold' or turn it off."""
    pinned = (account or {}).get("grade")
    if pinned is False or pinned == "none":
        return ""
    if pinned in GRADES:
        return pinned
    words = set(re.findall(r"[a-z]+", str(mood).lower()))
    for name, keys in GRADE_WORDS.items():
        if words & set(keys):
            return name
    return ""


# Sound effects the script can cue on a scene's first beat, made by ffmpeg itself (no files needed). They replace
# that cut's swish, and only the first MAX_HITS in a video play, so they stay special.
HITS = {
    "boom": "aevalsrc='0.9*sin(2*PI*(75-45*t)*t)*exp(-2.5*t)':d=1.4:s=44100",
    "heartbeat": "aevalsrc='0.9*sin(2*PI*52*t)*(exp(-28*t)+0.8*exp(-28*(t-0.26))*gte(t,0.26))':d=0.9:s=44100",
    "buzz": "aevalsrc='0.3*sin(2*PI*170*t)*lt(mod(t,0.45),0.28)':d=0.95:s=44100",
    "glitch": "anoisesrc=d=0.35:c=white:a=0.5:r=44100,acrusher=bits=4:mode=log:aa=1,highpass=f=800,volume=0.6",
    "sting": "aevalsrc='0.35*sin(2*PI*880*t)*exp(-4*t)+0.25*sin(2*PI*1320*t)*exp(-5*t)':d=1.2:s=44100",
}
MAX_HITS = 3

# The riser: big lore videos build tension into a reveal with a low swell that grows under the last seconds of the
# scene before it, so the boom lands harder. Only before a boom or sting, and only for the styles that use it.
RISER_SECONDS = 2.5
RISER_HITS = ("boom", "sting")
RISER_STYLES = ("lore",)
RISER = ("anoisesrc=d={d}:c=pink:a=0.5:r=44100,highpass=f=300,lowpass=f=3000,"
         "afade=t=in:st=0:d={d}:curve=exp,volume=0.35,aformat=channel_layouts=stereo,adelay={delay}|{delay}")


# The loop: the last scene ends on a short, slow settle into the video's very first frame, so when TikTok replays
# it the cut back to the start is seamless and the video feels like it never ended (rewatches push it out further).
LOOP_SECONDS = 0.8

# The flash-forward: lore videos open on a split-second flash of a later, puzzling moment, then the story starts, so
# the viewer has seen where it's going and stays to find out how it gets there (the "open on the answer" trick).
TEASER_SECONDS = 0.6
TEASER_STYLES = ("lore",)
TEASER_MOTION = ("1.25-0.15*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")  # a quick pull back out of the moment
LOOP_MOTION = ("1+0.04*(1-on/{n})", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")  # ends at zoom 1, where scene 1 starts


# the sound is re-encoded once per step (scene, room tone, music, loudness); the in-between steps keep a high
# bitrate so the voice doesn't pick up a little more AAC fizz at every step, and only the finished video is squeezed
WORK_AUDIO, FINAL_AUDIO = "320k", "192k"

# the voice gets a light studio polish: rumble cut, a little presence so it cuts through on a phone speaker,
# a de-esser so that lift doesn't make the "s" sounds hiss, and gentle compression so quiet words aren't lost
VOICE_POLISH = ("highpass=f=80,equalizer=f=3000:t=q:w=1.2:g=3,deesser=i=0.4,"
                "acompressor=threshold=0.125:ratio=3:attack=5:release=80:makeup=1.5")
# a style's own narrator sound on top of the polish. "storyteller" is the late-night lore voice: warmer and fuller in
# the chest, the hiss rolled off, and a faint small-room echo, so it sounds like someone telling you a story in the
# dark rather than a text-to-speech read
# "close" is the last line, the one that loops back to the start: the room echo drops away and the voice comes in
# fuller and drier, as if the narrator leaned in to say it right in your ear. The change of sound makes the ending
# land as the ending, and the line people quote in the comments
VOICE_TONES = {"storyteller": "equalizer=f=140:t=q:w=1:g=3,equalizer=f=8000:t=h:w=3000:g=-2,aecho=0.85:0.5:35:0.1",
               "close": "equalizer=f=180:t=q:w=1:g=4,equalizer=f=8000:t=h:w=3000:g=-3,volume=0.9"}
STYLE_VOICE_TONE = {"lore": "storyteller"}
STYLE_LAST_TONE = {"lore": "close"}


# x264 with its "auto-variance" adaptive quantisation set to favour dark, flat areas: smooth gradients (night skies,
# the vignette's falloff, AI art's soft backgrounds) keep their bits instead of breaking into visible bands
VIDEO_CODEC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-x264-params", "aq-mode=3"]


EDGE_SECONDS = 0.015
EDGE_FADE = f",afade=t=in:d={EDGE_SECONDS},afade=t=out:st={{out:.3f}}:d={EDGE_SECONDS}"


# The still pictures come alive with the weather of the story's world: rain streaks falling past the camera, or dust
# drifting slowly through the light in a quiet room or at night, so a picture never sits dead still on screen.
# One tile is drawn per video (twice as tall as the screen, its two halves identical) and scrolled down behind the
# captions, so the fall loops seamlessly. (kind, pixels per second)
# A story with no weather of its own (an explainer, a place with no sound) still gets the faintest slow dust, so no
# lore video is ever "just a picture".
PARTICLES = {"rain": ("rain", 2400), "night": ("dust", 45), "room": ("dust", 35), "wind": ("dust", 160),
             "city": ("dust", 60)}
STILL_AIR = ("dust", 25)
PARTICLE_STYLES = ("lore",)


def particle_tile(kind: str, out: Path, seed: int = 0) -> Path:
    rng = random.Random(seed)
    tile = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    if kind == "rain":
        for _ in range(260):
            x, y, n = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 80)
            draw.line([(x, y), (x - n * 0.12, y + n)], fill=(220, 230, 255, rng.randint(35, 75)), width=2)
    else:
        for _ in range(110):
            x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.0, 3.5)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 245, 225, rng.randint(50, 120)))
        tile = tile.filter(ImageFilter.GaussianBlur(1.2))
    full = Image.new("RGBA", (W, 2 * H), (0, 0, 0, 0))
    full.paste(tile, (0, 0))
    full.paste(tile, (0, H))
    full.save(out)
    return out


# Lore viewers love the moment a twist proves a clue they saw earlier: as the reveal (the first "boom" after the
# planted clue) lands, the clue scene's closeup flashes back for the same split second as the opening teaser.
CLUE_STYLES = ("lore",)


def clue_flashback(shots: list, clue: int, played: list) -> dict:
    """{scene index: the still to flash at its start}: the clue scene's closeup, at the first boom after it."""
    if not 1 <= clue <= len(shots):
        return {}
    twist = next((i for i in range(clue, len(shots)) if i < len(played) and played[i] == "boom"), None)
    if twist is None:
        return {}
    clue_shots = shots[clue - 1]
    return {twist: clue_shots[1] if len(clue_shots) > 1 else clue_shots[0]}


def render_scene(stills, audio: Path | None, seconds: float, out: Path, captions: Path | None = None, move: int = 0,
                 whoosh: bool = False, loop_to: Path | None = None, hit: str = "", pace: str = "normal",
                 grade: str = "", dip: bool = False, atmosphere: str = "", teaser: Path | None = None,
                 tone: str = "", riser: bool = False, particles: tuple | None = None) -> None:
    """One scene: its shots one after another (each with its own camera move), the captions on top, the voice under it,
    and (whoosh) a soft swish as it cuts in. loop_to (the last scene only) adds a short tail settling into that picture,
    the opening frame, so the video loops seamlessly. hit (one of HITS) plays a sound effect as the scene starts,
    in place of the swish, and a boom or glitch shakes the camera as it lands
    (with a white flash or a colour-split glitch, HIT_LOOKS). pace sets how fast the camera pushes. teaser flashes
    another picture for TEASER_SECONDS before the scene's own shots, inside its length: a later moment on the first
    scene, or the planted clue on the twist scene."""
    stills = [stills] if isinstance(stills, (str, Path)) else list(stills)
    frames = max(1, round(seconds * FPS))
    split = [frames] if len(stills) == 1 else [round(frames * 0.55), frames - round(frames * 0.55)] if len(
        stills) == 2 else [round(frames * 0.4), round(frames * 0.3), frames - round(frames * 0.4) - round(frames * 0.3)]
    stills = stills[:3]
    motions = [MOTIONS[(move + i) % len(MOTIONS)] for i in range(len(stills))]
    if teaser is not None and split[0] > 1:
        flash = min(round(TEASER_SECONDS * FPS), split[0] // 2)  # never more than half the first shot
        stills, split, motions = [teaser, *stills], [flash, split[0] - flash, *split[1:]], [TEASER_MOTION, *motions]
    if loop_to is not None:
        tail = max(1, round(LOOP_SECONDS * FPS))
        stills, split, motions = [*stills, loop_to], [*split, tail], [*motions, LOOP_MOTION]
        frames += tail
    inputs, chains = [], []
    rate = PUSH_RATE.get(pace, PUSH_RATE["normal"])
    for i, (image, n, (z, x, y)) in enumerate(zip(stills, split, motions)):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
        shake = SHAKE.format(w=int(W * 1.04), h=int(H * 1.04), W=W, H=H) if i == 0 and hit in SHAKE_HITS else ""
        chains.append(f"[{i}:v]scale={int(W * 1.2)}:{int(H * 1.2)},zoompan=z='{z.format(n=max(1, n), r=rate)}':d=1:"
                      f"x='{x.format(n=max(1, n))}':y='{y}':s={W}x{H}:fps={FPS},trim=end_frame={n},"
                      f"setpts=PTS-STARTPTS,setsar=1{shake}[s{i}]")
    k = len(stills)
    graded = "".join(f",{f}" for f in (SHARPEN, GRADES.get(grade, ""), VIGNETTE, ATMOSPHERES.get(atmosphere, "")) if f)
    chains.append("".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0{graded}[vc]")
    inputs += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    effects = [f"{HITS[hit]},volume=0.8,aformat=channel_layouts=stereo" if hit in HITS else WHOOSH] if (
        hit in HITS or whoosh) else []
    if riser:
        swell = min(RISER_SECONDS, frames / FPS)
        effects.append(RISER.format(d=swell, delay=round((frames / FPS - swell) * 1000)))
    video = "[vc]"
    if particles:  # the particle layer is the last input, after the captions and the sound effects
        layer, speed = particles
        at = k + 1 + bool(captions) + len(effects)
        chains.append(f"[{at}:v]format=rgba,crop={W}:{H}:0:'{H}-mod(t*{speed},{H})'[pt];"
                      f"[vc][pt]overlay=0:0:shortest=1[vp]")
        video = "[vp]"
    if captions:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(captions)]
        chains.append(f"[{k + 1}:v]format=rgba,setpts=PTS-STARTPTS[cap];{video}[cap]overlay=0:{CAPTION_Y}:eof_action=pass[vo]")
        video = "[vo]"
    look = f"{HIT_LOOKS[hit]}," if hit in HIT_LOOKS else (f"fade=t=in:st=0:d={DIP_SECONDS}," if dip else "")
    chains.append(f"{video}{look}format=yuv420p[v]")
    polish = f"{VOICE_POLISH},{VOICE_TONES[tone] + ',' if tone in VOICE_TONES else ''}" if audio else ""
    edges = EDGE_FADE.format(out=max(0.0, frames / FPS - EDGE_SECONDS))
    if effects:
        first = k + 1 + bool(captions)
        for effect in effects:
            inputs += ["-f", "lavfi", "-i", effect]
        # the voice is padded to the scene's full length first, so an effect near the end (the riser) isn't cut off
        chains.append(f"[{k}:a]{polish}aresample=44100,aformat=channel_layouts=stereo,apad,atrim=0:{frames / FPS:.3f}[vo1];"
                      f"[vo1]{''.join(f'[{first + j}:a]' for j in range(len(effects)))}amix=inputs={1 + len(effects)}:"
                      f"duration=first:normalize=0,apad{edges}[a]")
    else:
        chains.append(f"[{k}:a]{polish}apad,aresample=44100{edges}[a]")
    if particles:
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(particles[0])]
    run([*inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-frames:v", str(frames), "-t", f"{frames / FPS:.3f}", "-r", str(FPS), *VIDEO_CODEC,
         "-c:a", "aac", "-b:a", WORK_AUDIO, "-ar", "44100", "-ac", "2", str(out)])


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


# most tracks open with a quiet intro; a full-length song starts MUSIC_SKIP seconds in (with a quick fade so it
# doesn't click), so the bed has energy from the first frame, when viewers decide whether to stay
MUSIC_SKIP, MUSIC_SKIP_FROM = 12.0, 45.0


# Big lore videos pull the music out from under the story just before the twist: a sudden half-second of silence
# makes people look up from the comments, then the "boom" lands on nothing but the voice. The bed slides out over
# DROP_FADE seconds, stays at DROP_LEVEL for the rest of the gap, and is back the moment the reveal scene starts.
DROP_SECONDS, DROP_FADE, DROP_LEVEL = 0.7, 0.15, 0.05
DROP_HITS = ("boom",)
DROP_STYLES = ("lore",)


def drop_gain(drops) -> str:
    """The music's volume over time (an ffmpeg expression in t): 1, except in the gap before each drop time."""
    if not drops:
        return "1"
    gaps = [f"(1-{1 - DROP_LEVEL:.2f}*clip((t-{at - DROP_SECONDS:.3f})/{DROP_FADE},0,1)*clip(({at:.3f}+0.05-t)/0.05,0,1))"
            for at in drops if at >= DROP_SECONDS]
    return "*".join(gaps) or "1"


def drop_times(lengths, played) -> list[float]:
    """When each reveal scene starts (its "boom"), from how long every scene before it runs."""
    starts = [sum(lengths[:i]) for i in range(len(lengths))]
    return [starts[i] for i, hit in enumerate(played[:len(lengths)]) if i > 0 and hit in DROP_HITS]


# ...and the narrator stops talking for that moment too: the scene before a reveal holds at least TWIST_BEAT seconds
# after its last word, so the music drop and the riser play in a real silence, the held breath before the twist.
TWIST_BEAT = DROP_SECONDS + 0.1


def twist_beats(lengths: list[float], voiced: list[float], played: list) -> list[float]:
    """The scene lengths with a beat of silence before every "boom" reveal (the scene before it stretched to fit)."""
    out = list(lengths)
    for i in range(len(out) - 1):
        if i + 1 < len(played) and played[i + 1] in DROP_HITS:
            out[i] = max(out[i], round((voiced[i] + TWIST_BEAT) * FPS) / FPS)
    return out


def add_music(video: Path, track: Path, out: Path, drops=()) -> None:
    """Lay the track quietly under the voice, dipping further whenever Alfred speaks, and fade it out at the end.
    At each of drops (seconds into the video) the music falls silent for a moment first, so the reveal hits."""
    seconds = audio_seconds(video)
    skip = MUSIC_SKIP if audio_seconds(track) > MUSIC_SKIP_FROM else 0.0
    fade_in = "afade=t=in:d=0.4," if skip else ""
    gain = drop_gain(drops)
    drop = f",volume='{gain}':eval=frame" if gain != "1" else ""
    run(["-i", str(video), "-stream_loop", "-1", "-ss", f"{skip:.2f}", "-i", str(track), "-filter_complex",
         f"[0:a]asplit[v1][v2];[1:a]aresample=44100,asetpts=N/SR/TB,{fade_in}volume=0.25{drop}[m];"
         "[m][v1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];"
         f"[duck]afade=t=out:st={max(0.0, seconds - 2.5):.2f}:d=2.5[bed];"
         "[v2][bed]amix=inputs=2:duration=first:normalize=0[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", WORK_AUDIO, "-t", f"{seconds:.3f}",
         "-movflags", "+faststart", str(out)])


# A score made by ffmpeg itself for the styles that need one, when the user hasn't dropped a track in a Music folder:
# big lore videos never run on a bare voice. A slow, dark A-minor drone (root, octave, minor third, fifth), each upper
# note breathing in and out at its own pace so it never sounds like a held organ key; tense moods add the flat
# second for unease. It goes through add_music, so it ducks under the voice like any track.
SCORE_STYLES = ("lore",)
SCORE_NOTES = {"calm": (55, 110, 130.81, 164.81), "tense": (55, 110, 116.54, 130.81, 164.81)}
TENSE_WORDS = ("tense", "dread", "eerie", "dark", "creepy", "suspense", "horror", "ominous", "uneasy")


def score_notes(mood: str) -> tuple:
    return SCORE_NOTES["tense" if any(w in (mood or "").lower() for w in TENSE_WORDS) else "calm"]


def make_score(seconds: float, mood: str, out: Path) -> None:
    notes = score_notes(mood)
    voices = [f"0.3*sin(2*PI*{notes[0]}*t)"] + [
        f"{0.16 / (1 + i * 0.3):.3f}*sin(2*PI*{f}*t)*(0.55+0.45*sin(2*PI*{0.03 + i * 0.017:.3f}*t+{i}))"
        for i, f in enumerate(notes[1:])]
    length = seconds + MUSIC_SKIP + 1  # longer than add_music can ever need, so it never loops with a click
    run(["-f", "lavfi", "-i", f"aevalsrc='{'+'.join(voices)}':s=44100:d={length:.2f}",
         "-af", "lowpass=f=1400,aecho=0.8:0.6:420:0.3,afade=t=in:d=3,volume=0.9", "-ac", "2", str(out)])


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
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", WORK_AUDIO, "-t", f"{seconds:.3f}",
         "-movflags", "+faststart", str(out)])


LOUDNESS = "loudnorm=I=-14:TP=-1.5:LRA=11"  # TikTok plays everything at about -14 LUFS; match it so nothing sounds quiet


def measure_loudness(video: Path) -> dict | None:
    """loudnorm's first pass: how loud the mix really is, so the levelling pass can apply one steady gain instead
    of riding the volume up and down as it goes (which pumps). None if it can't be measured."""
    try:
        out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(video), "-vn", "-af", f"{LOUDNESS}:print_format=json",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        found = json.loads(out[out.rindex("{"):out.rindex("}") + 1])
        values = {k: float(found[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    except Exception:
        return None
    return values if all(math.isfinite(v) for v in values.values()) else None  # pure silence measures -inf


def normalise(video: Path, out: Path) -> None:
    """Level the finished mix to TikTok's loudness, so the voice is as loud as the videos around it in the feed
    (a quiet video gets swiped), without clipping. Measured first, then levelled in one even pass, so the voice
    keeps its natural rise and fall. The picture is copied, not re-encoded."""
    m = measure_loudness(video)
    level = (f"{LOUDNESS}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
             f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true") if m else LOUDNESS
    run(["-i", str(video), "-af", f"{level},aresample=44100", "-map", "0:v", "-map", "0:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", FINAL_AUDIO, "-movflags", "+faststart", str(out)])


VOICE_TRIES = 2
VOICE_JOBS = 3  # scene voices fetched side by side (gentle on the voice service, much quicker than one by one)
RENDER_JOBS = 2  # scenes rendered side by side: most PCs have the cores, and it cuts the wait for a video a lot


async def render_all(jobs: list[tuple]) -> None:
    """Render every scene, RENDER_JOBS at a time (each is its own ffmpeg), keeping the first error if any fail."""
    gate = asyncio.Semaphore(RENDER_JOBS)

    async def one(job):
        async with gate:
            await asyncio.to_thread(render_scene, *job)
    results = await asyncio.gather(*(one(j) for j in jobs), return_exceptions=True)
    for r in results:
        if isinstance(r, BaseException):
            raise r


def join(parts: list[Path], out: Path) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out)])
    listing.unlink(missing_ok=True)


async def picture_or_retry(http, description: str, style: str, seed: int, size=(1024, 1024)):
    """A scene's main picture, asked for once more (a fresh seed) the moment it fails, so one slow failure
    doesn't hold every other scene back for a second round."""
    return (await fetch_picture(http, description, style, seed, size=size)
            or await fetch_picture(http, description, style, seed + 13, size=size))


async def make(client, http: httpx.AsyncClient, settings: Settings, account: dict, folder: Path,
               idea: str = "", recent: list[str] | None = None, script: dict | None = None,
               best: list[str] | None = None, taste: str = "", part: int = 1, variety: str = "") -> dict:
    """Write, picture, voice and render one video into folder. Returns the script plus the MP4 path."""
    script = script or await write_script(client, settings, account, idea, recent, best, taste, variety)
    cast = cs.assign_voices(account, script.get("bible"))  # named characters keep one voice across every video
    grade = grade_for(script.get("mood", ""), account)
    work = folder / f".{cs.new_id()}"
    work.mkdir(parents=True, exist_ok=True)
    seed = random.randint(1, 10**6)
    who = f"{script['character']}. " if script.get("character") else ""
    scenes = script["scenes"]
    gate = asyncio.Semaphore(VOICE_JOBS)

    async def voice_for(i, scene):  # every scene's voice is fetched at once (a few at a time), not one after another
        voice, words = work / f"scene{i}.mp3", []
        speaks = cast.get(scene.get("speaker", "")) or SPEAKERS.get(scene.get("speaker", ""), account.get("voice", ""))
        async with gate:
            for _ in range(VOICE_TRIES):  # the free voice service drops the odd request; one retry saves a silent scene
                words.clear()
                has_voice = await narrate(http, settings, scene["narration"], speaks, voice, words,
                                          scene.get("pace", "normal"), narrator=STYLE_VOICES.get(account.get("style"), ""))
                if has_voice:
                    break
        if has_voice:
            try:
                shift_words(words, await asyncio.to_thread(trim_head, voice))
                await asyncio.to_thread(trim_tail, voice)
            except Exception as exc:  # keep the untrimmed voice
                print(f"[jarvis] Voice trim skipped: {exc}", flush=True)
        seconds = await asyncio.to_thread(audio_seconds, voice) if has_voice else 0
        return (voice, seconds, words) if seconds > 0.3 else (None, reading_seconds(scene["narration"]), [])
    shape = picture_size(account)
    # voices, pictures and close-ups are all fetched at the same time: none of them waits for another
    voicing = asyncio.ensure_future(asyncio.gather(*(voice_for(i, scene) for i, scene in enumerate(scenes))))
    try:
        pictures, closeups, details = await asyncio.gather(
            asyncio.gather(*(picture_or_retry(http, who + s["picture"], account["style"], seed, size=shape)
                             for s in scenes)),
            asyncio.gather(*(fetch_picture(http, who + s["closeup"], account["style"], seed + 7, size=shape)
                             if s.get("closeup") else _none() for s in scenes)),
            asyncio.gather(*(fetch_picture(http, who + s["detail"], account["style"], seed + 13, size=shape)
                             if s.get("detail") and account.get("style") in THREE_SHOT_STYLES else _none()
                             for s in scenes)))
        missing = sum(p is None for p in pictures)
        pictures, closeups, details = fill_gaps(list(pictures), list(closeups), list(details))
        captions = captions_on(account)
        accent = ac.hex_colour(account.get("accent"), "#e8c547")
        shots = []
        for i, (scene, picture, closeup, detail) in enumerate(zip(scenes, pictures, closeups, details)):
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
            if detail is not None:
                third = work / f"scene{i}c.png"
                await asyncio.to_thread(draw_still, detail, third)
                mine.append(third)
            shots.append(mine)
        voices = list(await voicing)
    except BaseException:
        voicing.cancel()  # a failed picture or still must not leave voice fetches running
        raise
    lengths = fit_to_length([v[1] for v in voices], paces=[sc.get("pace", "normal") for sc in scenes])
    sfx = account.get("sfx", True) is not False
    played = []  # each scene's sound effect, at most MAX_HITS a video, worked out first so a riser can lead into one
    for scene in scenes:
        played.append(scene.get("hit", "") if sfx and sum(map(bool, played)) < MAX_HITS else "")
    if account.get("style") in DROP_STYLES:
        lengths = twist_beats(lengths, [v[1] for v in voices], played)
    async def track_for(i, spoken, words, seconds):
        if not captions:
            return None
        timed = words or estimate_words(scenes[i]["narration"], spoken)
        return await asyncio.to_thread(caption_track, timed, seconds, accent, work, f"cap{i}", scenes[i].get("punch", []))
    # every scene's caption pictures are drawn side by side rather than one scene after another
    tracks = await asyncio.gather(*(track_for(i, spoken, words, seconds)
                                    for i, ((_, spoken, words), seconds) in enumerate(zip(voices, lengths))))
    parts, jobs = [], []
    tease = script.get("teaser", 0)
    weather = PARTICLES.get(script.get("ambience", ""), STILL_AIR) if account.get("style") in PARTICLE_STYLES else None
    particles = (await asyncio.to_thread(particle_tile, weather[0], work / "particles.png", random.randint(1, 10**6)),
                 weather[1]) if weather else None
    flashback = clue_flashback(shots, script.get("clue", 0), played) if account.get("style") in CLUE_STYLES else {}
    teaser = shots[tease - 1][0] if account.get("style") in TEASER_STYLES and 3 <= tease <= len(shots) else None
    for i, (mine, (voice, spoken, words), seconds, track) in enumerate(zip(shots, voices, lengths, tracks)):
        part = work / f"scene{i}.mp4"
        loop_to = shots[0][0] if i == len(shots) - 1 and i > 0 and account.get("loop", True) is not False else None
        hit = played[i]
        pace = scenes[i].get("pace", "normal")
        jobs.append((mine, voice, seconds, part, track, i, i > 0 and sfx, loop_to, hit,
                     pace, grade, i > 0 and pace == "slow" and not hit, STYLE_ATMOSPHERE.get(account.get("style"), ""),
                     teaser if i == 0 else flashback.get(i),
                     (STYLE_LAST_TONE if i == len(shots) - 1 and i > 0 else STYLE_VOICE_TONE).get(account.get("style"), ""),
                     account.get("style") in RISER_STYLES and i + 1 < len(played) and played[i + 1] in RISER_HITS,
                     particles))
        parts.append(part)
    await render_all(jobs)
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
    if track is None and account.get("style") in SCORE_STYLES and account.get("music", True) is not False:
        try:
            await asyncio.to_thread(make_score, audio_seconds(work / "joined.mp4"), script.get("mood", ""),
                                    work / "score.wav")
            track = work / "score.wav"
        except Exception as exc:  # no score: the voice and room tone still carry it
            print(f"[jarvis] Score skipped: {exc}", flush=True)
    if track:
        try:
            # the drops are timed from the rendered scenes, which include any teaser flash at the start
            drops = (drop_times([audio_seconds(p) for p in parts], played)
                     if account.get("style") in DROP_STYLES else [])
            await asyncio.to_thread(add_music, work / "joined.mp4", track, work / "scored.mp4", drops)
            (work / "scored.mp4").replace(work / "joined.mp4")
        except Exception as exc:  # a track ffmpeg can't read: keep the voice-only cut
            print(f"[jarvis] Backing track skipped: {exc}", flush=True)
    try:
        await asyncio.to_thread(normalise, work / "joined.mp4", work / "loud.mp4")
        (work / "loud.mp4").replace(work / "joined.mp4")
    except Exception as exc:
        print(f"[jarvis] Loudness levelling skipped: {exc}", flush=True)
    (work / "joined.mp4").replace(video)
    try:
        checks = await asyncio.to_thread(check_video, video)
    except Exception as exc:  # the check is a safety net; never lose a finished video over it
        print(f"[jarvis] Quality check skipped: {exc}", flush=True)
        checks = []
    silent = [str(i + 1) for i, v in enumerate(voices) if v[0] is None]
    if silent:  # the voice service failed even after a retry: say which scenes, so they're checked before posting
        checks.append(f"no voice on scene{'s' if len(silent) > 1 else ''} {', '.join(silent)} "
                      "(the voice service failed; remake it)")
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
    facts = video_facts(video)
    if facts:
        lines += [f"Length: {facts}", ""]
    lines += [f"Quality check: {'; '.join(checks) if checks else 'passed'}", ""]
    if grade:
        lines += [f"Colour grade: {grade} (from the mood; set the account's grade to change it)", ""]
    lines += ["## Script", ""]
    lines += [f"{i}. {s['narration']}" for i, s in enumerate(scenes, 1)]
    video.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {**script, "path": video, "missing_pictures": missing, "checks": checks, "grade": grade,
            "music": track.name if track else ""}


def fill_gaps(pictures: list, closeups: list, details: list | None = None) -> tuple:
    """Scenes whose picture never came: use the scene's own close-up or detail shot (it shows that very moment),
    else a mirrored, tighter crop of the nearest scene's picture, so a video never cuts to a blank gradient while
    other pictures exist. Returns (pictures, closeups), plus details when they were given."""
    spare = details if details is not None else [None] * len(pictures)
    for i, picture in enumerate(pictures):
        if picture is not None:
            continue
        if closeups[i] is not None:
            pictures[i], closeups[i] = closeups[i], None
            continue
        if spare[i] is not None:
            pictures[i], spare[i] = spare[i], None
            continue
        near = sorted((abs(j - i), j) for j, p in enumerate(pictures) if p is not None and j != i)
        if near:
            src = pictures[near[0][1]]
            w, h = src.size
            pictures[i] = ImageOps.mirror(src.crop((w // 8, h // 8, w - w // 8, h - h // 8)).resize((w, h)))
    return (pictures, closeups) if details is None else (pictures, closeups, spare)


async def _none():
    return None
