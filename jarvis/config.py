"""Settings, read from environment variables (or a .env file next to this one)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("JARVIS_MODEL", "claude-opus-5")
    effort: str = os.getenv("JARVIS_EFFORT", "low")
    user_name: str = os.getenv("JARVIS_USER_NAME", "")
    user_address: str = os.getenv("JARVIS_USER_ADDRESS", "sir")
    city: str = os.getenv("JARVIS_CITY", "")
    tasks_file: str = os.getenv("JARVIS_TASKS_FILE", "")
    speech_lang: str = os.getenv("JARVIS_SPEECH_LANG", "en-GB")
    language: str = os.getenv("JARVIS_LANGUAGE", "English")
    persona: str = os.getenv("JARVIS_PERSONA", "jarvis").strip().lower()
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    elevenlabs_model: str = os.getenv("ELEVENLABS_MODEL", "")  # empty: picked from speech_lang
    enable_screen: bool = _bool("JARVIS_ENABLE_SCREEN", True)
    enable_web: bool = _bool("JARVIS_ENABLE_WEB", True)
    host: str = os.getenv("JARVIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("JARVIS_PORT", "8340"))


    @property
    def lang_code(self) -> str:
        """Primary language subtag of speech_lang, e.g. 'af' for 'af-ZA'."""
        return self.speech_lang.split("-")[0].lower()


settings = Settings()
