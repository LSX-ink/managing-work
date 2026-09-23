"""Text-to-speech via ElevenLabs. Without an API key the browser's built-in voice is used instead."""

import re

import httpx

from config import Settings

CHUNK_CHARS = 400


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
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            },
        )
        if resp.status_code != 200:
            print(f"[jarvis] ElevenLabs error {resp.status_code}: {resp.text[:200]}", flush=True)
            return None
        audio += resp.content
    return bytes(audio)
