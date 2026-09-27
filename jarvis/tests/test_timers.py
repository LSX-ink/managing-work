import asyncio

import pytest

import timers
from config import Settings


@pytest.fixture(autouse=True)
def clean():
    timers.timers.clear()
    timers.on_break = False
    yield
    timers.timers.clear()
    timers.on_break = False


def test_spoken():
    assert timers.spoken(90) == "1 minute 30 seconds"
    assert timers.spoken(3600) == "1 hour"
    assert timers.spoken(1) == "1 second"


def test_timer_rings_and_can_be_listed_and_cancelled():
    said = []

    async def announce(text, kind):
        said.append((text, kind))

    async def main():
        timers.set_announcer(announce)
        s = Settings(user_address="sir")
        assert timers.set_timer(s, 0.05) == "Timer set for 0 seconds."
        assert "pasta" in timers.set_timer(s, 60, "pasta")
        assert "pasta: " in timers.list_timers()
        assert "More than one" in timers.cancel_timer()
        await asyncio.sleep(0.15)
        assert said == [("Sir, your timer is done.", "timer")]
        assert timers.cancel_timer("pasta timer") == "Cancelled the pasta timer."
        assert timers.list_timers() == "No timers are running."

    asyncio.run(main())


def test_timer_limits():
    async def main():
        with pytest.raises(ValueError):
            timers.set_timer(Settings(), 0)
        with pytest.raises(ValueError):
            timers.set_timer(Settings(), 25 * 3600)
    asyncio.run(main())


def test_break_until_called_by_name():
    s = Settings(persona="alfred")
    assert timers.wakes_from_break(s, "what's the weather")
    timers.take_break()
    assert not timers.wakes_from_break(s, "what's the weather")
    assert not timers.wakes_from_break(s, "Alfredo's pizza")
    assert timers.on_break
    assert timers.wakes_from_break(s, "Alfred, I'm back")
    assert not timers.on_break
