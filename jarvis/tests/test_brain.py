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
    assert "No open jobs." in tool_turn["content"][0]["content"]
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
    opts = request_options(replace(SETTINGS, enable_screen=False, enable_web=False, enable_pc=False))
    names = {t["name"] for t in opts["tools"]}
    assert "look_at_screen" not in names and "web_search" not in names
    assert names >= {"get_weather", "get_tasks", "open_url", "save_to_memory", "read_memory", "download_file", "open_memory_folder", "create_memory_folder", "delete_memory_folder", "move_chat_panel", "remember_about_user", "forget_about_user", "set_reminder", "list_reminders", "cancel_reminder", "get_calendar", "shopping_list", "listen_for_name", "read_document", "pc_health", "jarvis_status", "request_new_ability", "set_timer", "check_timers", "cancel_timer", "take_a_break"}


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


async def test_an_empty_claude_account_is_named_out_loud():
    async def broke(**kwargs):
        raise RuntimeError("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': "
                           "'Your credit balance is too low to access the Anthropic API.'}}")
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=broke)))
    said = await run(Brain(SETTINGS, client, http=None), "Make 2 TikTok videos")
    assert said == [brain.LINES["en"]["no_credit"]] and "console dot anthropic" in said[0]


def test_alfred_persona_changes_the_prompt():
    alfred = replace(SETTINGS, persona="alfred")
    prompt = brain.system_prompt(alfred)
    assert prompt.startswith("You are Alfred")
    assert brain.persona(alfred)["name"] == "Alfred"
    assert brain.persona(replace(SETTINGS, persona="nobody"))["name"] == "Jarvis"


async def test_fixed_greeting_skips_claude():
    client = FakeClient()  # no scripted responses: any API call would fail
    b = Brain(replace(SETTINGS, greeting="Good evening, sir."), client, http=None)
    said = []

    async def speak(t):
        said.append(t)

    await b.activate(speak)
    assert said == ["Good evening, sir."]
    assert client.requests == [] and b.messages == []


@pytest.mark.parametrize("hour, expected", [(6, "morning"), (11, "morning"), (12, "afternoon"),
                                            (17, "afternoon"), (18, "evening"), (2, "evening")])
def test_time_of_day(hour, expected):
    assert brain.time_of_day(hour) == expected


async def test_greeting_fills_in_time_of_day(monkeypatch):
    monkeypatch.setattr(brain, "time_of_day", lambda: "afternoon")
    b = Brain(replace(SETTINGS, greeting="Good {time_of_day}, sir."), FakeClient(), http=None)
    said = []

    async def speak(t):
        said.append(t)

    await b.activate(speak)
    assert said == ["Good afternoon, sir."]


async def test_conversation_carries_over_a_restart(tmp_path):
    s = replace(SETTINGS, memory_dir=str(tmp_path))
    first = Brain(s, FakeClient(reply("tool_use", text("One moment."), tool_use("get_tasks", {})),
                                reply("end_turn", text("Your slate is clean."))), http=None)
    await run(first, "What's on my list?")
    await run(Brain(s, FakeClient(reply("end_turn", text("Good evening."))), http=None), "[activate]\nWeather: fine")

    client = FakeClient(reply("end_turn", text("I said it was clean.")))
    later = Brain(s, client, http=None)  # a restart or a page reload
    await run(later, "What did you just tell me?")
    sent = client.requests[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[0]["content"].endswith("What's on my list?")
    assert sent[1] == {"role": "assistant", "content": "One moment. Your slate is clean."}  # the greeting isn't kept
    (tmp_path / ".recent-chat.json").write_text("not json", encoding="utf-8")
    assert Brain(s, FakeClient(), http=None).messages == []


def test_old_documents_are_pruned():
    doc = {"type": "document", "source": {}}
    messages = [{"role": "user", "content": [{"type": "tool_result", "content": [dict(doc)]}]} for _ in range(8)]
    brain.prune_images(messages)
    kinds = [m["content"][0]["content"][0]["type"] for m in messages]
    assert kinds == ["text", "text"] + ["document"] * 6


def test_failed_calls_name_what_the_user_can_fix():
    import anthropic
    import httpx

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def status(cls, code):
        return cls("x", response=httpx.Response(code, request=request), body=None)

    assert brain.error_key(TypeError("Could not resolve authentication method.")) == "no_key"
    assert brain.error_key(status(anthropic.AuthenticationError, 401)) == "bad_key"
    assert brain.error_key(anthropic.APIConnectionError(request=request)) == "no_connection"
    assert brain.error_key(status(anthropic.NotFoundError, 404)) == "bad_model"
    assert brain.error_key(status(anthropic.RateLimitError, 429)) == "busy"
    assert brain.error_key(status(anthropic.InternalServerError, 529)) == "busy"
    assert brain.error_key(RuntimeError("no key")) == "error"
    assert set(brain.LINES["af"]) == set(brain.LINES["en"])


def test_alfred_is_told_the_name_of_every_ability_he_can_load():
    options = brain.request_options(replace(SETTINGS, model="claude-opus-5"))
    deferred = [t["name"] for t in options["tools"] if t.get("defer_loading")]
    assert deferred and all(name in options["system"] for name in deferred)
    assert "Never tell the user you can't" in options["system"]


def test_alfred_is_taught_to_solve_problems_on_his_own():
    prompt = brain.system_prompt(SETTINGS)
    assert "How you solve problems on your own" in prompt
    assert "take a different route" in prompt and "Never claim something happened" in prompt


async def test_a_failing_tool_gets_recovery_advice_more_thought_and_a_warning_on_repeats(monkeypatch):
    async def broken(name, args, *rest):
        raise ValueError("no such city")

    monkeypatch.setattr(brain.tools, "run_tool", broken)
    client = FakeClient(
        reply("tool_use", tool_use("get_weather", {"city": "Jozi"})),
        reply("tool_use", tool_use("get_weather", {"city": "Jozi"}, id="toolu_2")),
        reply("end_turn", text("Johannesburg is sunny, sir.")),
    )
    said = await run(Brain(SETTINGS, client, http=None), "Weather in Jozi?")

    first = client.requests[1]["messages"][-1]["content"][0]
    second = client.requests[2]["messages"][-1]["content"][0]
    assert first["is_error"] and brain.RETRY_ADVICE in first["content"]
    assert "failed twice" in second["content"]
    assert client.requests[0]["output_config"]["effort"] == "low"
    assert client.requests[1]["output_config"]["effort"] == "medium"  # stuck: think harder
    assert said == ["Johannesburg is sunny, sir."]


async def test_running_out_of_steps_reports_progress_instead_of_a_canned_line(monkeypatch):
    async def ok(name, args, *rest):
        return "done"

    monkeypatch.setattr(brain.tools, "run_tool", ok)
    monkeypatch.setattr(brain, "MAX_TOOL_ROUNDS", 2)
    client = FakeClient(
        reply("tool_use", tool_use("get_tasks", {})),
        reply("tool_use", tool_use("get_tasks", {}, id="toolu_2")),
        reply("end_turn", text("I've checked your list twice; the sorting is still to do.")),
    )
    said = await run(Brain(SETTINGS, client, http=None), "Sort my whole life out")

    wrap = client.requests[2]
    assert wrap["tool_choice"] == {"type": "none"}
    assert "used every step" in wrap["messages"][-1]["content"][-1]["text"]
    assert said == ["I've checked your list twice; the sorting is still to do."]
