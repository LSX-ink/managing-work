"""Record a stays page on a phone screen (CDP screencast frames -> mp4): the gold line, the fly-in, then a slow scroll."""
import asyncio, base64, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright
sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
from tiktokstudio_video import ffmpeg

async def main(url, out):
    tmp = Path(out).with_suffix(""); tmp.mkdir(exist_ok=True)
    frames = []
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": 432, "height": 768}, device_scale_factor=2.5, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        def on(f):
            frames.append((time.time(), f["data"])); asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]}))
        cdp.on("Page.screencastFrame", on)
        await pg.goto(url, wait_until="domcontentloaded"); await pg.wait_for_timeout(1500)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": 1080, "maxHeight": 1920, "everyNthFrame": 1})
        await pg.wait_for_timeout(5500)            # intro + gold line drawing
        await pg.click(".door .go"); await pg.wait_for_timeout(9000)   # dive in + drone fly-in
        for _ in range(60):                        # slow scroll into the story and the 3D
            await pg.mouse.wheel(0, 45); await pg.wait_for_timeout(110)
        await pg.wait_for_timeout(800)
        await cdp.send("Page.stopScreencast"); await b.close()
    t0 = frames[0][0]; lst = []
    for i, (t, d) in enumerate(frames):
        f = tmp / f"{i:05d}.jpg"; f.write_bytes(base64.b64decode(d)); lst.append((f, t))
    with open(tmp / "list.txt", "w") as fh:
        for i, (f, t) in enumerate(lst):
            dur = (lst[i + 1][1] - t) if i + 1 < len(lst) else 0.1
            fh.write(f"file '{f.name}'\nduration {dur:.3f}\n")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
                    "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-an", "-movflags", "+faststart", out], check=True)
    print(len(frames), "frames,", round(lst[-1][1] - t0, 1), "s")

asyncio.run(main(sys.argv[1], sys.argv[2]))
