"""J.A.R.V.I.S. — local voice assistant server.

The browser does speech-to-text and plays the audio; this server thinks (Claude) and
speaks (ElevenLabs, or the browser's own voice as a fallback).
"""

import asyncio
import base64
import hashlib
import hmac
import itertools
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

import anthropic
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import alerts
import memory
import nowplaying
import tools
import tts
from brain import Brain, computer_enabled, persona
from config import ROOT, settings

FRONTEND = ROOT / "frontend"
WEATHER_TTL = 600  # seconds the HUD weather panel reuses a reading
CONFIRM_TIMEOUT = 120  # seconds to approve mouse/keyboard actions before they are declined
SESSION_COOKIE = "jarvis_session"
SESSION_DAYS = 30
MAX_ALERTS = 30  # notifications kept for the page


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = anthropic.AsyncAnthropic()
    app.state.http = httpx.AsyncClient(timeout=30)
    app.state.pages = {}  # open pages: id(WebSocket) -> (WebSocket, its speak function, its Brain)
    app.state.alerts = []  # notifications shown on the page, newest last
    app.state.alert_ids = itertools.count(1)
    watchers = alerts.start(settings, lambda text, kind: announce(app, text, kind))
    if settings.now_playing:
        watchers.append(asyncio.create_task(nowplaying.watch(lambda song: broadcast(app, {"type": "nowplaying", **song}))))
    yield
    for task in watchers:
        task.cancel()
    await app.state.http.aclose()
    await app.state.client.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.middleware("http")
async def always_fresh(request: Request, call_next):
    """Make the browser check for newer page files every time, so an update shows without a hard refresh."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


async def announce(app: FastAPI, text: str, kind: str = "phone") -> None:
    """Add a heads-up (a delivery, a call) to the notifications and say it on every open page."""
    item = {"id": next(app.state.alert_ids), "kind": kind, "text": text, "at": time.strftime("%H:%M")}
    app.state.alerts = [*app.state.alerts, item][-MAX_ALERTS:]
    if not app.state.pages:
        print(f"  Jarvis (no page open): {text}", flush=True)
    for ws, speak, brain in list(app.state.pages.values()):
        brain.note(text)
        try:
            await ws.send_json({"type": "alert", **item})
            await speak(text, quiet=True)
        except Exception:  # the page closed mid-send
            pass


async def broadcast(app: FastAPI, message: dict) -> None:
    """Send a message to every open page."""
    for ws, _, _ in list(app.state.pages.values()):
        try:
            await ws.send_json(message)
        except Exception:  # the page closed mid-send
            pass


async def dismiss_alert(app: FastAPI, alert_id) -> None:
    """Remove one notification, from every open page."""
    app.state.alerts = [a for a in app.state.alerts if a["id"] != alert_id]
    await broadcast(app, {"type": "dismissed", "id": alert_id})


# ---- password (JARVIS_PASSWORD) ----------------------------------------------

def session_token() -> str:
    """Cookie value for a logged-in browser. Changing the password logs every browser out."""
    return hmac.new(settings.password.encode(), b"jarvis-session", hashlib.sha256).hexdigest()


def logged_in(cookies) -> bool:
    return not settings.password or hmac.compare_digest(cookies.get(SESSION_COOKIE, ""), session_token())


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J.A.R.V.I.S.</title><link rel="icon" href="data:,">
<style>
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #07090f; color: #d8e1ee;
       font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; }
form { display: flex; flex-direction: column; gap: 12px; width: min(320px, 90vw); }
input, button { padding: 12px 14px; border-radius: 8px; border: 1px solid #2a3547; background: #0c121c; color: inherit; font-size: 16px; }
button { background: #16202e; cursor: pointer; }
p { margin: 0; color: #ff7a7a; min-height: 1.2em; }
</style></head>
<body><form method="post" action="/login">
<input type="password" name="password" placeholder="Password" autofocus required>
<button type="submit">Unlock</button><p>ERROR</p>
</form></body></html>"""


def login_page(error: str = "", status: int = 200) -> HTMLResponse:
    return HTMLResponse(LOGIN_PAGE.replace("ERROR", error), status_code=status)


@app.middleware("http")
async def require_password(request: Request, call_next):
    if logged_in(request.cookies) or request.url.path == "/login":
        return await call_next(request)
    if request.url.path == "/":
        return login_page()
    return Response("Log in first.", status_code=401)


@app.post("/login")
async def login(request: Request):
    password = parse_qs((await request.body()).decode()).get("password", [""])[0]
    if not settings.password or not hmac.compare_digest(password.encode(), settings.password.encode()):
        await asyncio.sleep(1)  # slows down guessing
        return login_page("Wrong password.", status=401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(SESSION_COOKIE, session_token(), max_age=SESSION_DAYS * 86400,
                        httponly=True, samesite="strict")
    return response


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


# ---- memory folders (the HUD brain) -----------------------------------------------

def from_our_page(request: Request) -> bool:
    """Any site can send requests to localhost, so only let our own page change the folders."""
    origin = request.headers.get("origin")
    return origin is not None and urlparse(origin).netloc == request.headers.get("host")


async def memory_call(request: Request | None, fn, *args):
    if request is not None and not from_our_page(request):
        return Response("Not from the Jarvis page.", status_code=403)
    try:
        return await asyncio.to_thread(fn, settings, *args)
    except ValueError as exc:
        return Response(str(exc), status_code=400)


@app.get("/memory")
async def memory_list():
    return {"folders": await memory_call(None, memory.listing)}


@app.post("/memory/{index}/rename")
async def memory_rename(index: int, request: Request):
    name = (await request.json()).get("name", "")
    result = await memory_call(request, memory.rename, index, name)
    return result if isinstance(result, Response) else {"name": result}


@app.post("/memory/{index}/note")
async def memory_note(index: int, request: Request):
    body = await request.json()
    result = await memory_call(request, memory.save_note, index, body.get("title", ""), body.get("text", ""))
    return result if isinstance(result, Response) else {"name": result.name}


@app.put("/memory/{index}/files/{filename}")
async def memory_upload(index: int, filename: str, request: Request):
    if int(request.headers.get("content-length") or 0) > memory.MAX_FILE_BYTES:
        return Response("That file is too big; the limit is 20 MB.", status_code=413)
    result = await memory_call(request, memory.save_file, index, filename, await request.body())
    return result if isinstance(result, Response) else {"name": result.name}


@app.get("/memory/{index}/files/{filename}")
async def memory_open(index: int, filename: str):
    result = await memory_call(None, memory.file_path, index, filename)
    # sandboxed so an uploaded web page can't run scripts as the Jarvis page
    headers = {"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"}
    return result if isinstance(result, Response) else FileResponse(result, headers=headers)


@app.delete("/memory/{index}/files/{filename}")
async def memory_delete(index: int, filename: str, request: Request):
    result = await memory_call(request, memory.delete_file, index, filename)
    return result if isinstance(result, Response) else {"ok": True}


def same_origin(ws: WebSocket) -> bool:
    """Browsers let any site open a WebSocket to localhost, so only accept our own page."""
    origin = ws.headers.get("origin")
    return origin is None or urlparse(origin).netloc == ws.headers.get("host")


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    if not same_origin(ws) or not logged_in(ws.cookies):
        await ws.close(code=1008)
        return
    await ws.accept()
    http = ws.app.state.http
    pending: dict[int, asyncio.Future] = {}
    next_id = itertools.count(1)

    async def speak(text: str, quiet: bool = False) -> None:
        """Say text aloud; quiet leaves it out of the transcript (notifications show it instead)."""
        print(f"  Jarvis: {text}", flush=True)
        audio = await tts.synthesize(http, settings, text)
        await ws.send_json({
            "type": "say",
            "text": text,
            "audio": base64.b64encode(audio).decode() if audio else "",
            "quiet": quiet,
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

    brain = Brain(settings, ws.app.state.client, http, confirm=confirm, page=ws.send_json)
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
    ws.app.state.pages[id(ws)] = (ws, speak, brain)
    await ws.send_json({"type": "alerts", "items": ws.app.state.alerts})
    if note := alerts.setup_note(settings):
        await ws.send_json({"type": "note", "text": note})
    try:
        # Keep reading while a turn runs, so approval clicks reach the waiting turn.
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "dismiss":
                await dismiss_alert(ws.app, msg.get("id"))
            elif msg.get("type") == "confirm_reply":
                fut = pending.get(msg.get("id"))
                if fut and not fut.done():
                    answer = msg.get("answer")
                    fut.set_result(answer if answer in ("allow", "allow_all") else "deny")
            else:
                inbox.put_nowait(msg)
    except WebSocketDisconnect:
        pass
    finally:
        ws.app.state.pages.pop(id(ws), None)
        task.cancel()
        for fut in pending.values():
            if not fut.done():
                fut.set_result("deny")


if __name__ == "__main__":
    import uvicorn

    print(f"J.A.R.V.I.S. on http://{settings.host}:{settings.port}  (model: {settings.model})", flush=True)
    uvicorn.run(app, host=settings.host, port=settings.port)
