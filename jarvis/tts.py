"""Text-to-speech via ElevenLabs. Without an API key the browser's built-in voice is used instead."""

import re

import httpx

from config import Settings

CHUNK_CHARS = 400
FIRST_PART_MIN = 12  # a first sentence shorter than this ("Right.") is kept with the next one
VOICE_TIMEOUT = 15  # seconds to wait for ElevenLabs before the browser voice takes over

# Languages the fast Turbo v2.5 model speaks; anything else (e.g. Afrikaans) goes to Eleven v3.
TURBO_LANGS = {
    "ar", "bg", "cs", "da", "de", "el", "en", "es", "fi", "fil", "fr", "hi", "hr", "hu", "id", "it",
    "ja", "ko", "ms", "nl", "no", "pl", "pt", "ro", "ru", "sk", "sv", "ta", "tr", "uk", "vi", "zh",
}


def elevenlabs_model(settings: Settings) -> str:
    if settings.elevenlabs_model:
        return settings.elevenlabs_model
    return "eleven_turbo_v2_5" if settings.lang_code in TURBO_LANGS else "eleven_v3"


def split_sentences(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Group sentences into chunks of at most `limit` characters (a single long sentence stays whole)."""
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


async def _voice(http: httpx.AsyncClient, settings: Settings, chunk: str, model: str = "") -> bytes | None:
    """One chunk from ElevenLabs, or None when it fails (offline, slow, out of credit)."""
    try:
        resp = await http.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"},
            json={
                "text": chunk,
                "model_id": model or elevenlabs_model(settings),
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            },
            timeout=VOICE_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        print(f"[jarvis] ElevenLabs unreachable: {exc!r}", flush=True)
        return None
    if resp.status_code != 200:
        print(f"[jarvis] ElevenLabs error {resp.status_code}: {resp.text[:200]}", flush=True)
        return None
    return resp.content


async def synthesize(http: httpx.AsyncClient, settings: Settings, text: str) -> bytes | None:
    """MP3 audio for `text`, or None when ElevenLabs is not configured or fails."""
    if not settings.elevenlabs_api_key or not text.strip():
        return None
    audio = bytearray()
    for chunk in split_sentences(text):
        part = await _voice(http, settings, chunk)
        if part is None:
            return None
        audio += part
    return bytes(audio)


def live_model(settings: Settings) -> str:
    """Alfred's own replies use ElevenLabs' fastest model (Flash), so the first words come sooner.
    ELEVENLABS_MODEL still wins when it is set; other uses (videos) keep elevenlabs_model()."""
    if settings.elevenlabs_model:
        return settings.elevenlabs_model
    return "eleven_flash_v2_5" if settings.lang_code in TURBO_LANGS else "eleven_v3"


def speaking_parts(text: str) -> list[str]:
    """The opening sentence on its own, so the voice starts quickly, then the rest in normal-sized chunks."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    first = ""
    while sentences and len(first) < FIRST_PART_MIN:
        first = f"{first} {sentences.pop(0)}".strip()  # "Right." alone is too short: keep it with the next
    rest = " ".join(sentences)
    return [first, *split_sentences(rest)] if rest else ([first] if first else [])


async def stream(http: httpx.AsyncClient, settings: Settings, text: str):
    """Yield (text, MP3 audio or None) part by part, as each is ready. None means the browser voice says it.

    If ElevenLabs fails part-way, the rest is handed to the browser voice in one go rather than retried.
    """
    if not text.strip():
        return
    if not settings.elevenlabs_api_key:
        yield text, None
        return
    parts = speaking_parts(text)
    for i, part in enumerate(parts):
        audio = await _voice(http, settings, part, live_model(settings))
        if audio is None:
            yield " ".join(parts[i:]), None
            return
        yield part, audio
