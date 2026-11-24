import asyncio

import aboutyou
import brain
import standing
import tools
from config import Settings


def make(tmp_path, **kw):
    return Settings(memory_dir=str(tmp_path), user_name="Thato", user_address="sir", **kw)


def test_stop_calling_me_by_name_is_caught_on_the_spot(tmp_path):
    s = make(tmp_path)
    assert not standing.no_name(s)
    for said in ["stop calling me by my name", "Don't call me Thato", "please stop calling me sir",
                 "never call me by my name again", "quit saying my name"]:
        assert standing.instant(s, said) is not None, said
    assert standing.no_name(s)
    assert len(standing.orders(s)) == 1  # saved once, not five times
    assert standing.instant(make(tmp_path), "stop the timer") is None
    assert standing.instant(make(tmp_path), "don't call me later") is None


def test_instant_answer_saves_it(tmp_path):
    s = make(tmp_path)
    assert brain.instant_answer("stop calling me by my name", s)
    assert standing.no_name(s)
    assert "Thato" not in brain.instant_answer("hello", s)


def test_scrub_takes_the_name_out_of_what_he_says(tmp_path):
    s = make(tmp_path)
    assert standing.scrub(s, "Sir, the timer is done.") == "Sir, the timer is done."  # no order yet
    standing.add(s, standing.NO_NAME_ORDER)
    assert standing.scrub(s, "Sir, the timer is done.") == "The timer is done."
    assert standing.scrub(s, "Thato, a reminder: call mum.") == "A reminder: call mum."
    assert standing.scrub(s, "Good morning, Thato. It's sunny.") == "Good morning. It's sunny."
    assert standing.scrub(s, "All clear, sir: that's fixed now.") == "All clear: that's fixed now."
    assert standing.scrub(s, "Hello Thato, what can I do?") == "Hello, what can I do?"
    assert standing.scrub(s, "Done. Thato, anything else?") == "Done. Anything else?"
    assert standing.scrub(s, "I've emailed Thato's client.") == "I've emailed Thato's client."


def test_name_from_about_you(tmp_path):
    s = Settings(memory_dir=str(tmp_path), user_name="", user_address="sir")
    aboutyou.remember(s, "User's name is Thato, pronounced Tah-toe")
    standing.add(s, "Never call the user by name")
    assert standing.scrub(s, "Right away, Thato.") == "Right away."


def test_prompt_orders_beat_everything(tmp_path):
    s = make(tmp_path)
    assert 'Address them as "sir"' in brain.system_prompt(s)
    standing.add(s, standing.NO_NAME_ORDER)
    standing.add(s, "Don't mention drive space", ["drive", "health check"])
    prompt = brain.system_prompt(s)
    assert 'Address them as "sir"' not in prompt
    assert prompt.rstrip().endswith("just talk to them.")
    assert "STANDING ORDERS" in prompt and "Don't mention drive space" in prompt and "[quiet" not in prompt


def test_quiet_alerts(tmp_path):
    s = make(tmp_path)
    standing.add(s, "No health check alerts", ["health check", "kind:health"])
    assert standing.is_quiet(s, "Sir, a health check: the main drive is nearly full.")
    assert standing.is_quiet(s, "anything", "health")
    assert not standing.is_quiet(s, "Sir, a reminder: call mum.", "timer")


def test_remove_and_list(tmp_path):
    s = make(tmp_path)
    standing.add(s, standing.NO_NAME_ORDER)
    assert "name" in standing.listing(s)
    assert standing.remove(s, "name").startswith("Dropped 1")
    assert not standing.no_name(s)


def test_tools_registered(tmp_path):
    defs = {t["name"]: t for t in tools.client_tool_definitions(Settings())}
    for name in standing.NAMES:
        assert name in defs and not defs[name].get("defer_loading")
    s = make(tmp_path)
    out = asyncio.run(tools.run_tool("add_standing_order", {"order": "Keep answers short"}, s, None)) \
        if asyncio.iscoroutinefunction(tools.run_tool) else tools.run_tool("add_standing_order", {"order": "x"}, s, None)
    assert "standing order" in str(out).lower()
