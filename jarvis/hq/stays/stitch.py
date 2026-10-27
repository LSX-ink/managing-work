"""Download the five walkthrough clips, check them, and join them with soft crossfades into one looping hero video."""
import subprocess, sys
from pathlib import Path
import httpx
sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
from tiktokstudio_video import ffmpeg

OUT = Path(sys.argv[1])
work = Path(sys.argv[2]); work.mkdir(exist_ok=True)
urls = sys.argv[3:]
ff = ffmpeg()
files = []
for i, u in enumerate(urls):
    f = work / f"c{i}.mp4"
    f.write_bytes(httpx.get(u, timeout=120).content)
    files.append(f)
    probe = subprocess.run([ff, "-i", str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    print(f.name, [l.strip() for l in probe.splitlines() if "Duration" in l or "Video:" in l][:2])
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(f), "-vf", "fps=1,scale=320:-1,tile=5x1", "-frames:v", "1", str(work / f"c{i}.jpg")])
# crossfade chain: each clip 5s, 0.8s fades
fade, dur = 0.8, 5.0
inputs = sum((["-i", str(f)] for f in files), [])
chain, prev, offset = [], "[0:v]", 0.0
for i in range(1, len(files)):
    offset += dur - fade
    label = f"[v{i}]"
    chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}{label}")
    prev = label
pre = ";".join(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1,format=yuv420p[s{i}]" for i in range(len(files)))
chain = [c.replace(f"[{i}:v]", f"[s{i}]") for c in chain for i in [0]] if False else chain
graph = pre + ";" + ";".join(c.replace("[0:v]", "[s0]") for c in chain)
for i in range(1, len(files)):
    graph = graph.replace(f"[{i}:v]xfade", f"[s{i}]xfade")
r = subprocess.run([ff, "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", prev, "-an",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-movflags", "+faststart", str(OUT / "walkthrough.mp4")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("ffmpeg", r.returncode, r.stderr[-300:])
print((OUT / "walkthrough.mp4").stat().st_size // 1024, "KB")
