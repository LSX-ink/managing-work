"""Builds the phone copy of the LSX HQ screen: the chosen design with the PC's current numbers baked in.

Run from the jarvis folder:  python -m hq.phone_snapshot
Writes memory/LSX HQ/Phone/lsx-hq.html and core.js, ready to publish to the owner's LSX HQ page.
"""

import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).parent / "static"
OUT = ROOT / "memory" / "LSX HQ" / "Phone"
HQ = "http://127.0.0.1:8341"

SHIM = """<script>
// Phone view of LSX HQ: the PC's live data as recorded at the time shown, so the page works away from the PC.
(() => { const S = %s, E = %s; S.agents.forEach(a => { if (a.status === "working") a.status = "idle"; });
  const J = o => new Response(JSON.stringify(o), { headers: { "Content-Type": "application/json" } }), real = window.fetch.bind(window);
  window.fetch = async (u, o) => { u = String(u);
    if (u.startsWith("/api/state")) return J(S);
    if (u.startsWith("/api/events")) { const q = new URLSearchParams(u.split("?")[1] || ""), after = +(q.get("after") || 0), ag = q.get("agent");
      return J(E.filter(e => e.id > after && (!ag || e.agent === ag)).slice(-(+(q.get("limit") || 80)))); }
    if (u.startsWith("/api/")) return J({ ok: true });
    return real(u, o); }; })();
</script>
"""


def build() -> str:
    state = httpx.get(f"{HQ}/api/state", timeout=30).json()
    events = httpx.get(f"{HQ}/api/events", params={"limit": 150}, timeout=30).json()
    view = int(state.get("view") or 4)
    html = (STATIC / f"v{view}.html").read_text(encoding="utf-8")
    html = re.sub(r"(?is)<!doctype html>|</?html[^>]*>|</?head>|</?body[^>]*>", "", html)
    html = html.replace('"/static/core.js"', '"./core.js"')
    html = re.sub(r"<title>[^<]*</title>", "<title>LSX HQ</title>", html, count=1)
    html = html.replace('<script type="importmap">', SHIM % (json.dumps(state), json.dumps(events)) + '<script type="importmap">', 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lsx-hq.html").write_text(html, encoding="utf-8")
    (OUT / "core.js").write_text((STATIC / "core.js").read_text(encoding="utf-8"), encoding="utf-8")
    return state["time"]


if __name__ == "__main__":
    try:
        print("snapshot at", build(), "->", OUT)
    except httpx.HTTPError as e:
        sys.exit(f"LSX HQ is not answering on {HQ}: {e}")
