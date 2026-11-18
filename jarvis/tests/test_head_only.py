from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def read(name):
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_head_only_loads_in_the_head_before_the_hud_extras():
    page = read("index.html")
    assert "/static/headonly.css" in page
    head = page[: page.index("</head>")]
    assert "/static/headonly.js" in head   # set before the first paint, so the panels never flash
    assert page.index("/static/headonly.js") < page.index("/static/hudplus.js")   # sees H and letters first


def test_head_only_hides_the_panels_but_not_the_pop_ups():
    css = read("headonly.css")
    for hidden in (".hud-bar", ".hud-left", ".hud-rightcol", "#status", "#alerts", "#folder-stars", "body.hud::before"):
        assert hidden in css
    for kept in ("#popups", "#memory-panel", "#np-popup", "#mic-help"):
        assert kept not in css
    assert "#confirm:not([hidden])" in css   # an approval still shows its tick and cross


def test_head_only_keys():
    js = read("headonly.js")
    assert "alfred-head-only" in js and "localStorage" in js
    for key in ("'h'", "'Escape'", "'/'", "head-peek"):
        assert key in js
    assert "else if (key === 'h') setClean" not in read("hudplus.js")
