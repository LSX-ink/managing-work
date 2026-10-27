"""The 15-reel website series (Kinetic content calendar), made from the example sites on kineticwebdesigns.co.uk: each
look is opened in its phone frame, the frame fills the screen, and it scrolls top to bottom while a CDP screencast
records it; ffmpeg turns that into a 1080x1920 reel with the series title and a "Comment SITE" end card. No credits.

Usage: python series_reels.py <out folder> [numbers ...]"""
import asyncio, base64, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
from tiktokstudio_video import ffmpeg  # noqa: E402

SERIES = [  # (n, title, tab, look)
    (1, "Pilates studio", "wellness", "pilates"), (2, "Spa & massage", "wellness", "spa"), (3, "Beauty & skincare", "beauty", "bloom"),
    (4, "Wigs", "wigs", "elegant"), (5, "Outerwear", "fashion", "drift"), (6, "Night café", "drinks", "nocturne"),
    (7, "Roastery", "drinks", "playful"), (8, "Desserts", "desserts", "velvet"), (9, "Honey", "honey", "hive"),
    (10, "Plumber", "trades", "bold"), (11, "Carpenter", "trades", "crafted"), (12, "Painter & decorator", "trades", "splash"),
    (13, "Window cleaner", "trades", "fresh"), (14, "Tool hire", "trades", "clean"), (15, "Grooming lounge barber", "barber", "gentry"),
]
FONT = "fontfile='C\\:/Windows/Fonts/segoeuib.ttf'"


def txt(t, size, y, start, end, box=True):
    t = t.replace("'", "\u2019").replace(":", r"\:")
    b = ":box=1:boxcolor=black@0.55:boxborderw=24" if box else ":shadowcolor=black@0.8:shadowx=2:shadowy=2"
    return f"drawtext={FONT}:text='{t}':fontsize={size}:fontcolor=white:x=(w-text_w)/2:y={y}{b}:enable='between(t,{start},{end})'"


async def record(b, n, title, tab, look, out: Path) -> Path:
    tmp = out / f"_f{n:02d}"; tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*"): f.unlink()
    ctx = await b.new_context(viewport={"width": 432, "height": 768}, device_scale_factor=2.5, is_mobile=True, has_touch=True)
    pg = await ctx.new_page()
    await pg.goto("https://kineticwebdesigns.co.uk/", wait_until="domcontentloaded"); await pg.wait_for_timeout(3000)
    await pg.evaluate("const g=document.getElementById('gate'); if(g) g.style.display='none'; document.body.style.overflow='auto'")
    await pg.evaluate(f"document.getElementById('sx-tab-{tab}').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate(f"(()=>{{const l=document.querySelector(\"#sx-panel [data-look='{look}']\"); if(l) l.click()}})()"); await pg.wait_for_timeout(1500)  # some tabs have one design and no picker
    await pg.evaluate("(()=>{const b=[...document.querySelectorAll('#sx-panel button')].find(x=>x.textContent.trim()==='Phone'); if(b) b.click()})()")
    await pg.wait_for_timeout(800)
    # the phone frame fills the screen, everything else hidden
    await pg.evaluate("""(()=>{const s=document.querySelector('#sx-panel .sx-scroll');document.body.appendChild(s);
      Object.assign(s.style,{position:'fixed',inset:'0',width:'100vw',height:'100vh',maxWidth:'none',maxHeight:'none',zIndex:99999,background:'#000',borderRadius:'0',margin:'0',border:'0',overflowY:'auto'});
      [...document.body.children].forEach(c=>{if(c!==s)c.style.visibility='hidden'});s.style.visibility='visible';s.scrollTop=0;})()""")
    await pg.wait_for_timeout(2500)
    cdp = await ctx.new_cdp_session(pg); frames = []
    cdp.on("Page.screencastFrame", lambda f: (frames.append((time.time(), f["data"])), asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]}))))
    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": 1080, "maxHeight": 1920})
    await pg.wait_for_timeout(2500)  # the hero plays first
    H = await pg.evaluate("document.querySelector('.sx-scroll').scrollHeight - innerHeight")
    steps = 220
    for i in range(steps + 1):  # ~16 s of smooth scrolling, eased
        k = i / steps; e = k * k * (3 - 2 * k)
        await pg.evaluate(f"document.querySelector('.sx-scroll').scrollTop={int(H * e)}"); await pg.wait_for_timeout(70)
    await pg.wait_for_timeout(1500)
    await cdp.send("Page.stopScreencast"); await ctx.close()
    t0 = frames[0][0]; lst = tmp / "list.txt"
    with open(lst, "w") as fh:
        for i, (t, d) in enumerate(frames):
            (tmp / f"{i:05d}.jpg").write_bytes(base64.b64decode(d))
            dur = (frames[i + 1][0] - t) if i + 1 < len(frames) else 3.0  # hold the last frame under the end card
            fh.write(f"file '{i:05d}.jpg'\nduration {dur:.3f}\n")
        fh.write(f"file '{len(frames) - 1:05d}.jpg'\n")  # the concat reader ignores the last duration unless the file repeats
    total = frames[-1][0] - t0 + 3.0
    end = total - 3.2
    vf = ",".join(["scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                   txt(f"WEBSITE SERIES {n}/15", 48, 300, 0, 4), txt(title, 96, 390, 0, 4),
                   f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.78:t=fill:enable='gte(t,{end:.2f})'",
                   txt("Want one for your business?", 62, 760, end, total + 1, False), txt("Comment SITE", 92, 860, end + .3, total + 1, False),
                   txt("for a free mock-up", 54, 980, end + .3, total + 1, False), txt("kineticwebdesigns.co.uk", 40, 1640, end + .5, total + 1, False),
                   "format=yuv420p"])
    mp4 = out / f"Reel {n:02d} - {title.replace('&', 'and')}.mp4"
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf, "-t", f"{total:.2f}",
                    "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-an", "-movflags", "+faststart", str(mp4)], check=True)
    for f in tmp.glob("*"): f.unlink()
    tmp.rmdir()
    print(f"reel {n}: {mp4.name} ({total:.1f}s, {mp4.stat().st_size // 1024} KB)", flush=True)
    return mp4


async def main(out: Path, nums):
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--autoplay-policy=no-user-gesture-required"])
        for n, title, tab, look in SERIES:
            if nums and n not in nums:
                continue
            try:
                await record(b, nums.get(n, n) if isinstance(nums, dict) else n, title, tab, look, out)
            except Exception as ex:
                print(f"reel {n} FAILED: {ex}", flush=True)
        await b.close()


if __name__ == "__main__":
    # numbers, or item=label to show a different series number (e.g. 6=5 makes Night café, titled 5/15)
    asyncio.run(main(Path(sys.argv[1]), {int(x.split("=")[0]): int(x.split("=")[-1]) for x in sys.argv[2:]}))
