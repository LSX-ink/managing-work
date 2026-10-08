import asyncio
import json

import httpx
import pytest

import design_extract as dx
import memory
import tools
from config import Settings

PAGE = """<!doctype html><html><head>
<title>Kinetic Demo</title>
<meta name="theme-color" content="#4f46e5">
<link rel="icon" href="/favicon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Space+Grotesk">
<link rel="stylesheet" href="/css/main.css">
<link rel="stylesheet" href="https://cdn.test/extra.css">
<style>
:root { --brand: #4f46e5; --bg-page: #ffffff; --text-main: #111827; --radius-card: 12px; }
@media (max-width: 768px) { .nav { display: none; } }
</style>
</head><body style="background: var(--bg-page); color: var(--text-main)">
<div class="card" style="padding: 24px; border-radius: 12px">Hi</div>
</body></html>"""

MAIN = """/* main */
@font-face { font-family: "Ignored Face"; src: url(a.woff2); }
body { font-family: "Inter", system-ui, sans-serif; font-size: 16px; line-height: 1.5; margin: 0; }
h1 { font-family: 'Space Grotesk', sans-serif; font-size: 3rem; font-weight: 700; }
h2 { font-size: 2rem; font-weight: 600; }
small { font-size: 14px; }
.btn { background-color: var(--brand); color: #fff; padding: 8px 16px; border-radius: 9999px;
  transition: background-color 200ms cubic-bezier(0.4, 0, 0.2, 1); }
.btn:hover { background-color: rgb(67, 56, 202); }
.card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
.tag { background: hsl(160, 84%, 39%); color: white; border-radius: 4px; margin-bottom: 8px; }
.muted { color: #6b7280; }
p { color: var(--text-main); margin: 0 0 16px; }
@media (min-width: 1024px) { .wrap { padding: 32px; } }
"""

EXTRA = ".modal { box-shadow: 0 10px 25px rgba(0,0,0,.2); border-radius: 12px; transition: opacity .3s ease; }"

seen = []


def handler(request: httpx.Request) -> httpx.Response:
    seen.append(str(request.url))
    host, path = request.url.host, request.url.path
    if host == "kinetic.test" and path == "/":
        return httpx.Response(200, text=PAGE, headers={"content-type": "text/html; charset=utf-8"})
    if host == "kinetic.test" and path == "/css/main.css":
        return httpx.Response(200, text=MAIN, headers={"content-type": "text/css"})
    if host == "cdn.test":
        return httpx.Response(200, text=EXTRA, headers={"content-type": "text/css"})
    if host == "many.test" and path == "/":
        links = "".join(f'<link rel="stylesheet" href="/s{i}.css">' for i in range(12))
        return httpx.Response(200, text=f"<html><head>{links}</head></html>", headers={"content-type": "text/html"})
    if host == "many.test" and path == "/s0.css":
        return httpx.Response(200, text="a{color:#123456}" * 200_000, headers={"content-type": "text/css"})
    if host == "many.test":
        return httpx.Response(200, text=".x { color: #ff0000; padding: 4px; }", headers={"content-type": "text/css"})
    if host == "bare.test":
        return httpx.Response(200, text="<html><body><p>No styles here</p></body></html>",
                              headers={"content-type": "text/html"})
    if host == "moved.test":
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def public_links(monkeypatch):
    real = memory.check_public

    async def ok(url):
        if "127.0.0.1" in url or "192.168." in url:
            await real(url)  # the real check: refuses without touching the network
    monkeypatch.setattr(memory, "check_public", ok)
    seen.clear()


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def call(s, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await dx.run_tool("extract_design_system", args, s, http)
    return asyncio.run(go())


def test_extracts_palette_fonts_and_scales():
    found = asyncio.run(_extract("kinetic.test"))
    g = found["groups"]
    assert g["brand"] == "#4f46e5"
    assert g["background"] == "#ffffff"
    assert g["text"] == "#111827"
    assert g["border"] == "#e5e7eb"
    assert g["accent"] == "#10b77f"  # hsl(160, 84%, 39%)
    assert "#4338ca" in found["palette"]  # rgb(67, 56, 202)
    assert found["font_list"][:2] == ["Inter", "Space Grotesk"]
    assert "Ignored Face" not in found["font_list"] and "Ignored Face" in found["faces"]
    assert found["google"] == ["Inter", "Space Grotesk"]
    assert found["type_scale"] == [14, 16, 32, 48]
    assert {700, 600} <= set(found["weights"])
    assert {8, 16, 24, 32} <= set(found["space_scale"])
    assert found["radius_scale"][-1] == "full" and "12px" in found["radius_scale"] and "4px" in found["radius_scale"]
    assert found["shadow_list"][0] in ("0 1px 3px rgba(0, 0, 0, 0.1)", "0 10px 25px rgba(0,0,0,.2)")
    assert len(found["shadow_list"]) == 2
    assert found["breakpoint_list"] == [768, 1024]
    assert found["duration_list"] == [200, 300]
    assert "cubic-bezier(0.4,0,0.2,1)" in found["easing_list"]
    assert found["variables"]["--brand"] == "#4f46e5"
    assert found["title"] == "Kinetic Demo" and found["theme"] == "#4f46e5"
    assert found["icon"] == "https://kinetic.test/favicon.png"
    assert "light look" in found["vibe"] and ("blue" in found["vibe"] or "purple" in found["vibe"])


async def _extract(url):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        return await dx.extract(http, url)


def test_saves_three_files_in_kinetic_web_designs(s):
    out = call(s, url="https://kinetic.test/")
    assert "#4f46e5" in out and "Inter" in out and "Kinetic Web Designs/kinetic.test" in out
    folder = memory.root(s) / "Kinetic Web Designs" / "kinetic.test"
    md = (folder / "DESIGN.md").read_text(encoding="utf-8")
    assert "## Colours" in md and "| Brand | `#4f46e5`" in md and "## Typography" in md and "## Spacing" in md
    t = json.loads((folder / "tokens.json").read_text(encoding="utf-8"))
    assert set(t) >= {"color", "fontFamily", "fontSize", "spacing", "borderRadius", "shadow", "duration"}
    assert t["color"]["brand"] == {"$type": "color", "$value": "#4f46e5"}
    assert t["fontFamily"]["primary"]["$type"] == "fontFamily" and t["fontFamily"]["primary"]["$value"][0] == "Inter"
    assert t["fontSize"]["1"] == {"$type": "dimension", "$value": "14px"}
    assert t["borderRadius"]["full"]["$value"] == "9999px"
    shadow = next(v["$value"] for v in t["shadow"].values() if isinstance(v["$value"], dict))
    assert set(shadow) >= {"color", "offsetX", "offsetY", "blur", "spread"}
    assert t["duration"]["1"] == {"$type": "duration", "$value": "200ms"}
    for group in ("color", "fontSize", "spacing", "borderRadius", "shadow", "duration"):
        for key, token in t[group].items():
            if key != "palette":
                assert "$type" in token and "$value" in token
    css = (folder / "tokens.css").read_text(encoding="utf-8")
    assert css.count(":root {") == 1 and "--color-brand: #4f46e5;" in css and "--brand: #4f46e5;" in css


def test_name_and_no_save(s):
    call(s, url="kinetic.test", name="My Pick")
    assert (memory.root(s) / "Kinetic Web Designs" / "My Pick" / "tokens.css").exists()
    out = call(s, url="kinetic.test", name="Not Saved", save=False)
    assert "Saved" not in out and not (memory.root(s) / "Kinetic Web Designs" / "Not Saved").exists()


def test_refuses_private_addresses(s):
    with pytest.raises(ValueError, match="home network"):
        call(s, url="http://127.0.0.1/")
    with pytest.raises(ValueError, match="home network"):
        call(s, url="http://192.168.1.1/")
    with pytest.raises(ValueError, match="home network"):
        call(s, url="https://moved.test/")  # a redirect into the PC is refused too
    assert not any("127.0.0.1" in u for u in seen)


def test_sheet_count_and_size_caps(s, monkeypatch):
    monkeypatch.setattr(dx, "MAX_CSS", 1024 * 1024)
    out = call(s, url="many.test", save=False)
    css = [u for u in seen if u.endswith(".css")]
    assert len(css) == dx.MAX_SHEETS == 8
    assert "skipped 1 stylesheet" in out
    found = asyncio.run(_extract("many.test"))
    assert "#123456" not in found["palette"] and found["groups"]["brand"] == "#ff0000"


def test_friendly_errors(s):
    with pytest.raises(ValueError, match="website address"):
        call(s, url="not a site")
    with pytest.raises(ValueError, match="http or https"):
        call(s, url="ftp://kinetic.test/")
    with pytest.raises(ValueError, match="any CSS"):
        call(s, url="bare.test")
    with pytest.raises(ValueError, match="404"):
        call(s, url="nowhere.test")


def test_registered_and_deferred():
    assert dx in tools.ABILITIES and dx not in tools.ALWAYS_LOADED
    assert "design_advice" in dx.tool_definitions()[0]["description"]
