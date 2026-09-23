"""Text-to-speech via ElevenLabs. Without an API key the browser's built-in voice is used instead."""

import re

import httpx

from config import Settings

CHUNK_CHARS = 400

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


async def synthesize(http: httpx.AsyncClient, settings: Settings, text: str) -> bytes | None:
    """MP3 audio for `text`, or None when ElevenLabs is not configured or fails."""
    if not settings.elevenlabs_api_key or not text.strip():
        return None
    audio = bytearray()
    for chunk in split_sentences(text):
        resp = await http.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"},
            json={
                "text": chunk,
                "model_id": elevenlabs_model(settings),
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            },
        )
        if resp.status_code != 200:
            print(f"[jarvis] ElevenLabs error {resp.status_code}: {resp.text[:200]}", flush=True)
            return None
        audio += resp.content
    return bytes(audio)
