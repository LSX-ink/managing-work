import asyncio

import pytest

import design
import tools
from config import Settings


def ask(args):
    return asyncio.run(design.run_tool("design_advice", args, Settings()))


def test_design_system_plan():
    out = ask({"query": "bakery website warm cosy", "design_system": True, "project": "Lebo's Bakery"})
    assert "Design System" in out and "Colors" in out and "Typography" in out
    assert "#" in out  # hex colours


def test_domain_search():
    out = ask({"query": "focus outline keyboard", "domain": "ux", "max_results": 2})
    assert "Domain:** ux" in out and "Result 1" in out


def test_stack_search():
    assert "Stack" in ask({"query": "responsive grid", "stack": "html-tailwind"})


def test_bad_input():
    with pytest.raises(ValueError):
        design.command({"query": " "})
    with pytest.raises(ValueError):
        design.command({"query": "x", "domain": "nope"})


def test_registered_and_deferred():
    assert design in tools.ABILITIES and design not in tools.ALWAYS_LOADED
    assert design.SCRIPTS.joinpath("search.py").exists()


def guide(args):
    return asyncio.run(design.run_tool("design_guide", args, Settings()))


def test_guide_list_and_read():
    listing = guide({})
    assert "emil-design-eng:" in listing and "review-animations:" in listing and len(design.guides()) == 29
    assert "Taste Skill guides:" in listing and "taste-skill:" in listing
    assert guide({"guide": "taste-skill"}).startswith("taste-skill/SKILL.md")
    out = guide({"guide": "animate", "file": "RECIPES.md"})
    assert out.startswith("animate/RECIPES.md")
    assert "Anime prompt guides:" in listing and "anime-mj:" in listing and "higgsfield-anime:" in listing
    assert "Niji" in guide({"guide": "anime-mj", "file": "sref-library.md"})
    assert "Example 2" in guide({"guide": "higgsfield-anime"}) or "EXAMPLE 2" in guide({"guide": "higgsfield-anime"})
    long = guide({"guide": "write-swift"})
    assert "call again with offset 20000" in long
    assert "offset" not in guide({"guide": "write-swift", "offset": 40000}).split("\n\n", 1)[1][-60:]


def test_guide_bad_names():
    with pytest.raises(ValueError):
        design.guide({"guide": "nope"})
    with pytest.raises(ValueError):
        design.guide({"guide": "animate", "file": "../../config.py"})
