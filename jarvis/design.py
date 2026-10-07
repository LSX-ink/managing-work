"""Design advice from UI UX Pro Max: styles, colour palettes, font pairings, UX rules, icons, charts and
stack tips for websites, apps and pages.

The library lives in skills/ui-ux-pro-max (MIT, from github.com/nextlevelbuilder/ui-ux-pro-max-skill). Its search
script reads local CSV files only and makes no internet calls. It runs in its own Python process so its modules
(core, design_system) never mix with Alfred's.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from config import Settings

SCRIPTS = Path(__file__).resolve().parent / "skills" / "ui-ux-pro-max" / "scripts"
DOMAINS = ["style", "color", "chart", "landing", "product", "ux", "typography", "icons", "gsap", "react", "web",
           "google-fonts"]
STACKS = ["react", "nextjs", "vue", "svelte", "astro", "swiftui", "react-native", "flutter", "nuxtjs", "nuxt-ui",
          "html-tailwind", "shadcn", "jetpack-compose", "threejs", "angular", "laravel", "javafx", "wpf", "winui",
          "avalonia", "uno", "uwp"]
MAX_CHARS = 8000
TIMEOUT = 60


def command(args: dict) -> list[str]:
    query = (args.get("query") or "").strip()
    if not query:
        raise ValueError("Say what to design or look up, e.g. 'bakery website warm' or 'button focus'.")
    cmd = [sys.executable, "search.py", query]
    if args.get("design_system"):
        cmd += ["--design-system", "-f", "markdown"]
        if args.get("project"):
            cmd += ["-p", str(args["project"])]
        for dial in ("variance", "motion", "density"):
            if args.get(dial):
                cmd += [f"--{dial}", str(max(1, min(10, int(args[dial]))))]
        return cmd
    if args.get("stack"):
        if args["stack"] not in STACKS:
            raise ValueError(f"Unknown stack. Pick one of: {', '.join(STACKS)}.")
        cmd += ["--stack", args["stack"]]
    elif args.get("domain"):
        if args["domain"] not in DOMAINS:
            raise ValueError(f"Unknown domain. Pick one of: {', '.join(DOMAINS)}.")
        cmd += ["--domain", args["domain"]]
    if args.get("max_results"):
        cmd += ["-n", str(max(1, min(10, int(args["max_results"]))))]
    return cmd


def run(cmd: list[str]) -> str:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        done = subprocess.run(cmd, cwd=SCRIPTS, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return "The design library took too long to answer. Try a shorter search."
    out = (done.stdout or "").strip()
    if done.returncode != 0 or not out:
        err = (done.stderr or "").strip().splitlines()
        return "The design library couldn't answer: " + (err[-1] if err else "no results.")
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS] + "\n... (cut short)"
    return out


def tool_definitions() -> list[dict]:
    return [{
        "name": "design_advice",
        "description": "UI UX Pro Max design library (offline). For designing a website, app, page, HUD, thumbnail "
                       "or brand: set design_system=true with a short description (product, industry, mood) to get "
                       "a full plan with layout pattern, style, colour palette with hex codes, font pairing, effects "
                       "and mistakes to avoid. For a focused question, search one domain: style, color, typography, "
                       "google-fonts, ux (usability and accessibility rules), landing, product, icons, chart, gsap "
                       "(animation presets), react or web. Use stack for tips for a framework (html-tailwind, react, "
                       "nextjs, flutter...). Keep queries to 2-5 words. Summarise the result in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "2-5 words, e.g. 'bakery website warm cosy'."},
                "design_system": {"type": "boolean", "description": "True for a complete design plan."},
                "project": {"type": "string", "description": "Name for the design plan."},
                "domain": {"type": "string", "enum": DOMAINS},
                "stack": {"type": "string", "enum": STACKS},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                "variance": {"type": "integer", "minimum": 1, "maximum": 10,
                             "description": "Design plan only: 1 calm and centred, 10 bold and asymmetric."},
                "motion": {"type": "integer", "minimum": 1, "maximum": 10,
                           "description": "Design plan only: 1 subtle, 10 rich animation."},
                "density": {"type": "integer", "minimum": 1, "maximum": 10,
                            "description": "Design plan only: 1 spacious, 10 packed like a dashboard."},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }]


NAMES = {"design_advice"}


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    return await asyncio.to_thread(run, command(args))
