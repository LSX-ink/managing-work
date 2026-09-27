"""Email filing rules: save matching emails (and their attachments) into a memory folder automatically.

"Alfred, save every VGC payslip email into my HS2 folder" adds a rule. Jarvis then checks the inbox (read-only,
nothing is marked as read) and files each matching email once: its attachments, plus the email text, named
"<name> <date the email was sent>", e.g. "VGC Payslip 2026-09-27.pdf". Rules live in email-rules.json in the
memory folder; what has been filed is remembered in .filed.json so nothing is saved twice.
"""

import asyncio
import email
import email.policy
import email.utils
import imaplib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import memory
from config import Settings

CATCH_UP_DAYS = 120  # a new rule files matching emails from this far back


def rules_path(settings: Settings) -> Path:
    return memory.root(settings) / "email-rules.json"


def filed_path(settings: Settings) -> Path:
    return memory.root(settings) / ".filed.json"


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def rules(settings: Settings) -> list[dict]:
    found = _load(rules_path(settings), [])
    return found if isinstance(found, list) else []


def save_rules(settings: Settings, items: list[dict]) -> None:
    memory.names(settings)  # makes the memory folder
    rules_path(settings).write_text(json.dumps(items, indent=2), encoding="utf-8")


def add_rule(settings: Settings, sender: str, words: str, folder: str, name: str) -> dict:
    sender, words = sender.strip(), words.strip()
    if not sender:
        raise ValueError("Say who the emails come from, e.g. VGC.")
    try:
        target = memory.folder(settings, folder)
    except ValueError:
        if "/" in folder or "\\" in folder:
            raise
        target = memory.create_folder(settings, "", folder)  # a new folder of Alfred's own
    rule = {"from": sender, "words": words, "folder": target.relative_to(memory.root(settings)).as_posix(),
            "name": memory.safe_name(name.strip() or f"{sender} email", "file name")}
    save_rules(settings, [r for r in rules(settings) if (r["from"].lower(), r["words"].lower()) !=
                          (sender.lower(), words.lower())] + [rule])
    return rule


def remove_rule(settings: Settings, sender: str) -> int:
    kept = [r for r in rules(settings) if sender.strip().lower() not in r["from"].lower()]
    removed = len(rules(settings)) - len(kept)
    save_rules(settings, kept)
    return removed


def matches(rule: dict, sender: str, subject: str) -> bool:
    """From contains the rule's sender, and the subject has any of its words (payslip also matches pay slip)."""
    if rule["from"].lower() not in sender.lower():
        return False
    words = [w for w in re.split(r"[,\s]+", rule.get("words", "").lower()) if w]
    squashed = re.sub(r"[\s_-]+", "", subject.lower())
    return not words or any(w in subject.lower() or w in squashed for w in words)


def _text(msg: email.message.EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    body = part.get_content() if part else ""
    if part is not None and part.get_content_type() == "text/html":
        body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", body, flags=re.I)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"[ \t]+", " ", re.sub(r"&nbsp;", " ", body))
    return body.strip()


def file_message(settings: Settings, rule: dict, raw: bytes) -> list[Path]:
    """Save one email into the rule's folder: every attachment, plus the email itself as text."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    try:
        sent = email.utils.parsedate_to_datetime(msg["Date"]).astimezone()
    except (TypeError, ValueError):
        sent = datetime.now()
    base = f"{rule['name']} {sent:%Y-%m-%d}"
    target = memory.folder(settings, rule["folder"], create=True)
    saved = []
    attachments = [p for p in msg.iter_attachments()   # real attachments, not logos inside the email
                   if (p.get_filename() or p.get_content_maintype() == "application")
                   and not (p.get_content_disposition() == "inline" and p.get_content_maintype() == "image")]
    for part in attachments:
        ext = Path(part.get_filename() or "").suffix or ".bin"
        data = part.get_payload(decode=True) or b""
        name = memory.safe_name(f"{base}{ext}"[-60:], "file name")
        saved.append(memory.save_file(settings, rule["folder"], name, data))
    header = f"From: {msg['From']}\nDate: {msg['Date']}\nSubject: {msg['Subject']}\n\n"
    note = memory.unique_path(target / memory.safe_name(f"{base}.txt"[-60:], "file name"))
    note.write_text(header + _text(msg), encoding="utf-8")
    return saved + [note]


def _key(folder: str, message_id: str, uid: int) -> str:
    return f"{folder}|{message_id or uid}"


def run_once(settings: Settings, days: int = 2) -> list[Path]:
    """File every matching email from the last few days that hasn't been filed yet."""
    active = rules(settings)
    if not active:
        return []
    done = set(_load(filed_path(settings), []))
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    saved: list[Path] = []
    with imaplib.IMAP4_SSL(settings.email_imap_host) as imap:
        imap.login(settings.email_address, settings.email_app_password.replace(" ", ""))
        imap.select("INBOX", readonly=True)
        for rule in active:
            _, data = imap.uid("search", None, "SINCE", since, "FROM", f'"{rule["from"]}"')
            uids = data[0].split()[-200:]
            if not uids:
                continue
            _, heads = imap.uid("fetch", b",".join(uids), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID)])")
            for part in heads:
                if not isinstance(part, tuple):
                    continue
                uid = int(re.search(rb"UID (\d+)", part[0]).group(1))
                head = email.message_from_bytes(part[1], policy=email.policy.default)
                key = _key(rule["folder"], str(head["Message-ID"] or ""), uid)
                if key in done or not matches(rule, str(head["From"] or ""), str(head["Subject"] or "")):
                    continue
                _, body = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
                raw = next((p[1] for p in body if isinstance(p, tuple)), None)
                if raw:
                    saved += file_message(settings, rule, raw)
                    done.add(key)
    filed_path(settings).write_text(json.dumps(sorted(done)), encoding="utf-8")
    return saved


async def watch(settings: Settings, announce) -> None:
    """Check the rules every few minutes and say when something is filed."""
    while True:
        try:
            saved = await asyncio.to_thread(run_once, settings)
            if saved:
                folders = sorted({p.parent.name for p in saved})
                await announce(f"{settings.user_address.capitalize()}, I've filed {len(saved)} "
                               f"new item{'s' if len(saved) != 1 else ''} into {', '.join(folders)}.", "email")
        except Exception as exc:  # bad password, no network: say so in the console and keep trying
            print(f"[jarvis] Email filing failed: {exc}", flush=True)
        await asyncio.sleep(max(settings.email_check_seconds, 120))


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "add_email_rule",
            "description": "Automatically save emails from a sender (optionally only ones whose subject has certain "
                           "words) into a memory folder, from now on and going back a few months. Attachments and "
                           "the email text are saved, named with the given name plus the date the email was sent. "
                           "A folder that doesn't exist yet is created.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sender": {"type": "string", "description": "Who it's from: a name or address part, e.g. 'VGC'."},
                    "subject_words": {"type": "string", "description": "Optional words, any of which the subject "
                                                                         "must contain, e.g. 'payslip'."},
                    "folder": {"type": "string", "description": "Folder to save into, e.g. 'HS2' or 'Work/Payslips'."},
                    "name": {"type": "string", "description": "Start of each file name, e.g. 'VGC Payslip'."},
                },
                "required": ["sender", "folder", "name"],
                "additionalProperties": False,
            },
        },
        {
            "name": "list_email_rules",
            "description": "The automatic email filing rules that are set up.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "remove_email_rule",
            "description": "Stop automatically filing emails from a sender.",
            "input_schema": {
                "type": "object",
                "properties": {"sender": {"type": "string"}},
                "required": ["sender"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {t["name"] for t in tool_definitions()}


async def run_tool(name: str, args: dict, settings: Settings) -> str:
    if name == "add_email_rule":
        rule = await asyncio.to_thread(add_rule, settings, args["sender"], args.get("subject_words") or "",
                                       args["folder"], args["name"])
        saved = await asyncio.to_thread(run_once, settings, CATCH_UP_DAYS)
        return (f"Rule saved: emails from {rule['from']} go into {rule['folder']} as '{rule['name']} <date>'. "
                f"Filed {len(saved)} item{'s' if len(saved) != 1 else ''} from the last {CATCH_UP_DAYS} days now.")
    if name == "list_email_rules":
        found = rules(settings)
        if not found:
            return "No email filing rules."
        return "Email filing rules:\n" + "\n".join(
            f"- from {r['from']}{' with ' + r['words'] if r['words'] else ''} -> {r['folder']} as '{r['name']} <date>'"
            for r in found)
    removed = await asyncio.to_thread(remove_rule, settings, args["sender"])
    return f"Removed {removed} rule{'s' if removed != 1 else ''}."
