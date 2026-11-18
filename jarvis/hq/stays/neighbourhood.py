"""Explore the neighbourhood (owner, 24 Oct 2026: "could we not use Google Maps Street View and satellite"): Google's
own satellite map and Street View of their street, embedded the way Google allows (their live player, with Google's
attribution), not copied images. place.json needs "loc" {"latitude", "longitude"}; "streetview": false hides that half
when Google has no imagery there. Used by stays_page.py and ash_page.py."""
import json
from html import escape as e
from pathlib import Path

CSS = """
#hood{padding:110px 0 30px}#hood .grid2{display:grid;grid-template-columns:1.25fr 1fr;gap:18px;margin-top:34px}
#hood figure{margin:0;position:relative;border-radius:22px;overflow:hidden;border:1px solid var(--line);background:#e9e4da;height:min(58vh,480px)}
#hood iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
#hood figcaption{position:absolute;left:14px;bottom:44px;z-index:2;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.9);font:600 .72rem var(--body);letter-spacing:.18em;text-transform:uppercase;color:#222;pointer-events:none}
#hood .head p{color:var(--muted)}
@media (max-width:900px){#hood .grid2{grid-template-columns:1fr}}
"""


def add_hood(html: str, out: Path) -> str:
    p = json.load(open(out / "place.json", encoding="utf-8"))
    loc = p.get("loc")
    if not loc:
        return html
    lat, lng = loc["latitude"], loc["longitude"]
    sat = f"https://maps.google.com/maps?q={lat},{lng}&t=k&z=18&output=embed"
    figs = f'<figure><figcaption>From above</figcaption><iframe loading="lazy" title="Satellite view" src="{e(sat)}"></iframe></figure>'
    if p.get("streetview", True):
        sv = f"https://maps.google.com/maps?layer=c&cbll={lat},{lng}&cbp=12,0,0,0,0&output=svembed"
        figs += f'<figure><figcaption>Street View</figcaption><iframe loading="lazy" title="Street View" src="{e(sv)}"></iframe></figure>'
    else:
        terrain = f"https://maps.google.com/maps?q={lat},{lng}&t=p&z=13&output=embed"
        figs += f'<figure><figcaption>The area</figcaption><iframe loading="lazy" title="The area" src="{e(terrain)}"></iframe></figure>'
    sec = ('<section id="hood"><div class="wrap"><div class="head"><div><p class="kicker reveal">The neighbourhood</p>'
           '<h2 class="reveal">See exactly<br>where you&rsquo;ll be.</h2></div><p class="reveal">Fly over it from above, then drop in and look around the street, live from Google Maps.</p></div>'
           f'<div class="grid2">{figs}</div></div></section>\n')
    html = html.replace('<section id="visit">', sec + '<section id="visit">', 1)
    return html.replace("</style>", CSS + "</style>", 1)
