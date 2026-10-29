"""The HQ brain: one SQLite file every agent writes to and reads from.

events  - everything that happened (who, what, when), newest last; the office's live feed
facts   - the latest value of each thing worth knowing (key -> JSON value), e.g. health.site or numbers.week
runs    - each time an agent worked: when it started, finished, whether it worked and a one-line result

Every day's events are also written out as a plain markdown journal (memory/Kinetic Web Designs/HQ/<date>.md) so
the brain can be read in Obsidian or any text editor. Nothing secret is ever stored here.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, ts REAL, agent TEXT, kind TEXT, text TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS events_agent ON events(agent, ts);
CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, value TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, agent TEXT, started REAL, finished REAL, ok INTEGER, result TEXT);
"""
KINDS = {"info", "win", "warn", "error", "start", "done"}


class Brain:
    def __init__(self, path: Path, journal_dir: Path | None = None):
        self.path, self.journal_dir = Path(path), journal_dir
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._listeners: list = []
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    # ---- writing ----
    def log(self, agent: str, text: str, kind: str = "info", data: dict | None = None) -> dict:
        kind = kind if kind in KINDS else "info"
        row = {"ts": time.time(), "agent": agent, "kind": kind, "text": str(text)[:2000], "data": data or {}}
        with self._lock, self._db() as db:
            cur = db.execute("INSERT INTO events (ts, agent, kind, text, data) VALUES (?, ?, ?, ?, ?)",
                             (row["ts"], agent, kind, row["text"], json.dumps(row["data"], default=str)))
            row["id"] = cur.lastrowid
        self._journal(row)
        for listener in list(self._listeners):
            try:
                listener(row)
            except Exception:
                pass
        return row

    def set(self, key: str, value) -> None:
        with self._lock, self._db() as db:
            db.execute("INSERT INTO facts (key, value, ts) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                       "value = excluded.value, ts = excluded.ts", (key, json.dumps(value, default=str), time.time()))

    def run_started(self, agent: str) -> int:
        with self._lock, self._db() as db:
            return db.execute("INSERT INTO runs (agent, started) VALUES (?, ?)", (agent, time.time())).lastrowid

    def run_finished(self, run_id: int, ok: bool, result: str) -> None:
        with self._lock, self._db() as db:
            db.execute("UPDATE runs SET finished = ?, ok = ?, result = ? WHERE id = ?",
                       (time.time(), 1 if ok else 0, str(result)[:500], run_id))

    # ---- reading ----
    def get(self, key: str, default=None):
        with self._db() as db:
            row = db.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def facts(self, prefix: str = "") -> dict:
        with self._db() as db:
            rows = db.execute("SELECT key, value, ts FROM facts WHERE key LIKE ? ORDER BY key", (prefix + "%",)).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def events(self, agent: str | None = None, limit: int = 50, after: int = 0) -> list[dict]:
        sql, args = "SELECT * FROM events WHERE id > ?", [after]
        if agent:
            sql, args = sql + " AND agent = ?", args + [agent]
        with self._db() as db:
            rows = db.execute(sql + " ORDER BY id DESC LIMIT ?", args + [limit]).fetchall()
        return [self._event(r) for r in reversed(rows)]

    def search(self, text: str, limit: int = 30) -> list[dict]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM events WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
                              (f"%{text}%", limit)).fetchall()
        return [self._event(r) for r in rows]

    def last_run(self, agent: str) -> dict | None:
        with self._db() as db:
            r = db.execute("SELECT * FROM runs WHERE agent = ? ORDER BY id DESC LIMIT 1", (agent,)).fetchone()
        return dict(r) if r else None

    def count_today(self, agent: str, kind: str | None = None) -> int:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        sql, args = "SELECT COUNT(*) FROM events WHERE agent = ? AND ts >= ?", [agent, start]
        if kind:
            sql, args = sql + " AND kind = ?", args + [kind]
        with self._db() as db:
            return db.execute(sql, args).fetchone()[0]

    def events_today(self, agent: str, kind: str | None = None) -> list[dict]:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        sql, args = "SELECT * FROM events WHERE agent = ? AND ts >= ?", [agent, start]
        if kind:
            sql, args = sql + " AND kind = ?", args + [kind]
        with self._db() as db:
            return [self._event(r) for r in db.execute(sql + " ORDER BY id", args).fetchall()]

    def runs_today(self, agent: str) -> int:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        with self._db() as db:
            return db.execute("SELECT COUNT(*) FROM runs WHERE agent = ? AND started >= ? AND ok = 1",
                              (agent, start)).fetchone()[0]

    def listen(self, fn) -> None:
        self._listeners.append(fn)

    def unlisten(self, fn) -> None:
        if fn in self._listeners:
            self._listeners.remove(fn)

    @staticmethod
    def _event(r) -> dict:
        d = dict(r)
        d["data"] = json.loads(d.get("data") or "{}")
        return d

    def _journal(self, row: dict) -> None:
        if not self.journal_dir or row["kind"] in ("start",):
            return
        try:
            self.journal_dir.mkdir(parents=True, exist_ok=True)
            when = datetime.fromtimestamp(row["ts"])
            f = self.journal_dir / f"{when:%Y-%m-%d}.md"
            if not f.exists():
                f.write_text(f"# Kinetic HQ journal, {when:%A %d %B %Y}\n\n", encoding="utf-8")
            mark = {"win": "✅", "warn": "⚠️", "error": "❌", "done": "•"}.get(row["kind"], "•")
            with f.open("a", encoding="utf-8") as out:
                out.write(f"- {when:%H:%M} {mark} **{row['agent']}**: {row['text']}\n")
        except OSError:
            pass
