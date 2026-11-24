"""Alfred restarts himself after an update.

When his code on disk changes (a git pull, by you or by Claude on the PC), the running server would keep the old
version until someone pressed Ctrl+C and started it again. Instead, `python server.py` runs the server as a child
(supervise); this watcher notices the change, waits until he isn't in the middle of answering, and the child exits
with RESTART_CODE so the first copy starts a fresh one in the same window. Open pages reconnect on their
own (and reload when the page itself changed), so nothing needs doing by hand.

JARVIS_AUTO_RESTART=false turns it off.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

CHECK_EVERY = 20  # seconds between looks at the code on disk
SETTLE = 10  # seconds the files must stay unchanged first (a git pull writes many files)
IDLE_FOR = 5  # seconds with no answer in progress before restarting
WATCHED = ("*.py", "requirements.txt", ".env")


def fingerprint(root: Path) -> tuple:
    """When each of Alfred's own files was last changed (not his memory, data or the page's files)."""
    found = []
    for pattern in WATCHED:
        for path in sorted(root.glob(pattern)):
            try:
                found.append((path.name, path.stat().st_mtime_ns))
            except OSError:
                pass
    return tuple(found)


RESTART_CODE = 3  # the server's exit code that asks the window's first copy to start it again
CHILD_FLAG = "--serve"


def restart() -> None:
    """Stop this copy of the server; the first copy in the window (supervise) starts a fresh one at once."""
    print("[jarvis] New version on disk: restarting to load it…", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(RESTART_CODE)


def supervise(script: str) -> int:
    """Run the server as a child and start it again whenever it asks to (after an update). Ctrl+C stops both.
    Returns the exit code to leave with."""
    while True:
        child = subprocess.Popen([sys.executable, script, CHILD_FLAG, *sys.argv[1:]])
        try:
            code = child.wait()
        except KeyboardInterrupt:
            try:
                code = child.wait(timeout=10)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                child.kill()
                code = 1
            return code
        if code != RESTART_CODE:
            return code
        time.sleep(1)


async def watch(root: Path, busy: Callable[[], bool], restart_now: Callable[[], None] = restart,
                every: float = CHECK_EVERY, settle: float = SETTLE, idle_for: float = IDLE_FOR) -> None:
    """Restart once the code has changed, the change has settled and no answer is in progress."""
    start = fingerprint(root)
    while True:
        await asyncio.sleep(every)
        now = fingerprint(root)
        if now == start:
            continue
        await asyncio.sleep(settle)
        if fingerprint(root) != now:
            continue  # still being written: look again next time
        quiet_since = None
        while True:
            if busy():
                quiet_since = None
            elif quiet_since is None:
                quiet_since = time.monotonic()
            elif time.monotonic() - quiet_since >= idle_for:
                break
            await asyncio.sleep(1)
        restart_now()
        return
