"""J.A.R.V.I.S. — local voice assistant server.

The browser does speech-to-text and plays the audio; this server thinks (Claude) and
speaks (ElevenLabs, or the browser's own voice as a fallback).
"""

import asyncio
import base64
import itertools
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import anthropic
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import tools
import tts
from brain import Brain, computer_enabled, persona
from config import ROOT, settings

FRONTEND = ROOT / "frontend"
WEATHER_TTL = 600  # seconds the HUD weather panel reuses a reading
CONFIRM_TIMEOUT = 120  # seconds to approve mouse/keyboard actions before they are declined


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = anthropic.AsyncAnthropic()
    app.state.http = httpx.AsyncClient(timeout=30)
    yield
    await app.state.http.aclose()
    await app.state.client.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/")
async def index():
    return FileResponse(FRONTEND / "index.html")


@app.get("/config")
async def client_config():
    return {
        "speechLang": settings.speech_lang,
        "language": settings.language,
        "name": persona(settings)["name"],
        "serverVoice": bool(settings.elevenlabs_api_key),
        "computer": computer_enabled(settings),
        "theme": settings.theme,
        "model": settings.model,
        "city": settings.city,
    }


_weather: dict = {"at": 0.0, "text": ""}


@app.get("/weather")
async def weather():
    """Current weather line for the HUD, cached so page refreshes don't hit the weather service."""
    if not settings.city:
        return {"text": ""}
    now = asyncio.get_running_loop().time()
    if not _weather["text"] or now - _weather["at"] > WEATHER_TTL:
        try:
            _weather["text"] = await tools.get_weather(app.state.http, settings.city)
            _weather["at"] = now
        except Exception as exc:
            return {"text": "", "error": str(exc)}
    return {"text": _weather["text"]}


def same_origin(ws: WebSocket) -> bool:
    """Browsers let any site open a WebSocket to localhost, so only accept our own page."""
    origin = ws.headers.get("origin")
    return origin is None or urlparse(origin).netloc == ws.headers.get("host")


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    if not same_origin(ws):
        await ws.close(code=1008)
        return
    await ws.accept()
    http = ws.app.state.http
    pending: dict[int, asyncio.Future] = {}
    next_id = itertools.count(1)

    async def speak(text: str) -> None:
        print(f"  Jarvis: {text}", flush=True)
        audio = await tts.synthesize(http, settings, text)
        await ws.send_json({
            "type": "say",
            "text": text,
            "audio": base64.b64encode(audio).decode() if audio else "",
        })

    async def confirm(steps: list[str]) -> str:
        """Ask the page to approve mouse/keyboard actions; no answer in time counts as no."""
        cid = next(next_id)
        pending[cid] = asyncio.get_running_loop().create_future()
        await ws.send_json({"type": "confirm", "id": cid, "steps": steps})
        try:
            return await asyncio.wait_for(pending[cid], CONFIRM_TIMEOUT)
        except asyncio.TimeoutError:
            return "deny"
        finally:
            pending.pop(cid, None)

    brain = Brain(settings, ws.app.state.client, http, confirm=confirm)
    inbox: asyncio.Queue = asyncio.Queue()

    async def worker() -> None:
        while True:
            msg = await inbox.get()
            if msg.get("type") == "activate":
                await brain.activate(speak)
            elif text := str(msg.get("text", "")).strip():
                print(f"  You:    {text}", flush=True)
                await brain.handle(text, speak)
            await ws.send_json({"type": "done"})

    task = asyncio.create_task(worker())
    try:
        # Keep reading while a turn runs, so approval clicks reach the waiting turn.
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "confirm_reply":
                fut = pending.get(msg.get("id"))
                if fut and not fut.done():
                    answer = msg.get("answer")
                    fut.set_result(answer if answer in ("allow", "allow_all") else "deny")
            else:
                inbox.put_nowait(msg)
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        for fut in pending.values():
            if not fut.done():
                fut.set_result("deny")


if __name__ == "__main__":
    import uvicorn

    print(f"J.A.R.V.I.S. on http://{settings.host}:{settings.port}  (model: {settings.model})", flush=True)
    uvicorn.run(app, host=settings.host, port=settings.port)
