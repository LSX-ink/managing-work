"""LSX HQ server: the agents' scheduler plus the office screen on http://127.0.0.1:8341.

Run from the jarvis folder:  python -m hq.app
Only listens on this PC. Nothing here sends messages to anyone.
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import httpx  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

import memory  # noqa: E402
from config import Settings  # noqa: E402
from hq.agents import Ctx, roster  # noqa: E402
from hq.brain import Brain  # noqa: E402

PORT = int(os.getenv("KINETIC_HQ_PORT", "8341"))
SETTINGS = Settings()
HQ_DIR = memory.root(SETTINGS) / "LSX HQ"
BRAIN = Brain(HQ_DIR / "brain.db", journal_dir=HQ_DIR / "Journal")
AGENTS = {a.key: a for a in roster()}
TICK = 20  # seconds between schedule checks


async def run_agent(ctx: Ctx, key: str, reason: str = "schedule") -> None:
    agent = AGENTS[key]
    if agent.running:
        return
    agent.running = True
    run_id = BRAIN.run_started(key)
    BRAIN.log(key, f"{agent.name} started ({reason})", "start")
    try:
        result = await agent.run(ctx)
        BRAIN.run_finished(run_id, True, result)
        BRAIN.log(key, f"{agent.name}: {result}", "done")
    except Exception as e:  # one agent failing never stops the office
        msg = f"{type(e).__name__}: {str(e)[:300]}"
        BRAIN.run_finished(run_id, False, msg)
        BRAIN.log(key, f"{agent.name} hit a problem: {msg}", "error")
    finally:
        agent.running = False


async def scheduler(ctx: Ctx) -> None:
    BRAIN.log("hq", "LSX HQ is open. Agents reporting for duty.", "win")
    while True:
        now = datetime.now()
        for key, agent in AGENTS.items():
            if not BRAIN.get(f"paused.{key}", False) and agent.due(BRAIN, now):
                asyncio.create_task(run_agent(ctx, key))
        await asyncio.sleep(TICK)


@asynccontextmanager
async def lifespan(app: FastAPI):
    http = httpx.AsyncClient(timeout=60, follow_redirects=True)
    app.state.ctx = Ctx(SETTINGS, BRAIN, http)
    task = asyncio.create_task(scheduler(app.state.ctx))
    yield
    task.cancel()
    await http.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def page():
    return FileResponse(Path(__file__).parent / "static" / "hq.html")


@app.get("/api/state")
async def state():
    now = datetime.now()
    agents = []
    for a in AGENTS.values():
        last = BRAIN.last_run(a.key)
        agents.append({
            "key": a.key, "division": a.division, "name": a.name, "title": a.title, "emoji": a.emoji, "colour": a.colour, "job": a.job,
            "status": "working" if a.running else ("paused" if BRAIN.get(f"paused.{a.key}", False) else
                                                    ("error" if last and last.get("ok") == 0 else "idle")),
            "last": last and {"when": datetime.fromtimestamp(last["started"]).strftime("%H:%M"),
                              "result": last.get("result") or ""},
            "next": a.next_text(BRAIN, now),
            "wins_today": BRAIN.count_today(a.key, "win"),
            "runs_today": BRAIN.runs_today(a.key),
        })
    facts = BRAIN.facts()
    pipeline = {}
    try:
        import kinetic_store as st
        for r in st.rows_of(SETTINGS, st.OUTREACH):
            pipeline[r.get("status", "new")] = pipeline.get(r.get("status", "new"), 0) + 1
        pipeline["leads"] = len(st.rows_of(SETTINGS, st.PROSPECTS))
    except Exception:
        pass
    return JSONResponse({
        "pipeline": pipeline,
        "outbox": {"sent_today": BRAIN.count_today("warden", "win"), "cap": facts.get("settings.send_per_day", 15)},
        "time": now.strftime("%H:%M"), "hour": now.hour, "agents": agents,
        "divisions": sorted({a.division for a in AGENTS.values()}),
        "brain": {
            "priorities": facts.get("ceo.priorities"), "numbers": facts.get("numbers.briefing"),
            "leads_total": facts.get("leads.total"), "instagram": facts.get("ig.counts"),
            "needs_you": facts.get("ig.needs_you"), "studio": facts.get("studio.today"),
            "health": {k[7:]: v for k, v in facts.items() if k.startswith("health.") and isinstance(v, bool)},
            "settings": {"trade": facts.get("settings.trade", "barbers"),
                         "drafts_per_day": facts.get("settings.drafts_per_day", 20),
                         "videos": facts.get("settings.videos", False)},
            "memories": BRAIN.events(limit=1)[0]["id"] if BRAIN.events(limit=1) else 0,
        },
    })


@app.get("/api/events")
async def events(after: int = 0, agent: str | None = None, limit: int = 80):
    return BRAIN.events(agent=agent, limit=min(limit, 300), after=after)


@app.get("/api/search")
async def search(q: str):
    return BRAIN.search(q[:80])


@app.post("/api/run/{key}")
async def run_now(key: str):
    if key not in AGENTS:
        raise HTTPException(404, "No such agent")
    asyncio.create_task(run_agent(app.state.ctx, key, "you asked"))
    return {"ok": True}


@app.post("/api/pause/{key}")
async def pause(key: str):
    if key not in AGENTS:
        raise HTTPException(404, "No such agent")
    paused = not BRAIN.get(f"paused.{key}", False)
    BRAIN.set(f"paused.{key}", paused)
    BRAIN.log(key, f"{AGENTS[key].name} {'paused' if paused else 'back to work'}", "info")
    return {"paused": paused}


@app.post("/api/settings")
async def settings(body: dict):
    if "trade" in body:
        BRAIN.set("settings.trade", str(body["trade"])[:40].strip() or "barbers")
    if "drafts_per_day" in body:
        BRAIN.set("settings.drafts_per_day", max(0, min(int(body["drafts_per_day"]), 40)))
    if "videos" in body:
        BRAIN.set("settings.videos", bool(body["videos"]))
    BRAIN.log("hq", f"settings changed: {body}", "info")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
