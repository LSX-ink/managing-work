"""The "one line, an entire home" opening (owner, 24 Oct 2026, from a reel): the hero opens on the host's building as a
model (build/3.jpg), a glowing gold line draws itself along the ground to their real front door, then the camera dives
through the door into the walkthrough video ("Your journey starts here."). A strip of their real room photos runs
along the bottom; tapping one opens that room.

Needs door.json next to the page: {"path": [[x%, y%], ...]} on build/3.jpg, ending at the door. Optional "image",
"line1", "line2". Used by stays_page.py and ash_page.py; does nothing when door.json is missing."""
import json
from html import escape as e
from pathlib import Path

CSS = """
.door{position:absolute;inset:0;z-index:6;overflow:hidden;background:#f3efe8;transition:opacity 1.2s ease}
.door img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform-origin:var(--ox) var(--oy);transition:transform 1.6s cubic-bezier(.6,0,.2,1),filter 1.6s}
.door svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;transform-origin:var(--ox) var(--oy);transition:transform 1.6s cubic-bezier(.6,0,.2,1),opacity .6s}
.door path{fill:none;stroke:#ffd25e;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 6px #ffcf5a) drop-shadow(0 0 16px rgba(255,190,60,.7))}
.door circle{fill:#fff6d8;filter:drop-shadow(0 0 10px #ffcf5a) drop-shadow(0 0 22px #ffb020);opacity:0;transition:opacity .4s}
.door .t{position:absolute;left:0;right:0;top:15vh;text-align:center;z-index:2;padding:0 20px;font-family:var(--head);color:#22201c;letter-spacing:.08em;text-transform:uppercase;font-size:clamp(1.4rem,3.4vw,2.6rem);transition:opacity .6s}
.door .t span{display:inline-block;padding:10px 22px;border-radius:14px;background:rgba(250,247,241,.82);backdrop-filter:blur(8px)}
.door .t small{display:block;font-family:var(--body);letter-spacing:.32em;font-size:.72rem;color:#6b665d;margin-top:10px;text-transform:uppercase}
.door .go{position:absolute;left:50%;bottom:150px;transform:translateX(-50%);z-index:3;padding:12px 22px;border-radius:999px;border:1px solid rgba(34,32,28,.35);background:rgba(255,255,255,.75);backdrop-filter:blur(6px);font:600 .8rem var(--body);letter-spacing:.2em;text-transform:uppercase;color:#22201c;cursor:pointer;opacity:0;transition:opacity .6s}
.door.lit .go,.door.lit circle{opacity:1}
.door.in img,.door.in svg{transform:scale(7)}.door.in img{filter:brightness(1.4) blur(2px)}.door.in .t,.door.in .go{opacity:0}.door.gone{opacity:0;pointer-events:none}
.hero .journey{position:absolute;left:0;right:0;top:16vh;text-align:center;z-index:5;font-family:var(--head);font-size:clamp(1.6rem,4vw,3.2rem);color:#fff;text-shadow:0 2px 30px rgba(0,0,0,.5);opacity:0;transition:opacity 1s;pointer-events:none}
.hero.journeying .journey{opacity:1}.hero.dooring .wrap,.hero.journeying .wrap{opacity:0}.hero .wrap{transition:opacity 1s}
.hero .strip{position:absolute;left:0;right:0;bottom:0;z-index:7;display:flex;gap:8px;padding:10px 12px;overflow-x:auto;background:linear-gradient(180deg,transparent,rgba(0,0,0,.35))}
.hero .strip button{flex:0 0 auto;width:min(180px,28vw);aspect-ratio:16/10;border-radius:10px;background-size:cover;background-position:center;border:2px solid rgba(255,255,255,.65);cursor:pointer;transition:transform .3s}
.hero .strip button:hover{transform:translateY(-3px)}
.hero.has-strip .wrap{padding-bottom:calc(9vh + 110px)}
.hero.has-strip h2{font-size:clamp(2.2rem,5vw,4.3rem);max-width:17ch;margin:12px 0 16px}
@media (max-width:700px){.door .go{bottom:120px}.hero .strip button{width:38vw}.hero.has-strip .wrap{padding-bottom:calc(5vh + 92px)}.hero.has-strip h2{font-size:clamp(1.9rem,8.4vw,2.5rem);margin:8px 0 10px}.hero.has-strip .lead{font-size:.88rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:12px}.hero.has-strip .stat{margin-top:14px}.hero.has-strip .stat b{font-size:1.25rem}}
"""

JS = """<script>
(() => { const d = document.querySelector(".door"); if (!d) return;
  const hero = d.closest(".hero"), img = d.querySelector("img"), svg = d.querySelector("svg"), P = JSON.parse(d.dataset.path);
  hero.classList.add("dooring");
  function layout() { const cw = d.clientWidth, ch = d.clientHeight, iw = img.naturalWidth || 1920, ih = img.naturalHeight || 1080;
    const s = Math.max(cw / iw, ch / ih), ox = (cw - iw * s) / 2, oy = (ch - ih * s) / 2, pts = P.map(([x, y]) => [ox + x / 100 * iw * s, oy + y / 100 * ih * s]);
    svg.setAttribute("viewBox", `0 0 ${cw} ${ch}`);
    const path = svg.querySelector("path"); path.setAttribute("d", "M" + pts.map(p => p.join(" ")).join(" L"));
    const [dx, dy] = pts[pts.length - 1], c = svg.querySelector("circle"); c.setAttribute("cx", dx); c.setAttribute("cy", dy);
    d.style.setProperty("--ox", dx + "px"); d.style.setProperty("--oy", dy + "px"); return path; }
  let entered = false;
  function enter() { if (entered) return; entered = true; d.classList.add("in");
    setTimeout(() => { d.classList.add("gone"); hero.classList.remove("dooring"); hero.classList.add("journeying");
      const v = hero.querySelector("video");
      if (v && d.dataset.flyin) {   // a real drone fly-in plays once, then the walkthrough carries on looping
        const loop = v.querySelector("source") ? v.querySelector("source").src : v.src;
        v.loop = false; v.src = d.dataset.flyin; v.play().catch(() => {});
        v.addEventListener("ended", () => { v.src = loop; v.loop = true; v.play().catch(() => {}); }, {once: true});
      } else if (v) { try { v.currentTime = 0; v.play(); } catch (e) {} } }, 1500);
    setTimeout(() => { hero.classList.remove("journeying"); d.remove(); }, d.dataset.flyin ? 11500 : 5200); }
  function start() { const path = layout(), L = path.getTotalLength();
    path.style.strokeDasharray = L; path.style.strokeDashoffset = L; path.getBoundingClientRect();
    path.style.transition = "stroke-dashoffset 2.6s cubic-bezier(.5,0,.2,1)"; path.style.strokeDashoffset = 0;
    setTimeout(() => d.classList.add("lit"), 2600); setTimeout(enter, 8000); }
  const go = () => (img.complete ? start() : img.addEventListener("load", start, {once: true}));
  setTimeout(go, document.getElementById("intro") ? 3200 : 300);
  addEventListener("resize", () => { if (!entered) layout(); });
  d.querySelector(".go").addEventListener("click", enter);
  addEventListener("wheel", enter, {once: true, passive: true}); addEventListener("touchmove", enter, {once: true, passive: true});
  document.querySelectorAll(".hero .strip button").forEach(b => b.addEventListener("click", () => {
    const card = document.querySelector(`.suite[data-slug="${b.dataset.slug}"]`); if (card) card.click(); }));
})();
</script>"""


def add_door(html: str, out: Path, rooms: list) -> str:
    """rooms: [(slug, cover)] for the photo strip."""
    f = out / "door.json"
    if not f.exists():
        return html
    dj = json.load(open(f, encoding="utf-8"))
    img = dj.get("image", "build/3.jpg")
    if not (out / img).exists():
        return html
    l1, l2 = dj.get("line1", "One line. An entire home."), dj.get("line2", "Your journey starts here.")
    fly = ' data-flyin="flyin.mp4"' if (out / "flyin.mp4").exists() else ""
    door = (f'<div class="door"{fly} data-path="{e(json.dumps(dj["path"]))}"><img src="{e(img)}" alt="">'
            '<svg><path/><circle r="7"/></svg>'
            f'<p class="t"><span>{e(l1)}<small>Follow the light</small></span></p><button class="go" type="button">Step inside</button></div>'
            f'<p class="journey">{e(l2)}</p>')
    strip = '<div class="strip">' + "".join(f'<button type="button" data-slug="{e(s)}" style="background-image:url({e(c)})" aria-label="Open room"></button>'
                                            for s, c in rooms[:8]) + "</div>"
    html = html.replace('<header class="hero">', '<header class="hero has-strip">' + door + strip, 1)
    html = html.replace("</style>", CSS + "</style>", 1)
    return html.replace("</body>", JS + "</body>", 1)
