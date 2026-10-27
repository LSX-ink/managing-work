"""Before and after (owner, 25 Oct 2026: "show the before and after if they already have a website"): their current
homepage beside our concept, with a drag slider. Only for hosts with a real website of their own (not just an Airbnb
or Booking.com page). shoot() makes before.jpg (their live homepage) and after.jpg (our page, once the door opening has
played); add_compare() puts the section on the page when both images exist.

Usage: python beforeafter.py <folder> <their website> <our page url>"""
import asyncio, json, sys
from html import escape as e
from pathlib import Path

CSS = """
#compare{padding:110px 0 40px}#compare .head p{color:var(--muted)}
.ba{position:relative;margin-top:34px;border-radius:22px;overflow:hidden;border:1px solid var(--line);aspect-ratio:16/10;max-width:100%;user-select:none;background:#ddd;--x:50%}
.ba img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:top;pointer-events:none}
.ba .after{clip-path:inset(0 0 0 var(--x))}
.ba .bar{position:absolute;top:0;bottom:0;left:var(--x);width:3px;margin-left:-1.5px;background:#fff;box-shadow:0 0 18px rgba(0,0,0,.35)}
.ba .knob{position:absolute;top:50%;left:var(--x);width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:#fff;box-shadow:0 6px 24px rgba(0,0,0,.3);display:grid;place-items:center;font:700 14px var(--body);color:#222;cursor:ew-resize}
.ba .tag{position:absolute;top:16px;padding:7px 12px;border-radius:999px;font:600 .72rem var(--body);letter-spacing:.2em;text-transform:uppercase}
.ba .tag.b{left:16px;background:rgba(0,0,0,.65);color:#fff}.ba .tag.a{right:16px;background:var(--gold);color:#fff}
.ba{cursor:ew-resize;touch-action:pan-y}.ba input{position:absolute;inset:0;width:100%;height:100%;opacity:0;margin:0;pointer-events:none}
@media (max-width:700px){.ba{aspect-ratio:4/3}.ba .tag{top:10px;padding:5px 9px;font-size:.6rem}.ba .tag.b{left:10px}.ba .tag.a{right:10px}.ba .knob{width:38px;height:38px;margin:-19px 0 0 -19px}}
"""
JS = """<script>document.querySelectorAll(".ba").forEach(b=>{const r=b.querySelector("input"),s=v=>{v=Math.max(0,Math.min(100,v));b.style.setProperty("--x",v+"%");r.value=v};r.addEventListener("input",()=>s(+r.value));let d=false;const at=ev=>{const q=b.getBoundingClientRect();s((ev.clientX-q.left)/q.width*100)};b.addEventListener("pointerdown",ev=>{d=true;b.setPointerCapture(ev.pointerId);at(ev)});b.addEventListener("pointermove",ev=>{if(d)at(ev)});b.addEventListener("pointerup",()=>d=false);b.addEventListener("pointercancel",()=>d=false);s(50);new IntersectionObserver((es,o)=>{if(es[0].isIntersecting){o.disconnect();let t=0;const w=()=>{if(d)return;t+=.02;s(50+38*Math.sin(t*Math.PI));if(t<2)requestAnimationFrame(w);else s(50)};setTimeout(w,500)}},{threshold:.4}).observe(b)});</script>"""


def add_compare(html: str, out: Path) -> str:
    if not ((out / "before.jpg").exists() and (out / "after.jpg").exists()):
        return html
    p = json.load(open(out / "place.json", encoding="utf-8"))
    site = (p.get("website") or "").replace("http://", "").replace("https://", "").rstrip("/")
    sec = ('<section id="compare"><div class="wrap"><div class="head"><div><p class="kicker reveal">Before and after</p>'
           '<h2 class="reveal">Your website today,<br>and what it could be.</h2></div>'
           f'<p class="reveal">Drag the handle. On the left, your current homepage ({e(site)}) as it looks right now. On the right, this new design.</p></div>'
           '<div class="ba"><img src="before.jpg" alt="Your current website"><img class="after" src="after.jpg" alt="The new design">'
           '<span class="bar"></span><span class="knob">&#8596;</span><span class="tag b">Before</span><span class="tag a">After</span>'
           '<input id="ba-range" type="range" min="0" max="100" value="50" aria-label="Compare before and after"></div></div></section>\n')
    anchor = '<section id="suites">'
    html = html.replace(anchor, sec + anchor, 1)
    html = html.replace("</style>", CSS + "</style>", 1)
    return html.replace("</body>", JS + "</body>", 1)


async def shoot(folder: Path, site: str, ours: str) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--autoplay-policy=no-user-gesture-required"])
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        await pg.goto(site, wait_until="domcontentloaded", timeout=45000); await pg.wait_for_timeout(12000)  # hero videos load slowly
        home = pg.url
        for label in ("Reject all", "Reject", "Decline", "Only necessary", "Necessary only"):   # cookie banners: decline, so the real page shows
            for role in ("button", "link"):
                btn = pg.get_by_role(role, name=label, exact=True)
                if await btn.count() and await btn.first.is_visible():
                    try:
                        await btn.first.click(timeout=2000); await pg.wait_for_timeout(1500)
                    except Exception:
                        continue
                    if pg.url.split("/")[2] != home.split("/")[2]:   # it was a link off their site: come back
                        await pg.goto(home, wait_until="domcontentloaded"); await pg.wait_for_timeout(3000)
                    break
        await pg.screenshot(path=str(folder / "before.jpg"), type="jpeg", quality=80)
        await pg.goto(ours, wait_until="domcontentloaded"); await pg.wait_for_timeout(8500)
        if await pg.locator(".door .go").count():
            await pg.click(".door .go"); await pg.wait_for_timeout(13000)
        await pg.screenshot(path=str(folder / "after.jpg"), type="jpeg", quality=80)
        await b.close()


if __name__ == "__main__":
    asyncio.run(shoot(Path(sys.argv[1]), sys.argv[2], sys.argv[3]))
