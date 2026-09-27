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


# IMAP servers for common email providers, used when JARVIS_EMAIL_IMAP_HOST is left empty.
IMAP_HOSTS = {
    "gmail.com": "imap.gmail.com", "googlemail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com", "hotmail.com": "outlook.office365.com",
    "hotmail.co.uk": "outlook.office365.com", "live.com": "outlook.office365.com", "live.co.uk": "outlook.office365.com",
    "yahoo.com": "imap.mail.yahoo.com", "yahoo.co.uk": "imap.mail.yahoo.com",
    "icloud.com": "imap.mail.me.com", "me.com": "imap.mail.me.com",
}


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
    theme: str = os.getenv("JARVIS_THEME", "classic").strip().lower()  # "classic" orb or "hud" dashboard
    greeting: str = os.getenv("JARVIS_GREETING", "").strip()  # fixed wake-up line; empty = weather and tasks
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    elevenlabs_model: str = os.getenv("ELEVENLABS_MODEL", "")  # empty: picked from speech_lang
    enable_screen: bool = _bool("JARVIS_ENABLE_SCREEN", True)
    enable_web: bool = _bool("JARVIS_ENABLE_WEB", True)
    enable_pc: bool = _bool("JARVIS_ENABLE_PC", True)  # open apps/folders/files, media keys, read files
    enable_computer: bool = _bool("JARVIS_ENABLE_COMPUTER", False)  # mouse + keyboard, each action confirmed
    host: str = os.getenv("JARVIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("JARVIS_PORT", "8340"))
    password: str = os.getenv("JARVIS_PASSWORD", "")  # empty: no login page
    memory_dir: str = os.getenv("JARVIS_MEMORY_DIR", "").strip() or str(ROOT / "memory")  # the brain's folders
    # Delivery emails: IMAP login (for Gmail, an app password, not your normal one)
    email_address: str = os.getenv("JARVIS_EMAIL_ADDRESS", "").strip()
    email_app_password: str = os.getenv("JARVIS_EMAIL_APP_PASSWORD", "").strip()
    email_imap_host: str = os.getenv("JARVIS_EMAIL_IMAP_HOST", "").strip()  # empty: picked from the address
    email_check_seconds: int = int(os.getenv("JARVIS_EMAIL_CHECK_SECONDS", "60"))
    phone_alerts: bool = _bool("JARVIS_PHONE_ALERTS", False)  # calls and delivery apps via Phone Link (Windows)
    # Calls over the internet: your phone posts to a private ntfy topic that Jarvis makes up himself
    now_playing: bool = _bool("JARVIS_NOW_PLAYING", True)  # pop-up card when a new song starts (Windows)
    music_country: str = os.getenv("JARVIS_MUSIC_COUNTRY", "").strip()  # Apple Music store, e.g. gb, za, us
    phone_relay: bool = _bool("JARVIS_CALL_ALERTS", True)
    ntfy_topic: str = os.getenv("JARVIS_NTFY_TOPIC", "").strip()  # empty: made up and kept in .phone-topic
    ntfy_server: str = os.getenv("JARVIS_NTFY_SERVER", "https://ntfy.sh").strip()
    # New abilities: requests Alfred can't handle go to Claude as GitHub issues on this repository
    github_repo: str = os.getenv("JARVIS_GITHUB_REPO", "LSX-ink/managing-work").strip()
    github_token: str = os.getenv("JARVIS_GITHUB_TOKEN", "").strip()  # empty: open the issue page to click Submit

    def __post_init__(self) -> None:
        # A blank or mistyped host (an email address, a space) can't connect; pick it from the email address instead.
        host = self.email_imap_host.strip()
        if not host or "@" in host or " " in host:
            domain = self.email_address.rpartition("@")[2].lower()
            host = IMAP_HOSTS.get(domain, "imap.gmail.com")
        object.__setattr__(self, "email_imap_host", host)

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_address and self.email_app_password)

    @property
    def lang_code(self) -> str:
        """Primary language subtag of speech_lang, e.g. 'af' for 'af-ZA'."""
        return self.speech_lang.split("-")[0].lower()


settings = Settings()
