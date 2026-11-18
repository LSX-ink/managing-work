"""Brenton on the Rocks (Knysna, South Africa) concept: the stays page (stays_page.py) re-dressed for a two-storey
clifftop guesthouse in their own colours, with the ocean, plunge-pool terrace and reception in the 3D house.
No public building plans exist for it online, so the 3D layout is labelled as illustrative."""
import runpy, sys
from pathlib import Path

src = Path(__file__).with_name("stays_page.py").read_text(encoding="utf-8")
cut_a = src.index("// the front door off School Road")
cut_b = src.index("// warm lamps through the house")
src = src[:cut_a] + r'''// the ocean on the cliff side, the plunge-pool terrace and reception
const sea = new THREE.Mesh(new THREE.PlaneGeometry(60, 80), new THREE.MeshStandardMaterial({{color: 0x2f7fa3, roughness: .25, metalness: .2, emissive: 0x1d5f80, emissiveIntensity: .25}}));
sea.rotation.x = -Math.PI / 2; sea.position.set(-46, -.45, 0); scene.add(sea);
const cliff = new THREE.Mesh(new THREE.BoxGeometry(6, 3, 60), new THREE.MeshStandardMaterial({{color: 0x6f8a55, roughness: 1}})); cliff.position.set(-16.5, -1.9, 0); scene.add(cliff);
const gf = floors[0];
const terrace = new THREE.Mesh(new THREE.BoxGeometry(4.2, .12, D * 2 + C), new THREE.MeshStandardMaterial({{color: 0xc9a77a, roughness: .9}})); terrace.position.set(-LEN / 2 - 2.3, -.06, 0); gf.add(terrace);
const pool = new THREE.Mesh(new THREE.BoxGeometry(2.4, .1, 3.4), new THREE.MeshStandardMaterial({{color: 0x5ec8e0, roughness: .1, emissive: 0x2aa6d6, emissiveIntensity: .35}})); pool.position.set(-LEN / 2 - 2.4, .02, -1.6); gf.add(pool);
marker("Plunge pool · ocean view", gf, -LEN / 2 - 2.4, 1.6, -1.6, 0);
marker("Reception & breakfast", gf, 0, 1.9, 0, 0);
''' + src[cut_b:]
R = [
    ('FLOORS = ["Ground floor", "First floor", "Second floor"]', 'FLOORS = ["Ground floor", "First floor"]'),
    ("family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,500&family=DM+Sans:wght@400;500;600",
     "family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=DM+Sans:wght@400;500;600"),
    ("--bg:#fbf8f2;--ink:#2b2a28;--muted:#6f6a62;--gold:#b8860b;--gold2:#d9a521;", "--bg:#f8f6f1;--ink:#24343a;--muted:#5f6b6e;--gold:#2f7f96;--gold2:#4fa3b8;"),
    ("--head:'Cinzel',Georgia,serif", "--head:'Cormorant Garamond',Georgia,serif"),
    (".hero h2 em{{color:#f3c64f}}", ".hero h2 em{{color:#bfe6ee}}"), (".suite small{{color:#f3c64f;", ".suite small{{color:#bfe6ee;"),
    (".brand img{{height:52px;display:block;filter:brightness(0) invert(1);", ".brand img{{height:46px;display:block;filter:brightness(0) invert(1);"),
    ("MOSELEY VILLAGE &middot; BIRMINGHAM", "BRENTON-ON-SEA &middot; KNYSNA &middot; GARDEN ROUTE"),
    ('<a href="#suites">Suites</a>', '<a href="#suites">Rooms</a>'),
    ("Twelve suites &middot; Moseley Village", "On the cliffs &middot; Brenton-on-Sea, Knysna"),
    ("<h2>Distinctive luxury,<br><em>in Moseley Village.</em></h2>", "<h2>Wake up to<br><em>the Indian Ocean.</em></h2>"),
    ("Twelve individually designed suites with king-size beds, walk-in showers, underfloor heating and a private entrance, in the heart of Moseley Village.",
     "A guesthouse on the cliffs of Brenton-on-Sea with a 180&deg; view of the Indian Ocean, where whales and dolphins swim past. Sea-view rooms with balconies, a heated plunge pool and breakfast with a view."),
    ("<div><b>12</b>unique suites</div><div><b>4</b>floors</div>", "<div><b>180&deg;</b>ocean view</div><div><b>6</b>ways to stay</div>"),
    ("The house, in 3D", "The guesthouse, in 3D"), ("Choose your suite.", "Choose your room."),
    ("This is the real layout of the house, room by room, from the street front to the garden. Spin it, pick a floor, then tap any suite to walk into it and see every photo. Every room is different, so take a look around before you book.",
     "Spin the guesthouse, pick a floor, then tap any room to walk into it and see every photo. Every room looks out to sea."),
    ('<button data-f="-1">Lower ground</button>', ""), ('<button data-f="2">Second</button>', ""),
    ("tap a suite to enter", "tap a room to enter"),
    ("Laid out from the house&rsquo;s approved floor plans (Birmingham City Council, ref. 2023/07524/PA)", "3D layout is illustrative, arranged by floor from the guesthouse&rsquo;s own room details"),
    ('<p class="kicker reveal">The suites</p>', '<p class="kicker reveal">The rooms</p>'),
    ("Twelve rooms. No two alike.", "Six ways to stay. All facing the sea."),
    ("Same suites. Better price.", "Same rooms. Better price."),
    ("you skip them, with the same rooms", "you skip them, with the same rooms"),
    ("Calendar synced with Airbnb, so what you see here is what's free", "Calendar synced with Airbnb and Booking.com, so what you see here is what's free"),
    ("this calendar reads the Airbnb calendar automatically.", "this calendar reads your Airbnb and Booking.com calendars automatically."),
    ("In the heart of<br>Moseley Village.", "On the cliffs of<br>Brenton-on-Sea."),
    ("Book this suite", "Book this room"),
    ('<a href="#house">The House</a>', '<a href="#house">The Guesthouse</a>'),
    ('<p class="kicker">On the cliffs', '<p class="kicker" style="color:#bfe6ee">On the cliffs'),
    (".labels span.x{{background:rgba(184,134,11,.9);", ".labels span.x{{background:rgba(47,127,150,.92);"), ("Next suite &rarr;", "Next room &rarr;"),
    ("[0, 1, 2].forEach(f => {{", "[0, 1].forEach(f => {{"),
    ("ground.position.y = -FLOOR_H * 1.55 - .3;", "ground.position.y = -.3;"),
    ("const ground = new THREE.Mesh(new THREE.CircleGeometry(26, 64), new THREE.MeshStandardMaterial({{color: 0xe9dfcc, roughness: 1}}));",
     "const ground = new THREE.Mesh(new THREE.CircleGeometry(26, 64), new THREE.MeshStandardMaterial({{color: 0x86a86a, roughness: 1}}));"),
    ("scene.fog = new THREE.Fog(0xf1e8d8, 45, 95);", "scene.fog = new THREE.Fog(0xdcebf0, 50, 110);"),
    ("background:radial-gradient(1200px 600px at 50% 40%,#fffaf0 0%,#f1e8d8 60%,#e6dac5 100%)", "background:radial-gradient(1200px 600px at 50% 40%,#ffffff 0%,#e3f0f3 60%,#cfe3e8 100%)"),
    ("controls.target.set(0, 2.6, 0);", "controls.target.set(-3, 1.6, 0);"),
    ("const HOME = new THREE.Vector3(25, 16, 25)", "const HOME = new THREE.Vector3(20, 15, 24)"),
    ("Explore the house in 3D", "Explore the guesthouse in 3D"),
    ("1: [{{x: 1, s: -1, l: 4.9, balcony: 1}}", "1: [{{x: 1, s: -1, l: 4.9}}"),
    ("0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7, bay: 1}}", "0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7}}"),
    ("const y = mode === \"all\" ? 2.6 :", "const y = mode === \"all\" ? 1.6 :"),
    ("tt: new THREE.Vector3(0, 2.6, 0), done", "tt: new THREE.Vector3(-3, 1.6, 0), done"),
]
missing = [a[:60] for a, b in R if a not in src]
for a, b in R:
    src = src.replace(a, b)
if missing:
    print("missing:", missing)
tmp = Path(__file__).with_name("_za_page_run.py")
tmp.write_text(src, encoding="utf-8")
runpy.run_path(str(tmp), run_name="__main__")
