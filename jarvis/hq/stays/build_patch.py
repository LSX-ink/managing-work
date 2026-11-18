"""The "from a line to a home" upgrades (owner, 24 Oct 2026, after a reel of a house building itself as you scroll):

A. Scroll story: when the host's folder has build/1.jpg..4.jpg (Higgsfield stages made from their own exterior photo:
   plan, white model, materials, lit cutaway), a pinned full-screen section after the hero cross-fades through the
   stages and ends on their real photo, with a headline per stage. build.json {"lines": [...5 headlines]} overrides.
B. The 3D house builds itself: the first time it scrolls into view, every wall and piece of furniture grows up out of
   the floor plan, floor by floor, while the camera flies in.
Applies to stays_page.py (all stays concepts) and ash_page.py. Idempotent."""
from pathlib import Path

HERE = Path(__file__).parent

GROW_JS = '''// the house builds itself out of the floor plan the first time it is seen
const grow = [];
function collectGrow(root) {{ root.traverse(o => {{ if (!o.isMesh || !o.geometry || !o.geometry.parameters) return;
  const h = o.geometry.parameters.height; if (!(h > .05) || o.geometry.type === "PlaneGeometry") return;
  grow.push({{o, y: o.position.y, d: Math.max(0, o.position.y) * .25 + Math.random() * .15}}); o.scale.y = .001; o.position.y = o.position.y * .001; }}); }}
let growT = -1;
function growTick(dt) {{ if (growT < 0 || growT > 2.2) return; growT += dt;
  for (const g of grow) {{ const k = Math.min(1, Math.max(.001, (growT - g.d) / .9)), e = 1 - Math.pow(1 - k, 3); g.o.scale.y = e; g.o.position.y = g.y * e; }} }}
'''

STORY_CSS = (".story{position:relative;height:520vh;background:#0d0d0d}.story .pin{position:sticky;top:0;height:100svh;overflow:hidden}"
             ".story .st{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.04);transition:opacity .25s linear}"
             ".story .cap{position:absolute;left:0;right:0;top:12vh;text-align:center;z-index:3;padding:0 24px;pointer-events:none}"
             ".story .cap h2{font-family:var(--head);font-weight:500;font-size:clamp(2rem,5vw,4.2rem);line-height:1.05;color:#1d1d1b;text-shadow:0 1px 30px rgba(255,255,255,.6);transition:opacity .4s,transform .4s}"
             ".story .cap p{font-size:.8rem;letter-spacing:.32em;text-transform:uppercase;color:#6b6760;margin-bottom:10px}"
             ".story.dark .cap h2{color:#fff;text-shadow:0 2px 30px rgba(0,0,0,.6)}.story.dark .cap p{color:#e7e2d8}"
             ".story .dots{position:absolute;right:22px;top:50%;transform:translateY(-50%);display:grid;gap:10px;z-index:3}"
             ".story .dots i{width:7px;height:7px;border-radius:50%;background:rgba(120,120,120,.45);transition:background .3s,transform .3s}.story .dots i.on{background:var(--gold);transform:scale(1.5)}")

STORY_JS = r"""<script>
(() => { const s = document.querySelector(".story"); if (!s) return;
  const st = [...s.querySelectorAll(".st")], dots = [...s.querySelectorAll(".dots i")], h = s.querySelector(".cap h2"), k = s.querySelector(".cap p"), lines = JSON.parse(s.dataset.lines);
  let cur = -1;
  function draw() { const r = s.getBoundingClientRect(), p = Math.min(.9999, Math.max(0, -r.top / (r.height - innerHeight))), f = p * st.length, i = Math.floor(f), t = f - i;
    st.forEach((el, n) => { el.style.opacity = n < i ? 0 : n === i ? 1 : n === i + 1 ? Math.max(0, (t - .55) / .45) : 0; el.style.transform = `scale(${1.06 - .06 * (n === i ? t : 0)})`; });
    if (i !== cur) { cur = i; h.style.opacity = 0; setTimeout(() => { h.textContent = lines[i] || ""; k.textContent = `${i + 1} / ${st.length}`; h.style.opacity = 1; }, 180);
      dots.forEach((d, n) => d.classList.toggle("on", n === i)); s.classList.toggle("dark", i >= st.length - 2); } }
  addEventListener("scroll", draw, {passive: true}); addEventListener("resize", draw); draw(); })();
</script>"""


def patch(name: str, loop_anchor: str) -> None:
    f = HERE / name
    t = f.read_text(encoding="utf-8")
    if "growTick" in t:
        print(name, "already has the build-up"); return
    R = [("introIO.observe(stage);", GROW_JS + "collectGrow(scene);\nintroIO.observe(stage);"),
         ("introIO.disconnect();\n", "introIO.disconnect(); growT = 0;\n"),
         (loop_anchor, loop_anchor + "\n  growTick(dt);")]
    for a, b in R:
        assert a in t, (name, a[:60])
        t = t.replace(a, b, 1)
    f.write_text(t, encoding="utf-8")
    print(name, "3D build-up added")


if __name__ == "__main__":
  patch("stays_page.py", "  const dt = Math.min(.05, clock.getDelta());")
  patch("ash_page.py", "  const dt = Math.min(.05, clock.getDelta());")

# A. the scroll story, inserted after the hero when build/ images exist (post-processing in stays_page.py)
f = HERE / "stays_page.py"
t = f.read_text(encoding="utf-8")
if "STORY_CSS" not in t:
    anchor = '(OUT / "index.html").write_text(html, encoding="utf-8")\nprint("written", len(html) // 1024, "KB")'
    add = '''STORY_CSS = ''' + repr(STORY_CSS) + '''
STORY_JS = ''' + repr(STORY_JS) + '''
if (OUT / "build" / "1.jpg").exists():
    bj = json.load(open(OUT / "build.json", encoding="utf-8")) if (OUT / "build.json").exists() else {}
    stages = [f"build/{i}.jpg" for i in range(1, 5) if (OUT / "build" / f"{i}.jpg").exists()]
    final = json.load(open(OUT / "hero.json"))[0] if (OUT / "hero.json").exists() else "exterior.jpg"
    stages.append(bj.get("final", final))
    lines = bj.get("lines") or ["It starts with a line.", "Then it takes shape.", "Material, texture, detail.", "Lit from within.", f"Welcome to {name}."]
    story = (f'<section class="story" data-lines="{e(json.dumps(lines[:len(stages)]))}"><div class="pin">'
             + "".join(f'<div class="st" style="background-image:url({s})"></div>' for s in stages)
             + '<div class="cap"><p></p><h2></h2></div><div class="dots">' + "<i></i>" * len(stages) + "</div></div></section>")
    html = html.replace("</style>", STORY_CSS + "</style>", 1)
    html = html.replace('<section id="house">', story + "\\n" + '<section id="house">', 1)
    html = html.replace("</body>", STORY_JS + "</body>", 1)
'''
    assert anchor in t
    t = t.replace(anchor, add + anchor, 1)
    f.write_text(t, encoding="utf-8")
    print("stays_page.py scroll story added")
