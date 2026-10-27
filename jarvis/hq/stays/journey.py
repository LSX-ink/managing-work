"""The scroll journey (owner, 24 Oct 2026: "learn from these and be better", after reels of AUREN, NOMA/Vantage and
Webild sites): a pinned, dark, full-screen section where scrolling drives their own walkthrough film forward and back,
a gold line runs along the bottom with your progress, one editorial line appears per space (big serif, bottom-left,
very little else on screen), and the end pulls back to a facts panel with Book direct.

Needs scrub.mp4 (the walkthrough re-encoded with a keyframe every few frames so it seeks smoothly: make_scrub()) and
journey.json {"chapters": [[start 0-1, "kicker", "line"], ...], "facts": [["label", "value"], ...], "end": "line"}.
Used by stays_page.py and ash_page.py; does nothing without both files. Only their real footage, nothing invented."""
import json, subprocess, sys
from html import escape as e
from pathlib import Path

CSS = """
.journey-s{position:relative;height:640vh;background:#0b0b0b;color:#f4efe6}
.journey-s .pin{position:sticky;top:0;height:100svh;overflow:hidden}
.journey-s video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(.82)}
.journey-s .shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35),transparent 30%,transparent 55%,rgba(0,0,0,.7))}
.journey-s .cap{position:absolute;left:clamp(20px,6vw,90px);bottom:clamp(70px,12vh,130px);max-width:min(720px,84vw)}
.journey-s .cap small{display:block;font:600 .72rem var(--body);letter-spacing:.34em;text-transform:uppercase;color:#e9c46a;margin-bottom:14px}
.journey-s .cap h2{font-family:var(--head);font-weight:500;font-size:clamp(2.2rem,5.6vw,5rem);line-height:1;letter-spacing:-.01em;margin:0;text-shadow:0 4px 40px rgba(0,0,0,.45)}
.journey-s .cap{transition:opacity .5s,transform .5s}.journey-s .cap.swap{opacity:0;transform:translateY(14px)}
.journey-s .line{position:absolute;left:0;bottom:34px;height:2px;width:0;background:linear-gradient(90deg,rgba(255,210,94,.2),#ffd25e);box-shadow:0 0 12px #ffcf5a,0 0 26px rgba(255,190,60,.6)}
.journey-s .line i{position:absolute;right:-6px;top:-5px;width:12px;height:12px;border-radius:50%;background:#fff6d8;box-shadow:0 0 14px #ffcf5a,0 0 28px #ffb020}
.journey-s .count{position:absolute;right:clamp(20px,6vw,90px);bottom:clamp(70px,12vh,130px);font:500 .8rem var(--body);letter-spacing:.3em;color:rgba(255,255,255,.75)}
.journey-s .end{position:absolute;inset:0;display:grid;place-items:center;background:rgba(8,8,8,.55);backdrop-filter:blur(6px);opacity:0;pointer-events:none;transition:opacity .8s}
.journey-s.done .end{opacity:1;pointer-events:auto}.journey-s.done .cap,.journey-s.done .count{opacity:0}
.journey-s .card{width:min(520px,88vw);padding:34px 34px 30px;border:1px solid rgba(255,255,255,.18);border-radius:22px;background:rgba(20,20,20,.72);text-align:left}
.journey-s .card h3{font-family:var(--head);font-weight:500;font-size:clamp(1.8rem,3.4vw,2.6rem);margin:6px 0 18px;color:#fff}
.journey-s .card dl{display:grid;grid-template-columns:1fr auto;gap:10px 18px;margin:0 0 24px;font-size:.92rem}
.journey-s .card dt{color:rgba(255,255,255,.65)}.journey-s .card dd{margin:0;color:#fff;text-align:right}
.journey-s .card .btn.ghost{color:#fff;border-color:rgba(255,255,255,.5)}
nav{transition:transform .5s,background .4s}body.in-journey nav{transform:translateY(-100%)}
@media (max-width:700px){.journey-s .count{top:22px;bottom:auto;right:20px}.journey-s .hint{top:52px}}
.journey-s .hint{position:absolute;left:50%;top:22px;transform:translateX(-50%);font:600 .68rem var(--body);letter-spacing:.3em;text-transform:uppercase;color:rgba(255,255,255,.7);transition:opacity .6s}
"""

JS = r"""<script>
(() => { const s = document.querySelector(".journey-s"); if (!s) return;
  const v = s.querySelector("video"), cap = s.querySelector(".cap"), k = cap.querySelector("small"), h = cap.querySelector("h2"),
        line = s.querySelector(".line"), count = s.querySelector(".count"), hint = s.querySelector(".hint"), C = JSON.parse(s.dataset.chapters);
  let cur = 0, target = 0, idx = -1, primed = false;
  // load the film only when the journey is close, so the page itself opens fast
  new IntersectionObserver((es, o) => { if (es[0].isIntersecting) { o.disconnect(); v.src = v.dataset.src; v.load(); } }, {rootMargin: "200% 0px"}).observe(s);
  const prime = () => { if (primed) return; primed = true; const p = v.play(); if (p && p.then) p.then(() => v.pause()).catch(() => {}); };
  addEventListener("touchstart", prime, {once: true, passive: true}); addEventListener("wheel", prime, {once: true, passive: true});
  function progress() { const r = s.getBoundingClientRect(); return Math.min(1, Math.max(0, -r.top / (r.height - innerHeight))); }
  function onScroll() { const p = progress(); if (v.duration) target = Math.min(p / .9, 1) * (v.duration - .05);
    line.style.width = (p * 100) + "%"; const r2 = s.getBoundingClientRect(); document.body.classList.toggle("in-journey", r2.top <= 0 && r2.bottom >= innerHeight * .6); s.classList.toggle("done", p > .9); hint.style.opacity = p > .02 ? 0 : 1;
    let i = 0; C.forEach((c, n) => { if (p / .9 >= c[0]) i = n; });
    if (i !== idx) { idx = i; cap.classList.add("swap"); setTimeout(() => { k.textContent = C[i][1]; h.textContent = C[i][2]; cap.classList.remove("swap"); }, 260);
      count.textContent = String(i + 1).padStart(2, "0") + " / " + String(C.length).padStart(2, "0"); } }
  (function tick() { cur += (target - cur) * .18; if (v.readyState >= 1 && Math.abs(v.currentTime - cur) > .04) { try { v.currentTime = cur; } catch (e) {} } requestAnimationFrame(tick); })();
  addEventListener("scroll", onScroll, {passive: true}); v.addEventListener("loadedmetadata", onScroll); onScroll();
})();
</script>"""


def make_scrub(folder: Path) -> bool:
    """scrub.mp4: the walkthrough with a keyframe every 6 frames, 1280 wide, no sound, so it seeks smoothly on scroll."""
    src, out = folder / "walkthrough.mp4", folder / "scrub.mp4"
    if not src.exists():
        return False
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return True
    sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
    from tiktokstudio_video import ffmpeg
    r = subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale=1280:-2,fps=30", "-c:v", "libx264", "-preset", "slow",
                        "-crf", "27", "-g", "6", "-keyint_min", "6", "-sc_threshold", "0", "-an", "-movflags", "+faststart", str(out)])
    return r.returncode == 0 and out.exists()


def add_journey(html: str, out: Path, book: str = "#book") -> str:
    f = out / "journey.json"
    if not f.exists() or not make_scrub(out):
        return html
    j = json.load(open(f, encoding="utf-8"))
    poster = j.get("poster", "exterior.jpg")
    facts = "".join(f"<dt>{e(a)}</dt><dd>{e(b)}</dd>" for a, b in j.get("facts", []))
    sec = (f'<section class="journey-s" data-chapters="{e(json.dumps(j["chapters"]))}"><div class="pin">'
           f'<video muted playsinline preload="auto" poster="{e(poster)}" data-src="scrub.mp4"></video><div class="shade"></div>'
           '<p class="hint">Scroll to walk through</p><div class="cap"><small></small><h2></h2></div><p class="count"></p><div class="line"><i></i></div>'
           f'<div class="end"><div class="card"><p class="kicker" style="color:#e9c46a">The stay</p><h3>{e(j.get("end", "Your stay starts here."))}</h3><dl>{facts}</dl>'
           f'<a class="btn" href="{e(book)}">Book direct</a>&nbsp; <a class="btn ghost" href="#house">Explore in 3D</a></div></div></div></section>')
    anchor = '<section class="story"' if '<section class="story"' in html else '<section id="house">'
    html = html.replace(anchor, sec + "\n" + anchor, 1)
    html = html.replace("</style>", CSS + "</style>", 1)
    return html.replace("</body>", JS + "</body>", 1)
