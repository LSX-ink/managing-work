"""Concept site for Ash Lodge (Billingsley Park Lodges): a single-storey lodge. Cinematic walkthrough hero, a 3D lodge
laid out from the park's council-approved lodge plans with every space clickable, book direct (synced with Airbnb),
reviews and location. Built from the host's own Airbnb photos and words. Shares the stays page's base styles."""
import json, re, sys
from html import escape as e
from pathlib import Path

OUT = Path(sys.argv[1])
place = json.load(open(OUT / "place.json", encoding="utf-8"))
base = Path(__file__).with_name("stays_page.py").read_text(encoding="utf-8")
CSS = base[base.index("<style>\n") + 8: base.index("</style>")].replace("{{", "{").replace("}}", "}")

AIRBNB = "https://www.airbnb.co.uk/rooms/48307594"
P = lambda *f: [f"p/{x}.jpg" for x in f]
ZONES = [
    {"slug": "living", "name": "Living room", "kicker": "Open-plan living",
     "text": ["Light and airy, with comfortable sofas, a large-screen smart TV and free wi-fi throughout.",
              "French doors open straight onto the sun deck, so the countryside is part of the room."],
     "gallery": P("q22", "q29")},
    {"slug": "dining", "name": "Dining & kitchen", "kicker": "Open-plan living",
     "text": ["A dining area for two and a fully fitted modern kitchen with integrated appliances.",
              "Breakfast with the French doors open and the parkland in front of you."],
     "gallery": P("q15", "q29")},
    {"slug": "bedroom", "name": "The bedroom", "kicker": "King-size suite",
     "text": ["A master double bedroom with a king bed, dressing table and patio doors out to the deck and hot tub.",
              "Fully double glazed and centrally heated, so it is warm and cosy all year."],
     "gallery": P("q28", "q12", "q19", "q21")},
    {"slug": "ensuite", "name": "The en-suite", "kicker": "Bathroom",
     "text": ["A spacious en-suite with a freestanding bath and a separate walk-in shower.",
              "The perfect end to a day exploring South Shropshire."],
     "gallery": P("q07", "q18", "q00", "q16")},
    {"slug": "deck", "name": "Deck & hot tub", "kicker": "Outside",
     "text": ["A large, elevated sun deck with furniture, relaxer beds and your own private hot tub.",
              "The hot tub is checked every day, and lights up blue after dark."],
     "gallery": P("q25", "q20", "q26", "q06", "q11", "q13", "q02", "q24")},
    {"slug": "park", "name": "The park", "kicker": "Billingsley Park",
     "text": ["Private parkland in the rolling open countryside of South Shropshire, with private parking right outside.",
              "Deer, woodpeckers and wildflowers are regular visitors."],
     "gallery": P("q17", "q27", "q23", "q10", "q03", "q01", "q14", "q04", "q09", "q05", "q08")},
]
for z in ZONES:
    z["thumbs"] = [g.replace("p/", "t/") for g in z["gallery"]]
data = json.dumps({"zones": ZONES}, ensure_ascii=False)
quotes = [q for q in place["quotes"] if q["text"] and "Hazel" not in q["text"]][:4]
reviews = "".join(f'<blockquote class="reveal" style="--d:{i * 90}ms"><span>{"★" * int(q.get("rating") or 5)}</span>'
                  f'<p>&ldquo;{e(q["text"][:300])}{"…" if len(q["text"]) > 300 else ""}&rdquo;</p><cite>{e(q["author"])}</cite></blockquote>'
                  for i, q in enumerate(quotes))
cards = "".join(
    f'<button class="suite reveal" data-slug="{z["slug"]}" style="--d:{(i % 3) * 80}ms"><span class="img" style="background-image:url({z["thumbs"][0]})"></span>'
    f'<span class="meta"><small>{e(z["kicker"])}</small><b>{e(z["name"])}</b><em>{e(z["text"][0])}</em></span></button>' for i, z in enumerate(ZONES))
tel = "".join(ch for ch in place.get("phone", "") if ch.isdigit() or ch == "+")
LEAF = ('<svg class="leaf" viewBox="0 0 120 40" aria-hidden="true"><path d="M4 20 H116 M24 20 c6-10 16-12 22-10 c-4 6-12 10-22 10z M24 20 c6 10 16 12 22 10 '
        'c-4-6-12-10-22-10z M58 20 c6-10 16-12 22-10 c-4 6-12 10-22 10z M58 20 c6 10 16 12 22 10 c-4-6-12-10-22-10z M92 20 c5-7 13-9 20-6 c-5 5-12 6-20 6z"/></svg>')

html = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Ash Lodge | Billingsley Park | concept website</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
:root{{--bg:#f6f3ec;--ink:#22302a;--muted:#5f675f;--gold:#2f5d46;--gold2:#4f8a63;--wood:#b9783f;--panel:#ffffff;--line:rgba(34,48,42,.13);
--head:'Fraunces',Georgia,serif;--body:'DM Sans',system-ui,sans-serif}}
h1,h2,h3{{letter-spacing:-.01em}}em{{font-family:'Fraunces',serif;font-style:italic}}
.btn{{box-shadow:0 18px 40px -20px var(--gold)}}.btn.wood{{background:linear-gradient(120deg,#cf9256,var(--wood))}}
#intro{{background:#f6f3ec}}#intro .mark{{text-align:center;color:var(--gold)}}
#intro .mark b{{display:block;font-family:var(--head);font-weight:500;font-size:clamp(4rem,14vw,8.5rem);letter-spacing:.32em;margin-right:-.32em;line-height:1}}
#intro .mark b span{{display:inline-block;opacity:0;transform:translateY(40px);animation:up 1s cubic-bezier(.2,.8,.2,1) forwards}}
#intro p{{color:var(--wood)}}
.leaf{{width:min(260px,60vw);display:block;margin:14px auto 0;fill:none;stroke:var(--gold);stroke-width:1.6;stroke-linecap:round;stroke-dasharray:600;stroke-dashoffset:600;animation:draw 2s .5s ease forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
.brand{{display:flex;align-items:center;gap:12px;text-decoration:none}}.brand b{{font-family:var(--head);font-weight:500;font-size:1.7rem;letter-spacing:.24em}}
.brand small{{font-size:.62rem;letter-spacing:.24em;text-transform:uppercase;line-height:1.3;opacity:.85;border-left:1px solid currentColor;padding-left:12px}}
.hero h2 em{{color:#f2c88f}}.stat b{{font-family:var(--head)}}
.stage{{background:radial-gradient(1200px 600px at 50% 40%,#fbfaf4 0%,#e9efe2 60%,#d9e3d0 100%)}}
.labels{{overflow:hidden}}.labels span.x{{background:rgba(185,120,63,.92)}}.tip small{{color:var(--wood)}}
.grid{{grid-template-columns:repeat(3,1fr)}}.suite{{aspect-ratio:4/3}}.suite small{{color:#f2c88f}}
.plan{{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center;padding:0 0 110px}}.plan img{{width:100%;border-radius:18px;border:1px solid var(--line);background:#fff}}
.plan h3{{font-size:2rem;margin:10px 0}}.plan p{{color:var(--muted);margin-bottom:12px}}
.airbnb{{display:flex;align-items:center;gap:14px;margin-top:16px;padding:16px 18px;border-radius:18px;background:#fff;border:1px solid var(--line);font-size:.9rem}}
.airbnb b{{font-family:var(--head);font-size:1.5rem;color:#ff385c}}
@media (max-width:980px){{.grid{{grid-template-columns:1fr 1fr}}.plan{{grid-template-columns:1fr}}}}
@media (max-width:600px){{.grid{{grid-template-columns:1fr}}.brand b{{font-size:1.35rem}}.brand small{{display:none}}}}
</style>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
</head><body>
<div id="intro"><div class="mark"><b>{"".join(f'<span style="animation-delay:{150 + i * 160}ms">{c}</span>' for i, c in enumerate("ASH"))}</b>{LEAF}<p>COUPLES LODGE &middot; BILLINGSLEY PARK &middot; SHROPSHIRE</p></div></div>
<nav id="nav"><div class="wrap"><a class="brand" href="#"><b>ASH</b><small>Billingsley<br>Park Lodges</small></a>
<span class="links"><a href="#house">The Lodge</a><a href="#suites">Inside</a><a href="#book">Book direct</a><a href="#reviews">Reviews</a><a href="#visit">Find us</a></span>
<a class="btn" href="#book">Book direct</a></div></nav>
<header class="hero"><video autoplay muted loop playsinline preload="auto" poster="p/q17.jpg"><source src="walkthrough.mp4" type="video/mp4"></video><div class="wrap">
<p class="kicker" style="color:#f2c88f">Hot tub lodge for two &middot; South Shropshire</p>
<h2>Your own lodge,<br><em>your own hot tub.</em></h2>
<p class="lead">A light, spacious lodge on private parkland near Bridgnorth, with a king-size suite, a freestanding bath and an elevated deck with a private hot tub.</p>
<a class="btn" href="#house">Explore the lodge in 3D &darr;</a>&nbsp; <a class="btn ghost" href="#book">Book direct and save</a>
<div class="stat"><div><b>{place["rating"]:.1f}★</b>{place["reviews"]} Google reviews</div><div><b>4.88★</b>Airbnb Guest favourite</div><div><b>1</b>king suite</div><div><b>Private</b>hot tub</div></div>
</div></header>

<section id="house"><div class="wrap head"><div><p class="kicker reveal">The lodge, in 3D</p><h2 class="reveal">Lift the roof.<br>Look around.</h2></div>
<p class="reveal">This is the real layout of the lodge, all on one floor. Spin it, lift the roof, then tap any room to walk in and see every photo.</p></div>
<div class="stage"><canvas id="three"></canvas><div class="labels" id="labels"></div>
<div class="floors" id="floors"><button data-f="roof">Put the roof on</button><button data-f="all" class="on">Inside</button><button data-f="deck">Deck &amp; hot tub</button></div>
<div class="tip" id="tip"></div><div class="hint">Drag to spin &middot; scroll to zoom &middot; tap a room to enter<br><span class="concept">Laid out from the lodge plans approved by Shropshire Council for Billingsley Park Lodges (ref. 17/04800/FUL)</span></div></div>
</section>

<section id="suites"><div class="wrap"><p class="kicker reveal">Inside and out</p><h2 class="reveal" style="font-size:clamp(2.4rem,5vw,4rem);margin:12px 0 40px">Everything for two.</h2>
<div class="grid">{cards}</div></div></section>

<div class="wrap plan"><img class="reveal" src="plan.png" alt="The approved lodge floor plan"><div class="reveal"><p class="kicker">The plans</p><h3>Built on the real floor plan</h3>
<p>The 3D lodge above follows the lodge plans approved for Billingsley Park, so guests see exactly how the space flows before they arrive: in through the front, open-plan living to one end, the bedroom suite to the other, and the deck wrapping round.</p>
<p class="concept">Plan: Billingsley Park Lodges, Shropshire Council planning ref. 17/04800/FUL.</p></div></div>

<section id="book"><div class="wrap"><div class="bookbox">
<div class="card reveal"><p class="kicker">Book direct</p><h3>Same lodge. Better price.</h3>
<p>Booking sites add their fees on top. Book with us directly and you skip them, with the same lodge, the same welcome and a direct line to your hosts.</p>
<div class="save"><div><b>No</b>booking-site fees</div><div><b>Best</b>rate, guaranteed</div><div><b>Direct</b>chat with your hosts</div></div>
<a class="btn" href="{AIRBNB}">Check dates and book</a>
<div class="airbnb"><b>4.88</b><span>Guest favourite on Airbnb, from 85 reviews. Superhost for 7 years.</span></div></div>
<div class="card reveal" style="--d:120ms"><p class="kicker">Live availability</p><h3>Pick your dates</h3>
<div class="cal" id="cal"></div>
<p class="sync"><i></i>Calendar synced with Airbnb, so what you see here is what's free</p>
<p class="concept">Concept: on the live site this calendar reads the Airbnb calendar automatically, so you can never be double-booked.</p></div>
</div></div></section>

<section id="reviews"><div class="wrap"><div class="head" style="margin:0"><div><p class="kicker reveal">Guests say</p>
<p class="score reveal">{place["rating"]:.1f}<span style="font-size:.35em;color:var(--muted)"> / 5</span></p></div>
<p class="reveal">Rated {place["rating"]:.1f} out of 5 by {place["reviews"]} guests on Google, and 4.88 on Airbnb.</p></div>
<div class="rev">{reviews}</div></div></section>

<section id="visit"><div class="wrap visit"><div><p class="kicker reveal">Find us</p><h2 class="reveal">South Shropshire<br>countryside.</h2>
<p class="reveal" style="color:var(--muted);margin-top:16px">Billingsley Park Lodges, Billingsley, near Bridgnorth WV16 6PF. Private parking right outside the lodge.</p></div>
<div class="reveal"><a class="btn" href="{e(place.get('maps') or '#')}" target="_blank" rel="noopener">Directions</a>&nbsp; {f'<a class="btn ghost" href="tel:{e(tel)}">{e(place.get("phone", ""))}</a>' if tel else ''}</div></div></section>
<footer><div class="wrap">A free concept website for Ash Lodge at Billingsley Park Lodges, designed by Kinetic Web Designs using the photos and words from their own Airbnb listing and Google profile. Not the live site.</div></footer>

<div id="room"><div class="pics"><div class="big" id="big"></div><div class="thumbs" id="thumbs"></div></div>
<div class="info"><button class="close" id="close" aria-label="Close">&times;</button><p class="kicker" id="rfloor"></p><h3 id="rname"></h3><div id="rtext"></div>
<a class="btn" href="{AIRBNB}">Book Ash Lodge</a><div class="nextprev"><button class="btn ghost" id="prev">&larr; Previous</button><button class="btn ghost" id="next">Next &rarr;</button></div></div></div>

<script>window.STAY = {data};</script>
<script type="module">
import * as THREE from "three";
import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
import {{ RoomEnvironment }} from "three/addons/environments/RoomEnvironment.js";
import {{ RoundedBoxGeometry }} from "three/addons/geometries/RoundedBoxGeometry.js";
const Z = window.STAY.zones;
setTimeout(() => document.getElementById("intro").classList.add("out"), 3000);
const nav = document.getElementById("nav"); addEventListener("scroll", () => nav.classList.toggle("solid", scrollY > 60));
const io = new IntersectionObserver(es => es.forEach(x => {{ if (x.isIntersecting) {{ x.target.classList.add("in"); io.unobserve(x.target); }} }}), {{threshold: .12}});
document.querySelectorAll(".reveal").forEach(el => io.observe(el));
const cal = document.getElementById("cal"); const now = new Date(); const first = new Date(now.getFullYear(), now.getMonth(), 1);
cal.innerHTML = ["M","T","W","T","F","S","S"].map(d => `<span class="h">${{d}}</span>`).join("") + Array((first.getDay() + 6) % 7).fill('<span class="h"></span>').join("")
  + Array.from({{length: new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}}, (_, i) => {{ const d = i + 1;
    return `<span class="${{d < now.getDate() || [2,3,9,10,16,17,24,30,31].includes(d) ? "x" : ""}}">${{d}}</span>`; }}).join("");
cal.addEventListener("click", ev => {{ const s = ev.target; if (s.tagName === "SPAN" && !s.classList.contains("x") && !s.classList.contains("h")) s.classList.toggle("sel"); }});
// room overlay
const ov = document.getElementById("room"), big = document.getElementById("big"), thumbs = document.getElementById("thumbs"); let cur = 0;
function openRoom(i) {{
  cur = (i + Z.length) % Z.length; const r = Z[cur];
  document.getElementById("rfloor").textContent = r.kicker; document.getElementById("rname").textContent = r.name;
  document.getElementById("rtext").innerHTML = r.text.map(t => `<p>${{t}}</p>`).join("");
  const show = k => {{ big.style.backgroundImage = `url(${{r.gallery[k]}})`; thumbs.querySelectorAll("button").forEach((b, j) => b.classList.toggle("on", j === k)); }};
  thumbs.innerHTML = r.thumbs.map(g => `<button style="background-image:url(${{g}})"></button>`).join("");
  thumbs.querySelectorAll("button").forEach((b, j) => b.onclick = () => show(j));
  show(0); ov.classList.add("open"); document.body.style.overflow = "hidden";
}}
function closeRoom() {{ ov.classList.remove("open"); document.body.style.overflow = ""; flyHome(); }}
document.getElementById("close").onclick = closeRoom; document.getElementById("next").onclick = () => openRoom(cur + 1); document.getElementById("prev").onclick = () => openRoom(cur - 1);
addEventListener("keydown", ev => {{ if (ev.key === "Escape") closeRoom(); }});
document.querySelectorAll(".suite").forEach(b => b.onclick = () => openRoom(Z.findIndex(z => z.slug === b.dataset.slug)));

// ---- the 3D lodge, in metres, from the approved plan: 11.3m x 6.8m, deck along the long side and the living-room end
const canvas = document.getElementById("three"), stage = canvas.parentElement;
const renderer = new THREE.WebGLRenderer({{canvas, antialias: true, alpha: true}});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.shadowMap.enabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = .72; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0xdfe8d6, 40, 90);
const camera = new THREE.PerspectiveCamera(36, 1, .1, 200);
const controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.autoRotate = true; controls.autoRotateSpeed = .5;
controls.minDistance = 7; controls.maxDistance = 45; controls.maxPolarAngle = Math.PI * .46; controls.target.set(-.6, .4, -.8);
const HOME = new THREE.Vector3(11, 12.5, 15).multiplyScalar(innerWidth < 700 ? 1.9 : 1); camera.position.copy(HOME);
const pmrem = new THREE.PMREMGenerator(renderer); scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture;
scene.add(new THREE.HemisphereLight(0xfffbea, 0x3c5a3a, 1.15));
const sun = new THREE.DirectionalLight(0xffe9c4, 2.3); sun.position.set(10, 18, 8); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, {{left: -16, right: 16, top: 16, bottom: -16}}); scene.add(sun);
const M = (c, o = {{}}) => new THREE.MeshStandardMaterial({{color: c, roughness: .8, ...o}});
const grass = new THREE.Mesh(new THREE.CircleGeometry(30, 64), M(0x8fb06b, {{roughness: 1}})); grass.rotation.x = -Math.PI / 2; grass.position.y = -.6; grass.receiveShadow = true; scene.add(grass);
const box = (w, h, d, mat, x, y, z) => {{ const o = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(.035, Math.min(w, h, d) * .3)), mat); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; scene.add(o); return o; }};
const L = 11.3, W = 6.8, H = 1.25, pick = [], labelEls = [];
box(L + .3, .5, W + .3, M(0x6b5a48), 0, -.33, 0);                                  // the lodge's base
const deckMat = M(0xb98a5a, {{roughness: .9}});
box(L + 2.2, .14, 2.6, deckMat, -1.1, -.05, -W / 2 - 1.3);                         // long deck
box(2.2, .14, W, deckMat, -L / 2 - 1.1, -.05, 0);                                  // deck at the living-room end
for (let i = 0; i < 26; i++) box(.06, .7, .06, M(0x8a6a48), -L / 2 - 2.1 + i * .55, .3, -W / 2 - 2.55); // railing posts
box(L + 2.2, .06, .08, M(0x8a6a48), -1.1, .66, -W / 2 - 2.55);
box(.08, .06, W + 2.6, M(0x8a6a48), -L / 2 - 2.15, .66, -1.3);
box(1.2, .25, 2.2, M(0x9a7a58), -.3, -.3, W / 2 + 1.1);                            // access ramp to the front door
const tub = box(2.1, .75, 2.1, M(0x3b3f45, {{roughness: .5}}), 3.4, .32, -W / 2 - 1.25);
const water = new THREE.Mesh(new THREE.BoxGeometry(1.8, .05, 1.8), M(0x55c7e6, {{roughness: .1, emissive: 0x2aa6d6, emissiveIntensity: .35}})); water.position.set(3.4, .71, -W / 2 - 1.25); scene.add(water);
// rooms: floored with their own photo, glass walls with oak trims
const loader = new THREE.TextureLoader();

// ---- a real 3D floor plan: solid walls, floors and furniture modelled in every room
const mat = (c, o = {{}}) => new THREE.MeshStandardMaterial({{color: c, roughness: .75, ...o}});
function planks(c1, c2, tile) {{
  const cv = document.createElement("canvas"); cv.width = cv.height = 256; const x = cv.getContext("2d");
  x.fillStyle = c1; x.fillRect(0, 0, 256, 256); x.strokeStyle = c2; x.lineWidth = 2;
  if (tile) for (let i = 0; i <= 256; i += 64) {{ x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 256); x.moveTo(0, i); x.lineTo(256, i); x.stroke(); }}
  else for (let i = 0; i < 256; i += 32) {{ x.beginPath(); x.moveTo(0, i); x.lineTo(256, i); x.stroke();
    for (let j = (i / 32 % 2) * 64; j < 256; j += 128) {{ x.beginPath(); x.moveTo(j, i); x.lineTo(j, i + 32); x.stroke(); }} }}
  const tx = new THREE.CanvasTexture(cv); tx.wrapS = tx.wrapT = THREE.RepeatWrapping; tx.colorSpace = THREE.SRGBColorSpace; return tx;
}}
const ARTS = {{}}; const art = src => {{ if (!ARTS[src]) {{ const tx = new THREE.TextureLoader().load(src); tx.colorSpace = THREE.SRGBColorSpace; ARTS[src] = tx; }} return ARTS[src]; }};
const FLOORTEX = {{oak: planks("#cfa97f", "#b48d64"), tile: planks("#e6e3de", "#cdc8c0", 1), deck: planks("#ad855c", "#8e6b47")}};
function floorMat(kind, w, d) {{
  const tx = FLOORTEX[kind === "bath" ? "tile" : kind === "pool" || kind === "outdoor" ? "deck" : "oak"].clone();
  tx.needsUpdate = true; tx.repeat.set(w / 1.6, d / 1.6); return new THREE.MeshStandardMaterial({{map: tx, roughness: .8}});
}}
function kindOf(r) {{
  const n = r.name.toLowerCase(), t = n + " " + (r.summary || "").toLowerCase();
  if (/pool/.test(n) && !/suite|room|studio/.test(n)) return "pool";
  if (/garden|park|terrace|deck|grounds|view/.test(n) && !/suite|room|studio/.test(n)) return "outdoor";
  if (/en-suite|bathroom/.test(n)) return "bath";
  if (/dining|kitchen/.test(n) && !/lounge|living/.test(n)) return "dining";
  if (/lounge|kitchen|dining|breakfast|living|reception/.test(n)) return "living";
  if (/villa|apartment|cottage/.test(n)) return "apartment";
  if (/family|twin/.test(t)) return "twin";
  return "suite";
}}
function walls(g, x, z, W, D, s, trim, open) {{   // white walls with a door to the corridor and a window to the outside
  if (open) {{ box(W, .08, .08, trim, x, .04, z - s * D / 2, g); return; }}
  const Hh = 1.3, T = .12, wm = mat(0xf6f3ee, {{roughness: .9}});
  const seg = (a, b, pz) => {{ if (b - a > .05) {{ box(b - a, Hh, T, wm, (a + b) / 2, Hh / 2, pz, g); box(b - a + .01, .05, T + .02, trim, (a + b) / 2, Hh, pz, g); }} }};
  for (const px of [x - W / 2, x + W / 2]) {{ box(T, Hh, D, wm, px, Hh / 2, z, g); box(T + .02, .05, D + .01, trim, px, Hh, z, g); }}
  const L = x - W / 2, R = x + W / 2, cz = z - s * D / 2, oz = z + s * D / 2, door = x + W / 2 - 1.0, win = x + W * .15, ww = W * .35;
  seg(L, door - .48, cz); seg(door + .48, R, cz);
  seg(L, win - ww / 2, oz); seg(win + ww / 2, R, oz);
  box(ww, .45, T, wm, win, .225, oz, g); box(ww, .6, .04, mat(0xcfe8f2, {{transparent: true, opacity: .45, roughness: .05}}), win, .75, oz, g);
}}
function furnish(kind, g, x, z, W, D, s, accent, img) {{
  const P = (lx, lz) => [x + lx, z + s * lz];   // lz grows towards the outside wall
  const put = (w, h, d, m, lx, y, lz) => {{ const [px, pz] = P(lx, lz); return box(w, h, d, m, px, y, pz, g); }};
  const wood = mat(0x8a6a4a), white = mat(0xf8f6f2), linen = mat(0xece6dc), fab = mat(accent.getHex(), {{roughness: .95}}),
        dark = mat(0x34302c), water = mat(0x5ec8e0, {{roughness: .1, emissive: 0x2aa6d6, emissiveIntensity: .3}}), green = mat(0x58864f, {{roughness: 1}});
  const rug = (lx, lz, w, d, c = 0xdcd0bb) => {{ const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c, {{roughness: 1}}));
    m.rotation.x = -Math.PI / 2; const [px, pz] = P(lx, lz); m.position.set(px, .03, pz); m.receiveShadow = true; g.add(m); }};
  const bed = (lx, wide) => {{ const bw = wide ? 1.8 : .95, lz = D / 2 - 1.2;
    put(bw + .1, .32, 2.1, wood, lx, .16, lz); put(bw, .16, 2.0, white, lx, .4, lz); put(bw + .02, .07, 1.25, fab, lx, .51, lz - .35);
    put(bw + .2, .9, .08, dark, lx, .45, lz + 1.06);
    if (img && wide) {{ put(1.0, .7, .04, dark, lx, 1.12, lz + 1.12); const ph = new THREE.Mesh(new THREE.PlaneGeometry(.9, .6), new THREE.MeshStandardMaterial({{map: art(img), roughness: .6}}));
      const [px, pz] = P(lx, lz + 1.09); ph.position.set(px, 1.12, pz); ph.rotation.y = s > 0 ? Math.PI : 0; g.add(ph); }}
    for (const o of wide ? [-.45, .45] : [0]) put(.6, .12, .32, linen, lx + o, .54, lz + .78);
    for (const o of [-(bw / 2 + .32), bw / 2 + .32]) {{ put(.42, .45, .4, wood, lx + o, .225, lz + .8); put(.14, .3, .14, mat(0xfff1d6, {{emissive: 0xffc77a, emissiveIntensity: .9}}), lx + o, .6, lz + .8); }}
  }};
  const sofa = (lx, lz, w = 2) => {{ put(w, .4, .85, fab, lx, .2, lz); put(w, .45, .2, fab, lx, .52, lz + .33);
    put(.18, .55, .85, fab, lx - w / 2, .28, lz); put(.18, .55, .85, fab, lx + w / 2, .28, lz); }};
  const table = (lx, lz) => {{ put(1.2, .06, .8, wood, lx, .74, lz); put(.1, .72, .1, wood, lx, .36, lz);
    for (const [a, b] of [[-.4, .55], [.4, .55], [-.4, -.55], [.4, -.55]]) {{ put(.42, .45, .42, white, lx + a, .225, lz + b); put(.42, .4, .06, white, lx + a, .65, lz + b + Math.sign(b) * .18); }} }};
  const tv = (lx) => {{ put(1.3, .5, .4, wood, lx, .25, -D / 2 + .3); put(1.1, .62, .05, dark, lx, .95, -D / 2 + .2); }};
  const plant = (lx, lz) => {{ put(.3, .35, .3, dark, lx, .17, lz); const m = new THREE.Mesh(new THREE.SphereGeometry(.3, 12, 10), green); const [px, pz] = P(lx, lz); m.position.set(px, .62, pz); m.castShadow = true; g.add(m); }};
  const ensuite = (lx, lz) => {{   // a bathroom in the corridor-side corner: partition, bath, basin, toilet
    put(.1, 1.0, 1.8, white, lx + .9, .5, lz); put(1.8, 1.0, .1, white, lx, .5, lz + .9);
    put(1.5, .5, .7, white, lx, .25, lz - .45); put(1.3, .05, .52, water, lx, .48, lz - .45);
    put(.5, .8, .4, white, lx - .55, .4, lz + .55); put(.36, .38, .5, white, lx + .45, .19, lz + .5);
  }};
  if (kind === "suite" || kind === "twin" || kind === "apartment" || kind === "bedroom") {{
    if (kind === "twin") {{ bed(-W / 2 + 1.0, 0); bed(-W / 2 + 2.4, 0); }} else bed(-W / 2 + 1.35, 1);
    rug(-W / 2 + 1.5, D / 2 - 2.3, 2.4, 1.2);
    if (kind !== "bedroom") ensuite(-W / 2 + 1.0, -D / 2 + 1.0);
    tv(.25);
    if (kind === "apartment") sofa(W / 2 - 1.25, D / 2 - .6, 1.7); else {{ put(.75, .45, .75, fab, W / 2 - .9, .22, D / 2 - .8); put(.75, .4, .15, fab, W / 2 - .9, .6, D / 2 - .5); }}
    plant(W / 2 - .35, -D / 2 + .35 + 1.1);
  }} else if (kind === "living") {{
    sofa(-W / 4, D / 2 - .65, 2.2); put(1.0, .38, .6, wood, -W / 4, .19, D / 2 - 1.65); rug(-W / 4, D / 2 - 1.45, 2.6, 1.8);
    tv(-W / 4); table(W / 4, -.1);
    put(2.4, .9, .6, white, W / 2 - 1.4, .45, D / 2 - .35); put(2.42, .04, .62, dark, W / 2 - 1.4, .92, D / 2 - .35);
    plant(-W / 2 + .4, -D / 2 + .4);
  }} else if (kind === "dining") {{
    table(-W / 4, 0); put(2.6, .9, .6, white, W / 4, .45, D / 2 - .35); put(2.62, .04, .62, dark, W / 4, .92, D / 2 - .35);
    put(1.6, .9, .8, white, W / 4, .45, -.2); put(1.62, .04, .82, dark, W / 4, .92, -.2); plant(-W / 2 + .4, -D / 2 + .4);
  }} else if (kind === "bath") {{
    put(1.7, .55, .8, white, -W / 4, .27, D / 2 - .55); put(1.5, .05, .6, water, -W / 4, .52, D / 2 - .55);
    put(1.6, 2.0, .05, mat(0xd9eef5, {{transparent: true, opacity: .35, roughness: .05}}), W / 4, 1, D / 2 - 1.35); put(1.6, .04, 1.2, mat(0xcfcac2), W / 4, .03, D / 2 - .75);
    put(1.2, .8, .5, white, -.3, .4, -D / 2 + .35); put(.4, .4, .55, white, W / 2 - .5, .2, -D / 2 + .5); plant(-W / 2 + .4, -D / 2 + .4);
  }} else {{
    if (kind === "pool") put(W * .55, .08, D * .5, water, -W * .12, .04, -.1);
    else for (const [a, b] of [[-W / 3, D / 4], [W / 5, -D / 4]]) {{ put(.14, .9, .14, wood, a, .45, b); const m = new THREE.Mesh(new THREE.SphereGeometry(.6, 14, 10), green); const [px, pz] = P(a, b); m.position.set(px, 1.2, pz); m.castShadow = true; g.add(m); }}
    for (const o of [-.75, .75]) {{ put(.62, .18, 1.6, white, W / 2 - 1.3 + o, .2, D / 2 - 1.1); put(.62, .4, .1, white, W / 2 - 1.3 + o, .38, D / 2 - .35); }}
    put(.05, 1.8, .05, wood, W / 2 - 1.3, .9, D / 2 - 1.1); const u = new THREE.Mesh(new THREE.ConeGeometry(1.0, .4, 16), linen); const [ux, uz] = P(W / 2 - 1.3, D / 2 - 1.1); u.position.set(ux, 1.9, uz); u.castShadow = true; g.add(u);
  }}
}}
function room(i, x0, x1, z0, z1, s, kind, label = true) {{
  const w = x1 - x0, d = z1 - z0, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2, r = Z[i];
  const fl = new THREE.Mesh(new THREE.PlaneGeometry(w - .08, d - .08), floorMat(kind, w, d));
  fl.rotation.x = -Math.PI / 2; fl.position.set(cx, .01, cz); fl.receiveShadow = true; scene.add(fl);
  const trim = M(0x3a342e, {{emissive: 0xe0a060, emissiveIntensity: 0}});
  walls(scene, cx, cz, w, d, s, trim, false);
  furnish(kind, scene, cx, cz, w, d, s, new THREE.Color("#7f9b8a"), r.gallery[0]);
  const hit = new THREE.Mesh(new THREE.BoxGeometry(w, H, d), new THREE.MeshBasicMaterial({{visible: false}})); hit.position.set(cx, H / 2, cz);
  hit.userData = {{idx: i, trim}}; scene.add(hit); pick.push(hit);
  if (label) tag(r.name, hit, false);
  return hit;
}}
function tag(text, obj, x) {{ const s = document.createElement("span"); if (x) s.className = "x"; s.textContent = text; document.getElementById("labels").appendChild(s); labelEls.push({{el: s, obj}}); }}
function marker(text, x, y, z) {{ const o = new THREE.Object3D(); o.position.set(x, y, z); scene.add(o); tag(text, o, true); }}
room(0, -L / 2, -1.6, -W / 2, 0, -1, "living");        // living: the end with French doors to the deck
room(1, -L / 2, -1.6, 0, W / 2, 1, "dining");         // dining & kitchen
room(2, 1.0, L / 2, -W / 2, .3, -1, "bedroom");         // bedroom, patio doors to the deck and hot tub
room(3, 1.0, L / 2, .3, W / 2, 1, "bath");          // en-suite
const hall = new THREE.Mesh(new THREE.PlaneGeometry(2.6, W), M(0xd8b98e)); hall.rotation.x = -Math.PI / 2; hall.position.set(-.3, .01, 0); scene.add(hall);
// deck + park as clickable areas
const deckHit = new THREE.Mesh(new THREE.BoxGeometry(L + 2.2, .8, 2.6), new THREE.MeshBasicMaterial({{visible: false}})); deckHit.position.set(-1.1, .3, -W / 2 - 1.3);
const deckTrim = M(0x000000); deckHit.userData = {{idx: 4, trim: deckTrim, glow: water}}; scene.add(deckHit); pick.push(deckHit); tag("Deck & hot tub", tub, false);
marker("Front door", -.3, 1.6, W / 2 + .6); marker("French doors", -L / 2 - .2, 1.6, -1.6);
// trees around the lodge
const trunk = M(0x6d4c33), leaf = M(0x5d8a4a, {{roughness: 1}});
[[-12, -9], [-9, -12], [9, -11], [13, -6], [14, 5], [-14, 6], [-6, 12], [7, 13], [16, -1], [-16, -3]].forEach(([x, z], k) => {{
  box(.3, 2, .3, trunk, x, .4, z); const c = new THREE.Mesh(new THREE.SphereGeometry(1.4 + (k % 3) * .4, 16, 12), leaf); c.position.set(x, 2.4 + (k % 2) * .4, z); c.castShadow = true; scene.add(c); }});
const parkHit = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 3, 16), new THREE.MeshBasicMaterial({{visible: false}})); parkHit.position.set(9, 1, -11);
parkHit.userData = {{idx: 5, trim: M(0)}}; scene.add(parkHit); pick.push(parkHit); tag("The park", parkHit, false);
// the roof: a low pitched roof that lifts off to show inside
const roof = new THREE.Group(), roofMat = M(0x4a4440, {{roughness: .7, transparent: true, opacity: 1}});
[-1, 1].forEach(s => {{ const p = new THREE.Mesh(new THREE.BoxGeometry(L + .6, .1, W / 2 + .5), roofMat); p.position.set(0, .45, s * (W / 4 + .1)); p.rotation.x = s * .17; p.castShadow = true; roof.add(p); }});
const wallMat = M(0xc49565, {{transparent: true, opacity: 1}});
[[0, -W / 2, L, .12], [0, W / 2, L, .12], [-L / 2, 0, .12, W], [L / 2, 0, .12, W]].forEach(([x, z, w, d]) => {{ const m = new THREE.Mesh(new THREE.BoxGeometry(w, 1.6, d), wallMat); m.position.set(x, -.8, z); roof.add(m); }});
roof.position.y = 1.6; scene.add(roof);
let roofOn = false, roofT = 0;
for (let i = 0; i < 8; i++) {{ const l = new THREE.PointLight(0xffd59a, .8, 6); l.position.set(-4.5 + i * 1.3, 1, (i % 2 ? 1 : -1) * 1.6); scene.add(l); }}
document.getElementById("floors").onclick = ev => {{ const b = ev.target.closest("button"); if (!b) return;
  document.querySelectorAll("#floors button").forEach(x => x.classList.toggle("on", x === b)); controls.autoRotate = false;
  if (b.dataset.f === "roof") {{ roofOn = true; fly = {{t: 0, from: camera.position.clone(), to: HOME.clone(), tf: controls.target.clone(), tt: new THREE.Vector3(-.6, .4, -.8), done: () => controls.autoRotate = true}}; }}
  else if (b.dataset.f === "deck") {{ roofOn = false; fly = {{t: 0, from: camera.position.clone(), to: new THREE.Vector3(9, 7, -15), tf: controls.target.clone(), tt: new THREE.Vector3(2, .3, -W / 2 - 1.2), done: () => {{}}}}; }}
  else {{ roofOn = false; flyHome(); }} }};
const ray = new THREE.Raycaster(), m = new THREE.Vector2(-9, -9), tip = document.getElementById("tip"); let hover = null, downAt = 0, fly = null;
canvas.addEventListener("pointermove", ev => {{ const b = canvas.getBoundingClientRect(); m.set((ev.clientX - b.left) / b.width * 2 - 1, -(ev.clientY - b.top) / b.height * 2 + 1);
  tip.style.left = (ev.clientX - b.left) + "px"; tip.style.top = (ev.clientY - b.top) + "px"; }});
canvas.addEventListener("pointerdown", () => downAt = performance.now());
canvas.addEventListener("pointerup", () => {{ if (hover && performance.now() - downAt < 250) flyInto(hover); }});
function flyInto(hit) {{ const p = new THREE.Vector3(); hit.getWorldPosition(p); controls.autoRotate = false; roofOn = false;
  fly = {{t: 0, from: camera.position.clone(), to: p.clone().add(new THREE.Vector3(1.6, 3.6, 3.4)), tf: controls.target.clone(), tt: p.clone(), done: () => openRoom(hit.userData.idx)}}; }}
function flyHome() {{ fly = {{t: 0, from: camera.position.clone(), to: HOME.clone(), tf: controls.target.clone(), tt: new THREE.Vector3(-.6, .4, -.8), done: () => controls.autoRotate = true}}; }}
// a cinematic fly-in the first time the house scrolls into view
const introIO = new IntersectionObserver(es => {{ if (!es[0].isIntersecting) return; introIO.disconnect(); growT = 0;
  const from = HOME.clone().multiplyScalar(1.8); from.y = HOME.y * 2.3; camera.position.copy(from); controls.autoRotate = false;
  fly = {{t: 0, from, to: HOME.clone(), tf: controls.target.clone(), tt: controls.target.clone(), done: () => controls.autoRotate = true}}; }}, {{threshold: .3}});
// the house builds itself out of the floor plan the first time it is seen
const grow = [];
function collectGrow(root) {{ root.traverse(o => {{ if (!o.isMesh || !o.geometry || !o.geometry.parameters) return;
  const h = o.geometry.parameters.height; if (!(h > .05) || o.geometry.type === "PlaneGeometry") return;
  grow.push({{o, y: o.position.y, d: Math.max(0, o.position.y) * .25 + Math.random() * .15}}); o.scale.y = .001; o.position.y = o.position.y * .001; }}); }}
let growT = -1;
function growTick(dt) {{ if (growT < 0 || growT > 2.2) return; growT += dt;
  for (const g of grow) {{ const k = Math.min(1, Math.max(.001, (growT - g.d) / .9)), e = 1 - Math.pow(1 - k, 3); g.o.scale.y = e; g.o.position.y = g.y * e; }} }}
collectGrow(scene);
introIO.observe(stage);
function resize() {{ const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }}
addEventListener("resize", resize); resize();
const clock = new THREE.Clock(), v = new THREE.Vector3();
renderer.setAnimationLoop(() => {{
  const dt = Math.min(.05, clock.getDelta());
  growTick(dt);
  roofT += ((roofOn ? 1 : 0) - roofT) * Math.min(1, dt * 3);
  roof.position.y = 1.6 + (1 - roofT) * 7; roofMat.opacity = wallMat.opacity = roofT;
  roof.visible = roofT > .02; water.material.emissiveIntensity = .35 + Math.sin(performance.now() / 500) * .1;
  if (fly) {{ fly.t = Math.min(1, fly.t + dt / 1.1); const k = fly.t < .5 ? 4 * fly.t ** 3 : 1 - (-2 * fly.t + 2) ** 3 / 2;
    camera.position.lerpVectors(fly.from, fly.to, k); controls.target.lerpVectors(fly.tf, fly.tt, k); if (fly.t === 1) {{ const d = fly.done; fly = null; d(); }} }}
  ray.setFromCamera(m, camera);
  const hits = roofT > .5 ? [] : ray.intersectObjects(pick); const h = hits.length ? hits[0].object : null;
  if (h !== hover) {{ if (hover) hover.userData.trim.emissiveIntensity = 0; hover = h;
    if (h) {{ h.userData.trim.emissiveIntensity = 1.2; const r = Z[h.userData.idx]; tip.innerHTML = `<small>${{r.kicker}}</small><b>${{r.name}}</b>Tap to step inside`; tip.style.opacity = 1; }}
    else tip.style.opacity = 0; canvas.style.cursor = h ? "pointer" : "grab"; }}
  const b = canvas.getBoundingClientRect();
  labelEls.forEach(l => {{ l.obj.getWorldPosition(v); v.y += .9; v.project(camera);
    l.el.style.left = ((v.x + 1) / 2 * b.width) + "px"; l.el.style.top = ((1 - v.y) / 2 * b.height) + "px"; l.el.style.opacity = v.z < 1 && roofT < .5 ? .9 : 0; }});
  controls.update(); renderer.render(scene, camera);
}});
</script>
</body></html>
"""
STORY_CSS = '.story{position:relative;height:520vh;background:#0d0d0d}.story .pin{position:sticky;top:0;height:100svh;overflow:hidden}.story .st{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.04);transition:opacity .25s linear}.story .cap{position:absolute;left:0;right:0;top:12vh;text-align:center;z-index:3;padding:0 24px;pointer-events:none}.story .cap h2{font-family:var(--head);font-weight:500;font-size:clamp(2rem,5vw,4.2rem);line-height:1.05;color:#1d1d1b;text-shadow:0 1px 30px rgba(255,255,255,.6);transition:opacity .4s,transform .4s}.story .cap p{font-size:.8rem;letter-spacing:.32em;text-transform:uppercase;color:#6b6760;margin-bottom:10px}.story.dark .cap h2{color:#fff;text-shadow:0 2px 30px rgba(0,0,0,.6)}.story.dark .cap p{color:#e7e2d8}.story .dots{position:absolute;right:22px;top:50%;transform:translateY(-50%);display:grid;gap:10px;z-index:3}.story .dots i{width:7px;height:7px;border-radius:50%;background:rgba(120,120,120,.45);transition:background .3s,transform .3s}.story .dots i.on{background:var(--gold);transform:scale(1.5)}'
STORY_JS = '<script>\n(() => { const s = document.querySelector(".story"); if (!s) return;\n  const st = [...s.querySelectorAll(".st")], dots = [...s.querySelectorAll(".dots i")], h = s.querySelector(".cap h2"), k = s.querySelector(".cap p"), lines = JSON.parse(s.dataset.lines);\n  let cur = -1;\n  function draw() { const r = s.getBoundingClientRect(), p = Math.min(.9999, Math.max(0, -r.top / (r.height - innerHeight))), f = p * st.length, i = Math.floor(f), t = f - i;\n    st.forEach((el, n) => { el.style.opacity = n < i ? 0 : n === i ? 1 : n === i + 1 ? Math.max(0, (t - .55) / .45) : 0; el.style.transform = `scale(${1.06 - .06 * (n === i ? t : 0)})`; });\n    if (i !== cur) { cur = i; h.style.opacity = 0; setTimeout(() => { h.textContent = lines[i] || ""; k.textContent = `${i + 1} / ${st.length}`; h.style.opacity = 1; }, 180);\n      dots.forEach((d, n) => d.classList.toggle("on", n === i)); s.classList.toggle("dark", i >= st.length - 2); } }\n  addEventListener("scroll", draw, {passive: true}); addEventListener("resize", draw); draw(); })();\n</script>'
if (OUT / "build" / "1.jpg").exists():   # the "from a line to a home" scroll story (build_patch.py)
    bj = json.load(open(OUT / "build.json", encoding="utf-8")) if (OUT / "build.json").exists() else {}
    stages = [f"build/{i}.jpg" for i in range(1, 4) if (OUT / "build" / f"{i}.jpg").exists()] + ["MOSAIC"] + [bj.get("final", "p/q17.jpg")]
    lines = bj.get("lines") or ["It starts with a line.", "Then it takes shape.", "Material, texture, detail.", "Every room, exactly as it is.", "Welcome to Ash Lodge."]
    lines = [("Every room, exactly as it is." if x == "Lit from within." else x) for x in lines]
    MOSAIC = '<div class="st mosaic">' + "".join(f'<span style="background-image:url({c})"></span>' for c in [z["thumbs"][0] for z in ZONES][:6]) + "</div>"
    story = (f'<section class="story" data-lines="{e(json.dumps(lines[:len(stages)]))}"><div class="pin">'
             + "".join(MOSAIC if s == "MOSAIC" else f'<div class="st" style="background-image:url({s})"></div>' for s in stages)
             + '<div class="cap"><p></p><h2></h2></div><div class="dots">' + "<i></i>" * len(stages) + "</div></div></section>")
    html = html.replace("</style>", STORY_CSS + '.story .mosaic{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:1fr;gap:8px;padding:24vh 5vw 7vh;background:#111}.story .mosaic span{background-size:cover;background-position:center;border-radius:12px}@media (max-width:700px){.story .mosaic{grid-template-columns:repeat(2,1fr);padding:22vh 12px 6vh}}' + "</style>", 1).replace('<section id="house">', story + "\n" + '<section id="house">', 1).replace("</body>", STORY_JS + "</body>", 1)
sys.path.insert(0, str(Path(__file__).parent))
from door import add_door  # the "one line, an entire home" opening
html = add_door(html, OUT, [(z["slug"], z["thumbs"][0]) for z in ZONES])
from journey import add_journey  # the scroll-driven walkthrough journey
html = add_journey(html, OUT)
from neighbourhood import add_hood  # Google satellite + Street View of their street
html = add_hood(html, OUT)
(OUT / "index.html").write_text(html, encoding="utf-8")
print("written", len(html) // 1024, "KB")
