"""J.A.R.V.I.S. — local voice assistant server.

The browser does speech-to-text and plays the audio; this server thinks (Claude) and
speaks (ElevenLabs, or the browser's own voice as a fallback).
"""

import asyncio
import base64
import hashlib
import hmac
import html
import ipaddress
import itertools
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

import anthropic
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.requests import ClientDisconnect

import alerts
import helpers
import tiktokstudio
import tiktokstudio_store
import memory
import nowplaying
import pc
import screen
import station
import reminders
import timers
import tiktok
import tools
import tts
from brain import Brain, computer_enabled, persona
from config import ROOT, settings

FRONTEND = ROOT / "frontend"
WEATHER_TTL = 600  # seconds the HUD weather panel reuses a reading
EMAIL_TTL = 60  # seconds the HUD email counter reuses a count
CONFIRM_TIMEOUT = 120  # seconds to approve mouse/keyboard actions before they are declined
SESSION_COOKIE = "jarvis_session"
SESSION_DAYS = 30
LOGIN_TRIES = 5  # wrong passwords in a row before that address has to wait
LOGIN_LOCK = 600  # seconds it waits
MAX_ALERTS = 30  # notifications kept for the page


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = anthropic.AsyncAnthropic()
    app.state.http = httpx.AsyncClient(timeout=30)
    app.state.pages = {}  # open pages: id(WebSocket) -> (WebSocket, its speak function, its Brain)
    app.state.alerts = []  # notifications shown on the page, newest last
    app.state.alert_ids = itertools.count(1)
    watchers = alerts.start(settings, lambda text, kind: announce(app, text, kind))
    timers.set_announcer(lambda text, kind: announce(app, text, kind))
    helpers.set_context(app.state.client, lambda text, kind: announce(app, text, kind))
    watchers.append(asyncio.create_task(reminders.watch(settings, lambda text, kind: announce(app, text, kind),
                                                        lambda: bool(app.state.pages))))
    watchers.append(tiktokstudio.start(settings, app.state.client, app.state.http, lambda text, kind: announce(app, text, kind)))
    if settings.now_playing:
        watchers.append(asyncio.create_task(nowplaying.watch(lambda song: broadcast(app, {"type": "nowplaying", **song}))))
    yield
    for task in watchers:
        task.cancel()
    await app.state.http.aclose()
    await app.state.client.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


# ---- security --------------------------------------------------------------

SECURITY_HEADERS = {
    "X-Frame-Options": "SAMEORIGIN",  # no other site can show Alfred inside its page and trick clicks on "Allow"
    "Content-Security-Policy": "frame-ancestors 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def allowed_host(host: str | None) -> bool:
    """Only answer requests addressed to this PC or the private phone link.

    A web page can point a name it owns at 127.0.0.1 ("DNS rebinding") and then talk to Alfred as if it were
    his own page. Such names always have a dot, so plain IP addresses, single-word PC names, localhost and
    the Tailscale phone link (*.ts.net) are safe; anything else must be listed in JARVIS_ALLOWED_HOSTS.
    """
    if not host:
        return True  # very old clients send none; the browser always does
    name = urlparse(f"//{host}").hostname or ""
    name = name.lower().rstrip(".")
    if name == "localhost" or name.endswith(".localhost") or name.endswith(".ts.net") or "." not in name:
        return True
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    return name in settings.allowed_hosts


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
            if kind == "timer":
                await ws.send_json({"type": "chime"})
            if not timers.on_break:  # on a break Alfred stays silent; it still goes in the notifications
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


PHONE_NEEDS_PASSWORD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alfred</title></head>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#000;color:#eee;font:18px system-ui,sans-serif;padding:24px;box-sizing:border-box">
<p style="max-width:28em">Alfred stays locked on your phone until he has a password.<br><br>
On your PC, open the <b>.env</b> file in the jarvis folder, add a line <b>JARVIS_PASSWORD=</b> followed by a password you choose, save it, and restart Alfred.</p>
</body></html>"""


def via_phone_link(request) -> bool:
    """True when a visit came through the phone link (Tailscale adds these headers), not from the PC itself."""
    return bool(request.headers.get("x-forwarded-for") or request.headers.get("tailscale-user-login"))


@app.middleware("http")
async def require_password(request: Request, call_next):
    if via_phone_link(request) and not settings.password:
        return HTMLResponse(PHONE_NEEDS_PASSWORD, status_code=403)
    if logged_in(request.cookies) or request.url.path == "/login":
        return await call_next(request)
    if request.url.path == "/":
        return login_page()
    return Response("Log in first.", status_code=401)


# Added last, so it runs first: every answer, the login page included, gets the headers and host check.
@app.middleware("http")
async def security(request: Request, call_next):
    if not allowed_host(request.headers.get("host")):
        return Response("Unknown address. Open Alfred at http://localhost instead, or add this name to "
                        "JARVIS_ALLOWED_HOSTS in .env.", status_code=421)
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


_login_fails: dict[str, list[float]] = {}  # address -> times of recent wrong passwords


def login_address(request: Request) -> str:
    """Who is trying: the phone link passes the real address on, everything else is the PC itself."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "?")


def login_locked(address: str, now: float) -> int:
    """Seconds left before `address` may try again (0 when it may)."""
    recent = [t for t in _login_fails.get(address, []) if now - t < LOGIN_LOCK]
    _login_fails[address] = recent
    if len(recent) < LOGIN_TRIES:
        return 0
    return int(LOGIN_LOCK - (now - recent[-LOGIN_TRIES])) + 1


@app.post("/login")
async def login(request: Request):
    address = login_address(request)
    if wait := login_locked(address, time.time()):
        return login_page(f"Too many wrong passwords. Try again in {wait // 60 + 1} minutes.", status=429)
    password = parse_qs((await request.body()).decode(errors="replace")).get("password", [""])[0]
    if not settings.password or not hmac.compare_digest(password.encode(), settings.password.encode()):
        _login_fails.setdefault(address, []).append(time.time())
        print(f"[jarvis] Wrong password from {address}", flush=True)
        await asyncio.sleep(1)  # slows down guessing
        return login_page("Wrong password.", status=401)
    _login_fails.pop(address, None)
    response = RedirectResponse("/", status_code=303)
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(SESSION_COOKIE, session_token(), max_age=SESSION_DAYS * 86400,
                        httponly=True, samesite="strict", secure=https)
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
        "wakeWord": settings.wake_word,
        "station": settings.station,
    }


_weather: dict = {"at": 0.0, "text": ""}
_emails: dict = {"at": 0.0, "unread": None, "problem": None}


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


@app.get("/emails")
async def emails():
    """Unread email count for the HUD, cached so each page refresh doesn't log in to the mail server."""
    if not settings.email_enabled:
        return {"unread": None}
    now = asyncio.get_running_loop().time()
    # Failures are cached too: retrying a wrong password on every refresh can get the account locked.
    if _emails["at"] == 0.0 or now - _emails["at"] > EMAIL_TTL:
        _emails["at"] = now
        try:
            _emails["unread"] = await asyncio.to_thread(alerts.unread_count, settings)
            _emails["problem"] = None
        except Exception as exc:
            _emails["problem"] = alerts.email_problem(settings, exc)
    if _emails.get("problem"):
        short, fix = _emails["problem"]
        return {"unread": _emails["unread"], "error": short, "fix": fix}
    return {"unread": _emails["unread"]}


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
    return {"folders": await memory_call(None, memory.listing), "extra": await memory_call(None, memory.extras)}


@app.post("/memory/open")
async def memory_open_path(request: Request):
    """Open any memory folder by its path ("Fitness", "Work/Invoices") in File Explorer: the folder stars."""
    path = await memory_call(request, memory.folder, str((await request.json()).get("path", "")))
    if isinstance(path, Response):
        return path
    try:
        await asyncio.to_thread(pc.launch, path.resolve())
    except OSError:
        return Response("Couldn't open File Explorer on this PC.", status_code=400)
    return {"opened": path.name}


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


TOO_BIG = f"That file is too big; the limit is {memory.MAX_UPLOAD_BYTES // 1024 ** 3} GB."
UPLOAD_CHUNK = 4 * 1024 * 1024


@app.put("/memory/{index}/files/{filename}")
async def memory_upload(index: int, filename: str, request: Request):
    """Stream the file straight to disk in big chunks, so large videos neither fill the memory nor stall Alfred."""
    if int(request.headers.get("content-length") or 0) > memory.MAX_UPLOAD_BYTES:
        return Response(TOO_BIG, status_code=413)
    target = await memory_call(request, memory.upload_target, index, filename)
    if isinstance(target, Response):
        return target
    part = target.with_name(target.name + ".part")
    out = await asyncio.to_thread(open, part, "wb")
    written, buffer = 0, bytearray()
    try:
        async for chunk in request.stream():
            written += len(chunk)
            if written > memory.MAX_UPLOAD_BYTES:
                raise OverflowError
            buffer += chunk
            if len(buffer) >= UPLOAD_CHUNK:
                await asyncio.to_thread(out.write, bytes(buffer))
                buffer.clear()
        await asyncio.to_thread(out.write, bytes(buffer))
    except (OverflowError, ClientDisconnect, OSError) as exc:
        await asyncio.to_thread(out.close)
        part.unlink(missing_ok=True)
        if isinstance(exc, OverflowError):
            return Response(TOO_BIG, status_code=413)
        return Response("The upload stopped before the whole file arrived.", status_code=400)
    await asyncio.to_thread(out.close)
    await asyncio.to_thread(part.replace, target)
    return {"name": target.name}


@app.post("/memory/{index}/open")
async def memory_open(index: int, request: Request):
    """Open a folder made inside a memory folder in File Explorer (the HUD panel lists them)."""
    sub = str((await request.json()).get("folder", ""))
    path = await memory_call(request, memory.inner_folder, index, sub)
    if isinstance(path, Response):
        return path
    try:
        await asyncio.to_thread(pc.launch, path.resolve())
    except OSError:
        return Response("Couldn't open File Explorer on this PC.", status_code=400)
    return {"opened": path.name}


@app.get("/memory/{index}/files/{filename}")
async def memory_open(index: int, filename: str):
    result = await memory_call(None, memory.file_path, index, filename)
    # sandboxed so an uploaded web page can't run scripts as the Jarvis page
    headers = {"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"}
    return result if isinstance(result, Response) else FileResponse(result, headers=headers)


# ---- TikTok studio -----------------------------------------------------------------------------------

@app.get("/creator/queue")
async def creator_queue():
    """The videos waiting for a tick or an X, for the HUD: [{id, account, title, kind, created, video_url, thumb_url}]."""
    return await asyncio.to_thread(tiktokstudio.queue, settings)


@app.post("/creator/videos/{video_id}/{action}")
async def creator_video_action(video_id: str, action: str, request: Request):
    """One tap on the studio card or the HUD: approve (tick: posts it) or reject (X: a better one gets made; skip
    means the same). reject takes an optional JSON body {"reason": "..."}. Answers {ok, said, card}."""
    if not from_our_page(request):
        return JSONResponse({"ok": False, "said": "Not from the Jarvis page."}, status_code=403)
    try:
        if action == "approve":
            said = await tiktokstudio.approve(settings, video_id)
        elif action in ("reject", "skip"):
            try:
                body = await request.json()
            except ValueError:  # no body, or not JSON
                body = {}
            reason = body.get("reason", "") if isinstance(body, dict) else ""
            said = await tiktokstudio.reject(settings, video_id, str(reason or ""))
        else:
            return JSONResponse({"ok": False, "said": "Unknown action."}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"ok": False, "said": str(exc)}, status_code=400)
    card = await asyncio.to_thread(lambda: tiktokstudio.studio_card(settings, tiktokstudio_store.load(settings)))
    return {"ok": True, "said": said, "card": card}


@app.get("/station/state")
async def station_state():
    """What the HUD's station world shows: videos being made, waiting for approval at LSX, and approved lately."""
    return await asyncio.to_thread(station.state, settings)


@app.get("/tiktok/connect")
async def tiktok_connect(account: str):
    try:
        name = tiktokstudio_store.account(await asyncio.to_thread(tiktokstudio_store.load, settings), account)["name"]
        return RedirectResponse(tiktok.login_url(settings, name))
    except ValueError as exc:
        return HTMLResponse(f"<p>{html.escape(str(exc))}</p>", status_code=400)


@app.get("/tiktok/callback")
async def tiktok_callback(state: str = "", code: str = "", error: str = "", error_description: str = ""):
    if error or not code:
        return HTMLResponse(f"<p>TikTok didn't connect: {html.escape(error_description or error or 'no code')}.</p>")
    try:
        name = await tiktok.finish_login(app.state.http, settings, state, code)
    except (ValueError, httpx.HTTPError) as exc:
        return HTMLResponse(f"<p>{html.escape(str(exc))}</p>", status_code=400)
    return HTMLResponse(f"<p style='font:18px sans-serif'>Connected {html.escape(name)} to TikTok. "
                        "You can close this tab and go back to Alfred.</p>")


@app.get("/screen/file")
async def screen_file(path: str, download: bool = False):
    """A memory-folder file for a pop-up window. Anything that isn't a picture, PDF, sound, video or plain text
    is sent as a download, and nothing can run scripts as the Jarvis page."""
    try:
        found = await asyncio.to_thread(screen.memory_path, settings, path)
    except ValueError as e:
        return Response(str(e), status_code=404)
    mime = screen.inline_type(found)
    headers = {"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"}
    if mime == "application/pdf":
        headers = {"X-Content-Type-Options": "nosniff"}  # the browser's PDF viewer won't run in a sandbox
    if mime is None or download:
        return FileResponse(found, headers=headers, filename=found.name, media_type="application/octet-stream")
    if mime.startswith("text/") or mime == "application/json":
        mime = "text/plain; charset=utf-8"
    return FileResponse(found, headers=headers, media_type=mime)


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
    if not allowed_host(ws.headers.get("host")) or not same_origin(ws) or not logged_in(ws.cookies) or (via_phone_link(ws) and not settings.password):
        await ws.close(code=1008)
        return
    await ws.accept()
    http = ws.app.state.http
    pending: dict[int, asyncio.Future] = {}
    next_id = itertools.count(1)

    async def speak(text: str, quiet: bool = False, join: bool = False) -> None:
        """Say text aloud; quiet leaves it out of the transcript (notifications show it instead), and join
        adds it to Alfred's last transcript line (the next sentence of a streamed answer).

        Each part is sent as soon as its voice is ready, so Alfred starts talking after the first sentence
        instead of waiting for the whole answer to be voiced. The first message carries the full text for
        the transcript; the rest are marked as parts of it.
        """
        print(f"  Jarvis: {text}", flush=True)
        first = True
        async for part, audio in tts.stream(http, settings, text):
            await ws.send_json({
                "type": "say",
                "text": text if first else part,
                "speak": part,
                "audio": base64.b64encode(audio).decode() if audio else "",
                "quiet": quiet or not first,
                "part": not first,
                "join": join and first,
            })
            first = False

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

    async def turn(msg: dict) -> None:
        if msg.get("type") == "activate":
            timers.on_break = False  # clicking the orb ends a break too
            await brain.activate(speak)
        elif text := str(msg.get("text", "")).strip():
            print(f"  You:    {text}", flush=True)
            if timers.wakes_from_break(settings, text):
                await brain.handle(text, speak)
            else:
                print("  (on a break: ignored until called by name)", flush=True)

    async def worker() -> None:
        # One failed turn must never stop the next: without "done" the page waits forever and stops listening.
        while True:
            msg = await inbox.get()
            try:
                await turn(msg)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[jarvis] Turn failed: {exc!r}", flush=True)
                try:
                    await ws.send_json({"type": "note", "text": "Sorry, that went wrong. Please say it again."})
                except Exception:
                    return  # the page has gone
            try:
                await ws.send_json({"type": "done"})
            except Exception:
                return  # the page has gone

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
    # Browsers only allow the microphone on https or localhost, so point at the address that works.
    print(f"  Open  http://localhost:{settings.port}  on this PC (the microphone only works on localhost or https)", flush=True)
    uvicorn.run(app, host=settings.host, port=settings.port)
