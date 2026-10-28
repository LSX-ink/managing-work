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
template for Higgsfield. skills/business holds pricing-strategy (MIT, from github.com/sickn33/antigravity-awesome-skills):
pricing, tiers, value metrics and price rises for a product or service; and client-websites (ours): creative Kinetic
client sites and mock-ups that sell, using 21st.dev components through the MCP bridge. skills/marketing holds Corey
Haines's Marketing Skills (MIT, from github.com/coreyhaines31/marketingskills, written guides only): copywriting,
copy-editing, cold-email, prospecting, cro, offers, social, seo-audit, ai-seo, schema, site-architecture,
marketing-psychology, lead-magnets, pricing, ad-creative, video, emails, content-strategy, referrals and more; each
can have extra files in references/. skills/anthropic also holds canvas-design (Apache 2.0, from
github.com/anthropics/skills): posters and still graphics from a design philosophy. skills/impeccable holds Paul
Bakaus's Impeccable (Apache 2.0, from github.com/pbakaus/impeccable, written guides only, no launcher): a design
director's playbook with critique, audit, polish, bolder, typeset, layout and more in reference/. skills/vercel holds
Vercel's web-design-guidelines (the Web Interface Guidelines rules saved in references/rules.md) and
writing-guidelines (MIT, from github.com/vercel-labs). guide "website" lists every skill to use for a website, in
order, and website_pack() hands excerpts of all of them to the mock-up builder's design review.
skills/superpowers holds five of Jesse Vincent's Superpowers (MIT, from github.com/obra/superpowers, written guides
only): systematic-debugging, verification-before-completion, test-driven-development, writing-plans and
receiving-code-review. skills/anthropic also holds mcp-builder and webapp-testing (guides only, their scripts left out).
3D for the web: skills/threejs holds the OpenAEC Three.js Skill Package (MIT, from
github.com/OpenAEC-Foundation/Three.js-Claude-Skill-Package, 22 guides: renderer, scene graph, lighting, shadows,
materials, shaders, post-processing, animation, loaders, controls, WebGPU, React Three Fiber, performance and
rendering fixes, a scene builder and a model optimiser) and skills/web3d holds freshtechbro's claudedesignskills (MIT,
written guides only): threejs-webgl, lightweight-3d-effects, web3d-integration-patterns, gsap-scrolltrigger,
spline-interactive, blender-web-pipeline, modern-web-design, scroll-reveal-libraries, lottie-animations, animejs and
react-three-fiber.

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
GUIDE_LIBRARIES = {"emil-kowalski": "Emil Kowalski", "taste": "Taste Skill", "anime": "Anime prompt", "anthropic": "Anthropic",
                   "business": "Business", "marketing": "Marketing Skills", "impeccable": "Impeccable",
                   "vercel": "Vercel", "superpowers": "Superpowers", "threejs": "Three.js",
                   "web3d": "3D and motion for the web", "ui-skills": "UI Skills",
                   "web-engineering": "Web engineering", "web-3d": "3D web"}  # labels
# The owner (27 Oct 2026): "when making websites always use all the skills so you get the best version". Every
# website and mock-up build reads the website kit: these guides, in this order, all applied.
WEBSITE_KIT = ["client-websites", "frontend-design", "taste-skill", "impeccable", "emil-design-eng", "baseline-ui",
               "improve-ui", "fixing-accessibility", "fixing-motion-performance", "fixing-metadata",
               "frontend-ui-engineering", "performance-optimization", "brand-guidelines", "theme-factory",
               "redesign-skill", "animate", "apple-design", "auteur", "threejs-r3f", "gsap", "motion-principles",
               "css-native", "igloo-style-3d"]
KIT_CHARS = 2500  # of each guide in the kit digest; the full guide is one design_guide call away
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


# Every website, every skill (owner, 27 Oct 2026: "when making websites always use all the skills so you get the best
# version"). In reading order: (guide, file, what it brings, characters used in an automatic design review).
WEBSITE_SKILLS = [
    ("client-websites", "SKILL.md", "Kinetic's own rules: a page structure that sells, 21st.dev components, the quality check", 4200),
    ("frontend-design", "SKILL.md", "pick a bold, specific aesthetic direction before anything else", 6000),
    ("impeccable", "SKILL.md", "work like a design director: the Persuade mode for sales pages", 5000),
    ("impeccable", "reference/mode-persuade.md", "what a landing page must do", 3700),
    ("impeccable", "reference/craft-floor.md", "the quality floor and the absolute bans", 4600),
    ("taste-skill", "SKILL.md", "no AI-looking pages: layout, type and colour taste", 9000),
    ("redesign-skill", "SKILL.md", "redesigning a business's existing site", 3000),
    ("emil-design-eng", "SKILL.md", "polish and motion that feels right", 5000),
    ("modern-web-design", "SKILL.md", "what a current, motion-rich site looks like", 3000),
    # 3D (owner, 27 Oct 2026: "include the skills best suited for 3d web designs"). 0: read when building by hand; the
    # automatic review only changes words, colours and photos, so it can't add 3D and doesn't need them.
    ("lightweight-3d-effects", "SKILL.md", "tasteful 3D touches (tilt, depth, a floating object) that stay fast", 0),
    ("threejs-webgl", "SKILL.md", "a full 3D scene with Three.js", 0),
    ("web3d-integration-patterns", "SKILL.md", "putting 3D into a real page: loading, fallbacks, phones", 0),
    ("threejs-agents-scene-builder", "SKILL.md", "planning and building a Three.js scene step by step", 0),
    ("threejs-impl-lighting", "SKILL.md", "lighting that makes 3D look real", 0),
    ("threejs-errors-performance", "SKILL.md", "keeping 3D smooth on a phone", 0),
    ("gsap-scrolltrigger", "SKILL.md", "scroll-driven animation and 3D camera moves", 0),
    ("spline-interactive", "SKILL.md", "ready-made interactive 3D from Spline", 0),
    ("web-design-guidelines", "references/rules.md", "accessibility, forms, motion, type and performance rules", 8300),
    ("copywriting", "SKILL.md", "every word on the page", 5000),
    ("cro", "SKILL.md", "turning visitors into bookings and calls", 4000),
    ("offers", "SKILL.md", "an offer worth acting on (only a real one)", 2500),
    ("marketing-psychology", "SKILL.md", "why people act, used honestly", 2500),
    ("writing-guidelines", "SKILL.md", "interface words: buttons, labels, errors", 2500),
    ("impeccable", "reference/polish.md", "the final pass before it ships", 4000),
]


def website_list() -> str:
    """The reading list for making or changing any website or mock-up: every skill, in order."""
    found = guides()
    lines = ["Making or changing a website or mock-up: use ALL of these, in this order (call design_guide with each "
             "guide and file). Also use design_advice (UI UX Pro Max) for the palette, fonts and style, and run the "
             "web-design-guidelines rules as the final check.", ""]
    for i, (name, file, why, _) in enumerate(WEBSITE_SKILLS, 1):
        here = name in found and (found[name] / file).exists()
        lines.append(f"{i}. {name}" + (f" (file '{file}')" if file != "SKILL.md" else "") + f": {why}"
                     + ("" if here else " [not installed]"))
    return "\n".join(lines)


def website_pack(settings: Settings | None = None) -> str:
    """Excerpts of every website skill, for an automatic design review (skipping any library the skill check blocked)."""
    found = guides()
    settings = settings or Settings()
    parts = []
    for name, file, why, size in WEBSITE_SKILLS:
        path = found.get(name)
        if not size or not path or not (path / file).exists() or skillscan.blocked_reason(settings, path.parent.name):
            continue
        text = (path / file).read_text(encoding="utf-8")
        parts.append(f"=== {name}/{file}: {why} ===\n{text[:size]}")
    return "\n\n".join(parts)


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
    if name in ("website", "websites", "all"):
        return (news + "\n\n" if news else "") + website_list()
    if name == "website-kit":
        return (news + "\n\n" if news else "") + website_kit(found, settings, int(args.get("offset") or 0))
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
    files = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.md"))  # references/*.md too
    if part not in files:
        raise ValueError(f"{name} has these files: {', '.join(files)}.")
    text = (folder / part).read_text(encoding="utf-8")
    start = max(0, int(args.get("offset") or 0))
    chunk = text[start:start + GUIDE_CHARS]
    head = (news + "\n\n" if news else "") + f"{name}/{part} (files: {', '.join(files)})\n\n"
    if start + GUIDE_CHARS < len(text):
        chunk += f"\n... more: call again with offset {start + GUIDE_CHARS}"
    return head + chunk


def website_kit(found: dict | None = None, settings: Settings | None = None, offset: int = 0) -> str:
    """The opening of every guide in WEBSITE_KIT, one after another, so a website build applies all of them."""
    found = found if found is not None else guides()
    parts = ["Website kit: apply EVERY guide below to this site or mock-up, not just one. Read a guide in full with "
             "design_guide when the part shown here isn't enough."]
    for name in WEBSITE_KIT:
        folder = found.get(name)
        if not folder or (settings and skillscan.blocked_reason(settings, folder.parent.name)):
            continue
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        parts.append(f"## {name} ({GUIDE_LIBRARIES.get(folder.parent.name, folder.parent.name)})\n"
                     + text[:KIT_CHARS] + ("\n..." if len(text) > KIT_CHARS else ""))
    text = "\n\n".join(parts)
    chunk = text[offset:offset + GUIDE_CHARS]
    if offset + GUIDE_CHARS < len(text):
        chunk += f"\n... more: call again with guide 'website-kit' and offset {offset + GUIDE_CHARS}"
    return chunk


def tool_definitions() -> list[dict]:
    return [{
        "name": "design_advice",
        "description": "UI UX Pro Max design library (offline). For designing a website, app, page, HUD, thumbnail "
                       "or brand: set design_system=true with a short description (product, industry, mood) to get "
                       "a full plan with layout pattern, style, colour palette with hex codes, font pairing, effects "
                       "and mistakes to avoid. For a focused question, search one domain: style, color, typography, "
                       "google-fonts, ux (usability and accessibility rules), landing, product, icons, chart, gsap "
                       "(animation presets), react or web. Use stack for tips for a framework (html-tailwind, react, "
                       "nextjs, flutter...). Keep queries to 2-5 words. Summarise the result in plain words. To match "
                       "a site the user likes, run extract_design_system on it first.",
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
                       "reviewing UI, then answer in plain words. Before making or changing ANY website, landing page or mock-up, "
                       "call it with guide 'website' (the playbook) and guide 'website-kit' (every kit guide in one read), and use "
                       "EVERY skill, in order (the owner's rule: all the skills, every time). Emil Kowalski (polish and motion): emil-design-eng "
                       "(his whole philosophy), animate, animate-expo, animation-vocabulary (names for a motion "
                       "effect), apple-design, review-animations, improve-animations, find-animation-opportunities, "
                       "mobile-native, break-ui, prototype, pick-ui-library, ask-sonner, write-swift. Taste Skill "
                       "(good taste instead of generic AI pages): taste-skill (main), minimalist-skill, "
                       "brutalist-skill, soft-skill, redesign-skill, brandkit, image-to-code-skill, stitch-skill, "
                       "imagegen-frontend-web, imagegen-frontend-mobile, output-skill, gpt-tasteskill, "
                       "taste-skill-v1. Anime prompts (for anime or manga art, images or video): anime-mj (genres, "
                       "30+ manga artists, 14 studios like Ghibli and KyoAni; files sref-library.md, "
                       "video-animation.md; --niji and --sref only work in Midjourney), higgsfield-anime "
                       "(fill-in template for Higgsfield). Anthropic: frontend-design (a distinctive look for a new page or "
                       "app: a clear aesthetic direction, bold typography and colour, nothing templated; read it "
                       "first when building or restyling a website), theme-factory (10 ready-made colour and font themes for "
                       "pages, slides and posters; the themes are its files, e.g. file 'ocean-depths.md', "
                       "'midnight-galaxy.md'; or make a custom one). Business: pricing-strategy (setting or changing prices for a "
                       "product, service or website package: value-based pricing, tiers, value metric, free trial "
                       "or freemium, price rises; ends with a pricing plan) and client-websites (read before making a Kinetic "
                       "client mock-up or site: 21st.dev components, a page structure that sells, a quality check). Marketing Skills: read "
                       "copywriting (and copy-editing) before writing any website words, DMs, captions or ads; cold-email and "
                       "prospecting before outreach or follow-ups; cro and offers for pages and packages that convert; "
                       "social and video for Instagram and TikTok content; seo-audit, ai-seo, schema and site-architecture "
                       "for search; marketing-psychology, lead-magnets, emails, referrals, sales-enablement and more. Their "
                       "extra files are e.g. file 'references/copy-frameworks.md'. Anthropic canvas-design: posters and still "
                       "graphics. Superpowers (working like a pro on any job): "
                       "systematic-debugging (find the real cause before fixing anything), verification-before-completion "
                       "(prove it works before saying it's done), writing-plans, test-driven-development, "
                       "receiving-code-review. 3D websites: lightweight-3d-effects, threejs-webgl, "
                       "web3d-integration-patterns, gsap-scrolltrigger, spline-interactive, blender-web-pipeline and "
                       "the threejs-* guides (renderer, lighting, materials, shaders, post-processing, performance...). "
                       "Anthropic mcp-builder (new connectors) and webapp-testing (testing a web "
                       "page with Playwright). Impeccable: impeccable (a full design language with references for "
                       "layout, colour, type, motion, critique and polish). UI Skills: baseline-ui, improve-ui, "
                       "fixing-accessibility, fixing-motion-performance, fixing-metadata, create-design-md. Web "
                       "engineering: frontend-ui-engineering, performance-optimization. More Anthropic: canvas-design, "
                       "brand-guidelines, web-artifacts-builder. 3D web: auteur (directs a site like a film: "
                       "storyboard, scroll cinema, 3D scenes, verify), threejs-r3f, gsap, motion-principles, "
                       "canvas-generative, css-native, framer-motion, genjutsu-cast, igloo-style-3d (award-level immersive 3D: ice and glass objects, particle shapes, WebGL text, frost transitions, fast loading). New libraries dropped into skills/ appear here too. Call "
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
