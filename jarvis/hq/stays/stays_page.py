"""The 'stays' concept site for a short-let host: cinematic hero, a 3D house you can spin with every suite clickable,
the suites, book direct (synced with Airbnb), real reviews and location. Built from their own photos and words."""
import json, sys
from html import escape as e
from pathlib import Path
from PIL import Image

sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
from hq.designer import vivid_colour, _hex  # noqa: E402

OUT = Path(sys.argv[1])
rooms = json.load(open(OUT / "rooms.json", encoding="utf-8"))
place = json.load(open(OUT / "place.json", encoding="utf-8"))
hero = json.load(open(OUT / "hero.json"))
FLOORS = ["Ground floor", "First floor", "Second floor"]

for r in rooms:
    try:
        c = vivid_colour(OUT / r["cover"])
        r["accent"] = _hex(c) if c else "#c9a77a"
    except Exception:
        r["accent"] = "#c9a77a"
    r["gallery"] = [r["cover"]] + [p for p in r["photos"] if not p.endswith("cover.jpg")]
    r["floor_name"] = FLOORS[r["floor"]]
json.dump(rooms, open(OUT / "rooms.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

name = place["name"]
quotes = [q for q in place["quotes"] if q["text"]][:4]
data = json.dumps({"rooms": [{k: r[k] for k in ("slug", "name", "summary", "story", "floor", "floor_name", "gallery", "cover", "accent")}
                             for r in rooms]}, ensure_ascii=False)
slides = "".join(f'<div class="slide" style="background-image:url({e(h)});animation-delay:{i * 6}s"></div>' for i, h in enumerate(hero[:5]))
cards = "".join(
    f'<button class="suite reveal" data-slug="{e(r["slug"])}" style="--a:{r["accent"]};--d:{(i % 4) * 80}ms">'
    f'<span class="img" style="background-image:url({e(r["cover"])})"></span><span class="meta"><small>{e(r["floor_name"])}</small>'
    f'<b>{e(r["name"])}</b><em>{e(r["summary"][:110])}{"…" if len(r["summary"]) > 110 else ""}</em></span></button>'
    for i, r in enumerate(rooms))
reviews = "".join(f'<blockquote class="reveal" style="--d:{i * 90}ms"><span>{"★" * int(q.get("rating") or 5)}</span>'
                  f'<p>&ldquo;{e(q["text"][:300])}{"…" if len(q["text"]) > 300 else ""}&rdquo;</p><cite>{e(q["author"])}</cite></blockquote>'
                  for i, q in enumerate(quotes))
tel = "".join(ch for ch in place.get("phone", "") if ch.isdigit() or ch == "+")

html = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>{e(name)} | concept website</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,500&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fbf8f2;--ink:#2b2a28;--muted:#6f6a62;--gold:#b8860b;--gold2:#d9a521;--panel:#ffffff;--line:rgba(43,42,40,.12);
--head:'Cinzel',Georgia,serif;--body:'DM Sans',system-ui,sans-serif}}
*{{box-sizing:border-box;margin:0}}html{{scroll-behavior:smooth}}body{{background:var(--bg);color:var(--ink);font:16px/1.65 var(--body);overflow-x:hidden}}
a{{color:inherit}}.wrap{{max-width:1240px;margin:0 auto;padding:0 24px}}
button{{font:inherit;color:inherit;background:none;border:0;cursor:pointer}}
.btn{{display:inline-flex;align-items:center;gap:10px;padding:15px 28px;border-radius:999px;background:linear-gradient(120deg,var(--gold2),var(--gold));
color:#fff;font-weight:600;text-decoration:none;letter-spacing:.02em;box-shadow:0 18px 40px -18px var(--gold);transition:transform .3s}}
.btn:hover{{transform:translateY(-2px)}}.btn.ghost{{background:transparent;color:inherit;border:1px solid currentColor;box-shadow:none}}
.kicker{{text-transform:uppercase;letter-spacing:.3em;font-size:.72rem;color:var(--gold);font-weight:600}}
h1,h2,h3{{font-family:var(--head);font-weight:500;letter-spacing:.02em}}em{{font-family:'Cormorant Garamond',serif;font-style:italic;letter-spacing:0}}
/* intro */
#intro{{position:fixed;inset:0;z-index:50;background:#fff;display:grid;place-items:center;transition:opacity 1s .2s,visibility 1s .2s}}
#intro.out{{opacity:0;visibility:hidden}}#intro h1{{font-size:clamp(2.4rem,7vw,5rem);letter-spacing:.06em}}
#intro img{{width:min(300px,62vw);display:block;margin:0 auto;opacity:0;transform:scale(.92);filter:blur(6px);animation:logo 1.6s cubic-bezier(.2,.8,.2,1) .15s forwards}}@keyframes logo{{to{{opacity:1;transform:none;filter:none}}}}#intro .shine{{position:relative;overflow:hidden}}#intro .shine::after{{content:"";position:absolute;inset:0;background:linear-gradient(105deg,transparent 40%,rgba(255,255,255,.85) 50%,transparent 60%);transform:translateX(-120%);animation:sweep 1.4s 1.3s ease-in-out forwards}}@keyframes sweep{{to{{transform:translateX(120%)}}}}
#intro p{{text-align:center;color:var(--gold);letter-spacing:.4em;font-size:.72rem;margin-top:10px;opacity:0;animation:up 1s 1.1s forwards}}
@keyframes up{{to{{opacity:1;transform:none}}}}
/* nav */
nav{{position:fixed;top:0;left:0;right:0;z-index:20;transition:background .4s,backdrop-filter .4s}}
nav{{color:#fff}}nav.solid{{background:rgba(255,255,255,.94);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);color:var(--ink)}}.brand img{{height:52px;display:block;filter:brightness(0) invert(1);transition:filter .4s}}nav.solid .brand img{{filter:none}}
nav .wrap{{display:flex;align-items:center;justify-content:space-between;height:76px}}
.brand{{font-family:var(--head);font-size:1.5rem;letter-spacing:.04em}}.brand i{{color:var(--gold);font-style:normal}}
.links{{display:flex;gap:28px;font-size:.9rem}}.links a{{text-decoration:none;opacity:.8}}.links a:hover{{opacity:1;color:var(--gold2)}}
nav .btn{{padding:11px 20px;font-size:.88rem}}
/* hero */
.hero{{position:relative;height:100svh;min-height:640px;overflow:hidden;display:grid;align-items:end}}
.hero video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}.hero{{color:#fff}}
@keyframes show{{0%{{opacity:0;transform:scale(1.12)}}4%{{opacity:1}}20%{{opacity:1}}25%{{opacity:0;transform:scale(1)}}100%{{opacity:0}}}}
.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(12,10,8,.82),rgba(12,10,8,.35) 55%,rgba(12,10,8,.1)),linear-gradient(180deg,rgba(15,13,11,.45),transparent 30%,rgba(15,13,11,.94))}}
.hero .wrap{{position:relative;z-index:2;padding-bottom:9vh;width:100%}}
.hero h2{{font-size:clamp(2.6rem,7vw,6rem);line-height:.98;max-width:13ch;margin:18px 0 22px}}.hero h2 em{{color:#f3c64f}}
.hero p.lead{{max-width:46ch;color:#f1ece4;font-size:1.12rem;margin-bottom:30px}}
.stat{{display:flex;gap:34px;flex-wrap:wrap;margin-top:42px;color:#e8e1d6;font-size:.9rem}}.stat b{{display:block;font-family:var(--head);font-size:2rem;color:#fff;font-weight:500}}
/* house */
#house{{position:relative;padding:110px 0 0}}
.head{{display:grid;grid-template-columns:1.1fr .9fr;gap:40px;align-items:end;margin-bottom:34px}}
.head h2{{font-size:clamp(2rem,4.2vw,3.4rem);line-height:1.05}}.head p{{color:var(--muted)}}
.stage{{position:relative;height:min(82vh,820px);border-top:1px solid var(--line);border-bottom:1px solid var(--line);
background:radial-gradient(1200px 600px at 50% 40%,#fffaf0 0%,#f1e8d8 60%,#e6dac5 100%)}}
#three{{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}}#three:active{{cursor:grabbing}}
.floors{{position:absolute;left:24px;top:24px;display:flex;gap:8px;flex-wrap:wrap;z-index:3}}
.floors button{{padding:9px 16px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.7);backdrop-filter:blur(8px);font-size:.82rem}}
.floors button.on{{background:var(--gold);color:#fff;border-color:var(--gold)}}
.tip{{position:absolute;pointer-events:none;z-index:4;transform:translate(-50%,-120%);padding:10px 14px;border-radius:12px;
background:rgba(255,255,255,.95);border:1px solid var(--line);font-size:.85rem;white-space:nowrap;opacity:0;transition:opacity .2s;box-shadow:0 12px 30px -12px rgba(0,0,0,.25)}}
.tip b{{display:block;font-family:var(--head);font-size:1.2rem;font-weight:500}}.tip small{{color:var(--gold)}}
.hint{{position:absolute;right:24px;bottom:22px;z-index:3;color:var(--muted);font-size:.8rem;text-align:right}}
.labels{{position:absolute;inset:0;pointer-events:none;z-index:2}}
.labels span.x{{background:rgba(184,134,11,.9);color:#fff;font-family:var(--body);font-size:.72rem}}.labels span{{position:absolute;transform:translate(-50%,-50%);font-family:var(--head);font-size:.82rem;font-weight:600;color:#2b2a28;padding:3px 9px;border-radius:999px;background:rgba(255,255,255,.82);
white-space:nowrap;transition:opacity .3s}}
/* suites */
#suites{{padding:120px 0}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}}
.suite{{position:relative;text-align:left;border-radius:22px;overflow:hidden;aspect-ratio:3/4;background:var(--panel);border:1px solid var(--line);color:#fff}}
.suite .img{{position:absolute;inset:0;background-size:cover;background-position:center;transition:transform 1.2s cubic-bezier(.2,.8,.2,1)}}
.suite::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(10,8,6,.92))}}
.suite:hover .img{{transform:scale(1.08)}}.suite .meta{{position:absolute;left:20px;right:20px;bottom:18px;z-index:2;display:grid;gap:4px}}
.suite small{{color:#f3c64f;text-transform:uppercase;letter-spacing:.2em;font-size:.68rem;font-weight:600}}
.suite b{{font-family:var(--head);font-size:1.6rem;font-weight:500;line-height:1.1}}.suite em{{font-family:var(--body);font-style:normal;color:#eee6da;font-size:.86rem;max-height:0;overflow:hidden;transition:max-height .5s}}
.suite:hover em{{max-height:120px}}
/* book */
#book{{padding:110px 0;background:#fff;border-block:1px solid var(--line)}}
.bookbox{{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:stretch}}
.card{{border:1px solid var(--line);border-radius:26px;padding:34px;background:var(--bg)}}
.card h3{{font-size:2.2rem;margin:10px 0}}.card p{{color:var(--muted)}}
.save{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}.bookbox>*,.visit>*,.head>*{{min-width:0}}.save div{{flex:1;border-radius:18px;padding:18px;background:#fff;border:1px solid var(--line)}}
.save b{{font-family:var(--head);font-size:1.6rem;color:var(--gold);font-weight:600;display:block}}
.cal{{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin:18px 0}}.cal span{{aspect-ratio:1;display:grid;place-items:center;border-radius:10px;font-size:.82rem;background:#fff;border:1px solid var(--line)}}
.cal span.x{{opacity:.3;text-decoration:line-through}}.cal span.h{{color:var(--muted);background:none;border:0;font-size:.7rem}}.cal span.sel{{background:var(--gold);color:#fff;font-weight:600}}
.sync{{display:flex;align-items:center;gap:10px;font-size:.85rem;color:var(--muted)}}.sync i{{width:9px;height:9px;border-radius:50%;background:#56c58a;box-shadow:0 0 12px #56c58a}}
/* reviews */
#reviews{{padding:120px 0}}.rev{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:40px}}
blockquote{{border:1px solid var(--line);border-radius:22px;padding:28px;background:var(--panel)}}blockquote span{{color:var(--gold)}}
blockquote p{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;line-height:1.35;margin:12px 0}}blockquote cite{{font-style:normal;color:var(--muted)}}
.score{{font-family:var(--head);font-size:clamp(4rem,10vw,7rem);line-height:1;color:var(--gold)}}
/* visit */
#visit{{padding:100px 0 60px;border-top:1px solid var(--line)}}.visit{{display:grid;grid-template-columns:1.2fr .8fr;gap:30px;align-items:end}}
.visit h2{{font-size:clamp(2.4rem,5vw,4rem);line-height:1}}footer{{padding:30px 0 50px;color:var(--muted);font-size:.8rem}}
/* room overlay */
#room{{position:fixed;inset:0;z-index:40;display:grid;grid-template-columns:1.35fr 1fr;background:#fff;
opacity:0;visibility:hidden;transition:opacity .5s,visibility .5s}}#room.open{{opacity:1;visibility:visible}}
#room .pics{{position:relative;overflow:hidden}}#room .big{{position:absolute;inset:0;background-size:cover;background-position:center;transition:opacity .5s,transform 6s linear}}
#room .thumbs{{position:absolute;left:18px;right:18px;bottom:18px;display:flex;gap:8px;overflow-x:auto;padding-bottom:4px}}
#room .thumbs button{{flex:0 0 74px;height:74px;border-radius:12px;background-size:cover;background-position:center;border:2px solid transparent;opacity:.75}}
#room .thumbs button.on{{border-color:var(--gold);opacity:1}}
#room .info{{padding:64px 48px;overflow-y:auto;border-left:1px solid var(--line)}}#room h3{{font-size:clamp(2.4rem,4vw,3.6rem);line-height:1;margin:14px 0 20px}}
#room .info p{{color:#4a4640;margin-bottom:14px}}#room .close{{position:absolute;top:18px;right:22px;z-index:3;width:46px;height:46px;border-radius:50%;
border:1px solid var(--line);background:#fff;font-size:1.3rem}}
.nextprev{{display:flex;gap:10px;margin-top:26px}}
.reveal{{opacity:0;transform:translateY(30px);transition:opacity .9s,transform .9s cubic-bezier(.2,.8,.2,1);transition-delay:var(--d,0ms)}}.reveal.in{{opacity:1;transform:none}}
.concept{{font-size:.75rem;color:var(--muted);margin-top:10px}}
@media (max-width:600px){{#intro p{{letter-spacing:.18em;font-size:.62rem}}.card{{padding:24px}}.card h3{{font-size:1.7rem}}.save div{{flex:1 1 40%}}nav .wrap{{gap:12px}}nav .btn{{padding:9px 14px;font-size:.78rem;white-space:nowrap;flex:none}}.brand img{{height:42px}}.stat{{gap:22px}}.stat b{{font-size:1.6rem}}.floors{{left:12px;right:12px;top:12px;gap:5px;flex-wrap:nowrap;overflow-x:auto}}.floors button{{padding:7px 11px;font-size:.72rem;white-space:nowrap;flex:none}}.labels span{{font-size:.68rem;padding:2px 7px}}}}@media (max-width:980px){{.grid{{grid-template-columns:repeat(2,1fr)}}.head,.bookbox,.visit,.rev{{grid-template-columns:1fr}}.links{{display:none}}
#room{{grid-template-columns:1fr;grid-template-rows:50vh 1fr}}#room .info{{padding:28px 24px}}.stage{{height:70vh}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}.reveal{{opacity:1;transform:none}}.slide:first-child{{opacity:1}}}}
</style>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}}}</script>
</head><body>
<div id="intro"><div class="shine"><img src="logo.png" alt="{e(name)}"><p>MOSELEY VILLAGE &middot; BIRMINGHAM</p></div></div>
<nav id="nav"><div class="wrap"><span class="brand"><img src="logo.png" alt="{e(name)}"></span>
<span class="links"><a href="#house">The House</a><a href="#suites">Suites</a><a href="#book">Book direct</a><a href="#reviews">Reviews</a><a href="#visit">Find us</a></span>
<a class="btn" href="#book">Book direct</a></div></nav>
<header class="hero"><video autoplay muted loop playsinline preload="auto" poster="exterior.jpg"><source src="walkthrough.mp4" type="video/mp4"></video><div class="wrap">
<p class="kicker">Twelve suites &middot; Moseley Village</p>
<h2>Distinctive luxury,<br><em>in Moseley Village.</em></h2>
<p class="lead">Twelve individually designed suites with king-size beds, walk-in showers, underfloor heating and a private entrance, in the heart of Moseley Village.</p>
<a class="btn" href="#house">Explore the house in 3D &darr;</a>&nbsp; <a class="btn ghost" href="#book">Book direct and save</a>
<div class="stat"><div><b>{place["rating"]:.1f}★</b>Google rating</div><div><b>{place["reviews"]}</b>guest reviews</div><div><b>12</b>unique suites</div><div><b>4</b>floors</div></div>
</div></header>

<section id="house"><div class="wrap head"><div><p class="kicker reveal">The house, in 3D</p><h2 class="reveal">Step inside.<br>Choose your suite.</h2></div>
<p class="reveal">This is the real layout of the house, room by room, from the street front to the garden. Spin it, pick a floor, then tap any suite to walk into it and see every photo. Every room is different, so take a look around before you book.</p></div>
<div class="stage"><canvas id="three"></canvas><div class="labels" id="labels"></div>
<div class="floors" id="floors"><button data-f="all" class="on">Whole house</button><button data-f="-1">Lower ground</button><button data-f="0">Ground</button><button data-f="1">First</button><button data-f="2">Second</button></div>
<div class="tip" id="tip"></div><div class="hint">Drag to spin &middot; scroll to zoom &middot; tap a suite to enter<br><span class="concept">Laid out from the house&rsquo;s approved floor plans (Birmingham City Council, ref. 2023/07524/PA)</span></div></div>
</section>

<section id="suites"><div class="wrap"><p class="kicker reveal">The suites</p><h2 class="reveal" style="font-size:clamp(2.4rem,5vw,4rem);margin:12px 0 40px">Twelve rooms. No two alike.</h2>
<div class="grid">{cards}</div></div></section>

<section id="book"><div class="wrap"><div class="bookbox">
<div class="card reveal"><p class="kicker">Book direct</p><h3>Same suites. Better price.</h3>
<p>Booking sites add their fees on top. Book with us directly and you skip them, with the same rooms, the same welcome and a direct line to your hosts.</p>
<div class="save"><div><b>No</b>booking-site fees</div><div><b>Best</b>rate, guaranteed</div><div><b>Direct</b>chat with your hosts</div></div>
<a class="btn" href="{e(place.get('website') or '#')}">Check dates and book</a></div>
<div class="card reveal" style="--d:120ms"><p class="kicker">Live availability</p><h3>Pick your dates</h3>
<div class="cal" id="cal"></div>
<p class="sync"><i></i>Calendar synced with Airbnb, so what you see here is what's free</p>
<p class="concept">Concept: on the live site this calendar reads the Airbnb calendar automatically.</p></div>
</div></div></section>

<section id="reviews"><div class="wrap"><div class="head" style="margin:0"><div><p class="kicker reveal">Guests say</p>
<p class="score reveal">{place["rating"]:.1f}<span style="font-size:.35em;color:var(--muted)"> / 5</span></p></div>
<p class="reveal">Rated {place["rating"]:.1f} out of 5 by {place["reviews"]} guests on Google.</p></div>
<div class="rev">{reviews}</div></div></section>

<section id="visit"><div class="wrap visit"><div><p class="kicker reveal">Find us</p><h2 class="reveal">In the heart of<br>Moseley Village.</h2>
<p class="reveal" style="color:var(--muted);margin-top:16px">{e(place.get("address", ""))}</p></div>
<div class="reveal"><a class="btn" href="{e(place.get('maps') or '#')}" target="_blank" rel="noopener">Directions</a>&nbsp; {f'<a class="btn ghost" href="tel:{e(tel)}">{e(place.get("phone", ""))}</a>' if tel else ''}</div></div></section>
<footer><div class="wrap">A free concept website for {e(name)}, designed by Kinetic Web Designs, using the photos and words from their own website and Google listing. Not the live site.</div></footer>

<div id="room"><div class="pics"><div class="big" id="big"></div><div class="thumbs" id="thumbs"></div></div>
<div class="info"><button class="close" id="close" aria-label="Close">&times;</button><p class="kicker" id="rfloor"></p><h3 id="rname"></h3><div id="rtext"></div>
<a class="btn" href="{e(place.get('website') or '#')}">Book this suite</a><div class="nextprev"><button class="btn ghost" id="prev">&larr; Previous</button><button class="btn ghost" id="next">Next suite &rarr;</button></div></div></div>

<script>window.STAY = {data};</script>
<script type="module">
import * as THREE from "three";
import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
import {{ RoomEnvironment }} from "three/addons/environments/RoomEnvironment.js";
import {{ RoundedBoxGeometry }} from "three/addons/geometries/RoundedBoxGeometry.js";
const S = window.STAY, rooms = S.rooms;
// intro + nav + reveals
setTimeout(() => document.getElementById("intro").classList.add("out"), 3100);
const nav = document.getElementById("nav"); addEventListener("scroll", () => nav.classList.toggle("solid", scrollY > 60));
const io = new IntersectionObserver(es => es.forEach(x => {{ if (x.isIntersecting) {{ x.target.classList.add("in"); io.unobserve(x.target); }} }}), {{threshold: .12}});
document.querySelectorAll(".reveal").forEach(el => io.observe(el));
// calendar (concept)
const cal = document.getElementById("cal"); const now = new Date(); const first = new Date(now.getFullYear(), now.getMonth(), 1);
cal.innerHTML = ["M","T","W","T","F","S","S"].map(d => `<span class="h">${{d}}</span>`).join("") + Array((first.getDay() + 6) % 7).fill('<span class="h"></span>').join("")
  + Array.from({{length: new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}}, (_, i) => {{ const d = i + 1;
    return `<span class="${{d < now.getDate() || [3,4,11,17,18,19,25].includes(d) ? "x" : ""}}">${{d}}</span>`; }}).join("");
cal.addEventListener("click", ev => {{ const s = ev.target; if (s.tagName === "SPAN" && !s.classList.contains("x") && !s.classList.contains("h")) s.classList.toggle("sel"); }});
// room overlay
const ov = document.getElementById("room"), big = document.getElementById("big"), thumbs = document.getElementById("thumbs");
let cur = 0;
function openRoom(i) {{
  cur = (i + rooms.length) % rooms.length; const r = rooms[cur];
  document.getElementById("rfloor").textContent = r.floor_name;
  document.getElementById("rname").textContent = r.name;
  document.getElementById("rtext").innerHTML = [r.summary, ...(r.story || [])].filter(Boolean).map(t => `<p>${{t.replace(/[<>]/g, "")}}</p>`).join("");
  const show = src => {{ big.style.backgroundImage = `url(${{src}})`; thumbs.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.src === src)); }};
  thumbs.innerHTML = r.gallery.map(g => `<button data-src="${{g}}" style="background-image:url(${{g}})"></button>`).join("");
  thumbs.querySelectorAll("button").forEach(b => b.onclick = () => show(b.dataset.src));
  show(r.gallery[0]); ov.classList.add("open"); document.body.style.overflow = "hidden";
}}
function closeRoom() {{ ov.classList.remove("open"); document.body.style.overflow = ""; flyHome(); }}
document.getElementById("close").onclick = closeRoom; document.getElementById("next").onclick = () => openRoom(cur + 1); document.getElementById("prev").onclick = () => openRoom(cur - 1);
addEventListener("keydown", ev => {{ if (ev.key === "Escape") closeRoom(); }});
document.querySelectorAll(".suite").forEach(b => b.onclick = () => openRoom(rooms.findIndex(r => r.slug === b.dataset.slug)));

// ---- the 3D house: three floors, four suites each, each floored with its own photo
const canvas = document.getElementById("three"), stage = canvas.parentElement;
const renderer = new THREE.WebGLRenderer({{canvas, antialias: true, alpha: true}});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.shadowMap.enabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = .72; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0xf1e8d8, 45, 95);
const camera = new THREE.PerspectiveCamera(36, 1, .1, 200);
const controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.autoRotate = true; controls.autoRotateSpeed = .55;
controls.minDistance = 12; controls.maxDistance = 80; controls.maxPolarAngle = Math.PI * .47; controls.target.set(0, 2.6, 0);
const HOME = new THREE.Vector3(25, 16, 25).multiplyScalar(innerWidth < 700 ? 1.5 : 1); camera.position.copy(HOME);
const pmrem = new THREE.PMREMGenerator(renderer); scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture;
scene.add(new THREE.HemisphereLight(0xfff1dc, 0x241a12, 1.1));
const sun = new THREE.DirectionalLight(0xffe2b8, 2.2); sun.position.set(14, 26, 10); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, {{left: -20, right: 20, top: 20, bottom: -20}}); scene.add(sun);
const FLOOR_H = 3.2; const ground = new THREE.Mesh(new THREE.CircleGeometry(26, 64), new THREE.MeshStandardMaterial({{color: 0xe9dfcc, roughness: 1}}));
ground.rotation.x = -Math.PI / 2; ground.position.y = -FLOOR_H * 1.55 - .3; ground.receiveShadow = true; scene.add(ground);
const loader = new THREE.TextureLoader(); const D = 3.8, C = 1.5, H = 1.35, LEN = 11.2;
// Room positions follow the approved plans: x runs from the street (bay window, -x) to the garden (+x),
// z = which side of the central corridor (+z is the bay side). Suites fill each floor's rooms in order.
const PLAN = {{
  0: [{{x: -1, s: -1, l: 5.7}}, {{x: -1, s: 1, l: 5.7, bay: 1}}, {{x: 1, s: 1, l: 5.3}}, {{x: 1, s: -1, l: 5.3}}],
  1: [{{x: 1, s: -1, l: 4.9, balcony: 1}}, {{x: 1, s: 1, l: 4.9}}, {{x: -1, s: -1, l: 6.1}}, {{x: -1, s: 1, l: 6.1, bay: 1}}],
  2: [{{x: 1, s: -1, l: 4.9}}, {{x: 1, s: 1, l: 4.9}}, {{x: -1, s: -1, l: 6.1}}, {{x: -1, s: 1, l: 6.1}}],
}};
const floors = {{}}, pick = [], labelEls = [];
const gold = () => new THREE.MeshStandardMaterial({{color: 0xc8960f, roughness: .35, metalness: .5}});
const glass = () => {{ const m = new THREE.MeshStandardMaterial({{color: 0xfff6e6, roughness: .15, metalness: .1, transparent: true, opacity: .22}}); m.userData.base = .22; return m; }};
const box = (w, h, d, mat, x, y, z, g) => {{ const o = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(.035, Math.min(w, h, d) * .3)), mat); o.position.set(x, y, z); o.castShadow = true; g.add(o); return o; }};
function marker(text, g, x, y, z, f) {{
  const o = new THREE.Object3D(); o.position.set(x, y, z); g.add(o);
  const lab = document.createElement("span"); lab.className = "x"; lab.textContent = text; document.getElementById("labels").appendChild(lab);
  labelEls.push({{el: lab, obj: o, f}});
}}

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
function level(f) {{
  const g = new THREE.Group(); g.position.y = f * FLOOR_H; scene.add(g); floors[f] = g;
  const slab = box(LEN + .4, .22, D * 2 + C + .4, new THREE.MeshStandardMaterial({{color: 0xe9e1d3, roughness: .9}}), 0, -.12, 0, g);
  slab.receiveShadow = true;
  const hall = new THREE.Mesh(new THREE.PlaneGeometry(LEN, C), new THREE.MeshStandardMaterial({{color: 0xd9c3a0, roughness: .7}}));
  hall.rotation.x = -Math.PI / 2; hall.position.y = .012; hall.receiveShadow = true; g.add(hall);
  // the stair in the middle of the corridor, as on every plan
  const step = new THREE.MeshStandardMaterial({{color: 0xf6efe3, roughness: .6}});
  for (let i = 0; i < 8; i++) box(.36, .12 + i * .14, C * .8, step, -1.3 + i * .36, (.12 + i * .14) / 2, 0, g);
  return g;
}}
[0, 1, 2].forEach(f => {{
  const g = level(f), list = rooms.map((r, i) => [r, i]).filter(([r]) => r.floor === f);
  list.forEach(([r, idx], k) => {{
    const p = PLAN[f][k], x = p.x * (LEN / 2 - p.l / 2), z = p.s * (C / 2 + D / 2), W = p.l - .1;
    const kind = kindOf(r);
    const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(W, D), floorMat(kind, W, D));
    floorMesh.rotation.x = -Math.PI / 2; floorMesh.position.set(x, .02, z); floorMesh.receiveShadow = true; g.add(floorMesh);
    const wallMat = mat(0xf6f3ee), trimMat = new THREE.MeshStandardMaterial({{color: 0x3a342e, roughness: .5, emissive: 0xe0b84a, emissiveIntensity: 0}});
    walls(g, x, z, W, D, p.s, trimMat, kind === "pool" || kind === "outdoor");
    furnish(kind, g, x, z, W, D, p.s, new THREE.Color(r.accent || "#c9a77a"), r.cover);
    if (p.bay) {{   // the canted bay window on the street front
      const bay = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, H, 6, 1, true, Math.PI, Math.PI), glass());
      bay.rotation.y = Math.PI / 2; bay.scale.set(1, 1, .45); bay.position.set(-LEN / 2, H / 2, z); g.add(bay);
      box(.07, .07, 3, trimMat, -LEN / 2 - .67, H, z, g);
    }}
    if (p.balcony) {{   // first-floor balcony over the garden
      box(1.4, .1, 4, new THREE.MeshStandardMaterial({{color: 0xf3ead9, roughness: .9}}), LEN / 2 + .7, -.05, z, g);
      box(.05, .7, 4, gold(), LEN / 2 + 1.38, .35, z, g); box(1.4, .7, .05, gold(), LEN / 2 + .7, .35, z - 2, g); box(1.4, .7, .05, gold(), LEN / 2 + .7, .35, z + 2, g);
      marker("Balcony", g, LEN / 2 + .7, .9, z, f);
    }}
    const hit = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), new THREE.MeshBasicMaterial({{visible: false}}));
    hit.position.set(x, H / 2, z); hit.userData = {{idx, trimMat, floorMesh, f}}; g.add(hit); pick.push(hit);
    const lab = document.createElement("span"); lab.textContent = r.name.replace(/^The /, ""); document.getElementById("labels").appendChild(lab);
    labelEls.push({{el: lab, obj: hit, f}});
  }});
}});
// the front door off School Road, with the self check-in kiosk
const gf = floors[0];
box(.12, 1.9, .12, gold(), -LEN / 2 - .05, .95, -.6, gf); box(.12, 1.9, .12, gold(), -LEN / 2 - .05, .95, .6, gf); box(.12, .12, 1.32, gold(), -LEN / 2 - .05, 1.9, 0, gf);
box(.8, .08, 1.6, new THREE.MeshStandardMaterial({{color: 0xd8cfbf}}), -LEN / 2 - .45, .04, 0, gf);
marker("Entrance · self check-in", gf, -LEN / 2 - .6, 2.4, 0, 0);
// lower ground: guest lounge with pool table, kitchenette and the team's rooms
const lg = level(-1);
const lounge = new THREE.Mesh(new THREE.PlaneGeometry(6, D * 2 + C), new THREE.MeshStandardMaterial({{color: 0xcbb38c, roughness: .8}}));
lounge.rotation.x = -Math.PI / 2; lounge.position.set(-LEN / 2 + 3, .02, 0); lg.add(lounge);
box(2.2, .5, 1.2, new THREE.MeshStandardMaterial({{color: 0x1f5b3a, roughness: .9}}), -LEN / 2 + 2.6, .25, 1.6, lg);
box(1.6, .45, 1.1, new THREE.MeshStandardMaterial({{color: 0x8a6b4a, roughness: .8}}), LEN / 2 - 1.6, .22, 1.9, lg);
const lw = glass(); box(.12, H, D * 2 + C, lw, 0, H / 2, 0, lg); box(LEN, H, .12, lw, 0, H / 2, -(D + C / 2), lg); box(LEN, H, .12, lw, 0, H / 2, D + C / 2, lg);
marker("Guest lounge · pool table", lg, -LEN / 2 + 3, 1.4, 1, -1);
marker("Kitchenette", lg, LEN / 2 - 2, 1.4, 2, -1);
// warm lamps through the house
for (let i = 0; i < 20; i++) {{ const l = new THREE.PointLight(0xffc98a, .6, 6); l.position.set((Math.random() - .5) * 10, (i % 4 - 1) * FLOOR_H + 1, (Math.random() - .5) * 7); scene.add(l); }}
let mode = "all", target = {{explode: 1}}, explode = 0;
function layout(dt) {{
  explode += (target.explode - explode) * Math.min(1, dt * 3);
  Object.entries(floors).forEach(([k, g]) => {{ const f = +k;
    const shown = mode === "all" || +mode === f, above = mode !== "all" && f > +mode;
    g.position.y += ((f * FLOOR_H * (1 + explode * .55)) + (above ? 12 : 0) - g.position.y) * Math.min(1, dt * 4);
    g.traverse(o => {{ if (o.material && o.material.transparent !== undefined && o !== g) {{ const base = o.material.userData.base ?? 1; o.material.transparent = true; o.material.opacity += (base * (above ? 0 : shown ? 1 : .18) - o.material.opacity) * Math.min(1, dt * 4); }} }});
  }});
}}
document.getElementById("floors").onclick = ev => {{ const b = ev.target.closest("button"); if (!b) return;
  mode = b.dataset.f; document.querySelectorAll("#floors button").forEach(x => x.classList.toggle("on", x === b));
  const y = mode === "all" ? 2.6 : +mode * FLOOR_H * 1.55 + .4; controls.autoRotate = false;
  fly = {{t: 0, from: camera.position.clone(), to: mode === "all" ? HOME.clone() : new THREE.Vector3(12, y + 11, 13.5),
         tf: controls.target.clone(), tt: new THREE.Vector3(0, y, 0), done: () => controls.autoRotate = true}}; }};
// hover + click
const ray = new THREE.Raycaster(), m = new THREE.Vector2(-9, -9), tip = document.getElementById("tip"); let hover = null, downAt = 0;
canvas.addEventListener("pointermove", ev => {{ const b = canvas.getBoundingClientRect(); m.set((ev.clientX - b.left) / b.width * 2 - 1, -(ev.clientY - b.top) / b.height * 2 + 1);
  tip.style.left = (ev.clientX - b.left) + "px"; tip.style.top = (ev.clientY - b.top) + "px"; }});
canvas.addEventListener("pointerdown", () => downAt = performance.now());
canvas.addEventListener("pointerup", () => {{ if (hover && performance.now() - downAt < 250) flyInto(hover); }});
let fly = null;
function flyInto(hit) {{
  const p = new THREE.Vector3(); hit.getWorldPosition(p); controls.autoRotate = false;
  fly = {{t: 0, from: camera.position.clone(), to: p.clone().add(new THREE.Vector3(2.2, 3.2, 3.2)), tf: controls.target.clone(), tt: p.clone(),
         done: () => openRoom(hit.userData.idx)}};
}}
function flyHome() {{ fly = {{t: 0, from: camera.position.clone(), to: HOME.clone(), tf: controls.target.clone(), tt: new THREE.Vector3(0, 2.6, 0), done: () => controls.autoRotate = true}}; }}
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
  layout(dt);
  if (fly) {{ fly.t = Math.min(1, fly.t + dt / 1.1); const k = fly.t < .5 ? 4 * fly.t ** 3 : 1 - (-2 * fly.t + 2) ** 3 / 2;
    camera.position.lerpVectors(fly.from, fly.to, k); controls.target.lerpVectors(fly.tf, fly.tt, k); if (fly.t === 1) {{ const d = fly.done; fly = null; d(); }} }}
  ray.setFromCamera(m, camera);
  const hits = ray.intersectObjects(pick.filter(h => mode === "all" || h.userData.f === +mode));
  const h = hits.length ? hits[0].object : null;
  if (h !== hover) {{ if (hover) hover.userData.trimMat.emissiveIntensity = 0; hover = h;
    if (h) {{ h.userData.trimMat.emissiveIntensity = 1.2; const r = rooms[h.userData.idx]; tip.innerHTML = `<small>${{r.floor_name}}</small><b>${{r.name}}</b>Tap to step inside`; tip.style.opacity = 1; }}
    else tip.style.opacity = 0; canvas.style.cursor = h ? "pointer" : "grab"; }}
  const b = canvas.getBoundingClientRect();
  labelEls.forEach(l => {{ l.obj.getWorldPosition(v); v.y += 1.1; v.project(camera);
    l.el.style.left = ((v.x + 1) / 2 * b.width) + "px"; l.el.style.top = ((1 - v.y) / 2 * b.height) + "px";
    l.el.style.opacity = (mode === "all" || l.f === +mode) && v.z < 1 ? (mode === "all" ? .75 : 1) : 0; }});
  controls.update(); renderer.render(scene, camera);
}});
</script>
</body></html>
"""
# ---- optional extras, used whenever the host's folder has them (every stays concept gets the same upgrades):
#   plan.png + plan.json {"title", "text", "note"}: a "built on the real floor plan" section with the drawing
#   airbnb.json {"rating", "note"}: their Airbnb rating card in the book-direct box (e.g. "Guest favourite, 85 reviews")
EXTRA_CSS = (".plan{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center;padding:0 0 110px}"
             ".plan img{width:100%;border-radius:18px;border:1px solid var(--line);background:#fff}.plan h3{font-size:2rem;margin:10px 0}"
             ".plan p{color:var(--muted);margin-bottom:12px}.airbnb{display:flex;align-items:center;gap:14px;margin-top:16px;padding:16px 18px;"
             "border-radius:18px;background:#fff;border:1px solid var(--line);font-size:.9rem}.airbnb b{font-family:var(--head);font-size:1.5rem;color:#ff385c}"
             "@media (max-width:980px){.plan{grid-template-columns:1fr}}")
html = html.replace("</style>", EXTRA_CSS + "</style>", 1)
#   plan.json "plans": [{"img", "label"}] shows several real plans with tabs to switch between them (owner, 25 Oct 2026: more floor plans)
_pj = json.load(open(OUT / "plan.json", encoding="utf-8")) if (OUT / "plan.json").exists() else {}
if _pj.get("plans"):
    tabs = "".join(f'<button type="button" data-img="{e(x["img"])}"{" class=on" if not i else ""}>{e(x["label"])}</button>' for i, x in enumerate(_pj["plans"]))
    block = (f'<div class="wrap plan"><div class="reveal"><img id="planimg" src="{e(_pj["plans"][0]["img"])}" alt="The floor plan"><div class="ptabs">{tabs}</div></div>'
             f'<div class="reveal"><p class="kicker">The plans</p><h3>{e(_pj.get("title", "Built on the real floor plans"))}</h3><p>{e(_pj.get("text", ""))}</p>'
             + (f'<p class="concept">{e(_pj["note"])}</p>' if _pj.get("note") else "") + "</div></div>\n"
             '<script>document.querySelectorAll(".ptabs button").forEach(b => b.onclick = () => { document.getElementById("planimg").src = b.dataset.img;'
             ' document.querySelectorAll(".ptabs button").forEach(x => x.classList.toggle("on", x === b)); });</script>\n')
    html = html.replace('<section id="book">', block + '<section id="book">', 1)
    html = html.replace("</style>", ".ptabs{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.ptabs button{padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;font:600 .78rem var(--body);cursor:pointer;color:var(--ink)}.ptabs button.on{background:var(--ink);color:#fff}</style>", 1)
elif (OUT / "plan.png").exists():
    pj = _pj
    block = (f'<div class="wrap plan"><img class="reveal" src="plan.png" alt="The floor plan"><div class="reveal"><p class="kicker">The plans</p>'
             f'<h3>{e(pj.get("title", "Built on the real floor plan"))}</h3><p>{e(pj.get("text", "The 3D house above follows the real layout, so guests see exactly how the space flows before they arrive."))}</p>'
             + (f'<p class="concept">{e(pj["note"])}</p>' if pj.get("note") else "") + "</div></div>\n")
    html = html.replace('<section id="book">', block + '<section id="book">', 1)
if (OUT / "airbnb.json").exists():
    ab = json.load(open(OUT / "airbnb.json", encoding="utf-8"))
    card = f'<div class="airbnb"><b>{e(str(ab.get("rating", "")))}</b><span>{e(ab.get("note", ""))}</span></div>'
    html = html.replace("Check dates and book</a></div>", "Check dates and book</a>" + card + "</div>", 1)
STORY_CSS = '.story{position:relative;height:520vh;background:#0d0d0d}.story .pin{position:sticky;top:0;height:100svh;overflow:hidden}.story .st{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.04);transition:opacity .25s linear}.story .cap{position:absolute;left:0;right:0;top:12vh;text-align:center;z-index:3;padding:0 24px;pointer-events:none}.story .cap h2{font-family:var(--head);font-weight:500;font-size:clamp(2rem,5vw,4.2rem);line-height:1.05;color:#1d1d1b;text-shadow:0 1px 30px rgba(255,255,255,.6);transition:opacity .4s,transform .4s}.story .cap p{font-size:.8rem;letter-spacing:.32em;text-transform:uppercase;color:#6b6760;margin-bottom:10px}.story.dark .cap h2{color:#fff;text-shadow:0 2px 30px rgba(0,0,0,.6)}.story.dark .cap p{color:#e7e2d8}.story .dots{position:absolute;right:22px;top:50%;transform:translateY(-50%);display:grid;gap:10px;z-index:3}.story .dots i{width:7px;height:7px;border-radius:50%;background:rgba(120,120,120,.45);transition:background .3s,transform .3s}.story .dots i.on{background:var(--gold);transform:scale(1.5)}'
STORY_JS = '<script>\n(() => { const s = document.querySelector(".story"); if (!s) return;\n  const st = [...s.querySelectorAll(".st")], dots = [...s.querySelectorAll(".dots i")], h = s.querySelector(".cap h2"), k = s.querySelector(".cap p"), lines = JSON.parse(s.dataset.lines);\n  let cur = -1;\n  function draw() { const r = s.getBoundingClientRect(), p = Math.min(.9999, Math.max(0, -r.top / (r.height - innerHeight))), f = p * st.length, i = Math.floor(f), t = f - i;\n    st.forEach((el, n) => { el.style.opacity = n < i ? 0 : n === i ? 1 : n === i + 1 ? Math.max(0, (t - .55) / .45) : 0; el.style.transform = `scale(${1.06 - .06 * (n === i ? t : 0)})`; });\n    if (i !== cur) { cur = i; h.style.opacity = 0; setTimeout(() => { h.textContent = lines[i] || ""; k.textContent = `${i + 1} / ${st.length}`; h.style.opacity = 1; }, 180);\n      dots.forEach((d, n) => d.classList.toggle("on", n === i)); s.classList.toggle("dark", i >= st.length - 2); } }\n  addEventListener("scroll", draw, {passive: true}); addEventListener("resize", draw); draw(); })();\n</script>'
if (OUT / "build" / "1.jpg").exists():
    bj = json.load(open(OUT / "build.json", encoding="utf-8")) if (OUT / "build.json").exists() else {}
    stages = [f"build/{i}.jpg" for i in range(1, 4) if (OUT / "build" / f"{i}.jpg").exists()] + ["MOSAIC"]
    final = json.load(open(OUT / "hero.json"))[0] if (OUT / "hero.json").exists() else "exterior.jpg"
    stages.append(bj.get("final", final))
    lines = bj.get("lines") or ["It starts with a line.", "Then it takes shape.", "Material, texture, detail.", "Every room, exactly as it is.", f"Welcome to {name}."]
    lines = [("Every room, exactly as it is." if x == "Lit from within." else x) for x in lines]
    MOSAIC = '<div class="st mosaic">' + "".join(f'<span style="background-image:url({c})"></span>' for c in [r["cover"] for r in rooms][:6]) + "</div>"
    story = (f'<section class="story" data-lines="{e(json.dumps(lines[:len(stages)]))}"><div class="pin">'
             + "".join(MOSAIC if s == "MOSAIC" else f'<div class="st" style="background-image:url({s})"></div>' for s in stages)
             + '<div class="cap"><p></p><h2></h2></div><div class="dots">' + "<i></i>" * len(stages) + "</div></div></section>")
    html = html.replace("</style>", STORY_CSS + '.story .mosaic{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:1fr;gap:8px;padding:24vh 5vw 7vh;background:#111}.story .mosaic span{background-size:cover;background-position:center;border-radius:12px}@media (max-width:700px){.story .mosaic{grid-template-columns:repeat(2,1fr);padding:22vh 12px 6vh}}' + "</style>", 1)
    html = html.replace('<section id="house">', story + "\n" + '<section id="house">', 1)
    html = html.replace("</body>", STORY_JS + "</body>", 1)
sys.path.insert(0, str(Path(__file__).parent))
from door import add_door  # the "one line, an entire home" opening
html = add_door(html, OUT, [(r["slug"], r["cover"]) for r in rooms])
from journey import add_journey  # the scroll-driven walkthrough journey
html = add_journey(html, OUT)
from neighbourhood import add_hood  # Google satellite + Street View of their street
html = add_hood(html, OUT)
from beforeafter import add_compare  # their current website beside ours, with a slider
html = add_compare(html, OUT)
(OUT / "index.html").write_text(html, encoding="utf-8")
print("written", len(html) // 1024, "KB")
