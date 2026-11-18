import asyncio

import aboutyou
import brain
import tools
from config import Settings


def test_remember_and_forget(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert aboutyou.prompt_section(s) == ""
    assert aboutyou.remember(s, "  Allergic   to nuts ") == "Remembered."
    assert aboutyou.remember(s, "allergic to nuts") == "I already knew that."
    aboutyou.remember(s, "Sister Lebo's birthday is 3 May")
    assert aboutyou.facts(s) == ["Allergic to nuts", "Sister Lebo's birthday is 3 May"]
    assert "- Sister Lebo's birthday is 3 May" in brain.system_prompt(s)
    assert aboutyou.forget(s, "birthday lebo") == "Forgotten: Sister Lebo's birthday is 3 May"
    assert "anything like that" in aboutyou.forget(s, "cats")
    assert aboutyou.facts(s) == ["Allergic to nuts"]
    # the user can edit the file by hand
    aboutyou.path(s).write_text("# notes\n- Likes jazz\nstray line\n- \n", encoding="utf-8")
    assert aboutyou.facts(s) == ["Likes jazz"]


def test_tools_route(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert asyncio.run(tools.run_tool("remember_about_user", {"fact": "Drives a Polo"}, s, None)) == "Remembered."
    assert aboutyou.facts(s) == ["Drives a Polo"]


class _Learner:
    def __init__(self, answer):
        self.answer, self.asked = answer, []
        self.messages = self

    async def create(self, **kw):
        self.asked.append(kw)
        return type("R", (), {"content": [type("B", (), {"text": self.answer})()]})()


def test_only_turns_that_sound_lasting_are_worth_learning():
    assert aboutyou.worth_learning("from now on only answer what I ask")
    assert aboutyou.worth_learning("my client Ada pays £300 a month")
    assert not aboutyou.worth_learning("what's the weather")
    assert not aboutyou.worth_learning("never")  # too short to mean anything


async def test_learns_up_to_two_lasting_facts_and_never_secrets(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    client = _Learner("- Wants short, direct answers\n- Ada's Salon pays £300 a month\n- Third fact")
    assert await aboutyou.learn(s, client, "only answer what I ask; Ada pays £300", "Very good, sir.") == [
        "Wants short, direct answers", "Ada's Salon pays £300 a month"]
    assert "Notebook so far:\n(empty)" in client.asked[0]["messages"][0]["content"]
    assert await aboutyou.learn(s, _Learner("NONE"), "stop that", "ok") == []
    assert await aboutyou.learn(s, _Learner("- His bank password is hunter2"), "remember my password", "ok") == []
    assert aboutyou.facts(s) == ["Wants short, direct answers", "Ada's Salon pays £300 a month"]
