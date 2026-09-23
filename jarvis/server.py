"""J.A.R.V.I.S. — local voice assistant server.

The browser does speech-to-text and plays the audio; this server thinks (Claude) and
speaks (ElevenLabs, or the browser's own voice as a fallback).
"""

import base64
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import anthropic
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import tts
from brain import Brain
from config import ROOT, settings

FRONTEND = ROOT / "frontend"


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
        "serverVoice": bool(settings.elevenlabs_api_key),
    }


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
    brain = Brain(settings, ws.app.state.client, http)

    async def speak(text: str) -> None:
        print(f"  Jarvis: {text}", flush=True)
        audio = await tts.synthesize(http, settings, text)
        await ws.send_json({
            "type": "say",
            "text": text,
            "audio": base64.b64encode(audio).decode() if audio else "",
        })

    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "activate":
                await brain.activate(speak)
            elif text := str(msg.get("text", "")).strip():
                print(f"  You:    {text}", flush=True)
                await brain.handle(text, speak)
            await ws.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    print(f"J.A.R.V.I.S. on http://{settings.host}:{settings.port}  (model: {settings.model})", flush=True)
    uvicorn.run(app, host=settings.host, port=settings.port)
