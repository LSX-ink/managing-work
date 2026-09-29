import pytest

import access
import screen
import tools
from config import Settings


def run(action, value=None):
    args = {"action": action}
    if value is not None:
        args["value"] = value
    return access.run_tool("accessibility_settings", args, Settings())


def test_every_action_returns_a_card():
    for action in access.ACTIONS:
        shown = run(action)
        assert isinstance(shown, screen.Shown)
        assert shown.card["kind"] == "access-set"
        assert shown.card["id"] == "access-settings"
        assert shown.card["data"]["action"] == action


def test_big_text_sizes():
    assert run("big_text", "large").card["data"]["value"] == "large"
    assert run("big_text", "extra large").card["data"]["value"] == "xl"
    assert run("big_text", "Extra_Large").card["data"]["value"] == "xl"
    assert run("big_text").card["data"]["value"] == "bigger"
    assert run("big_text", "smaller").card["data"]["value"] == "smaller"
    with pytest.raises(ValueError):
        run("big_text", "gigantic")


def test_toggles_default_to_on_and_accept_words():
    for action in access.TOGGLES:
        assert run(action).card["data"]["value"] == "on"
        assert run(action, "off").card["data"]["value"] == "off"
        assert run(action, "Toggle").card["data"]["value"] == "toggle"
    assert run("captions", "on") == "Captions on."
    with pytest.raises(ValueError):
        run("captions", "maybe")


def test_speech_speed():
    assert run("speech_speed", "slower").card["data"]["value"] == "slower"
    assert run("speech_speed", "normal").card["data"]["value"] == "normal"
    assert run("speech_speed", "0.8").card["data"]["value"] == "0.8"
    for bad in ("warp", "5", "0.1"):
        with pytest.raises(ValueError):
            run("speech_speed", bad)


def test_unknown_action_and_default():
    with pytest.raises(ValueError):
        run("levitate")
    shown = access.run_tool("accessibility_settings", {}, Settings())
    assert shown.card["data"]["action"] == "show_settings"


def test_registered_and_deferred():
    assert access in tools.ABILITIES
    assert access not in tools.ALWAYS_LOADED
    tool = access.tool_definitions()[0]
    assert tool["name"] in access.NAMES
    assert tool["input_schema"]["additionalProperties"] is False
