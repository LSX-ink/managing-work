"""Kinetic from start to finish, by voice: "Alfred, build a mock-up for A Cut Above in Sheffield" runs the whole premium
mock-up pipeline (hq/premium/auto.py: research, design, before/after, online, checks, Instagram name, short DM) in the
background, and "today's DMs" sends the day's ready-to-send DM list to the phone.

Nothing is ever sent to the business: the owner reads each DM and sends it himself on Instagram."""

import asyncio
import sys
from datetime import date
from pathlib import Path

import alerts
import helpers
from config import ROOT, Settings

NAMES = {"kinetic_premium_mockup"}
ACTIONS = ["build", "status", "dms"]
DM_FOLDER = Path.home() / "OneDrive" / "Desktop" / "Instagram DMs"
jobs: dict[str, dict] = {}  # business -> {"status": "working" | "done" | "failed", "result" | "error"}


def ready_text(r: dict) -> str:
    """The phone message: link, checks, Instagram and the DM to copy."""
    checks = "every check passed" if not r["issues"] else "check these first: " + "; ".join(r["issues"][:4])
    ig = (f"Instagram @{r['instagram']} is a real, live profile." if r["instagram_ok"] else
          f"Instagram @{r['instagram']} didn't check out, so find their real account first." if r["instagram"] else
          "No Instagram name found; look them up before sending.")
    return (f"Mock-up for {r['name']} ({r['layout']} design): {r['link']}\nOnline and {checks}. {ig}\n\n"
            f"DM to send:\n\n{r['dm']}")


async def _build(settings: Settings, business: str, website: str, instagram: str) -> None:
    sys.path.insert(0, str(ROOT / "hq" / "premium"))
    import auto  # noqa: E402 - only loaded when building
    job = jobs[business]
    try:
        r = await auto.make(business, settings, helpers._client, website, instagram,
                            progress=lambda t: job.update(step=t))
        job.update(status="done", result=r)
        await alerts.push(settings, ready_text(r), "mockup")
        if helpers._announce:
            ok = "Every check passed." if not r["issues"] else f"{len(r['issues'])} things need a look."
            await helpers._announce(f"{settings.user_address.capitalize()}, the mock-up for {r['name']} is ready. {ok} "
                                    "The link and the DM are on your phone.", "mockup")
    except Exception as exc:  # noqa: BLE001 - say what went wrong rather than fail silently
        job.update(status="failed", error=str(exc)[:300])
        print(f"[jarvis] Mock-up for {business} failed: {exc!r}", flush=True)
        if helpers._announce:
            await helpers._announce(f"{settings.user_address.capitalize()}, the mock-up for {business} didn't work: "
                                    f"{str(exc)[:160]}", "mockup")


def build(settings: Settings, args: dict) -> str:
    business = str(args.get("business") or "").strip()
    if not business:
        raise ValueError("Say which business, with its town, e.g. \"A Cut Above, Sheffield\".")
    if not settings.google_places_key:
        raise ValueError("The mock-up research needs the Google Places key (JARVIS_GOOGLE_PLACES_KEY).")
    if jobs.get(business, {}).get("status") == "working":
        return f"I'm already building the mock-up for {business}."
    jobs[business] = {"status": "working", "step": "Starting…"}
    asyncio.get_running_loop().create_task(_build(settings, business, str(args.get("website") or ""),
                                                  str(args.get("instagram") or "")))
    return (f"Building the mock-up for {business} now: research, design, before and after, online and checked. It "
            "takes about five minutes; I'll tell you when it's ready and send the link and DM to your phone.")


def status(settings: Settings, args: dict) -> str:
    if not jobs:
        return "No mock-ups are being built right now."
    lines = []
    for business, j in jobs.items():
        if j["status"] == "working":
            lines.append(f"{business}: {j.get('step', 'working')}")
        elif j["status"] == "done":
            lines.append(f"{business}: ready, {j['result']['link']}")
        else:
            lines.append(f"{business}: failed ({j.get('error', '')})")
    return "\n".join(lines)


async def dms(settings: Settings, args: dict) -> str:
    """Today's ready-to-send DM list (made each morning by the HQ team), sent to the phone."""
    file = DM_FOLDER / f"Instagram DMs {date.today().isoformat()}.md"
    if not file.exists():
        return "There's no DM list for today yet. Say \"build a mock-up for\" a business to make one now."
    text = file.read_text(encoding="utf-8")
    sent = await alerts.push(settings, text, "mockup")
    count = text.count("\n## ")
    return (f"Today's list has {count} DM{'s' if count != 1 else ''}"
            + (", and I've sent it to your phone." if sent else f". It's on your Desktop: {file.name}."))


def tool_definitions() -> list[dict]:
    return [{
        "name": "kinetic_premium_mockup",
        "description": "Kinetic Web Designs, end to end. build: a premium mock-up website for one business (\"build a "
                       "mock-up for Vox in Manchester\"): researches their website and Google listing, designs it in "
                       "their colours with their photos, prices and reviews, adds a before/after of their current "
                       "site, puts it online, checks it like a customer, checks their Instagram name and writes the "
                       "short DM; runs in the background (about five minutes) and sends the link and DM to the phone. "
                       "status: how the builds are going. dms: today's ready-to-send DM list, sent to the phone. "
                       "Nothing is ever sent to the business.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "business": {"type": "string", "description": "Business name and town, for build"},
                "website": {"type": "string", "description": "Their website, if known"},
                "instagram": {"type": "string", "description": "Their Instagram name, if known"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action") or "build"
    if action == "dms":
        return await dms(settings, args)
    if action == "status":
        return status(settings, args)
    return build(settings, args)
