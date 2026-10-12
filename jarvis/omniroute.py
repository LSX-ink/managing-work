"""Backup route through OmniRoute (a local AI gateway, https://github.com/diegosouzapw/OmniRoute).

Alfred talks to Claude directly, exactly as before. When that fails because the API key hit its limit, ran out
of credit, was refused, or Anthropic is down or busy, the same request is sent once more through OmniRoute,
which passes it to whichever backup AI is set up there. After such a failure Alfred stays on the backup for a
few minutes rather than waiting on Anthropic each time.

Backup AIs don't share Claude's built-in extras (its own web search, tool search, extended thinking), so the
request is trimmed to plain text, pictures and Alfred's own tools before it goes to OmniRoute.
"""

import contextlib
import time

import anthropic

from config import Settings

COOLDOWN = 300  # seconds Alfred stays on the backup after Claude itself failed
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
    return BackupClient(direct, gateway, settings.omniroute_model or "auto")


def should_switch(exc: BaseException) -> bool:
    """True for failures the backup can help with: limits, credit, a refused key, Anthropic down or busy."""
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

    async def create(self, **opts):
        if not self._owner.on_backup():
            try:
                return await self._direct.create(**opts)
            except Exception as exc:
                if not should_switch(exc):
                    raise
                self._owner.switched(exc)
        return await self._gateway.create(**gateway_request(opts, self._owner.model))

    @contextlib.asynccontextmanager
    async def stream(self, **opts):
        if not self._owner.on_backup():
            manager = self._direct.stream(**opts)
            try:
                stream = await manager.__aenter__()  # limits and outages show up here, before any words
            except Exception as exc:
                if not should_switch(exc):
                    raise
                self._owner.switched(exc)
            else:
                try:
                    yield stream
                except BaseException as exc:
                    if not await manager.__aexit__(type(exc), exc, exc.__traceback__):
                        raise
                else:
                    await manager.__aexit__(None, None, None)
                return
        async with self._gateway.stream(**gateway_request(opts, self._owner.model)) as stream:
            yield stream


class _Beta:
    def __init__(self, owner: "BackupClient"):
        self.messages = _Messages(owner, owner.direct.beta.messages, owner.gateway.messages)


class BackupClient:
    """Looks like anthropic.AsyncAnthropic for what Jarvis uses: messages and beta.messages, create and stream."""

    def __init__(self, direct, gateway, model: str):
        self.direct, self.gateway, self.model = direct, gateway, model
        self.backup_until = 0.0
        self.messages = _Messages(self, direct.messages, gateway.messages)
        self.beta = _Beta(self)

    def on_backup(self) -> bool:
        return time.monotonic() < self.backup_until

    def switched(self, exc: BaseException) -> None:
        print(f"[jarvis] Claude failed ({type(exc).__name__}); answering through OmniRoute for "
              f"{COOLDOWN // 60} minutes.", flush=True)
        self.backup_until = time.monotonic() + COOLDOWN

    async def close(self) -> None:
        await self.direct.close()
        await self.gateway.close()
