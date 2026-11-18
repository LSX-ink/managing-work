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


def backup(direct_error=None, gateway_error=None, free_first=False):
    direct, gateway = FakeClient("claude", direct_error), FakeClient("backup", gateway_error)
    return omniroute.BackupClient(direct, gateway, "alfred", free_first), direct, gateway


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
    client.rest_until = 0
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
    assert [t["name"] for t in request["tools"]] == ["get_time", omniroute.FIND_TOOL]  # "rare" waits to be found
    assert request["tools"][0] == {"name": "get_time", "description": "Time", "input_schema": {"type": "object"}}


def test_free_route_finds_and_loads_deferred_tools():
    """The free AI can't use Claude's tool search, so find_tool stands in and what it finds is sent from then on."""
    every = OPTS["tools"] + [{"name": "pc_system", "description": "Screen brightness, volume and Wi-Fi",
                              "input_schema": {"type": "object"}, "defer_loading": True}]
    found = omniroute.find_tools("turn the brightness down", every)
    assert found.startswith("Loaded: pc_system.")
    assert omniroute.find_tools("zebra", every).startswith("No tool matched")
    messages = [{"role": "user", "content": "dim it"},
                {"role": "assistant", "content": [{"type": "tool_use", "id": "f1", "name": "find_tool", "input": {"query": "brightness"}}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "f1", "content": found}]}]
    request = omniroute.gateway_request({**OPTS, "tools": every, "messages": messages,
                                         "system": "search with tool_search_tool_bm25"}, "auto")
    assert [t["name"] for t in request["tools"]] == ["get_time", "pc_system", omniroute.FIND_TOOL]
    assert request["system"] == "search with find_tool"


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


async def test_free_first_asks_omniroute_and_leaves_claude_alone():
    client, direct, gateway = backup(free_first=True)
    assert await client.beta.messages.create(**OPTS) == "backup"
    async with client.beta.messages.stream(**OPTS) as stream:
        assert stream == "backup"
    assert direct.beta.messages.calls == [] and gateway.messages.calls[0]["model"] == "alfred"


@pytest.mark.parametrize("exc", [status(anthropic.RateLimitError, 429), status(anthropic.BadRequestError, 400),
                                 anthropic.APIConnectionError(request=REQUEST)])
async def test_free_first_falls_back_to_claude_for_any_omniroute_failure(exc):
    client, direct, gateway = backup(gateway_error=exc, free_first=True)
    assert await client.beta.messages.create(**OPTS) == "claude"
    assert direct.beta.messages.calls == [OPTS]  # Claude gets the full request, extras and all
    async with client.beta.messages.stream(**OPTS) as stream:  # free AIs are skipped for a while
        assert stream == "claude"
    assert len(gateway.messages.calls) == 1


async def test_free_first_when_both_fail_the_claude_error_shows():
    client, _, _ = backup(direct_error=status(anthropic.AuthenticationError, 401),
                          gateway_error=anthropic.APIConnectionError(request=REQUEST), free_first=True)
    with pytest.raises(anthropic.AuthenticationError):
        await client.messages.create(**OPTS)


def test_free_first_setting_reaches_the_client():
    settings = replace(Settings(), omniroute_url="http://localhost:20128", omniroute_first=True)
    assert omniroute.make_client(settings, api_key="k").free_first


async def test_close_closes_both():
    client, direct, gateway = backup()
    await client.close()
    assert direct.closed and gateway.closed


NO_CREDIT = status(anthropic.BadRequestError, 400, "Your credit balance is too low to access the Anthropic API.")


@pytest.mark.parametrize("free_first", [True, False])
async def test_no_credit_and_no_free_ai_is_named_plainly(free_first):
    client, _, _ = backup(direct_error=NO_CREDIT, gateway_error=anthropic.APIConnectionError(request=REQUEST),
                          free_first=free_first)
    with pytest.raises(omniroute.NoThinkingCredit):
        await client.beta.messages.create(**OPTS)
    with pytest.raises(omniroute.NoThinkingCredit):  # the next turn too, while the first route rests
        async with client.beta.messages.stream(**OPTS):
            pass


def test_out_of_credit_spots_an_empty_account():
    assert omniroute.out_of_credit(NO_CREDIT) and omniroute.out_of_credit(status(anthropic.APIStatusError, 402))
    assert not omniroute.out_of_credit(status(anthropic.RateLimitError, 429)) and not omniroute.out_of_credit(None)


async def test_the_route_that_answered_is_remembered():
    client, _, _ = backup(direct_error=NO_CREDIT)
    async with client.beta.messages.stream(**OPTS) as stream:
        assert stream == "backup"
    assert client.last_route == "OmniRoute"
    client.rest_until = 0
    client.direct.beta.messages.error = None
    await client.beta.messages.create(**OPTS)
    assert client.last_route == "Claude"
