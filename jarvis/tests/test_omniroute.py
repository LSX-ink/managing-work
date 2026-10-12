import contextlib
from dataclasses import replace

import anthropic
import httpx
import pytest

import omniroute
from config import Settings

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def status(cls, code, message="x"):
    return cls(message, response=httpx.Response(code, request=REQUEST), body=None)


class FakeMessages:
    """Records requests; raises `error` when set, otherwise answers with `answer`."""

    def __init__(self, answer, error=None):
        self.answer, self.error, self.calls = answer, error, []

    async def create(self, **opts):
        self.calls.append(opts)
        if self.error:
            raise self.error
        return self.answer

    @contextlib.asynccontextmanager
    async def stream(self, **opts):
        self.calls.append(opts)
        if self.error:
            raise self.error
        yield self.answer


class FakeClient:
    def __init__(self, answer, error=None):
        self.messages = FakeMessages(answer, error)
        self.beta = type("Beta", (), {"messages": FakeMessages(answer, error)})()
        self.closed = False

    async def close(self):
        self.closed = True


def backup(direct_error=None):
    direct, gateway = FakeClient("claude", direct_error), FakeClient("backup")
    return omniroute.BackupClient(direct, gateway, "alfred"), direct, gateway


OPTS = {"model": "claude-opus-5", "max_tokens": 100, "betas": ["x"], "thinking": {"type": "adaptive"},
        "system": [{"type": "text", "text": "You are Alfred.", "cache_control": {"type": "ephemeral"}}],
        "tools": [{"name": "get_time", "description": "Time", "input_schema": {"type": "object"}},
                  {"name": "rare", "description": "Rare", "input_schema": {"type": "object"}, "defer_loading": True},
                  {"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": "Hello"}]}


def test_no_address_keeps_the_plain_client():
    client = omniroute.make_client(replace(Settings(), omniroute_url=""), api_key="k")
    assert isinstance(client, anthropic.AsyncAnthropic)


def test_address_adds_the_backup_pointing_at_omniroute():
    settings = replace(Settings(), omniroute_url="http://localhost:20128/v1", omniroute_key="sk-or",
                       omniroute_model="alfred")
    client = omniroute.make_client(settings, api_key="k")
    assert isinstance(client, omniroute.BackupClient)
    assert str(client.gateway.base_url).rstrip("/") == "http://localhost:20128"
    assert client.gateway.api_key == "sk-or" and client.model == "alfred"


@pytest.mark.parametrize("exc", [
    status(anthropic.RateLimitError, 429), status(anthropic.InternalServerError, 529),
    status(anthropic.AuthenticationError, 401), anthropic.APIConnectionError(request=REQUEST),
    status(anthropic.BadRequestError, 400, "Your credit balance is too low to access the Anthropic API."),
])
def test_switches_for_limits_credit_bad_key_and_outages(exc):
    assert omniroute.should_switch(exc)


@pytest.mark.parametrize("exc", [status(anthropic.BadRequestError, 400, "messages: field required"),
                                 status(anthropic.NotFoundError, 404), ValueError("bug")])
def test_ordinary_mistakes_are_not_hidden(exc):
    assert not omniroute.should_switch(exc)


async def test_claude_answers_when_it_works():
    client, direct, gateway = backup()
    assert await client.beta.messages.create(**OPTS) == "claude"
    assert direct.beta.messages.calls == [OPTS] and gateway.messages.calls == []


async def test_falls_back_on_a_limit_and_stays_there_for_a_while():
    client, direct, gateway = backup(status(anthropic.RateLimitError, 429))
    assert await client.beta.messages.create(**OPTS) == "backup"
    assert await client.messages.create(**OPTS) == "backup"
    assert len(direct.beta.messages.calls) == 1 and direct.messages.calls == []  # skipped during the cooldown
    client.backup_until = 0
    await client.messages.create(**OPTS)
    assert len(direct.messages.calls) == 1


async def test_other_errors_still_raise():
    client, _, gateway = backup(status(anthropic.BadRequestError, 400, "bad request"))
    with pytest.raises(anthropic.BadRequestError):
        await client.beta.messages.create(**OPTS)
    assert gateway.messages.calls == []


async def test_stream_falls_back_before_any_words():
    client, _, gateway = backup(status(anthropic.InternalServerError, 529))
    async with client.beta.messages.stream(**OPTS) as stream:
        assert stream == "backup"
    assert gateway.messages.calls[0]["model"] == "alfred"


async def test_stream_from_claude_when_it_works():
    client, direct, _ = backup()
    async with client.beta.messages.stream(**OPTS) as stream:
        assert stream == "claude"
    assert direct.beta.messages.calls == [OPTS]


def test_backup_request_drops_claude_only_extras():
    request = omniroute.gateway_request(OPTS, "auto")
    assert request["model"] == "auto" and "betas" not in request and "thinking" not in request
    assert request["system"] == "You are Alfred."
    assert request["tools"] == [{"name": "get_time", "description": "Time", "input_schema": {"type": "object"}}]


def test_backup_request_trims_the_conversation():
    messages = [
        {"role": "user", "content": "Weather?"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "hmm", "signature": "s"},
            {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {}},
            {"type": "web_search_tool_result", "tool_use_id": "s1", "content": []},
            {"type": "text", "text": "Sunny."},
            {"type": "tool_use", "id": "t1", "name": "get_time", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": [
            {"type": "tool_reference", "tool_name": "rare"}, {"type": "text", "text": "12:00"}]}]},
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "only thoughts", "signature": "s"}]},
        {"role": "user", "content": "Thanks"},
    ]
    trimmed = omniroute.gateway_request({**OPTS, "messages": messages}, "auto")["messages"]
    assert trimmed == [
        {"role": "user", "content": [{"type": "text", "text": "Weather?"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Sunny."},
                                          {"type": "tool_use", "id": "t1", "name": "get_time", "input": {}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "12:00"}]},
            {"type": "text", "text": "Thanks"}]},
    ]


async def test_close_closes_both():
    client, direct, gateway = backup()
    await client.close()
    assert direct.closed and gateway.closed
