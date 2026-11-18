import asyncio

import pytest
from PIL import Image

import design_gradient as dg
import tools
from config import Settings
from design_contrast import ratio


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ask(args, settings):
    return asyncio.run(dg.run_tool("make_gradient", args, settings))


def chroma(hex_):
    _, a, b = dg.oklab(hex_)
    return (a * a + b * b) ** 0.5


@pytest.mark.parametrize("hex_", ["#c2410c", "#2563eb", "#000000", "#ffffff", "#7c3aed"])
def test_oklab_round_trip(hex_):
    assert dg.from_oklab(dg.oklab(hex_)) == hex_


def test_middle_stays_colourful():
    middle = dg.mix("#2563eb", "#f97316", 0.5)
    plain = "#" + "".join(f"{(int('2563eb'[i:i + 2], 16) + int('f97316'[i:i + 2], 16)) // 2:02x}" for i in (0, 2, 4))
    assert chroma(middle) > 2 * chroma(plain)  # a plain RGB blend goes grey; this doesn't
    assert dg.mix("#000000", "#ffffff", 0.5) == "#636363"  # greys stay grey (perceptual mid-grey)


def test_ramp_and_css():
    g = dg.build(["#2563eb", "#f97316"], "linear", 90)
    assert len(g["points"]) == 2 + dg.STEPS and g["points"][0] == "#2563eb" and g["points"][-1] == "#f97316"
    assert g["css"].startswith("linear-gradient(90deg, #2563eb 0%,") and g["css"].endswith("#f97316 100%)")
    assert dg.build(["#000", "#fff"], "radial")["css"].startswith("radial-gradient(circle")
    assert dg.build(["#7c3aed", "#ec4899", "#f59e0b"], "aurora")["css"].count("radial-gradient") == 3


def test_text_colour_is_checked_everywhere():
    dark = dg.build(["#0f172a", "#1e3a8a"])["text"]
    assert dark["colour"] == "#ffffff" and dark["use"] == "all text"
    loud = dg.build(["#2563eb", "#f97316"])["text"]
    assert loud["ratio"] == min(ratio(loud["colour"], p) for p in dg.build(["#2563eb", "#f97316"])["points"])


def test_linear_png_runs_the_right_way():
    left_right = dg.draw(dg.build(["#000000", "#ffffff"], "linear", 90), (200, 100))
    assert left_right.getpixel((2, 50))[0] < 30 and left_right.getpixel((197, 50))[0] > 225
    top_bottom = dg.draw(dg.build(["#000000", "#ffffff"], "linear", 180), (100, 300))
    assert top_bottom.getpixel((50, 2))[0] < 30 and top_bottom.getpixel((50, 297))[0] > 225


def test_save(s, tmp_path):
    out = ask({"colours": ["#7c3aed", "#ec4899", "#f59e0b"], "style": "aurora", "name": "Lebo's Bakery"}, s)
    folder = tmp_path / "Kinetic Web Designs" / "Lebo's Bakery" / "gradients"
    assert "Made an aurora gradient" in out and "gradient-phone.png" in out
    assert Image.open(folder / "gradient-phone.png").size == (1080, 1920)
    assert Image.open(folder / "gradient-web.png").size == (1920, 1080)
    assert "--gradient: radial-gradient" in (folder / "gradient.css").read_text()
    assert 'href="gradient.css"' in (folder / "gradient.html").read_text()


def test_summary_without_saving(s):
    out = ask({"colours": ["#0f172a", "#1e3a8a"], "style": "radial"}, s)
    assert "Use white words" in out and "CSS: background: radial-gradient(" in out


def test_bad_input(s):
    assert "2 to 5 colours" in ask({"colours": ["#000"]}, s)
    assert "Pick a style" in ask({"colours": ["#000", "#fff"], "style": "conic"}, s)
    assert "Can't read the colour" in ask({"colours": ["#000", "bluey"]}, s)


def test_registered():
    assert dg in tools.ABILITIES
