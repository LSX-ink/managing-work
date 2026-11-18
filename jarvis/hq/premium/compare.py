"""The before/after and "what your site is costing you" sections on every premium mock-up (owner, 26 Oct 2026: "how come you
removed the before after, and what's wrong with their site and what we can do better?").

Their current homepage (before.jpg) beside this design (after.jpg), both on a phone, with a drag slider; then each real
problem we found on their site in plain English, what this design does instead, and Google's phone speed score for both.
Findings come from config.json "audit" {"title", "fixes": [[today, this design]], "speed": [theirs, ours]}."""
import shutil
from html import escape as e
from pathlib import Path

PLAIN = {  # the checker's short labels, said the way an owner would understand them
    "No main heading.": "Your homepage has no main heading, so Google can't tell what the page is about.",
    "Google can't read the business details.": "Google can't read your hours, address and services from your site.",
    "Weak page title.": "Your page title doesn't say who you are or where, so you show up less in searches.",
    "Phone number isn't tap-to-call.": "On a phone, customers can't tap your number to call you.",
    "No share preview.": "When your link is shared on WhatsApp or Instagram, it shows a blank card.",
    "Built with very old tech.": "Your site is built on very old technology, so it looks and feels dated.",
    "Heavy page.": "Your homepage is heavy, so it loads slowly on phones.",
    "No Google description.": "There's no description for Google, so searches show a random snippet of your page.",
}

CSS = """
.kx{padding:110px 0;background:var(--ba-bg);color:var(--ba-ink)}.kx .w{width:min(1180px,100% - 40px);margin:0 auto}
.kx .kk{font:600 .74rem var(--body);letter-spacing:.32em;text-transform:uppercase;color:var(--gold);margin:0 0 14px}
.kx h2{font:500 clamp(2rem,4.4vw,3.4rem)/1.05 var(--head);margin:0 0 16px}.kx .sub{color:var(--ba-soft);max-width:620px;margin:0 0 40px}
.kx .grid{display:grid;grid-template-columns:auto 1fr;gap:60px;align-items:start}
.ba{position:relative;width:min(340px,82vw);aspect-ratio:600/1169;border-radius:38px;overflow:hidden;border:10px solid #111;box-shadow:0 40px 90px rgba(0,0,0,.35);background:#111;--x:50%;user-select:none}
.ba img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:top;pointer-events:none}.ba .af{clip-path:inset(0 0 0 var(--x))}
.ba .ln{position:absolute;top:0;bottom:0;left:var(--x);width:3px;margin-left:-1.5px;background:var(--gold)}.ba .kn{position:absolute;top:50%;left:var(--x);width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;background:var(--gold);color:#111;display:grid;place-items:center;font:700 15px var(--body)}
.ba .tg{position:absolute;top:14px;padding:5px 10px;border-radius:999px;font:700 .62rem var(--body);letter-spacing:.16em;text-transform:uppercase}.ba .tg.b{left:12px;background:rgba(0,0,0,.7);color:#fff}.ba .tg.a{right:12px;background:var(--gold);color:#111}
.ba{cursor:ew-resize;touch-action:pan-y}.ba input{position:absolute;inset:0;width:100%;height:100%;opacity:0;margin:0;pointer-events:none}
.ba-cap{font-size:.82rem;color:var(--ba-soft);margin-top:14px;text-align:center;width:min(340px,82vw)}
.fx{list-style:none;margin:0;padding:0;display:grid;gap:14px}.fx li{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:20px 22px;border-radius:18px;background:color-mix(in srgb,var(--ba-ink) 5%,transparent);border:1px solid color-mix(in srgb,var(--ba-ink) 10%,transparent)}
.fx small{display:block;font:700 .62rem var(--body);letter-spacing:.2em;text-transform:uppercase;margin-bottom:6px}.fx .t small{color:#d9534f}.fx .n small{color:var(--gold)}
.fx .t{color:var(--ba-soft)}.fx .n{font-weight:500}
.spd{display:flex;gap:16px;margin:0 0 26px;flex-wrap:wrap}.spd div{flex:1;min-width:150px;padding:22px;border-radius:18px;background:color-mix(in srgb,var(--ba-ink) 5%,transparent)}
.spd b{display:block;font:500 3rem/1 var(--head)}.spd .bad b{color:#d9534f}.spd .good b{color:var(--gold)}.spd span{font-size:.8rem;color:var(--ba-soft)}
.kx .more{margin-top:26px;color:var(--ba-soft);font-size:.92rem}
.kx.scene::after{content:none}.kx.scene .w{position:relative;z-index:2}main .kx{padding:100px 7vw}main .kx .w{width:100%}main .kx .grid{grid-template-columns:1fr;gap:40px}.kx h2{overflow-wrap:anywhere}
@media (max-width:900px){.kx .grid{grid-template-columns:1fr;justify-items:center}.fx li{grid-template-columns:1fr}}
"""
JS = """<script>document.querySelectorAll(".ba").forEach(b=>{const r=b.querySelector("input"),s=v=>{v=Math.max(0,Math.min(100,v));b.style.setProperty("--x",v+"%");r.value=v};r.addEventListener("input",()=>s(+r.value));let d=false;const at=ev=>{const q=b.getBoundingClientRect();s((ev.clientX-q.left)/q.width*100)};b.addEventListener("pointerdown",ev=>{d=true;b.setPointerCapture(ev.pointerId);at(ev)});b.addEventListener("pointermove",ev=>{if(d)at(ev)});b.addEventListener("pointerup",()=>d=false);b.addEventListener("pointercancel",()=>d=false);s(50);new IntersectionObserver((es,o)=>{if(es[0].isIntersecting){o.disconnect();let t=0;const w=()=>{if(d)return;t+=.02;s(50+38*Math.sin(t*Math.PI));if(t<2)requestAnimationFrame(w);else s(50)};setTimeout(w,500)}},{threshold:.4}).observe(b)});</script>"""


def section(c: dict) -> str:
    au = c.get("audit") or {}
    fixes = "".join(f'<li><div class="t"><small>Today</small>{e(PLAIN.get(t, t))}</div><div class="n"><small>This design</small>{e(n)}</div></li>'
                    for t, n in au.get("fixes", []))
    spd = au.get("speed")
    speed = (f'<div class="spd"><div class="bad"><b>{spd[0]}<small style="font-size:1rem">/100</small></b><span>Your site\'s Google speed score on phones today</span></div>'
             f'<div class="good"><b>{spd[1]}<small style="font-size:1rem">/100</small></b><span>This design, tested the same way</span></div></div>') if spd else ""
    title = au.get("title") or "What this design does better."
    return (f'<section class="kx" id="compare"><div class="w"><p class="kk">Before &amp; after</p><h2>Your website today, and what it could be.</h2>'
            f'<p class="sub">Drag the handle. On the left, your current homepage as it looks on a phone right now. On the right, this design.</p>'
            f'<div class="grid"><div><div class="ba"><img src="before.jpg" alt="Your current website"><img class="af" src="after.jpg" alt="This design">'
            f'<span class="ln"></span><span class="kn">&#8596;</span><span class="tg b">Before</span><span class="tg a">After</span>'
            f'<input type="range" min="0" max="100" value="50" aria-label="Compare before and after"></div><p class="ba-cap">Both shown on a phone.</p></div>'
            f'<div><p class="kk">A note for {e(c["short"])} from Kinetic Web Designs</p><h2 style="font-size:clamp(1.6rem,3vw,2.4rem)">{e(title)}</h2>{speed}<ul class="fx">{fixes}</ul>'
            f'<p class="more">Plus everything above: your own colours and logo, your photos, prices and reviews, all moving, built to book you more customers.</p></div></div></div></section>\n')


def add(html: str, c: dict, src: Path, out: Path) -> str:
    """Put the section in when both pictures exist (before.jpg from their site, after.jpg of this design)."""
    if c.get("no_compare") or not ((src / "before.jpg").exists() and (src / "after.jpg").exists()):  # no_compare: already sent as it was
        return html
    shutil.copy(src / "before.jpg", out / "before.jpg"); shutil.copy(src / "after.jpg", out / "after.jpg")
    layout = c.get("layout", "atelier")
    vars_ = ("--ba-bg:color-mix(in srgb,var(--text) 4%,var(--paper));--ba-ink:var(--text);--ba-soft:var(--soft)" if layout == "editorial"
             else "--ba-bg:var(--panel);--ba-ink:var(--ink);--ba-soft:var(--muted)")
    sec = section(c)
    if layout == "cinema":  # full-screen scenes: give it its own scrollable scene
        sec = sec.replace('<section class="kx" id="compare">', '<section class="kx scene" id="compare" style="height:auto;min-height:100svh;display:block;scroll-snap-align:start">')
        anchor = '<section class="scene" id="s6">'
    elif layout == "split":
        sec = sec.replace('<section class="kx" id="compare">', '<section class="kx" id="compare" data-m="2" data-t="Before &amp; after">')
        anchor = '<section id="visit"'
    else:
        anchor = '<section id="visit"' if '<section id="visit"' in html else '<section class="visit" id="visit">'
    if anchor not in html:
        anchor = "<footer"
    html = html.replace(anchor, sec + anchor, 1)
    html = html.replace("</style>", f":root{{{vars_}}}" + CSS + "</style>", 1)
    return html.replace("</body>", JS + "</body>", 1)
