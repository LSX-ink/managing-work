import asyncio
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

import wishes
from config import Settings


@pytest.fixture(autouse=True)
def local_log(tmp_path, monkeypatch):
    monkeypatch.setattr(wishes, "ROOT", tmp_path)
    return tmp_path / "wishes.md"


def test_files_an_issue_with_a_token(local_log):
    seen = {}

    def handler(request):
        seen["url"], seen["auth"], seen["json"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        return httpx.Response(201, json={"number": 42})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(github_token="tok", github_repo="me/repo", persona="alfred")
    msg = asyncio.run(wishes.request(http, settings, "Set timers", "Let me say 'timer for 5 minutes'."))
    assert "42" in msg
    assert seen["url"] == "https://api.github.com/repos/me/repo/issues" and seen["auth"] == "Bearer tok"
    assert seen["json"]["title"] == "Set timers" and seen["json"]["labels"] == ["alfred-wish"]
    assert "timer for 5 minutes" in seen["json"]["body"] and "Alfred" in seen["json"]["body"]
    assert "Set timers" in local_log.read_text(encoding="utf-8")


def test_refused_token_says_so():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    msg = asyncio.run(wishes.request(http, Settings(github_token="bad"), "X", "y"))
    assert "401" in msg and "JARVIS_GITHUB_TOKEN" in msg


def test_without_a_token_opens_the_issue_page(monkeypatch, local_log):
    opened = []
    monkeypatch.setattr(wishes.webbrowser, "open", opened.append)
    msg = asyncio.run(wishes.request(None, Settings(github_token="", github_repo="me/repo"), "Set timers", "please"))
    assert "Submit" in msg
    url = urlparse(opened[0])
    assert url.path == "/me/repo/issues/new"
    q = parse_qs(url.query)
    assert q["title"] == ["Set timers"] and q["labels"] == ["alfred-wish"] and "please" in q["body"][0]


def test_requests_say_which_version_of_alfred_filed_them(tmp_path):
    import wishes
    from config import Settings

    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    (git / "refs" / "heads" / "main").write_text("5fa93c54789f996841544e3e486bce76a16c0859\n")
    assert wishes.code_version(tmp_path) == "5fa93c5"
    (git / "refs" / "heads" / "main").unlink()
    (git / "packed-refs").write_text("# pack-refs\n1234567890abcdef refs/heads/main\n")
    assert wishes.code_version(tmp_path) == "1234567"
    assert wishes.code_version(tmp_path / "nowhere") == "unknown"
    assert "running version" in wishes.issue_body(Settings(), "Make it fly")
