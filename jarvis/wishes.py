"""New abilities: when Alfred can't do something, he sends the request to Claude to build.

Each request becomes a GitHub issue labelled "alfred-wish" on this project's repository. Claude checks for new
ones regularly, builds each as a pull request, and the user merges it and runs git pull to get the new ability.
With JARVIS_GITHUB_TOKEN the issue is filed automatically; without it Alfred opens a filled-in issue page in the
browser and the user just clicks Submit.
"""

import asyncio
import time
import webbrowser
from urllib.parse import urlencode

import httpx

from config import ROOT, Settings

LABEL = "alfred-wish"


def tool_definition() -> dict:
    return {
        "name": "request_new_ability",
        "description": "Ask Claude (who builds you) to add an ability you don't have yet. Use it when the user asks "
                       "for something none of your tools can do, or asks you to improve how you do something. "
                       "Describe it clearly enough for a programmer; then tell the user it has been sent and will "
                       "arrive as an update they merge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short name for the ability, e.g. 'Set timers'."},
                "details": {"type": "string", "description": "What the user asked for, in their words, and what "
                                                             "the new ability should do."},
            },
            "required": ["title", "details"],
            "additionalProperties": False,
        },
    }


def issue_body(settings: Settings, details: str) -> str:
    return (f"{details.strip()}\n\n---\nAsked of {settings.persona.title()} on {time.strftime('%Y-%m-%d %H:%M')}. "
            f"Filed by Jarvis's request_new_ability tool for Claude to build.")


def log_locally(title: str, details: str) -> None:
    """Keep a copy on this PC too (wishes.md next to server.py, git-ignored)."""
    with (ROOT / "wishes.md").open("a", encoding="utf-8") as f:
        f.write(f"- [ ] {time.strftime('%Y-%m-%d')} **{title}**: {details.strip()}\n")


async def request(http: httpx.AsyncClient, settings: Settings, title: str, details: str) -> str:
    title, body = title.strip()[:100] or "New ability", issue_body(settings, details)
    await asyncio.to_thread(log_locally, title, details)
    repo = settings.github_repo
    if settings.github_token:
        response = await http.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "body": body, "labels": [LABEL]},
        )
        if response.status_code == 201:
            return f"Sent to Claude as request number {response.json()['number']}. It will come as an update to merge."
        return f"GitHub refused the request ({response.status_code}); check JARVIS_GITHUB_TOKEN. Saved in wishes.md."
    url = f"https://github.com/{repo}/issues/new?" + urlencode({"title": title, "body": body, "labels": LABEL})
    await asyncio.to_thread(webbrowser.open, url)
    return "Opened the request on GitHub in the browser; the user needs to click Submit to send it to Claude."
