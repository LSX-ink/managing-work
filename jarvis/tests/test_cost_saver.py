"""Cost saver: cheap model for simple turns, smart model for hard jobs, prompt caching, history trimming,
the out-of-credit line and the HUD's MODEL line."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

import brain
import omniroute
from brain import Brain, request_options, trim_history, turn_model
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False, cost_saver=True,
                    cheap_model="claude-haiku-5-5", smart_model="", enable_computer=False)
CHEAP, SMART = "claude-haiku-5-5", "claude-opus-5"


def text(t):
    return SimpleNamespace(type="text", text=t)


def reply(stop_reason, *blocks, model=None):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks), model=model)


class FakeClient:
    def __init__(self, *responses, error=None):
        self.responses, self.requests, self.error = list(responses), [], error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error:
            raise self.error
        return self.responses.pop(0)


async def run(b, said_text):
    said = []

    async def speak(t, **kwargs):
        said.append(t)

    await b.handle(said_text, speak)
    return said


@pytest.mark.parametrize("said", [
    "How are you?", "Thanks Alfred", "What's the weather like?", "Play some jazz", "Who won the match last night?",
    "Set a reminder for my dentist on Friday", "What's the capital of Peru?", "Turn the volume down",
    "[activate]\nWeather: sunny\nTasks: none",
])
def test_simple_turns_go_to_the_cheap_model(said):
    assert turn_model(SETTINGS, said) == CHEAP


@pytest.mark.parametrize("said", [
    "Write me a cover letter for the designer job", "Can you debug this Python script?",
    "Plan out my week step by step", "Design a logo for Kinetic Web Designs", "Write a TikTok video script about bees",
    "Draft outreach emails to ten local plumbers", "Think hard: should I take the job?",
    "Use your best brain for this one", "Compare these three laptops", "Write a blog post about saving money",
    " ".join(["word"] * 70),
])
def test_hard_jobs_go_to_the_smart_model(said):
    assert turn_model(SETTINGS, said) == SMART


def test_a_follow_up_to_a_hard_job_keeps_the_smart_model():
    assert turn_model(SETTINGS, "Yes, make it shorter", last=SMART) == SMART
    assert turn_model(SETTINGS, "Yes, make it shorter", last=CHEAP) == CHEAP
    assert turn_model(SETTINGS, "What time is it in Tokyo?", last=SMART) == CHEAP


def test_cost_saver_off_or_smart_model_set():
    assert turn_model(replace(SETTINGS, cost_saver=False), "Hello") == SMART
    smart = replace(SETTINGS, smart_model="claude-opus-5-5")
    assert turn_model(smart, "Write an essay on tea") == "claude-opus-5-5"
    assert turn_model(smart, "Hello") == CHEAP
    assert request_options(smart)["model"] == "claude-opus-5-5"  # background jobs use the smart model too


def test_cheap_model_keeps_tool_search_thinking_and_effort():
    opts = request_options(SETTINGS, "low", CHEAP)
    assert opts["model"] == CHEAP
    assert any(t.get("type") == "tool_search_tool_bm25_20251119" for t in opts["tools"])
    assert sum(1 for t in opts["tools"] if not t.get("defer_loading")) < 60  # not every ability in full
    assert opts["thinking"] == {"type": "adaptive"} and opts["output_config"] == {"effort": "low"}
    assert "fallbacks" not in opts  # Haiku has no server-side fallback
    assert any(t.get("type") == "web_search_20250305" for t in opts["tools"])


def test_prompt_caching_covers_tools_system_and_conversation():
    opts = request_options(SETTINGS)
    loaded = [t for t in opts["tools"] if not t.get("defer_loading") and "input_schema" in t]
    assert loaded[-1]["cache_control"] == {"type": "ephemeral"}
    assert opts["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert opts["cache_control"] == {"type": "ephemeral"}  # the conversation so far
    marks = sum("cache_control" in t for t in opts["tools"]) + 2
    assert marks <= 4  # the API allows four
    gateway = omniroute.gateway_request({**opts, "messages": []}, "auto")
    assert "cache_control" not in gateway and isinstance(gateway["system"], str)


def test_history_is_cut_back_in_one_go_so_the_cache_lasts():
    msgs = []
    for i in range(21):
        msgs += [{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": [text("a")]}]
    trimmed = trim_history(msgs, max_turns=20, keep=12)
    assert trimmed[0]["content"] == "q9" and len(trimmed) == 24
    assert trim_history(trimmed, max_turns=20, keep=12) is trimmed  # stays put until it grows past 20 again


async def test_each_turn_uses_its_own_model_and_the_hud_shows_who_answered():
    sent = []

    async def page(msg):
        sent.append(msg)

    client = FakeClient(reply("end_turn", text("Very well, sir."), model="claude-haiku-5-5"),
                        reply("end_turn", text("Here is your essay."), model="claude-opus-5"))
    b = Brain(SETTINGS, client, http=None, page=page)
    await run(b, "How are you?")
    await run(b, "Write me an essay about tea")
    assert [r["model"] for r in client.requests] == [CHEAP, SMART]
    assert [m["model"] for m in sent if m["type"] == "model"] == ["claude-haiku-5-5", "claude-opus-5"]
    assert b.last_model == SMART


async def test_the_hud_names_omniroute_when_it_answered():
    sent = []

    async def page(msg):
        sent.append(msg)

    client = FakeClient(reply("end_turn", text("Hello."), model="gemini-2.5-flash"))
    client.last_route = "OmniRoute"
    await run(Brain(SETTINGS, client, http=None, page=page), "Hello")
    assert sent[-1] == {"type": "model", "model": "OmniRoute · gemini-2.5-flash"}


async def test_no_credit_and_no_free_ai_is_said_plainly_once():
    b = Brain(SETTINGS, FakeClient(error=omniroute.NoThinkingCredit("both down")), http=None)
    first = await run(b, "Hello")
    second = await run(b, "Hello?")
    assert first == ["My thinking credit has run out and the free AI isn't connected — add the free Gemini key "
                     "in OmniRoute."]
    assert second == [brain.LINES["en"]["still_no_credit"]]
    b.client = FakeClient(reply("end_turn", text("I'm back.")))
    await run(b, "Hello")
    b.client = FakeClient(error=omniroute.NoThinkingCredit("both down again"))
    assert await run(b, "Hello") == first  # back in full after a working turn
    assert brain.error_key(omniroute.NoThinkingCredit("x")) == "no_credit_free"
