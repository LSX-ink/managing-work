"""Restyle the stays page in Moseley Luxury Stay's own brand: white and gold, their crown-M logo, a logo intro
animation, and their walkthrough video behind the hero instead of photo slides."""
from pathlib import Path

f = Path(__file__).with_name("stays_page.py")
t = f.read_text(encoding="utf-8")
R = [
 # fonts: their logo's classic serif caps + their site font
 ("family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Manrope:wght@300;400;500;600",
  "family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,500&family=DM+Sans:wght@400;500;600"),
 (":root{{--bg:#0f0d0b;--ink:#f3ece1;--muted:#b6aa98;--gold:#c9a77a;--gold2:#e8d3ad;--panel:#17140f;--line:rgba(232,211,173,.16);\n--head:'Cormorant Garamond',Georgia,serif;--body:'Manrope',system-ui,sans-serif}}",
  ":root{{--bg:#fbf8f2;--ink:#2b2a28;--muted:#6f6a62;--gold:#b8860b;--gold2:#d9a521;--panel:#ffffff;--line:rgba(43,42,40,.12);\n--head:'Cinzel',Georgia,serif;--body:'DM Sans',system-ui,sans-serif}}"),
 (".btn{{display:inline-flex;align-items:center;gap:10px;padding:15px 28px;border-radius:999px;background:linear-gradient(120deg,var(--gold2),var(--gold));\ncolor:#17120b;",
  ".btn{{display:inline-flex;align-items:center;gap:10px;padding:15px 28px;border-radius:999px;background:linear-gradient(120deg,var(--gold2),var(--gold));\ncolor:#fff;"),
 ("h1,h2,h3{{font-family:var(--head);font-weight:500;letter-spacing:-.01em}}",
  "h1,h2,h3{{font-family:var(--head);font-weight:500;letter-spacing:.02em}}em{{font-family:'Cormorant Garamond',serif;font-style:italic;letter-spacing:0}}"),
 # intro: their logo, drawn in gold
 ("#intro{{position:fixed;inset:0;z-index:50;background:var(--bg);",
  "#intro{{position:fixed;inset:0;z-index:50;background:#fff;"),
 ("#intro h1 span{{display:inline-block;opacity:0;transform:translateY(30px);animation:up .9s cubic-bezier(.2,.8,.2,1) forwards}}",
  "#intro img{{width:min(300px,62vw);display:block;margin:0 auto;opacity:0;transform:scale(.92);filter:blur(6px);animation:logo 1.6s cubic-bezier(.2,.8,.2,1) .15s forwards}}"
  "@keyframes logo{{to{{opacity:1;transform:none;filter:none}}}}"
  "#intro .shine{{position:relative;overflow:hidden}}#intro .shine::after{{content:\"\";position:absolute;inset:0;"
  "background:linear-gradient(105deg,transparent 40%,rgba(255,255,255,.85) 50%,transparent 60%);transform:translateX(-120%);animation:sweep 1.4s 1.3s ease-in-out forwards}}"
  "@keyframes sweep{{to{{transform:translateX(120%)}}}}"),
 # nav: white over the video, then solid white with their logo
 ("nav.solid{{background:rgba(15,13,11,.78);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}}",
  "nav{{color:#fff}}nav.solid{{background:rgba(255,255,255,.94);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);color:var(--ink)}}"
  ".brand img{{height:52px;display:block;filter:brightness(0) invert(1);transition:filter .4s}}nav.solid .brand img{{filter:none}}"),
 (".links a:hover{{opacity:1;color:var(--gold2)}}", ".links a:hover{{opacity:1;color:var(--gold2)}}"),
 # hero: their walkthrough video
 (".slide{{position:absolute;inset:-4%;background-size:cover;background-position:center;opacity:0;animation:show 30s infinite}}",
  ".hero video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}.hero{{color:#fff}}"),
 (".hero p.lead{{max-width:46ch;color:#e6dccd;", ".hero p.lead{{max-width:46ch;color:#f1ece4;"),
 (".stat{{display:flex;gap:34px;flex-wrap:wrap;margin-top:42px;color:var(--muted);font-size:.9rem}}.stat b{{display:block;font-family:var(--head);font-size:2.2rem;color:var(--ink);font-weight:500}}",
  ".stat{{display:flex;gap:34px;flex-wrap:wrap;margin-top:42px;color:#e8e1d6;font-size:.9rem}}.stat b{{display:block;font-family:var(--head);font-size:2rem;color:#fff;font-weight:500}}"),
 (".hero h2 em{{color:var(--gold2)}}", ".hero h2 em{{color:#f3c64f}}"),
 (".btn.ghost{{background:transparent;color:var(--ink);border:1px solid var(--line);box-shadow:none}}",
  ".btn.ghost{{background:transparent;color:inherit;border:1px solid currentColor;box-shadow:none}}"),
 # the 3D stage in their light, warm palette
 ("background:radial-gradient(1200px 600px at 50% 40%,#2a2218 0%,#120f0c 60%,#0d0b09 100%)}}",
  "background:radial-gradient(1200px 600px at 50% 40%,#fffaf0 0%,#f1e8d8 60%,#e6dac5 100%)}}"),
 ("background:rgba(15,13,11,.6);backdrop-filter:blur(8px);font-size:.82rem}}", "background:rgba(255,255,255,.7);backdrop-filter:blur(8px);font-size:.82rem}}"),
 (".floors button.on{{background:var(--gold);color:#17120b;border-color:var(--gold)}}", ".floors button.on{{background:var(--gold);color:#fff;border-color:var(--gold)}}"),
 ("background:rgba(15,13,11,.88);border:1px solid var(--line);font-size:.85rem;white-space:nowrap;opacity:0;transition:opacity .2s}}",
  "background:rgba(255,255,255,.95);border:1px solid var(--line);font-size:.85rem;white-space:nowrap;opacity:0;transition:opacity .2s;box-shadow:0 12px 30px -12px rgba(0,0,0,.25)}}"),
 ("text-shadow:0 2px 10px rgba(0,0,0,.9);white-space:nowrap;transition:opacity .3s}}", "text-shadow:0 2px 10px rgba(0,0,0,.75);white-space:nowrap;transition:opacity .3s}}"),
 ("scene.fog = new THREE.Fog(0x0e0b09, 40, 90);", "scene.fog = new THREE.Fog(0xf1e8d8, 45, 95);"),
 ("new THREE.MeshStandardMaterial({{color: 0x1a1510, roughness: 1}})", "new THREE.MeshStandardMaterial({{color: 0xe9dfcc, roughness: 1}})"),
 ("color: accent, roughness: .4, metalness: .2, emissive: accent", "color: 0xc8960f, roughness: .35, metalness: .5, emissive: 0xe0b84a"),
 # suites, booking, reviews, overlay on light backgrounds
 (".suite{{position:relative;text-align:left;border-radius:22px;overflow:hidden;aspect-ratio:3/4;background:var(--panel);border:1px solid var(--line)}}",
  ".suite{{position:relative;text-align:left;border-radius:22px;overflow:hidden;aspect-ratio:3/4;background:var(--panel);border:1px solid var(--line);color:#fff}}"),
 (".suite small{{color:var(--a);text-transform:uppercase;letter-spacing:.2em;font-size:.68rem;font-weight:600;filter:brightness(1.6)}}",
  ".suite small{{color:#f3c64f;text-transform:uppercase;letter-spacing:.2em;font-size:.68rem;font-weight:600}}"),
 ("#book{{padding:110px 0;background:linear-gradient(180deg,#0f0d0b,#16120d)}}", "#book{{padding:110px 0;background:#fff;border-block:1px solid var(--line)}}"),
 (".card{{border:1px solid var(--line);border-radius:26px;padding:34px;background:rgba(255,255,255,.02)}}", ".card{{border:1px solid var(--line);border-radius:26px;padding:34px;background:var(--bg)}}"),
 (".save div{{flex:1;border-radius:18px;padding:18px;background:rgba(201,167,122,.08);border:1px solid var(--line)}}", ".save div{{flex:1;border-radius:18px;padding:18px;background:#fff;border:1px solid var(--line)}}"),
 (".save b{{font-family:var(--head);font-size:2rem;color:var(--gold2);font-weight:500;display:block}}", ".save b{{font-family:var(--head);font-size:1.6rem;color:var(--gold);font-weight:600;display:block}}"),
 (".cal span{{aspect-ratio:1;display:grid;place-items:center;border-radius:10px;font-size:.82rem;background:rgba(255,255,255,.04)}}", ".cal span{{aspect-ratio:1;display:grid;place-items:center;border-radius:10px;font-size:.82rem;background:#fff;border:1px solid var(--line)}}"),
 (".cal span.h{{color:var(--muted);background:none;font-size:.7rem}}.cal span.sel{{background:var(--gold);color:#17120b;font-weight:600}}", ".cal span.h{{color:var(--muted);background:none;border:0;font-size:.7rem}}.cal span.sel{{background:var(--gold);color:#fff;font-weight:600}}"),
 ("blockquote p{{font-family:var(--head);font-size:1.35rem;line-height:1.35;margin:12px 0}}", "blockquote p{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;line-height:1.35;margin:12px 0}}"),
 (".score{{font-family:var(--head);font-size:clamp(4rem,10vw,7rem);line-height:1;color:var(--gold2)}}", ".score{{font-family:var(--head);font-size:clamp(4rem,10vw,7rem);line-height:1;color:var(--gold)}}"),
 ("#room{{position:fixed;inset:0;z-index:40;display:grid;grid-template-columns:1.35fr 1fr;background:rgba(10,8,6,.96);", "#room{{position:fixed;inset:0;z-index:40;display:grid;grid-template-columns:1.35fr 1fr;background:#fff;"),
 ("#room .info p{{color:#d6cbbb;margin-bottom:14px}}", "#room .info p{{color:#4a4640;margin-bottom:14px}}"),
 ("border:1px solid var(--line);background:rgba(15,13,11,.7);font-size:1.3rem}}", "border:1px solid var(--line);background:#fff;font-size:1.3rem}}"),
 (".suite em{{font-style:normal;color:#d8cdbd;", ".suite em{{font-family:var(--body);font-style:normal;color:#eee6da;"),
 # markup: logo intro, logo in nav, video hero
 ("""<div id="intro"><div><h1>{"".join(f'<span style="animation-delay:{i * 45}ms">{"&nbsp;" if ch == " " else e(ch)}</span>' for i, ch in enumerate(name))}</h1><p>MOSELEY VILLAGE &middot; BIRMINGHAM</p></div></div>""",
  """<div id="intro"><div class="shine"><img src="logo.png" alt="{e(name)}"><p>MOSELEY VILLAGE &middot; BIRMINGHAM</p></div></div>"""),
 ("""<span class="brand">Moseley <i>Luxury</i> Stay</span>""", """<span class="brand"><img src="logo.png" alt="{e(name)}"></span>"""),
 ("""<header class="hero">{slides}<div class="wrap">""",
  """<header class="hero"><video autoplay muted loop playsinline preload="auto" poster="exterior.jpg"><source src="walkthrough.mp4" type="video/mp4"></video><div class="wrap">"""),
 ("""<h2>Every room,<br><em>its own story.</em></h2>""", """<h2>Distinctive luxury,<br><em>in Moseley Village.</em></h2>"""),
 ("setTimeout(() => document.getElementById(\"intro\").classList.add(\"out\"), 2300);", "setTimeout(() => document.getElementById(\"intro\").classList.add(\"out\"), 3100);"),
]
missing = [a[:60] for a, b in R if a not in t]
for a, b in R:
    t = t.replace(a, b)
f.write_text(t, encoding="utf-8")
print("missing:", missing)
