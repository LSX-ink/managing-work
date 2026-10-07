"""The MCP bridge: Alfred uses the same MCP servers the user added to the Claude desktop app (Playwright, Perplexity,
Firecrawl...). It reads the app's claude_desktop_config.json, starts each server the first time Alfred needs it and
keeps it running, then lists and calls its tools.

The servers speak MCP over stdio: one JSON-RPC message per line. This is a small client for just the parts Alfred
needs (initialize, tools/list, tools/call), so there's no extra package to install. The API keys in the config's "env"
go to the server processes only; Alfred never sees them. Turn the bridge off with JARVIS_MCP=false, or point it at
another config file with JARVIS_MCP_CONFIG.

Online MCPs (a "url" instead of a command, like Higgsfield) run through mcp-remote (npx -y mcp-remote URL), which
opens the browser to sign in the first time and remembers the login. Higgsfield is always on the list.
"""

import atexit
import glob
import json
import os
import shutil
import subprocess
import threading
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

from config import Settings

NAMES = {"mcp_bridge"}
ACTIONS = ["servers", "tools", "call", "restart"]
PROTOCOL = "2025-06-18"
START_SECONDS = 180  # the first start can download the server (npx -y ...) or wait for a browser sign-in
REMOTES = {"higgsfield": "https://mcp.higgsfield.ai/mcp"}  # online MCPs Alfred always has, unless the app lists them
CALL_SECONDS = 120
MAX_TEXT = 8000
MAX_TOOLS_TEXT = 12000

_servers: dict = {}
_lock = threading.Lock()


def tool_definitions() -> list[dict]:
    return [{
        "name": "mcp_bridge",
        "description": "Use the MCP servers the user added to the Claude desktop app on this PC (for example "
                       "Perplexity for web research, Firecrawl for scraping sites, Playwright for a browser) plus Higgsfield "
                       "(AI images and videos, including anime): "
                       "'ask Perplexity...', 'use Firecrawl to scrape...', 'what MCPs have I got'. servers lists them; "
                       "tools (server) lists that server's tools with their inputs; call (server, tool, arguments) "
                       "runs one; restart (server) restarts a stuck one. Check tools first if you don't know a tool's "
                       "inputs. Ask the user before a tool that sends, buys, posts or deletes something, and before any "
                       "Higgsfield generation (each one spends the user's Higgsfield credits; check balance first). "
                       "The first Higgsfield use opens the browser to sign in.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "server": {"type": "string", "description": "The server's name in the Claude app, e.g. perplexity."},
                "tool": {"type": "string", "description": "call: the tool's name, from tools."},
                "arguments": {"type": "object", "description": "call: the tool's inputs."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


# ---- the Claude app's config ----------------------------------------------------------------------------------

def config_paths() -> list[Path]:
    """Where the Claude desktop app keeps its MCP list: the normal install, then the Microsoft Store one."""
    if os.getenv("JARVIS_MCP_CONFIG", "").strip():
        return [Path(os.getenv("JARVIS_MCP_CONFIG").strip())]
    found = []
    if os.getenv("APPDATA"):
        found.append(Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json")
    if os.getenv("LOCALAPPDATA"):
        found += [Path(p) for p in glob.glob(os.path.join(
            os.environ["LOCALAPPDATA"], "Packages", "Claude_*", "LocalCache", "Roaming", "Claude",
            "claude_desktop_config.json"))]
    home = Path.home()
    found += [home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
              home / ".config" / "Claude" / "claude_desktop_config.json"]
    return found


def remote(url: str) -> dict:
    return {"command": "npx", "args": ["-y", "mcp-remote", url], "env": {}}


def load_config() -> dict:
    """{name: {"command", "args", "env"}} for every server in the Claude app's config, plus Higgsfield."""
    found = app_config()
    for name, url in REMOTES.items():
        if not any(n.lower() == name for n in found):
            found[name] = remote(url)
    return found


def app_config() -> dict:
    for path in config_paths():
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as exc:
                raise ValueError(f"I couldn't read the Claude app's MCP list ({path.name}): {exc}") from None
            servers = data.get("mcpServers") or {}
            found = {}
            for name, spec in servers.items():
                if isinstance(spec, dict) and spec.get("command"):
                    found[name] = {"command": spec["command"], "args": [str(a) for a in spec.get("args") or []],
                                   "env": {k: str(v) for k, v in (spec.get("env") or {}).items()}}
                elif isinstance(spec, dict) and str(spec.get("url", "")).startswith("https://"):
                    found[name] = remote(spec["url"])
            return found
    return {}


def enabled() -> bool:
    return os.getenv("JARVIS_MCP", "true").strip().lower() not in ("0", "false", "no", "off")


# ---- one running server ---------------------------------------------------------------------------------------

class Server:
    def __init__(self, name: str, spec: dict):
        self.name, self.spec = name, spec
        self.proc = None
        self.pending: dict[int, Future] = {}
        self.next_id = 0
        self.write_lock = threading.Lock()
        self.tools: list[dict] = []
        self.errors: list[str] = []

    def start(self) -> None:
        command = shutil.which(self.spec["command"]) or self.spec["command"]  # npx -> npx.cmd on Windows
        env = {**os.environ, **self.spec["env"]}
        try:
            self.proc = subprocess.Popen(
                [command, *self.spec["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=env, text=True, encoding="utf-8", errors="replace", bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            hint = " Is Node.js installed?" if self.spec["command"] in ("npx", "node") else ""
            raise ValueError(f"I couldn't start the {self.name} MCP: {exc}.{hint}") from None
        threading.Thread(target=self._read, daemon=True, name=f"mcp-{self.name}").start()
        threading.Thread(target=self._read_errors, daemon=True, name=f"mcp-{self.name}-err").start()
        self.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                    "clientInfo": {"name": "alfred", "version": "1.0"}}, START_SECONDS)
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.tools = self.request("tools/list", {}, START_SECONDS).get("tools", [])

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def send(self, message: dict) -> None:
        with self.write_lock:
            try:
                self.proc.stdin.write(json.dumps(message) + "\n")
                self.proc.stdin.flush()
            except (OSError, ValueError):
                raise ValueError(f"The {self.name} MCP stopped. {self.last_error()}".strip()) from None

    def request(self, method: str, params: dict, timeout: float) -> dict:
        with self.write_lock:
            self.next_id += 1
            ident = self.next_id
        done = Future()
        self.pending[ident] = done
        self.send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        try:
            reply = done.result(timeout)
        except FutureTimeout:
            raise ValueError(f"The {self.name} MCP didn't answer in {timeout:g} seconds.") from None
        finally:
            self.pending.pop(ident, None)
        if "error" in reply:
            raise ValueError(f"{self.name}: {reply['error'].get('message', 'error')}")
        return reply.get("result") or {}

    def _read(self) -> None:
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue  # a server printing something that isn't MCP
            if not isinstance(message, dict):
                continue
            if "method" in message and "id" in message:  # the server asking us something (ping, roots): answer simply
                reply = {"roots": []} if message["method"] == "roots/list" else {}
                try:
                    self.send({"jsonrpc": "2.0", "id": message["id"], "result": reply})
                except ValueError:
                    pass
            elif message.get("id") in self.pending:
                self.pending[message["id"]].set_result(message)
        gone = ValueError(f"The {self.name} MCP stopped. {self.last_error()}".strip())
        for waiting in list(self.pending.values()):
            if not waiting.done():
                waiting.set_exception(gone)

    def _read_errors(self) -> None:
        for line in self.proc.stderr:
            if line.strip():
                self.errors = (self.errors + [line.strip()])[-5:]

    def last_error(self) -> str:
        text = self.errors[-1] if self.errors else ""
        for secret in self.spec["env"].values():  # never echo an API key back
            if len(secret) >= 6:
                text = text.replace(secret, "***")
        return text[:200]

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()


def get_server(name: str) -> Server:
    specs = load_config()
    if not specs:
        raise ValueError("There are no MCPs on this PC yet (Settings > Developer in the Claude app).")
    match = next((n for n in specs if n.lower() == (name or "").strip().lower()), None)
    if match is None:
        raise ValueError(f"There's no MCP called '{name}'. The ones in the Claude app are: {', '.join(specs)}.")
    with _lock:
        server = _servers.get(match)
        if server is None or not server.alive() or server.spec != specs[match]:
            if server is not None:
                server.stop()
            server = Server(match, specs[match])
            try:
                server.start()
            except Exception:
                server.stop()
                raise
            _servers[match] = server
    return server


@atexit.register
def stop_all() -> None:
    for server in list(_servers.values()):
        server.stop()
    _servers.clear()


# ---- what Alfred sees ------------------------------------------------------------------------------------------

def describe_tools(server: Server) -> str:
    rows = []
    for tool in server.tools:
        schema = tool.get("inputSchema") or {}
        need = set(schema.get("required") or [])
        inputs = ", ".join(f"{k}{'*' if k in need else ''} ({v.get('type', 'any')})"
                           for k, v in (schema.get("properties") or {}).items())
        rows.append(f"- {tool['name']}: {(tool.get('description') or '').strip()[:300]}\n  inputs: {inputs or 'none'}")
    text = f"{server.name} tools (* = required):\n" + "\n".join(rows)
    return text if len(text) <= MAX_TOOLS_TEXT else text[:MAX_TOOLS_TEXT] + "\n... (more tools not shown)"


def result_content(server: Server, result: dict):
    """An MCP tool result as Alfred's tool output: text, or a list with any pictures it returned."""
    texts, images = [], []
    for part in result.get("content") or []:
        if part.get("type") == "text":
            texts.append(part.get("text", ""))
        elif part.get("type") == "image" and part.get("data"):
            images.append({"type": "image", "source": {"type": "base64", "media_type": part.get("mimeType", "image/png"),
                                                       "data": part["data"]}})
        elif part.get("type") == "resource":
            texts.append(str((part.get("resource") or {}).get("text", ""))[:2000])
    if not texts and result.get("structuredContent") is not None:
        texts.append(json.dumps(result["structuredContent"])[:MAX_TEXT])
    text = "\n".join(t for t in texts if t).strip() or "(no text came back)"
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "\n... (cut short)"
    if result.get("isError"):
        text = f"The {server.name} tool reported a problem: {text}"
    return [*images, {"type": "text", "text": text}] if images else text


def run_tool(name: str, args: dict, settings: Settings, http=None):
    if not enabled():
        return "The MCP bridge is switched off (JARVIS_MCP=false in .env)."
    action = args.get("action")
    if action == "servers":
        specs = load_config()
        if not specs:
            return "There are no MCPs in the Claude app on this PC yet."
        return "MCPs Alfred can use: " + ", ".join(
            f"{n} ({'running' if n in _servers and _servers[n].alive() else 'starts when needed'})" for n in specs)
    if action == "restart":
        with _lock:
            old = _servers.pop(next((n for n in _servers if n.lower() == str(args.get("server", "")).lower()), ""),
                               None)
        if old:
            old.stop()
        server = get_server(args.get("server", ""))
        return f"Restarted {server.name}: {len(server.tools)} tools."
    if action == "tools":
        return describe_tools(get_server(args.get("server", "")))
    if action == "call":
        server = get_server(args.get("server", ""))
        tool = str(args.get("tool", "")).strip()
        if tool not in {t["name"] for t in server.tools}:
            raise ValueError(f"{server.name} has no tool '{tool}'. Its tools are: "
                             f"{', '.join(t['name'] for t in server.tools)}.")
        result = server.request("tools/call", {"name": tool, "arguments": args.get("arguments") or {}}, CALL_SECONDS)
        return result_content(server, result)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
