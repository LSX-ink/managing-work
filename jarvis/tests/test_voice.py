from dataclasses import replace

import pytest

import screen
import tools
import voice
from config import settings


def test_choose_pops_up_the_voice_picker():
    out = voice.run_tool("change_voice", {"action": "choose"}, replace(settings, elevenlabs_api_key=""))
    assert isinstance(out, screen.Shown)
    assert out.card["kind"] == "voice-picker"
    assert out.card["data"]["action"] == "choose" and out.card["data"]["server_voice"] is False
    assert "Try" in str(out)


@pytest.mark.parametrize("action", ["faster", "slower", "deeper", "higher", "reset"])
def test_adjustments_reach_the_page(action):
    out = voice.run_tool("change_voice", {"action": action}, replace(settings, elevenlabs_api_key=""))
    assert out.card["data"]["action"] == action


def test_elevenlabs_users_are_told_where_to_change_it():
    out = voice.run_tool("change_voice", {"action": "choose"}, replace(settings, elevenlabs_api_key="k"))
    assert "ELEVENLABS_VOICE_ID" in str(out) and out.card["data"]["server_voice"] is True


def test_unknown_action_is_refused():
    with pytest.raises(ValueError):
        voice.run_tool("change_voice", {"action": "sing"}, settings)


def test_change_voice_is_registered():
    names = {d["name"] for d in tools.client_tool_definitions(settings)}
    assert "change_voice" in names
