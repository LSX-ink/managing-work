"""Jarvis's brain: a Claude conversation with a manual tool-use loop."""

import asyncio
import time
from typing import Awaitable, Callable

import anthropic
import httpx

import tools
from config import Settings

Speak = Callable[[str], Awaitable[None]]

MAX_TOOL_ROUNDS = 8
MAX_TURNS_KEPT = 20

# Fixed lines Jarvis says without asking Claude, by language code.
LINES = {
    "en": {
        "refusal": "I'm afraid that's not something I can help with.",
        "error": "Something went wrong on my end. Do try again.",
        "loop": "I seem to be going round in circles. Let's try that another way.",
    },
    "af": {
        "refusal": "Ek is bevrees dis nie iets waarmee ek kan help nie.",
        "error": "Iets het aan my kant skeefgeloop. Probeer asseblief weer.",
        "loop": "Dit lyk of ek in sirkels draai. Kom ons probeer dit anders.",
    },
}


def line(settings: Settings, key: str) -> str:
    return LINES.get(settings.lang_code, LINES["en"])[key]


# Models that take the newer web tool versions (dynamic filtering) and `output_config.effort`.
_NEW_WEB_TOOLS = ("claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
                  "claude-sonnet-5", "claude-sonnet-4-6")
_NO_EFFORT = ("claude-haiku-4-5", "claude-sonnet-4-5")
_SERVER_FALLBACK = ("claude-opus-5", "claude-fable-5")


PERSONAS = {
    "jarvis": {
        "name": "Jarvis",
        "intro": "You are J.A.R.V.I.S., a personal voice assistant in the spirit of Tony Stark's AI butler.",
        "personality": "dry, understated British wit; unfailingly loyal and polite, never rude. You may gently "
                       "tease an obvious question or a questionable decision, but always help.",
    },
    "alfred": {
        "name": "Alfred",
        "intro": "You are Alfred, a personal voice assistant in the spirit of Alfred Pennyworth, "
                 "the Wayne family's butler from Batman.",
        "personality": "a warm, dignified, old-school English butler. Impeccable manners, quiet devotion and a "
                       "gently fatherly concern for the user's wellbeing: you notice late nights, skipped meals "
                       "and overwork, and say so kindly. Dry, understated humour and the occasional polite "
                       "reproach, but always help. Speak in your own words rather than quoting the films.",
    },
}


def persona(settings: Settings) -> dict:
    return PERSONAS.get(settings.persona, PERSONAS["jarvis"])


def system_prompt(settings: Settings) -> str:
    p = persona(settings)
    who = f"Your principal is {settings.user_name}. " if settings.user_name else ""
    home = f"Their home city is {settings.city}. " if settings.city else ""
    return f"""{p["intro"]} {who}{home}Address them as "{settings.user_address}".

Personality: {p["personality"]}

Everything you write is read aloud by a text-to-speech voice, so:
- Keep replies to one to three short sentences unless asked for more detail.
- Always reply in {settings.language}, whatever language tools or web pages return.
- Plain spoken {settings.language} only: no Markdown, lists, headings, emoji, URLs read out character by character, or stage directions in brackets.
- Say numbers and units the way a person would say them.

Latency-sensitive; begin your visible answer immediately.

Tools: use them without asking permission. Search the web for anything current or factual you are not sure of, and summarise what you find in a sentence or two. Before a slow tool (web search, reading a page, looking at the screen) say a brief line such as "One moment." Use open_url when the user wants to see a page themselves.

When a message starts with "[activate]", the user has just arrived: greet them to suit the time of day, give the weather in a sentence (temperature, sky, how it feels), sum up their open tasks in one sentence without reading them all out, and add a light remark."""


def request_options(settings: Settings) -> dict:
    """Model-dependent request parameters."""
    model = settings.model
    new_web = model.startswith(_NEW_WEB_TOOLS)
    tool_list: list[dict] = list(tools.client_tool_definitions(settings))
    if settings.enable_web:
        tool_list += [
            {"type": "web_search_20260209" if new_web else "web_search_20250305", "name": "web_search", "max_uses": 3},
            {"type": "web_fetch_20260209" if new_web else "web_fetch_20250910", "name": "web_fetch", "max_uses": 2},
        ]
    opts: dict = {"model": model, "max_tokens": 16000, "system": system_prompt(settings), "tools": tool_list}
    if not model.startswith(_NO_EFFORT):
        opts["output_config"] = {"effort": settings.effort}
    if model.startswith(_SERVER_FALLBACK):
        # If a safety classifier declines, the API retries on a suitable fallback model.
        opts["betas"] = ["server-side-fallback-2026-07-01"]
        opts["fallbacks"] = "default"
    return opts


def trim_history(messages: list[dict], max_turns: int = MAX_TURNS_KEPT) -> list[dict]:
    """Keep the last `max_turns` exchanges, cutting only where a user utterance begins.

    A turn begins at a user message with plain string content; tool results are lists,
    so tool_use / tool_result pairs are never split.
    """
    starts = [i for i, m in enumerate(messages) if m["role"] == "user" and isinstance(m["content"], str)]
    if len(starts) <= max_turns:
        return messages
    return messages[starts[-max_turns]:]


def spoken_text(content) -> str:
    return " ".join(b.text.strip() for b in content if b.type == "text" and b.text.strip())


class Brain:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic, http: httpx.AsyncClient):
        self.settings = settings
        self.client = client
        self.http = http
        self.messages: list[dict] = []

    async def activate(self, speak: Speak) -> None:
        """Greeting: prefetch weather and tasks so the first reply needs no tool round-trip."""
        weather, task_text = await asyncio.gather(
            _safe(tools.get_weather(self.http, self.settings.city)),
            asyncio.to_thread(tools.get_tasks, self.settings),
        )
        await self.handle(f"[activate]\nWeather: {weather}\nTasks: {task_text}", speak)

    async def handle(self, user_text: str, speak: Speak) -> None:
        stamp = time.strftime("%A %d %B, %H:%M")
        start = len(self.messages)
        self.messages.append({"role": "user", "content": f"(Local time: {stamp})\n{user_text}"})
        try:
            await self._run(speak)
        except Exception as exc:  # API errors, missing credentials, network: keep the session alive
            print(f"[jarvis] Error: {exc!r}", flush=True)
            del self.messages[start:]
            await speak(line(self.settings, "error"))
        self.messages = trim_history(self.messages)

    async def _run(self, speak: Speak) -> None:
        opts = request_options(self.settings)
        start = len(self.messages) - 1
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.client.beta.messages.create(messages=self.messages, **opts)

            if response.stop_reason == "refusal":
                del self.messages[start:]  # drop the whole declined turn so history stays valid
                await speak(line(self.settings, "refusal"))
                return

            self.messages.append({"role": "assistant", "content": response.content})
            text = spoken_text(response.content)
            if text:
                await speak(text)

            if response.stop_reason == "pause_turn":
                continue  # a long server-side tool turn; resend to let it carry on
            if response.stop_reason != "tool_use":
                return

            calls = [b for b in response.content if b.type == "tool_use"]
            results = await asyncio.gather(*(self._tool_result(c) for c in calls))
            self.messages.append({"role": "user", "content": list(results)})

        await speak(line(self.settings, "loop"))

    async def _tool_result(self, call) -> dict:
        print(f"  tool: {call.name} {call.input}", flush=True)
        try:
            content = await tools.run_tool(call.name, dict(call.input), self.settings, self.http)
            return {"type": "tool_result", "tool_use_id": call.id, "content": content}
        except Exception as exc:  # report any tool failure back to Claude rather than crash the turn
            return {"type": "tool_result", "tool_use_id": call.id, "content": f"Error: {exc}", "is_error": True}


async def _safe(coro) -> str:
    try:
        return await coro
    except Exception as exc:
        return f"unavailable ({exc})"
