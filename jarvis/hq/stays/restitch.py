"""Re-join the walkthrough clips in the real route through the house (from the approved plans):
outside -> ground floor suites front to back -> upstairs."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\Thato\managing-work\jarvis")
from tiktokstudio_video import ffmpeg

OUT, work = Path(sys.argv[1]), Path(sys.argv[2])
files = [work / f"c{i}.mp4" for i in sys.argv[3:]]
fade, dur = 0.8, 5.0
inputs = sum((["-i", str(f)] for f in files), [])
pre = ";".join(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1,format=yuv420p[s{i}]" for i in range(len(files)))
chain, prev, offset = [], "[s0]", 0.0
for i in range(1, len(files)):
    offset += dur - fade
    chain.append(f"{prev}[s{i}]xfade=transition=fade:duration={fade}:offset={offset:.2f}[v{i}]"); prev = f"[v{i}]"
r = subprocess.run([ffmpeg(), "-y", "-loglevel", "error", *inputs, "-filter_complex", pre + ";" + ";".join(chain), "-map", prev, "-an",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-movflags", "+faststart", str(OUT / "walkthrough.mp4")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("ffmpeg", r.returncode, r.stderr[-300:], (OUT / "walkthrough.mp4").stat().st_size // 1024, "KB")
