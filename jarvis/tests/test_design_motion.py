import asyncio

import pytest

import design_motion as dm
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dm.run_tool("make_motion", args, settings))


def test_spring_starts_at_0_ends_at_1():
    points, ms = dm.spring(170, 26)
    assert points[0] == 0 and points[-1] == 1 and len(points) == dm.SAMPLES + 1
    assert 300 < ms < 1500
    assert dm.overshoot(points) < 0.05  # near critically damped barely overshoots


def test_bouncy_overshoots_and_stiff_is_faster():
    soft, soft_ms = dm.spring(120, 22)
    bouncy, _ = dm.spring(300, 10)
    stiff, stiff_ms = dm.spring(600, 49)
    assert dm.overshoot(bouncy) > 0.2
    assert stiff_ms < soft_ms


def test_linear_easing_format():
    text = dm.linear_easing([0.0, 0.5, 1.0])
    assert text == "linear(0, 0.5, 1)"


def test_feels():
    snappy, calm = dm.build("snappy"), dm.build("calm")
    assert snappy["durations"]["base"] < calm["durations"]["base"]
    assert dm.build("bouncy")["bounce"] > 0
    with pytest.raises(ValueError):
        dm.build("wobbly")
    with pytest.raises(ValueError):
        dm.spring(0, 10)


def test_summary_and_save(s, tmp_path):
    out = ask({}, s)
    assert "Motion set (smooth)" in out and "linear(0," in out and "Saved" not in out
    out = ask({"stiffness": 300, "damping": 10, "name": "Lebo's Bakery"}, s)
    assert "Saved motion.md and motion.css" in out
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery"
    css = (folder / "motion.css").read_text()
    assert "--ease-spring: linear(" in css and "prefers-reduced-motion" in css
    assert "stiffness 300" in (folder / "motion.md").read_text()


def test_bad_input(s):
    assert "Pick a feel" in ask({"feel": "wobbly"}, s)


def test_registered():
    assert dm in tools.ABILITIES
