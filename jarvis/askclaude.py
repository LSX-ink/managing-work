"""Alfred asks Claude (owner, 24 Nov 2026: "when he's thinking can he not also ask you the question?" ... "build").

When Alfred can't answer from his own tools and memory, or the user says "ask Claude", he puts the request to Claude
Code on this PC (the `claude` command, run in the background with -p) and reads out the answer. Claude is given the
newest "Claude's work log" notes from Alfred's memory, so it knows what was done recently.

Three modes (owner, 24 Nov 2026: "Let Alfred's ask Claude make changes when I tell him to (websites, files, settings),
not just read. Keep these safeguards: he reads back what he's about to do and waits for my yes before anything
outward-facing (sending emails or DMs, deploying a live site, payments), never types passwords or card details, and
Vera still checks every outreach email."):
- ask: read-only. Claude can read files and search, nothing else.
- change: the user told Alfred to change something. Claude may edit files and settings and run local commands, but
  anything outward-facing is blocked: deploying or publishing, pushing code, sending emails or messages, payments.
  If the job needs one, Claude stops and replies "NEEDS YES:" with the exact action, which Alfred reads back.
- outward: only after the user said yes to that exact read-back. Claude does that one action and nothing more.
In every mode Claude never types passwords, card details or other secrets, and never sends outreach emails itself:
those go through HQ, where Vera checks every one.
"""

import os
import shutil
import subprocess

from config import ROOT, Settings

NAMES = {"ask_claude"}
MODES = ["ask", "change", "outward"]
TIMEOUT = {"ask": 180, "change": 900, "outward": 900}  # seconds
MAX_QUESTION = 3000
MAX_ANSWER = 4000
READ_ONLY_TOOLS = "Read,Grep,Glob,WebSearch,WebFetch"
CHANGE_TOOLS = "Read,Grep,Glob,WebSearch,WebFetch,Edit,Write,Bash,PowerShell"
# Outward-facing commands are blocked in change mode at the tool level, not just by asking nicely.
OUTWARD_COMMANDS = ["wrangler", "deploy", "git push", "gh ", "curl", "Invoke-WebRequest", "Invoke-RestMethod",
                    "Send-MailMessage", "smtp", "stripe", "npm publish"]
NEVER_TOOLS = "NotebookEdit,Agent,Task,mcp__*"
OFF = "Asking Claude is turned off (JARVIS_ASK_CLAUDE=false)."
MISSING = "Claude Code isn't installed on this PC, so I can't ask Claude."
NEEDS_YES = "NEEDS YES:"
HOME = os.path.expanduser("~")

RULES = (
    "Rules that always apply: never type, paste or store passwords, card numbers, bank details or other secrets, and "
    "never read .env files aloud or copy keys out of them. Never send Kinetic outreach emails yourself: new emails "
    "and follow-ups only go through HQ, where Vera checks every one. Never make or approve payments. ")


def enabled() -> bool:
    return os.getenv("JARVIS_ASK_CLAUDE", "true").strip().lower() not in ("0", "false", "no", "off")


def claude_command() -> str | None:
    return shutil.which("claude") or next((p for p in (os.path.expanduser(r"~\.local\bin\claude.exe"),
                                                       os.path.expanduser("~/.local/bin/claude"))
                                           if os.path.exists(p)), None)


def background(settings: Settings, question: str) -> str:
    """The newest work-log notes about the question, so Claude starts from what was done."""
    try:
        import alfredmem
        if not alfredmem.enabled(settings):
            return ""
        notes = alfredmem.search(settings, "Claude's work log " + question, 6)
        return "" if notes.startswith("Nothing about") else notes[:5000]
    except Exception:
        return ""


def build_prompt(question: str, notes: str, mode: str = "ask") -> str:
    head = ("Alfred, the user's voice assistant, is passing on a request from the user. The user runs Kinetic Web "
            "Designs (a web design business) and Alfred, both on this PC (code in C:\\Users\\Thato\\managing-work-hq, "
            "websites in C:\\Users\\Thato\\kinetic-repo). Reply in plain spoken British English, in two to five short "
            "sentences that Alfred can read aloud: no Markdown, lists or links read character by character. ")
    if mode == "ask":
        how = ("You may read files, search them and search the web. Do not change anything. If the answer needs a "
               "change, say what you'd change; the user can tell Alfred to go ahead. If you don't know, say so; never "
               "guess. ")
    elif mode == "change":
        how = ("The user told Alfred to make this change, so make it: edit files, settings and website source, and "
               "run local commands and tests as needed, then check it worked. Do NOT do anything outward-facing in "
               "this step: no deploying or publishing a live site, no pushing code, no sending emails, DMs or "
               "messages, no payments. If finishing the job needs one of those, make every local change first, then "
               f"end your reply with a line starting '{NEEDS_YES}' that says exactly what you would do (for example "
               f"'{NEEDS_YES} deploy chefmotso.com with the new shop pictures'). Alfred will read it to the user and "
               "only come back if they say yes. Say plainly what you changed and what you didn't. ")
    else:
        how = ("The user heard Alfred read back the action below and said yes to it. Do exactly that one action "
               "(for example deploy that site), check it worked, and say what happened. Do nothing beyond it. ")
    return (head + how + RULES + "\n\n"
            + (f"Recent notes from Claude's work log (Alfred's memory):\n{notes}\n\n" if notes else "")
            + ("The action the user said yes to: " if mode == "outward" else "The user's request: ") + question)


def command(exe: str, prompt: str, mode: str) -> list[str]:
    cmd = [exe, "-p", prompt, "--output-format", "text"]
    if mode == "ask":
        return cmd + ["--allowedTools", READ_ONLY_TOOLS, "--disallowedTools", "Bash,PowerShell,Edit,Write," + NEVER_TOOLS]
    blocked = NEVER_TOOLS
    if mode == "change":
        blocked += "," + ",".join(f"Bash(*{c}*),PowerShell(*{c}*)" for c in OUTWARD_COMMANDS)
    return cmd + ["--allowedTools", CHANGE_TOOLS, "--disallowedTools", blocked, "--permission-mode", "acceptEdits"]


def ask(settings: Settings, question: str, mode: str = "ask", user_said_yes: bool = False) -> str:
    question = str(question or "").strip()[:MAX_QUESTION]
    mode = mode if mode in MODES else "ask"
    if not question:
        raise ValueError("Say what to ask Claude.")
    if mode == "outward" and not user_said_yes:
        return ("I need the user's yes first. Read back exactly what Claude will do, and only call outward again "
                "after they say yes.")
    if not enabled():
        return OFF
    exe = claude_command()
    if not exe:
        return MISSING
    cmd = command(exe, build_prompt(question, background(settings, question), mode), mode)
    try:
        done = subprocess.run(cmd, cwd=HOME if mode != "ask" else str(ROOT.parent), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT[mode],
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return "Claude took too long, so I stopped waiting. Some changes may be half done; ask Claude what state it's in."
    answer = (done.stdout or "").strip()
    if done.returncode != 0 or not answer:
        why = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no answer"]
        return f"I couldn't get an answer from Claude ({why[0][:160]})."
    answer = answer[:MAX_ANSWER]
    if NEEDS_YES in answer:
        return ("Claude says: " + answer + "\n\n[For Alfred: read the NEEDS YES action back to the user word for word "
                "and ask if you should go ahead. Only if they say yes, call ask_claude with mode outward, that exact "
                "action as the question, and user_said_yes true.]")
    return "Claude says: " + answer


def tool_definitions() -> list[dict]:
    return [{
        "name": "ask_claude",
        "description": "Pass a question or a job to Claude (Claude Code on this PC, the assistant that builds and runs "
                       "Kinetic Web Designs' websites, HQ and Alfred himself) and read out its answer. "
                       "mode ask (default): questions about Kinetic's clients, websites, code, HQ or what Claude did, "
                       "when your own tools and long_term_memory can't answer; read-only. "
                       "mode change: only when the user tells you to change something (a website, a file, a "
                       "setting). Claude makes local changes but nothing outward-facing. If its answer contains "
                       "'NEEDS YES:', read that exact action back to the user and wait for their yes. "
                       "mode outward: only after the user said yes to that read-back (deploying a live site, sending, "
                       "payments); pass the exact action and user_said_yes true. Never pass passwords or card "
                       "details. Outreach emails always go through Vera, never through Claude. "
                       "It takes 20 seconds to several minutes, so say 'Let me check with Claude' or 'I'll ask Claude "
                       "to do that' first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The full question or job, in the user's words, with "
                                                              "names spelt correctly (e.g. ChefMotso, TKS Consulting)."},
                "mode": {"type": "string", "enum": MODES},
                "user_said_yes": {"type": "boolean", "description": "outward only: true once the user said yes to "
                                                                    "the exact action you read back."},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    return ask(settings, args.get("question", ""), args.get("mode") or "ask", bool(args.get("user_said_yes")))
