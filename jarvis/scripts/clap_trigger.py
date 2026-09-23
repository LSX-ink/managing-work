#!/usr/bin/env python3
"""Double-clap to wake Jarvis: starts the server if needed and opens it in your browser.

Needs: pip install sounddevice numpy
"""

import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ROOT, settings  # noqa: E402

THRESHOLD = 0.15   # peak level that counts as a clap; lower = more sensitive
MIN_GAP = 0.1      # seconds between the two claps
MAX_GAP = 1.2
COOLDOWN = 5.0     # ignore claps for this long after triggering

URL = f"http://{settings.host}:{settings.port}/"


def server_up() -> bool:
    try:
        urllib.request.urlopen(URL, timeout=1)
        return True
    except OSError:
        return False


def wake() -> None:
    if not server_up():
        subprocess.Popen([sys.executable, str(ROOT / "server.py")], cwd=ROOT)
        for _ in range(40):
            if server_up():
                break
            time.sleep(0.25)
    webbrowser.open(URL)


def main() -> None:
    last_clap = 0.0
    quiet_until = 0.0
    triggered = False

    def on_audio(indata, frames, time_info, status):
        nonlocal last_clap, quiet_until, triggered
        now = time.monotonic()
        if now < quiet_until or float(np.abs(indata).max()) < THRESHOLD:
            return
        gap = now - last_clap
        if gap < MIN_GAP:
            return
        if gap <= MAX_GAP:
            triggered = True
            last_clap = 0.0
            quiet_until = now + COOLDOWN
        else:
            last_clap = now

    with sd.InputStream(channels=1, samplerate=44100, blocksize=1024, dtype="float32", callback=on_audio):
        print("Listening for a double clap… (Ctrl+C to quit)", flush=True)
        while True:
            time.sleep(0.1)
            if triggered:
                triggered = False
                print("Double clap — waking Jarvis.", flush=True)
                wake()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
