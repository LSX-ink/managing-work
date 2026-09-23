from dataclasses import replace
from types import SimpleNamespace

import pytest

import brain
from brain import Brain, request_options, trim_history
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False)


def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(name, args, id="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=args, id=id)


def reply(stop_reason, *blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


class FakeClient:
    """Returns scripted responses and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


async def run(brain_obj, user_text):
    said = []

    async def speak(t):
        said.append(t)

    await brain_obj.handle(user_text, speak)
    return said


async def test_tool_loop_speaks_each_step_and_returns_tool_results():
    client = FakeClient(
        reply("tool_use", text("One moment, sir."), tool_use("get_tasks", {})),
        reply("end_turn", text("Your slate is clean.")),
    )
    b = Brain(SETTINGS, client, http=None)

    said = await run(b, "What's on my list?")

    assert said == ["One moment, sir.", "Your slate is clean."]
    tool_turn = client.requests[1]["messages"][-1]
    assert tool_turn["role"] == "user"
    assert tool_turn["content"][0]["tool_use_id"] == "toolu_1"
    assert "No task list configured" in tool_turn["content"][0]["content"]
    assert [m["role"] for m in b.messages] == ["user", "assistant", "user", "assistant"]


async def test_failing_tool_is_reported_as_error_result():
    client = FakeClient(
        reply("tool_use", tool_use("no_such_tool", {})),
        reply("end_turn", text("That did not go to plan.")),
    )
    b = Brain(SETTINGS, client, http=None)

    await run(b, "Do the impossible")

    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True
    assert "Unknown tool" in result["content"]


async def test_refusal_drops_the_turn_from_history():
    client = FakeClient(reply("end_turn", text("Hello.")), reply("refusal"))
    b = Brain(SETTINGS, client, http=None)

    await run(b, "Hi")
    said = await run(b, "Something declined")

    assert said == [brain.LINES["en"]["refusal"]]
    assert len(b.messages) == 2  # only the first exchange remains


async def test_pause_turn_resends_without_new_user_message():
    client = FakeClient(reply("pause_turn"), reply("end_turn", text("Found it.")))
    b = Brain(SETTINGS, client, http=None)

    said = await run(b, "Search for something")

    assert said == ["Found it."]
    assert client.requests[1]["messages"][-1]["role"] == "assistant"


def test_trim_history_cuts_only_at_user_utterances():
    msgs = []
    for i in range(5):
        msgs += [
            {"role": "user", "content": f"q{i}"},
            {"role": "assistant", "content": ["tool_use"]},
            {"role": "user", "content": [{"type": "tool_result"}]},
            {"role": "assistant", "content": ["answer"]},
        ]
    trimmed = trim_history(msgs, max_turns=2)
    assert trimmed[0] == {"role": "user", "content": "q3"}
    assert len(trimmed) == 8


@pytest.mark.parametrize(
    "model, has_fallback, has_effort, search_type",
    [
        ("claude-opus-5", True, True, "web_search_20260209"),
        ("claude-sonnet-5", False, True, "web_search_20260209"),
        ("claude-haiku-4-5", False, False, "web_search_20250305"),
    ],
)
def test_request_options_depend_on_model(model, has_fallback, has_effort, search_type):
    opts = request_options(replace(SETTINGS, model=model))
    assert ("fallbacks" in opts) is has_fallback
    assert ("output_config" in opts) is has_effort
    assert any(t.get("type") == search_type for t in opts["tools"])


def test_screen_and_web_tools_can_be_disabled():
    opts = request_options(replace(SETTINGS, enable_screen=False, enable_web=False))
    names = {t["name"] for t in opts["tools"]}
    assert names == {"get_weather", "get_tasks", "open_url"}


def test_afrikaans_prompt_and_fixed_lines():
    af = replace(SETTINGS, speech_lang="af-ZA", language="Afrikaans")
    assert "Always reply in Afrikaans" in brain.system_prompt(af)
    assert brain.line(af, "error") == brain.LINES["af"]["error"]
    assert brain.line(replace(SETTINGS, speech_lang="xx-YY"), "error") == brain.LINES["en"]["error"]


async def test_error_line_is_in_the_configured_language():
    class Broken:
        beta = SimpleNamespace(messages=SimpleNamespace(create=None))

    async def boom(**kwargs):
        raise RuntimeError("no key")

    Broken.beta.messages.create = boom
    b = Brain(replace(SETTINGS, speech_lang="af-ZA"), Broken(), http=None)
    said = await run(b, "Hallo")
    assert said == [brain.LINES["af"]["error"]]
    assert b.messages == []


def test_alfred_persona_changes_the_prompt():
    alfred = replace(SETTINGS, persona="alfred")
    prompt = brain.system_prompt(alfred)
    assert prompt.startswith("You are Alfred")
    assert brain.persona(alfred)["name"] == "Alfred"
    assert brain.persona(replace(SETTINGS, persona="nobody"))["name"] == "Jarvis"
