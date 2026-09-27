import health
from config import Settings


def test_pc_health_reads_the_machine():
    text = health.pc_health()
    assert "CPU" in text and "memory" in text and "drive" in text


def test_status_never_shows_secrets():
    s = Settings(city="Leeds", email_address="me@gmail.com", email_app_password="abcdabcdabcdabcd",
                 elevenlabs_api_key="sk_secret", calendar_url="")
    text = health.status(s)
    assert "Weather: on, for Leeds." in text and "Email: set up" in text and "Calendar: not connected" in text
    assert "abcd" not in text and "sk_secret" not in text
