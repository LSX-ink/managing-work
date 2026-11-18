"""Build a stays concept page for any short-let host from its folder's config.json, rooms.json and place.json.

The page is the stays design (stays_page.py: logo intro, walkthrough-video hero, 3D house with every room clickable,
book direct synced with Airbnb/Booking.com, reviews, find us) re-dressed per host from config.json:

{"intro": "BRENTON-ON-SEA · KNYSNA · GARDEN ROUTE", "kicker": "On the cliffs · Brenton-on-Sea, Knysna",
 "h2": ["Wake up to", "the Indian Ocean."], "lead": "...", "stats": [["180&deg;", "ocean view"], ["6", "ways to stay"]],  (two extra stats after the Google rating and review count)
 "kind": "guesthouse", "unit": "room", "heading": "Six ways to stay. All facing the sea.", "where": ["On the cliffs of", "Brenton-on-Sea."],
 "colours": {"bg": "#f8f6f1", "ink": "#24343a", "muted": "#5f6b6e", "accent": "#2f7f96", "accent2": "#4fa3b8", "light": "#bfe6ee"},
 "floors": ["Ground floor", "First floor"], "sea": true, "pool": "Plunge pool · ocean view", "markers": ["Reception & breakfast"],
 "book": "https://...", "platforms": "Airbnb and Booking.com"}

rooms.json: [{"slug", "name", "floor", "summary", "story": [...], "photos": [...], "cover"}] (at most 4 per floor).
place.json: Google name, rating, reviews, quotes, address, phone, maps, website.
The folder also needs logo.png (make_logo() draws a wordmark when they have none), exterior.jpg (video poster) and,
when made, walkthrough.mp4. Usage: python stays_build.py <folder>
"""
import json, runpy, sys
from pathlib import Path

HERE = Path(__file__).parent


def make_logo(folder: Path, name: str, colour: str = "#24343a") -> None:
    """A clean wordmark logo for hosts with no logo of their own."""
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in ("georgia.ttf", "Georgia.ttf", "times.ttf"):
        try:
            font = ImageFont.truetype(f, 96); break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    words = name.upper()
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = int(probe.textlength(words, font=font)) + 40
    im = Image.new("RGBA", (w, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 18), words, font=font, fill=colour)
    im.save(folder / "logo.png")


def build(folder: Path) -> None:
    c = json.load(open(folder / "config.json", encoding="utf-8"))
    col = {"bg": "#f8f6f1", "ink": "#24343a", "muted": "#5f6b6e", "accent": "#2f7f96", "accent2": "#4fa3b8", "light": "#bfe6ee", **c.get("colours", {})}
    unit, units = c.get("unit", "room"), c.get("unit", "room") + "s"
    kind = c.get("kind", "guesthouse")
    floors = c.get("floors", ["Ground floor"])
    rgb = tuple(int(col["accent"][i:i + 2], 16) for i in (1, 3, 5))
    src = (HERE / "stays_page.py").read_text(encoding="utf-8")
    a, b = src.index("// the front door off School Road"), src.index("// warm lamps through the house")
    extra = "const gf = floors[0];\n"
    if c.get("sea"):
        extra += ("const sea = new THREE.Mesh(new THREE.PlaneGeometry(60, 80), new THREE.MeshStandardMaterial({{color: 0x2f7fa3, roughness: .25, metalness: .2, emissive: 0x1d5f80, emissiveIntensity: .25}}));\n"
                  "sea.rotation.x = -Math.PI / 2; sea.position.set(-46, -.45, 0); scene.add(sea);\n")
    if c.get("pool"):
        extra += ("const terrace = new THREE.Mesh(new THREE.BoxGeometry(4.2, .12, D * 2 + C), new THREE.MeshStandardMaterial({{color: 0xc9a77a, roughness: .9}})); terrace.position.set(-LEN / 2 - 2.3, -.06, 0); gf.add(terrace);\n"
                  "const pool = new THREE.Mesh(new THREE.BoxGeometry(2.4, .1, 3.4), new THREE.MeshStandardMaterial({{color: 0x5ec8e0, roughness: .1, emissive: 0x2aa6d6, emissiveIntensity: .35}})); pool.position.set(-LEN / 2 - 2.4, .02, -1.6); gf.add(pool);\n"
                  f"marker({json.dumps(c['pool'])}, gf, -LEN / 2 - 2.4, 1.6, -1.6, 0);\n")
    for i, m in enumerate(c.get("markers", [])):
        extra += f"marker({json.dumps(m)}, gf, {i * 2.5}, 1.9, 0, 0);\n"
    src = src[:a] + extra + src[b:]
    buttons = '<button data-f="all" class="on">Whole house</button>' + "".join(
        f'<button data-f="{i}">{f.replace(" floor", "")}</button>' for i, f in enumerate(floors)) if len(floors) > 1 else ""
    stats = "".join(f"<div><b>{x}</b>{y}</div>" for x, y in c.get("stats", []))
    R = [
        ('FLOORS = ["Ground floor", "First floor", "Second floor"]', f"FLOORS = {json.dumps(floors)}"),
        ("family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,500&family=DM+Sans:wght@400;500;600",
         "family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=DM+Sans:wght@400;500;600"),
        ("--bg:#fbf8f2;--ink:#2b2a28;--muted:#6f6a62;--gold:#b8860b;--gold2:#d9a521;",
         f"--bg:{col['bg']};--ink:{col['ink']};--muted:{col['muted']};--gold:{col['accent']};--gold2:{col['accent2']};"),
        ("--head:'Cinzel',Georgia,serif", "--head:'Cormorant Garamond',Georgia,serif"),
        (".hero h2 em{{color:#f3c64f}}", f".hero h2 em{{{{color:{col['light']}}}}}"),
        (".suite small{{color:#f3c64f;", f".suite small{{{{color:{col['light']};"),
        (".brand img{{height:52px;display:block;filter:brightness(0) invert(1);", ".brand img{{height:46px;display:block;filter:brightness(0) invert(1);"),
        ("MOSELEY VILLAGE &middot; BIRMINGHAM", c["intro"]),
        ('<a href="#suites">Suites</a>', f'<a href="#suites">{units.title()}</a>'),
        ('<p class="kicker">Twelve suites &middot; Moseley Village</p>', f'<p class="kicker" style="color:{col["light"]}">{c["kicker"]}</p>'),
        ("<h2>Distinctive luxury,<br><em>in Moseley Village.</em></h2>", f"<h2>{c['h2'][0]}<br><em>{c['h2'][1]}</em></h2>"),
        ("Twelve individually designed suites with king-size beds, walk-in showers, underfloor heating and a private entrance, in the heart of Moseley Village.", c["lead"]),
        ("<div><b>12</b>unique suites</div><div><b>4</b>floors</div>", stats),
        ("The house, in 3D", f"The {kind}, in 3D"), ("Choose your suite.", f"Choose your {unit}."),
        ("This is the real layout of the house, room by room, from the street front to the garden. Spin it, pick a floor, then tap any suite to walk into it and see every photo. Every room is different, so take a look around before you book.",
         f"Spin the {kind}{', pick a floor,' if len(floors) > 1 else ''} then tap any {unit} to walk into it and see every photo."),
        ('<button data-f="all" class="on">Whole house</button><button data-f="-1">Lower ground</button><button data-f="0">Ground</button><button data-f="1">First</button><button data-f="2">Second</button>', buttons),
        ("tap a suite to enter", f"tap a {unit} to enter"),
        ("Laid out from the house&rsquo;s approved floor plans (Birmingham City Council, ref. 2023/07524/PA)",
         c.get("plan_note", f"3D layout is illustrative, arranged from the {kind}&rsquo;s own {unit} details")),
        ('<p class="kicker reveal">The suites</p>', f'<p class="kicker reveal">The {units}</p>'),
        ("Twelve rooms. No two alike.", c["heading"]),
        ("Same suites. Better price.", f"Same {units}. Better price."),
        ("Calendar synced with Airbnb, so what you see here is what's free", f"Calendar synced with {c.get('platforms', 'Airbnb')}, so what you see here is what's free"),
        ("this calendar reads the Airbnb calendar automatically.", f"this calendar reads your {c.get('platforms', 'Airbnb')} calendars automatically."),
        ("In the heart of<br>Moseley Village.", f"{c['where'][0]}<br>{c['where'][1]}"),
        ("Book this suite", f"Book this {unit}"), ("Next suite &rarr;", f"Next {unit} &rarr;"),
        ('<a href="#house">The House</a>', f'<a href="#house">The {kind.title()}</a>'),
        (".labels span.x{{background:rgba(184,134,11,.9);", f".labels span.x{{{{background:rgba({rgb[0]},{rgb[1]},{rgb[2]},.92);"),
        ("[0, 1, 2].forEach(f => {{", f"{json.dumps(list(range(len(floors))))}.forEach(f => {{{{"),
        ("ground.position.y = -FLOOR_H * 1.55 - .3;", "ground.position.y = -.3;"),
        ("const ground = new THREE.Mesh(new THREE.CircleGeometry(26, 64), new THREE.MeshStandardMaterial({{color: 0xe9dfcc, roughness: 1}}));",
         "const ground = new THREE.Mesh(new THREE.CircleGeometry(26, 64), new THREE.MeshStandardMaterial({{color: 0x86a86a, roughness: 1}}));"),
        ("scene.fog = new THREE.Fog(0xf1e8d8, 45, 95);", "scene.fog = new THREE.Fog(0xdcebf0, 50, 110);"),
        ("background:radial-gradient(1200px 600px at 50% 40%,#fffaf0 0%,#f1e8d8 60%,#e6dac5 100%)", "background:radial-gradient(1200px 600px at 50% 40%,#ffffff 0%,#e3f0f3 60%,#cfe3e8 100%)"),
        ("controls.target.set(0, 2.6, 0);", "controls.target.set(-2, 1.6, 0);"),
        ("const HOME = new THREE.Vector3(25, 16, 25)", "const HOME = new THREE.Vector3(20, 15, 24)"),
        ("Explore the house in 3D", f"Explore the {kind} in 3D"),
        ("1: [{{x: 1, s: -1, l: 4.9, balcony: 1}}", "1: [{{x: 1, s: -1, l: 4.9}}"),
        ("0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7, bay: 1}}", "0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7}}"),
        ('const y = mode === "all" ? 2.6 :', 'const y = mode === "all" ? 1.6 :'),
        ("tt: new THREE.Vector3(0, 2.6, 0), done", "tt: new THREE.Vector3(-2, 1.6, 0), done"),
    ]
    if c.get("book"):
        R.append(("{e(place.get('website') or '#')}", "{e(" + repr(c["book"]) + ")}"))
    missing = [x[:60] for x, _ in R if x not in src]
    for x, y in R:
        src = src.replace(x, y)
    if missing:
        print("note: not found in stays_page.py:", missing)
    if not (folder / "walkthrough.mp4").exists():  # no video (credits low): the poster photo carries the hero
        src = src.replace('<source src="walkthrough.mp4" type="video/mp4">', "")
    if not (folder / "logo.png").exists():
        make_logo(folder, json.load(open(folder / "place.json", encoding="utf-8"))["name"])
    tmp = HERE / "_stays_build_run.py"
    tmp.write_text(src, encoding="utf-8")
    old = sys.argv
    sys.argv = [str(tmp), str(folder)]
    try:
        runpy.run_path(str(tmp), run_name="__main__")
    finally:
        sys.argv = old


if __name__ == "__main__":
    build(Path(sys.argv[1]))
