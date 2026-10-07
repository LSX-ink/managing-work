"""Design advice from two built-in libraries.

UI UX Pro Max: styles, colour palettes, font pairings, UX rules, icons, charts and stack tips for websites, apps
and pages.

The library lives in skills/ui-ux-pro-max (MIT, from github.com/nextlevelbuilder/ui-ux-pro-max-skill). Its search
script reads local CSV files only and makes no internet calls. It runs in its own Python process so its modules
(core, design_system) never mix with Alfred's.

Emil Kowalski's skills (MIT, from github.com/emilkowalski/skills) live in skills/emil-kowalski: written guides on UI
polish and animation (emil-design-eng, animate, review-animations, apple-design, mobile-native...). design_guide
hands Alfred a guide's text to follow. Taste Skill (MIT, from github.com/Leonxlnx/taste-skill) lives in skills/taste:
rules that stop AI-looking pages (taste-skill, minimalist-skill, brutalist-skill, soft-skill, redesign-skill,
brandkit...), read the same way. skills/anime holds anime-mj (MIT, from github.com/jawhnycooke/claude-code-anime-mj),
an anime and manga prompt builder with manga artist and studio styles, and higgsfield-anime, the user's own prompt
template for Higgsfield.

Any other folder dropped into skills/ with */SKILL.md guides is picked up too, named after its folder. skillscan checks
every library first: blocked ones are refused, and a new or changed one is scanned the first time guides are listed
or read.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import skillscan
from config import Settings

SKILLS = Path(__file__).resolve().parent / "skills"
SCRIPTS = SKILLS / "ui-ux-pro-max" / "scripts"
GUIDE_LIBRARIES = {"emil-kowalski": "Emil Kowalski", "taste": "Taste Skill", "anime": "Anime prompt"}  # labels
DOMAINS = ["style", "color", "chart", "landing", "product", "ux", "typography", "icons", "gsap", "react", "web",
           "google-fonts"]
STACKS = ["react", "nextjs", "vue", "svelte", "astro", "swiftui", "react-native", "flutter", "nuxtjs", "nuxt-ui",
          "html-tailwind", "shadcn", "jetpack-compose", "threejs", "angular", "laravel", "javafx", "wpf", "winui",
          "avalonia", "uno", "uwp"]
MAX_CHARS = 8000
GUIDE_CHARS = 20000
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
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
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


def summary(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines()[:10]:
        if line.startswith("description:"):
            text = line.split(":", 1)[1].strip().strip('"')
            return text[:160] + ("..." if len(text) > 160 else "")
    return ""


def guide_libraries() -> list[str]:
    """Folders in skills/ with */SKILL.md guides: the named ones first, then any others."""
    found = [lib for lib in skillscan.libraries() if any((SKILLS / lib).glob("*/SKILL.md"))]
    return [lib for lib in GUIDE_LIBRARIES if lib in found] + [lib for lib in found if lib not in GUIDE_LIBRARIES]


def guides() -> dict[str, Path]:
    found = {}
    for lib in guide_libraries():
        for p in sorted((SKILLS / lib).glob("*/SKILL.md")):
            found.setdefault(p.parent.name, p.parent)
    return found


def guide(args: dict, settings: Settings | None = None) -> str:
    settings = settings or Settings()
    found = guides()
    checked, fresh = skillscan.check(settings, guide_libraries())
    news = skillscan.news(checked, fresh)
    name = (args.get("guide") or "").strip().lower()
    if not name:
        out = [news] if news else []
        for lib in guide_libraries():
            who = GUIDE_LIBRARIES.get(lib, lib)
            if checked.get(lib, {}).get("verdict") == "blocked":
                out.append(f"{who} guides: blocked by the skill check ({'; '.join(checked[lib]['reasons'][:2])}).")
                continue
            out.append(f"{who} guides:")
            out += [f"- {n}: {summary(d / 'SKILL.md')}" for n, d in found.items() if d.parent.name == lib]
        return "\n".join(out)
    if name not in found:
        raise ValueError(f"No guide called {name}. Pick one of: {', '.join(found)}.")
    folder = found[name]
    refusal = skillscan.blocked_reason(settings, folder.parent.name)
    if refusal:
        return (news + "\n" if news else "") + refusal
    part = (args.get("file") or "SKILL.md").strip()
    files = sorted(p.name for p in folder.glob("*.md"))
    if part not in files:
        raise ValueError(f"{name} has these files: {', '.join(files)}.")
    text = (folder / part).read_text(encoding="utf-8")
    start = max(0, int(args.get("offset") or 0))
    chunk = text[start:start + GUIDE_CHARS]
    head = (news + "\n\n" if news else "") + f"{name}/{part} (files: {', '.join(files)})\n\n"
    if start + GUIDE_CHARS < len(text):
        chunk += f"\n... more: call again with offset {start + GUIDE_CHARS}"
    return head + chunk


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
    }, {
        "name": "design_guide",
        "description": "Written design guides to read and follow when designing, animating, redesigning or "
                       "reviewing UI, then answer in plain words. Emil Kowalski (polish and motion): emil-design-eng "
                       "(his whole philosophy), animate, animate-expo, animation-vocabulary (names for a motion "
                       "effect), apple-design, review-animations, improve-animations, find-animation-opportunities, "
                       "mobile-native, break-ui, prototype, pick-ui-library, ask-sonner, write-swift. Taste Skill "
                       "(good taste instead of generic AI pages): taste-skill (main), minimalist-skill, "
                       "brutalist-skill, soft-skill, redesign-skill, brandkit, image-to-code-skill, stitch-skill, "
                       "imagegen-frontend-web, imagegen-frontend-mobile, output-skill, gpt-tasteskill, "
                       "taste-skill-v1. Anime prompts (for anime or manga art, images or video): anime-mj (genres, "
                       "30+ manga artists, 14 studios like Ghibli and KyoAni; files sref-library.md, "
                       "video-animation.md; --niji and --sref only work in Midjourney), higgsfield-anime "
                       "(fill-in template for Higgsfield). New libraries dropped into skills/ appear here too. Call "
                       "with no guide to list them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "guide": {"type": "string", "description": "Guide name, e.g. 'emil-design-eng'. Empty lists them."},
                "file": {"type": "string", "description": "Extra file in the guide, e.g. 'RECIPES.md'. "
                                                          "Default SKILL.md."},
                "offset": {"type": "integer", "minimum": 0, "description": "To read on from a cut-off point."},
            },
            "additionalProperties": False,
        },
    }]


NAMES = {"design_advice", "design_guide"}


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    if name == "design_guide":
        return guide(args, settings)
    cmd = command(args)
    refusal = skillscan.blocked_reason(settings, SCRIPTS.parent.name)
    return refusal or await asyncio.to_thread(run, cmd)
