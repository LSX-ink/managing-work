"""Kinetic Web Designs: a 30-second personal video of a lead's mock-up, to send with the first message.

make: opens the lead's mock-up page (Kinetic Web Designs/Mockups/<business>/index.html) in a phone-sized window and
records it scrolling slowly from top to bottom with Playwright, then lays a short voice-over on top (the business
name and their biggest problem, then "so we made you this" and "see your design before you pay anything"), spoken by
the same ElevenLabs voice Alfred uses (tts.py), and joins the two with ffmpeg into a vertical 1080x1920 MP4 (the
size TikTok, Reels and WhatsApp show full screen). It's saved as Mockups/<business>/<business> mock-up video.mp4,
for the user to attach to the message themselves.

The browser is found the same way as Alfred's own browser (browser.CHANNELS: Edge, then Chrome, then Playwright's
Chromium) but always runs headless, so no window ever opens, and it only ever loads the local mock-up file. Without
Playwright, a browser or ffmpeg there's no video, just one line saying why; without an ElevenLabs key the video is
silent. Nothing is uploaded or sent anywhere except the voice-over text to ElevenLabs.
"""

import asyncio
import importlib.util
import re
import shutil
import tempfile
from pathlib import Path

import httpx

import browser
import kinetic_store as st
import tts
import videojoin
from config import Settings
from tiktokstudio_video import ffmpeg

SECONDS = 30
WIDTH, HEIGHT = 1080, 1920  # vertical, full screen on a phone
VIEW = {"width": 540, "height": 960}  # a phone-sized window, recorded at twice the size
PAUSE_MS = 1500  # a still moment at the top and at the bottom
STEP_MS = 100


def video_file(name: str) -> str:
    """"<business> mock-up video.mp4" (kept short enough to attach)."""
    short = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()[:36].strip(" .") or "Your"
    return f"{short} mock-up video.mp4"


def missing() -> str:
    """Why a video can't be made on this PC ("" when it can): Playwright and ffmpeg are both needed."""
    if importlib.util.find_spec("playwright") is None:
        return "Playwright isn't installed (pip install -r requirements.txt)"
    exe = ffmpeg()
    if not (Path(exe).is_file() or shutil.which(exe)):
        return "ffmpeg isn't installed"
    return ""


def voice_script(name: str, line: str, me: str, made: str = "") -> str:
    """What the voice-over says: their name, the hook, the mock-up, the promise. About 15 to 20 seconds.
    made names the mock-up (default "a new home page"; a store makeover for a Shopify store)."""
    hook = re.sub(r"\s*\([^)]*\)", "", line or "").strip()  # "(joes.co.uk)" reads badly aloud
    return " ".join(x for x in (f"Hi, {name}.", hook, f"So we made you this: {made or 'a new home page'}, made for phones.",
                                st.PREVIEW, f"From {me}.") if x)


def record(html: Path, into: Path, seconds: int = SECONDS) -> Path:
    """The mock-up scrolling top to bottom in a phone-sized, headless browser, as a .webm. Runs on a worker thread."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError("Playwright isn't installed") from None
    with sync_playwright() as pw:
        last = None
        for channel in browser.CHANNELS:  # Edge, Chrome, then Playwright's own Chromium
            try:
                engine = pw.chromium.launch(channel=channel, headless=True)
                break
            except Exception as exc:  # that browser isn't on this PC: try the next
                last = exc
        else:
            raise ValueError(f"I couldn't start a browser to record it ({str(last).splitlines()[0][:120]})")
        try:
            context = engine.new_context(viewport=VIEW, device_scale_factor=2, is_mobile=True, has_touch=True,
                                         record_video_dir=str(into), record_video_size={"width": WIDTH,
                                                                                        "height": HEIGHT})
            page = context.new_page()
            page.goto(html.resolve().as_uri())
            page.wait_for_timeout(PAUSE_MS)
            tall = max(0, int(page.evaluate("document.documentElement.scrollHeight")) - VIEW["height"])
            steps = max(1, (seconds * 1000 - 2 * PAUSE_MS) // STEP_MS)
            for i in range(1, steps + 1):
                page.evaluate(f"window.scrollTo(0, {round(tall * i / steps)})")
                page.wait_for_timeout(STEP_MS)
            page.wait_for_timeout(PAUSE_MS)
            video = page.video
            context.close()  # finishes the recording
            return Path(video.path())
        finally:
            engine.close()


def encode(clip: Path, voice: Path | None, out: Path, seconds: int = SECONDS) -> None:
    """The recording as a 1080x1920 H.264 MP4 of exactly `seconds`, with the voice-over (or silence)."""
    picture = (f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
               f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration={seconds},"
               "fps=30,format=yuv420p[v]")
    sound = ["-i", str(voice)] if voice else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    videojoin.run(["-i", str(clip), *sound, "-filter_complex",
                   f"{picture};[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[a]",
                   "-map", "[v]", "-map", "[a]", "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                   str(out)])


async def voice_over(settings: Settings, text: str) -> bytes | None:
    """The voice-over as MP3 from ElevenLabs (tts.py), or None without a key or when it fails."""
    if not settings.elevenlabs_api_key:
        return None
    async with httpx.AsyncClient() as http:
        return await tts.synthesize(http, settings, text)


def build(settings: Settings, name: str, html: Path, audio: bytes | None) -> Path:
    """Record, then encode into Mockups/<business>/<business> mock-up video.mp4. Runs on a worker thread."""
    out = st.folder(settings, "Mockups", name) / video_file(name)
    with tempfile.TemporaryDirectory(prefix="kinetic-video-") as tmp:
        work = Path(tmp)
        voice = None
        if audio:
            voice = work / "voice.mp3"
            voice.write_bytes(audio)
        clip = record(html, work)
        encode(clip, voice, out)
    if not out.is_file():
        raise ValueError("ffmpeg didn't write the video")
    return out


async def make(settings: Settings, name: str, line: str, html: Path, made: str = "") -> tuple[Path | None, str]:
    """(the video, "") or (None, one line saying why there's no video). Never raises: the draft still comes."""
    why = missing()
    if why:
        return None, f"No video this time: {why}."
    if not html.is_file():
        return None, "No video this time: make the mock-up first."
    try:
        audio = await voice_over(settings, voice_script(name, line, st.business(settings)["name"], made))
        path = await asyncio.to_thread(build, settings, name, html, audio)
    except Exception as exc:  # no browser, ffmpeg trouble...: the message still goes without it
        return None, f"No video this time: {str(exc).splitlines()[0][:160] if str(exc) else type(exc).__name__}."
    return path, "" if audio else "The video is silent, as there's no ElevenLabs key for the voice-over."
