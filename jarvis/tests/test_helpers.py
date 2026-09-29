import asyncio
from types import SimpleNamespace

import pytest

import helpers
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False, enable_computer=True,
                    user_address="sir")


def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(name, args, id="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=args, id=id)


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


@pytest.fixture(autouse=True)
def no_jobs():
    helpers.jobs.clear()
    yield
    helpers.jobs.clear()


def announcer():
    said = []

    async def announce(text, kind):
        said.append((text, kind))

    return said, announce


def test_helper_gets_no_risky_or_recursive_tools():
    names = {t.get("name") for t in helpers.request_options(SETTINGS)["tools"]}
    types = {t.get("type", "") for t in helpers.request_options(SETTINGS)["tools"]}
    assert "save_to_memory" in names and "request_new_ability" in names
    assert not names & helpers.NAMES
    assert not any(n and n.startswith(helpers.RISKY_PREFIXES) for n in names)
    assert not any(t.startswith("computer_") for t in types)


def test_alfred_always_sees_the_helper_tools():
    import tools

    loaded = {t["name"] for t in tools.client_tool_definitions(SETTINGS) if not t.get("defer_loading")}
    assert helpers.NAMES <= loaded


async def test_job_runs_tools_then_announces_its_summary():
    client = FakeClient(
        reply("tool_use", tool_use("get_tasks", {})),
        reply("end_turn", text("Your week is planned, sir.\nMonday: gym. Tuesday: shopping.")),
    )
    said, announce = announcer()
    helpers.set_context(client, announce)
    started = helpers.start("Plan my week", SETTINGS, None)
    assert "job 1" in started.lower() or "job" in started
    job = next(iter(helpers.jobs.values()))
    assert "working" in helpers.status()
    await job.runner
    assert job.status == "done"
    assert said == [(f"Sir, the helper has finished job {job.id}. Your week is planned, sir.", "helper")]
    assert "Tuesday: shopping" in helpers.status(job.id)
    tool_result = client.requests[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and not tool_result.get("is_error")


async def test_helper_refuses_tools_it_was_not_given():
    client = FakeClient(
        reply("tool_use", tool_use("delete_memory_folder", {"folder": "Work"})),
        reply("end_turn", text("I left the folder alone.")),
    )
    said, announce = announcer()
    helpers.set_context(client, announce)
    helpers.start("Tidy up", SETTINGS, None)
    job = next(iter(helpers.jobs.values()))
    await job.runner
    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "can't use" in result["content"]


async def test_failures_are_announced_and_jobs_can_be_stopped():
    class Broken(FakeClient):
        async def _create(self, **kwargs):
            raise RuntimeError("no connection")

    said, announce = announcer()
    helpers.set_context(Broken(), announce)
    helpers.start("Research flights", SETTINGS, None)
    job = next(iter(helpers.jobs.values()))
    await job.runner
    assert job.status == "failed" and "couldn't finish" in said[0][0]

    class Slow(FakeClient):
        async def _create(self, **kwargs):
            await asyncio.sleep(60)

    helpers.set_context(Slow(), announce)
    helpers.start("Something slow", SETTINGS, None)
    slow = [j for j in helpers.jobs.values() if j.status == "working"][0]
    assert helpers.stop(slow.id) == f"Stopped job {slow.id}."
    with pytest.raises(asyncio.CancelledError):
        await slow.runner
    assert slow.status == "stopped"


async def test_only_a_few_jobs_at_once():
    class Slow(FakeClient):
        async def _create(self, **kwargs):
            await asyncio.sleep(60)

    _, announce = announcer()
    helpers.set_context(Slow(), announce)
    for i in range(helpers.MAX_RUNNING):
        helpers.start(f"job {i}", SETTINGS, None)
    with pytest.raises(ValueError):
        helpers.start("one too many", SETTINGS, None)
    for job in helpers.jobs.values():
        job.runner.cancel()
