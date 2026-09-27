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
