from dataclasses import replace
from types import SimpleNamespace

import pytest

import brain
import computer
from brain import Brain, request_options
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False, enable_computer=True)


def screen_call(name, id, **args):
    return SimpleNamespace(type="tool_use", name=name, input=args, id=id, toolset_name="computer")


def reply(stop_reason, *blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


class FakeComputer:
    def __init__(self, fail_on=None):
        self.ran = []
        self.fail_on = fail_on

    def run(self, name, args):
        if name == self.fail_on:
            raise RuntimeError("boom")
        self.ran.append(name)
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "x"}}] \
            if name == "screenshot" else "OK"


def make(answers, comp=None, *responses):
    asked = []

    async def confirm(steps):
        asked.append(steps)
        return answers.pop(0)

    client = FakeClient(*responses)
    return Brain(SETTINGS, client, http=None, confirm=confirm, pc_control=comp or FakeComputer()), client, asked


async def run(b, text="do it"):
    said = []

    async def speak(t):
        said.append(t)

    await b.handle(text, speak)
    return said


def last_results(client):
    return client.requests[-1]["messages"][-1]["content"]


async def test_denied_actions_do_not_run():
    comp = FakeComputer()
    b, client, asked = make(["deny"], comp,
                            reply("tool_use", screen_call("left_click", "t1", coordinate=[10, 20]),
                                  screen_call("type", "t2", text="hi")),
                            reply("end_turn", SimpleNamespace(type="text", text="Very well.")))
    await run(b)
    assert asked == [["Left click at (10, 20)", 'Type "hi"']]
    assert comp.ran == []
    results = last_results(client)
    assert all(r["is_error"] and r["toolset_name"] == "computer" for r in results)


async def test_allowed_batch_runs_in_order_and_screenshots_skip_confirmation():
    comp = FakeComputer()
    b, client, asked = make(["allow"], comp,
                            reply("tool_use", screen_call("screenshot", "s0")),
                            reply("tool_use", screen_call("left_click", "t1", coordinate=[1, 2]),
                                  screen_call("screenshot", "t2")),
                            reply("end_turn"))
    await run(b)
    assert len(asked) == 1  # the lone screenshot needed no OK
    assert comp.ran == ["screenshot", "left_click", "screenshot"]
    assert [r["tool_use_id"] for r in last_results(client)] == ["t1", "t2"]


async def test_allow_all_lasts_until_next_message():
    comp = FakeComputer()
    b, client, asked = make(["allow_all", "deny"], comp,
                            reply("tool_use", screen_call("key", "a", text="ctrl+s")),
                            reply("tool_use", screen_call("key", "b", text="Return")),
                            reply("end_turn"),
                            reply("tool_use", screen_call("key", "c", text="Return")),
                            reply("end_turn"))
    await run(b)
    assert len(asked) == 1 and comp.ran == ["key", "key"]
    await run(b, "again")
    assert len(asked) == 2 and comp.ran == ["key", "key"]


async def test_failure_stops_the_rest_of_the_batch():
    comp = FakeComputer(fail_on="left_click")
    b, client, _ = make(["allow"], comp,
                        reply("tool_use", screen_call("left_click", "t1", coordinate=[1, 1]),
                              screen_call("type", "t2", text="x")),
                        reply("end_turn"))
    await run(b)
    r1, r2 = last_results(client)
    assert r1["is_error"] and "boom" in r1["content"]
    assert r2["content"] == computer.NOT_EXECUTED
    assert comp.ran == []


def test_no_confirm_callback_means_deny():
    b = Brain(SETTINGS, FakeClient(), http=None, pc_control=FakeComputer())
    assert b.confirm is None


def test_toolset_only_when_enabled_and_supported():
    has = lambda s: any(t.get("type") == "computer_toolset_20260801" for t in request_options(s)["tools"])
    assert has(SETTINGS)
    assert not has(replace(SETTINGS, enable_computer=False))
    assert not has(replace(SETTINGS, model="claude-haiku-4-5"))
    names = {t.get("name") for t in request_options(replace(SETTINGS, enable_screen=True))["tools"]}
    assert "look_at_screen" not in names and "open_app" in names


def test_prune_images_keeps_newest():
    img = lambda: {"type": "image", "source": {}}
    msgs = [{"role": "user", "content": [{"type": "tool_result", "content": [img()]}]} for _ in range(5)]
    brain.prune_images(msgs, keep=2)
    kinds = [m["content"][0]["content"][0]["type"] for m in msgs]
    assert kinds == ["text", "text", "text", "image", "image"]


def test_scale_and_keys():
    assert computer.scale_factor(1024, 768) == 1.0
    assert computer.scale_factor(2560, 1440) == pytest.approx(0.5585, abs=1e-3)
    assert computer.to_keys("ctrl+Return") == ["ctrl", "enter"]
    assert computer.to_keys("alt+Tab") == ["alt", "tab"]


class FakeGui:
    def __init__(self, w, h):
        self.w, self.h, self.calls = w, h, []

    def size(self):
        return self.w, self.h

    def screenshot(self):
        from PIL import Image
        return Image.new("RGB", (self.w, self.h))

    def __getattr__(self, name):
        return lambda *a, **k: self.calls.append((name, a, k))


def fake_computer(w, h):
    c = computer.Computer.__new__(computer.Computer)
    c.gui, c._shot_size = FakeGui(w, h), None

    def shot():
        c._shot_size = (w, h)
        return c.gui.screenshot()
    c._shot = shot
    return c


def test_click_coordinates_are_scaled_back_to_the_screen():
    c = fake_computer(2560, 1440)
    shot = c.run("screenshot", {})
    assert shot[0]["type"] == "image"
    c.run("left_click", {"coordinate": [100, 50], "text": "ctrl"})
    names = [n for n, _, _ in c.gui.calls]
    assert names == ["keyDown", "click", "keyUp"]
    _, args, kwargs = c.gui.calls[1]
    assert args == (179, 90) and kwargs["clicks"] == 1


def test_type_and_key():
    c = fake_computer(1024, 768)
    c.run("type", {"text": "hello"})
    c.run("key", {"text": "ctrl+s", "repeat": 2})
    assert c.gui.calls[0][:2] == ("write", ("hello",))
    assert [call[1] for call in c.gui.calls[1:]] == [("ctrl", "s"), ("ctrl", "s")]
