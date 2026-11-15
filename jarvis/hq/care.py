"""Hosting-and-care plans: who is paying for changes, and who has stopped.

The owner, 15 Nov 2026: "track which websites unsubscribes so we stop making changes for them". The site's Stripe
webhook keeps the subscriptions table on kinetic-db up to date (kinetic-kit/migrations-subscriptions.sql). Ledger
(the analyst) reads it every hour. When a plan ends, it alerts the owner's phone, logs a warning and records the
business in the brain as stopped. may_change() is the check to run before making any change for a client.

    python -m hq.care            # the plans: active, ending and stopped
"""

import asyncio
from datetime import datetime
from pathlib import Path

STOPPED = ("canceled", "unpaid", "incomplete_expired")
SQL = ("SELECT id, email, name, website, status, amount, currency, cancel_at, canceled_at, updated "
       "FROM subscriptions ORDER BY updated DESC LIMIT 300")


def rows() -> list[dict]:
    import kinetic_site
    return kinetic_site.wrangler(SQL)


def who(r: dict) -> str:
    return " / ".join(x for x in (r.get("name"), r.get("website"), r.get("email")) if x) or r.get("id", "?")


def _day(ms) -> str:
    return datetime.fromtimestamp(int(ms) / 1000).strftime("%d %b %Y") if ms else ""


def keys(r: dict) -> list[str]:
    """What a client might be looked up by: their website (no scheme or www), their email."""
    out = []
    if r.get("website"):
        w = str(r["website"]).lower().strip().removeprefix("https://").removeprefix("http://").removeprefix("www.")
        out.append(w.rstrip("/"))
    if r.get("email"):
        out.append(str(r["email"]).lower().strip())
    return out


def may_change(brain, client: str) -> bool:
    """False when this website or email is on a plan that has ended: don't make changes for them."""
    c = client.lower().strip().removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
    return c not in set(brain.get("care.stopped_keys", []) or [])


async def check(settings, brain, push=None) -> str:
    """Update the brain from the subscriptions table and alert on plans that have just ended or will end."""
    if push is None:
        import alerts
        push = alerts.push
    try:
        rs = await asyncio.to_thread(rows)
    except ValueError as e:
        return f"care plans not checked: {e}"
    active, stopped, stopped_keys = [], [], set()
    for r in rs:
        sid = r.get("id")
        gone = r.get("status") in STOPPED
        if gone:
            stopped.append(r)
            stopped_keys.update(keys(r))
            if not brain.get(f"care.stopped.{sid}"):
                brain.set(f"care.stopped.{sid}", {"who": who(r), "at": r.get("canceled_at") or r.get("updated")})
                text = f"Care plan cancelled: {who(r)}. Stop making changes for them."
                brain.log("analyst", text, "warn", {"subscription": sid})
                await push(settings, text, "lead")
            continue
        active.append(r)
        if brain.get(f"care.stopped.{sid}"):  # they came back
            brain.set(f"care.stopped.{sid}", None)
        if r.get("cancel_at") and not brain.get(f"care.ending.{sid}"):
            brain.set(f"care.ending.{sid}", r["cancel_at"])
            text = f"Care plan ending on {_day(r['cancel_at'])}: {who(r)}. Changes stop after that date."
            brain.log("analyst", text, "warn", {"subscription": sid})
            await push(settings, text, "lead")
    for r in active:  # a website that has an active plan again isn't blocked by an older cancelled one
        stopped_keys.difference_update(keys(r))
    brain.set("care.active", [{"who": who(r), "status": r.get("status"), "ends": _day(r.get("cancel_at"))} for r in active])
    brain.set("care.stopped", [{"who": who(r), "ended": _day(r.get("canceled_at"))} for r in stopped])
    brain.set("care.stopped_keys", sorted(stopped_keys))
    return f"{len(active)} care plans active, {len(stopped)} cancelled"


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    rs = rows()
    if not rs:
        print("No hosting-and-care plans recorded yet.")
    for r in rs:
        end = f", ends {_day(r.get('cancel_at'))}" if r.get("cancel_at") and r.get("status") not in STOPPED else ""
        print(f"{'STOPPED' if r.get('status') in STOPPED else 'active '}  {who(r)}  ({r.get('status')}{end})")
