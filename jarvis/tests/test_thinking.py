from dataclasses import replace
from types import SimpleNamespace

import pytest

import brain
from brain import Brain, question_effort, request_options, turn_effort
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False, effort="low", thinking="auto")


@pytest.mark.parametrize("said", ["Thanks, Alfred", "How are you?", "Good morning", "What's the weather like?",
                                  "Tell me a fun fact", "why?", "Play some jazz"])
def test_small_talk_stays_quick(said):
    assert question_effort(said) == "low"


@pytest.mark.parametrize("said", ["Why is the sky blue?", "Explain how a heat pump works", "Plan my week",
                                  "Should I take the train or drive to Leeds tomorrow?"])
def test_a_question_that_needs_some_thought_gets_medium(said):
    assert question_effort(said) == "medium"


@pytest.mark.parametrize("said", [
    "Compare these two mortgages and tell me which is cheaper over five years",
    "Help me debug this Python script, it crashes when it reads the file",
    "Plan a budget for my trip to Lisbon, then put it in a spreadsheet",
    "Research the best electric cars under 30 grand and give me the pros and cons",
    "Can you look at my savings, work out how much I can put into my pension each month and still cover rent, "
    "bills and food, and then tell me what that would add up to by the time I'm sixty if it grows at five percent?",
])
def test_multi_step_planning_code_and_money_get_high(said):
    assert question_effort(said) == "high"


def test_auto_raises_the_base_effort_but_never_lowers_it():
    assert turn_effort(SETTINGS, "Thanks") == "low"
    assert turn_effort(SETTINGS, "Why is the sky blue?") == "medium"
    assert turn_effort(SETTINGS, "Compare these mortgages then plan my budget") == "high"
    assert turn_effort(replace(SETTINGS, effort="medium"), "Thanks") == "medium"
    assert turn_effort(replace(SETTINGS, effort="max"), "Thanks") == "max"  # efforts beyond high are left as set
    assert turn_effort(SETTINGS, "[activate]\nWeather: sunny. Tasks: plan the budget, then code") == "low"  # greeting


@pytest.mark.parametrize("fixed", ["low", "medium", "high"])
def test_jarvis_thinking_fixes_the_effort(fixed):
    s = replace(SETTINGS, thinking=fixed)
    assert turn_effort(s, "Thanks") == fixed
    assert turn_effort(s, "Compare these mortgages then plan my budget") == fixed


def test_request_options_take_the_turns_effort():
    assert request_options(SETTINGS)["output_config"] == {"effort": "low"}
    assert request_options(SETTINGS, "high")["output_config"] == {"effort": "high"}


@pytest.mark.parametrize("model, thinking, effort", [
    ("claude-opus-5", True, True),
    ("claude-opus-5-5", True, True),
    ("claude-opus-4-7", True, True),
    ("claude-sonnet-5", True, True),
    ("claude-sonnet-4-6", True, True),
    ("claude-fable-5", True, True),
    ("claude-haiku-4-5", False, False),  # would need a fixed thinking budget, and rejects effort
    ("claude-sonnet-4-5", False, False),
])
def test_adaptive_thinking_only_goes_to_models_that_take_it(model, thinking, effort):
    opts = request_options(replace(SETTINGS, model=model), "high")
    assert (opts.get("thinking") == {"type": "adaptive"}) is thinking
    assert ("output_config" in opts) is effort


def test_alfred_is_told_to_think_before_acting_but_keep_speech_short():
    prompt = brain.system_prompt(SETTINGS)
    assert "plan the steps" in prompt and "verify the answer" in prompt
    assert "what you say aloud stays short" in prompt


class FakeClient:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def done(text):
    return SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="thinking", thinking="", signature="sig"), SimpleNamespace(type="text", text=text)])


async def test_each_turn_gets_its_own_effort_and_thinking_is_never_spoken():
    client = FakeClient(done("Very good, sir."), done("The fixed rate wins, sir."), done("You're welcome."))
    said = []

    async def speak(t, **_):
        said.append(t)

    b = Brain(SETTINGS, client, http=None)
    for text in ("Good evening", "Compare these two mortgages and plan the cheapest one over five years", "Thanks"):
        await b.handle(text, speak)

    assert [r["output_config"]["effort"] for r in client.requests] == ["low", "high", "low"]
    assert all(r["thinking"] == {"type": "adaptive"} for r in client.requests)
    assert said == ["Very good, sir.", "The fixed rate wins, sir.", "You're welcome."]
    assert b.messages[-1]["content"][0].type == "thinking"  # thinking blocks go back to Claude unchanged


async def test_a_failing_tool_still_bumps_a_medium_turn_to_high(monkeypatch):
    async def broken(name, args, *rest):
        raise ValueError("no such city")

    async def speak(t, **_):
        pass

    monkeypatch.setattr(brain.tools, "run_tool", broken)
    call = SimpleNamespace(type="tool_use", name="get_weather", input={"city": "Jozi"}, id="toolu_1")
    client = FakeClient(SimpleNamespace(stop_reason="tool_use", content=[call]), done("Sunny, sir."))
    await Brain(SETTINGS, client, http=None).handle("Why is it so hot in Jozi today?", speak)

    assert [r["output_config"]["effort"] for r in client.requests] == ["medium", "high"]
