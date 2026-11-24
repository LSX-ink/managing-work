"""Alfred asks Claude (owner, 24 Nov 2026: "when he's thinking can he not also ask you the question?" ... "build").

When Alfred can't answer from his own tools and memory, or the user says "ask Claude", he puts the question to Claude
Code on this PC (the `claude` command, run in the background with -p) and reads out the answer. Each question goes
to a fresh Claude that can only look things up: it may read files, search them and search the web, but it can't
change files, run commands, send anything or deploy. Changes still go through the user to Claude directly.

Claude is given the newest "Claude's work log" notes from Alfred's memory, so it knows what was done recently.
"""

import os
import shutil
import subprocess

from config import ROOT, Settings

NAMES = {"ask_claude"}
TIMEOUT = 180  # seconds; Claude can take a minute or two when it has to read files
MAX_QUESTION = 2000
MAX_ANSWER = 4000
READ_ONLY_TOOLS = "Read,Grep,Glob,WebSearch,WebFetch"
NEVER_TOOLS = "Bash,PowerShell,Edit,Write,NotebookEdit,Agent,Task"
OFF = "Asking Claude is turned off (JARVIS_ASK_CLAUDE=false)."
MISSING = "Claude Code isn't installed on this PC, so I can't ask Claude."


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


def build_prompt(question: str, notes: str) -> str:
    return (
        "Alfred, the user's voice assistant, is asking you a question on the user's behalf. The user runs Kinetic "
        "Web Designs (a web design business) and Alfred, both on this PC. Answer in plain spoken British English, "
        "in two to five short sentences that Alfred can read aloud: no Markdown, lists or links read character by "
        "character. You may read files, search them and search the web. Do not change anything: no editing files, "
        "no commands, no emails, no deploying. If the answer needs a change, say what you'd change and that the "
        "user should ask Claude directly in the project chat. If you don't know, say so; never guess.\n\n"
        + (f"Recent notes from Claude's work log (Alfred's memory):\n{notes}\n\n" if notes else "")
        + f"Alfred's question: {question}"
    )


def ask(settings: Settings, question: str) -> str:
    question = str(question or "").strip()[:MAX_QUESTION]
    if not question:
        raise ValueError("Say what to ask Claude.")
    if not enabled():
        return OFF
    exe = claude_command()
    if not exe:
        return MISSING
    cmd = [exe, "-p", build_prompt(question, background(settings, question)), "--output-format", "text",
           "--allowedTools", READ_ONLY_TOOLS, "--disallowedTools", NEVER_TOOLS]
    try:
        done = subprocess.run(cmd, cwd=str(ROOT.parent), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=TIMEOUT,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return "Claude took too long to answer, so I stopped waiting. Try asking it in a simpler way."
    answer = (done.stdout or "").strip()
    if done.returncode != 0 or not answer:
        why = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no answer"]
        return f"I couldn't get an answer from Claude ({why[0][:160]})."
    return "Claude says: " + answer[:MAX_ANSWER]


def tool_definitions() -> list[dict]:
    return [{
        "name": "ask_claude",
        "description": "Ask Claude (Claude Code on this PC, the assistant that builds and runs Kinetic Web Designs' "
                       "websites, HQ and Alfred himself) a question, and read out its answer. Use it when the user "
                       "says 'ask Claude', or when a question is about Kinetic's clients, websites, code, HQ, emails "
                       "or what Claude has done, and your own tools and long_term_memory can't answer it. Claude "
                       "can only look things up here, never change anything. It takes 20 seconds to 2 minutes, so "
                       "say 'Let me check with Claude' first.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The full question, with any names spelt "
                                                                          "correctly (e.g. ChefMotso, TKS Consulting)."}},
            "required": ["question"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    return ask(settings, args.get("question", ""))
