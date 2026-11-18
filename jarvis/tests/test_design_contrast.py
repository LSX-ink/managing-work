import asyncio

import design_contrast as dc
import tools
from config import Settings


def ask(args):
    return asyncio.run(dc.run_tool("check_contrast", args, Settings()))


def test_known_ratios():
    assert round(dc.ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(dc.ratio("#ffffff", "#ffffff"), 2) == 1.0
    assert round(dc.ratio("#767676", "#ffffff"), 2) == 4.54  # the classic lightest AA grey on white


def test_pair_passes_and_fails():
    out = ask({"text": "#000", "background": "white"})
    assert "21.00:1" in out and "AAA text pass" in out and "Fix" not in out
    out = ask({"text": "#9ca3af", "background": "#ffffff"})
    assert "AA text fail" in out and "Fix: use #" in out


def test_fix_reaches_aa_and_keeps_hue():
    better = dc.fix("#60a5fa", "#ffffff")
    assert dc.ratio(better, "#ffffff") >= dc.AA
    r, g, b = dc.rgb(better)
    assert b > r and b > g  # still blue
    assert dc.ratio(dc.fix("#333333", "#000000"), "#000000") >= dc.AA  # lightens on dark backgrounds


def test_rgb_hsl_and_see_through():
    assert "21.00:1" in ask({"text": "rgb(255, 255, 255)", "background": "hsl(0, 0%, 0%)"})
    assert dc.colour("rgba(0, 0, 0, 0.5)", "#ffffff") in ("#7f7f7f", "#808080")  # half black over white


def test_pairs_and_palette():
    out = ask({"pairs": [["#111827", "#ffffff"], ["#ffffff", "#4f46e5"]]})
    assert out.count(":1,") == 2
    out = ask({"palette": ["#ffffff", "#111827", "#e5e7eb", "#6b7280"]})
    assert "Checked 4 colours (6 pairs)" in out and "#ffffff + #111827" in out


def test_bad_colour_and_empty():
    assert "Can't read the colour" in ask({"text": "notacolour", "background": "#fff"})
    assert "Give a text" in ask({})


def test_registered():
    assert dc in tools.ABILITIES
    assert "check_contrast" in {t["name"] for t in dc.tool_definitions()}
