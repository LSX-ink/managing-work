from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def test_mic_help_is_loaded_before_main():
    page = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "/static/mic-help.css" in page
    assert page.index("/static/mic-help.js") < page.index("/static/main.js")


def test_main_tells_mic_help_when_the_mic_is_refused():
    assert "jarvis:mic-blocked" in (FRONTEND / "main.js").read_text(encoding="utf-8")
    helper = (FRONTEND / "mic-help.js").read_text(encoding="utf-8")
    assert "jarvis:mic-blocked" in helper and "isSecureContext" in helper


def test_mic_help_tells_the_causes_apart():
    helper = (FRONTEND / "mic-help.js").read_text(encoding="utf-8")
    for cause in ("NotFoundError", "NotReadableError", "NotAllowedError", "ms-settings:privacy-microphone", "jarvis:mic-retry"):
        assert cause in helper
    assert "jarvis:mic-retry" in (FRONTEND / "main.js").read_text(encoding="utf-8")
