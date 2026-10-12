"""A second route through OmniRoute (a local AI gateway, https://github.com/diegosouzapw/OmniRoute).

Two ways round, picked by JARVIS_OMNIROUTE_FIRST:
- off (backup): Alfred talks to Claude directly. When that fails because the API key hit its limit, ran out of
  credit, was refused, or Anthropic is down or busy, the same request goes once more through OmniRoute.
- on (free first): Alfred asks OmniRoute first (point it at free AIs to save Claude tokens). When that fails for
  any reason, Claude answers directly.
After the first route fails, Alfred skips it for a few minutes rather than waiting on it each time.

OmniRoute's AIs don't share Claude's built-in extras (its own web search, tool search, extended thinking), so
the request is trimmed to plain text, pictures and Alfred's own loaded tools before it goes there.
"""

import contextlib
import time

import anthropic

from config import Settings

COOLDOWN = 300  # seconds Alfred skips the first route after it failed
_GATEWAY_KEEP = {"model", "max_tokens", "system", "messages", "tools", "tool_choice", "temperature",
                 "stop_sequences", "metadata"}
_BLOCKS_KEPT = {"text", "image", "tool_use", "tool_result"}
_TOOL_KEYS = ("name", "description", "input_schema")


def make_client(settings: Settings, **kwargs):
    """The Claude client the rest of Jarvis uses: plain, or with the OmniRoute backup when it is set up."""
    direct = anthropic.AsyncAnthropic(**kwargs)
    if not settings.omniroute_url:
        return direct
    gateway = anthropic.AsyncAnthropic(base_url=settings.omniroute_url.rstrip("/").removesuffix("/v1"),
                                       api_key=settings.omniroute_key or "omniroute", max_retries=1)
    return BackupClient(direct, gateway, settings.omniroute_model or "auto", settings.omniroute_first)


def should_switch(exc: BaseException) -> bool:
    """True for Claude failures the backup can help with: limits, credit, a refused key, Anthropic down or busy."""
    if isinstance(exc, (anthropic.RateLimitError, anthropic.AuthenticationError, anthropic.PermissionDeniedError,
                        anthropic.APIConnectionError, anthropic.InternalServerError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        if exc.status_code in (402, 429, 529) or exc.status_code >= 500:
            return True
        return "credit balance" in str(exc).lower() or "usage limit" in str(exc).lower()
    return False


def _plain(block):
    return block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block


def _trim_content(content):
    if isinstance(content, str):
        return content
    kept = []
    for block in map(_plain, content or []):
        kind = block.get("type") if isinstance(block, dict) else None
        if kind not in _BLOCKS_KEPT:
            continue
        block = {k: v for k, v in block.items() if k not in ("cache_control", "citations", "caller")}
        if kind == "tool_result" and isinstance(block.get("content"), list):
            block["content"] = _trim_content(block["content"]) or "(done)"
        kept.append(block)
    return kept


def _trim_messages(messages) -> list[dict]:
    """Drop what only Claude understands (thinking, its own web search results, tool references)."""
    trimmed = []
    for message in messages:
        content = _trim_content(message["content"])
        if not content:
            continue
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if trimmed and trimmed[-1]["role"] == message["role"]:  # a dropped message left two from one side
            trimmed[-1]["content"] += content
        else:
            trimmed.append({"role": message["role"], "content": content})
    return trimmed


def gateway_request(opts: dict, model: str) -> dict:
    """The request as it goes to OmniRoute: Alfred's own tools that are already loaded, no Claude-only extras."""
    request = {k: v for k, v in opts.items() if k in _GATEWAY_KEEP}
    request["model"] = model
    request["messages"] = _trim_messages(request.get("messages", []))
    tools = [{k: t[k] for k in _TOOL_KEYS if k in t} for t in request.pop("tools", None) or []
             if isinstance(t, dict) and "input_schema" in t and not t.get("defer_loading")]
    if tools:
        request["tools"] = tools
    else:
        request.pop("tool_choice", None)
    if isinstance(request.get("system"), list):
        request["system"] = "\n\n".join(b.get("text", "") for b in map(_plain, request["system"]) if b.get("text"))
    return request


class _Messages:
    def __init__(self, owner: "BackupClient", direct, gateway):
        self._owner, self._direct, self._gateway = owner, direct, gateway

    def _routes(self, opts: dict) -> list:
        """(name, the call's API, its request) in the order to try them."""
        direct = ("Claude", self._direct, opts)
        gateway = ("OmniRoute", self._gateway, gateway_request(opts, self._owner.model))
        routes = [gateway, direct] if self._owner.free_first else [direct, gateway]
        return routes[1:] if self._owner.resting() else routes

    def _move_on(self, exc: BaseException, name: str) -> bool:
        """After the first route failed: True to try the other one (and skip this one for a while)."""
        if name == "Claude" and not should_switch(exc):
            return False
        if name == "OmniRoute" and not isinstance(exc, anthropic.APIError):
            return False
        self._owner.rest(name, exc)
        return True

    async def create(self, **opts):
        *first, (_, api, request) = self._routes(opts)
        for name, first_api, first_request in first:
            try:
                return await first_api.create(**first_request)
            except Exception as exc:
                if not self._move_on(exc, name):
                    raise
        return await api.create(**request)

    @contextlib.asynccontextmanager
    async def stream(self, **opts):
        *first, (_, api, request) = self._routes(opts)
        for name, first_api, first_request in first:
            manager = first_api.stream(**first_request)
            try:
                stream = await manager.__aenter__()  # limits and outages show up here, before any words
            except Exception as exc:
                if not self._move_on(exc, name):
                    raise
                continue
            try:
                yield stream
            except BaseException as exc:
                if not await manager.__aexit__(type(exc), exc, exc.__traceback__):
                    raise
            else:
                await manager.__aexit__(None, None, None)
            return
        async with api.stream(**request) as stream:
            yield stream


class _Beta:
    def __init__(self, owner: "BackupClient"):
        self.messages = _Messages(owner, owner.direct.beta.messages, owner.gateway.messages)


class BackupClient:
    """Looks like anthropic.AsyncAnthropic for what Jarvis uses: messages and beta.messages, create and stream."""

    def __init__(self, direct, gateway, model: str, free_first: bool = False):
        self.direct, self.gateway, self.model, self.free_first = direct, gateway, model, free_first
        self.rest_until = 0.0
        self.messages = _Messages(self, direct.messages, gateway.messages)
        self.beta = _Beta(self)

    def resting(self) -> bool:
        return time.monotonic() < self.rest_until

    def rest(self, name: str, exc: BaseException) -> None:
        other = "Claude" if name == "OmniRoute" else "OmniRoute"
        print(f"[jarvis] {name} failed ({type(exc).__name__}); answering through {other} for "
              f"{COOLDOWN // 60} minutes.", flush=True)
        self.rest_until = time.monotonic() + COOLDOWN

    async def close(self) -> None:
        await self.direct.close()
        await self.gateway.close()
