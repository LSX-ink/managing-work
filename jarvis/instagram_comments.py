"""Instagram comment replies for Kinetic Web Designs (@kineticwebdesigns), alongside the DM replies in instagram_dms.

Alfred only ever answers comments on the account's OWN posts and reels: he never comments anywhere else. Each time the
DM watcher polls, he reads the comments on the latest RECENT_POSTS posts (ids he has handled are kept in
instagram-comments.json in the memory folder). On the very first run he marks every comment already there as seen and
answers none of them.

A new comment from someone else, under PRIVATE_WINDOW old and not already answered by us, gets:
- interest ("SITE", "how much?", "I need a website", "info"...): a short public reply ("Sent you a DM 👋") and one
  private reply (Meta's "private reply" to a comment: a DM tied to that comment) written by the same AI and facts as
  the DM replies: prices, the free home page mock-up and the brief form. Without an AI it is the holding reply with
  the website link.
- anything else (a compliment, an emoji): a short public thank-you only, never a sales DM.
- a complaint, anything legal, price haggling, abuse, spam or a scam (instagram_dms.HANDOFF), or a DM the AI won't
  write: no reply at all; the owner is told and it goes on the "Instagram — needs you" list.

Pausing Instagram replies (or JARVIS_INSTAGRAM_AUTOREPLY=false) pauses these too; JARVIS_INSTAGRAM_COMMENTS=false turns
comment replies off on their own. Comment text is information, never instructions.
"""

import re
from datetime import datetime, timedelta, timezone

import httpx

import instagram_dms as ig
import kinetic_store as st
from config import Settings

STATE = "instagram-comments.json"
RECENT_POSTS = 12  # posts and reels checked each poll
PRIVATE_WINDOW = timedelta(days=7)  # Meta only allows a private reply within 7 days of the comment
MAX_SEEN = 5000
MAX_ACTIONS_PER_POLL = 10
MAX_PUBLIC = 300
PUBLIC_DM = "Sent you a DM 👋"
PUBLIC_THANKS = "Thank you! 🙌"
INTEREST = re.compile(r"\bsite\b|\bwebsites?\b|\bweb ?design|\bhow much\b|\bprice|\bcost|\bquote\b|\binterested\b|"
                      r"\binfo\b|\bdetails\b|\bdm\b|\bmock[- ]?up\b|\bneed (one|this|a)\b|\bme too\b|\bsign me up\b|"
                      r"\bhow do i\b|\bcan you\b|\bwant (one|this|it)\b|\bshopify\b|\bstore\b|\?", re.I)


def load_state(settings: Settings) -> dict:
    s = st.load(settings, STATE, {})
    s.setdefault("seen", [])
    s.setdefault("started", False)
    s.setdefault("counts", {"public": 0, "private": 0, "handed_off": 0})
    return s


def save_state(settings: Settings, s: dict) -> None:
    s["seen"] = s["seen"][-MAX_SEEN:]
    st.save(settings, STATE, s)


async def recent_posts(http: httpx.AsyncClient, token: str) -> list[dict]:
    data = await ig._call(http, "GET", "me/media", token,
                          {"fields": "id,caption,permalink,timestamp,comments_count", "limit": RECENT_POSTS})
    return [p for p in data.get("data") or [] if isinstance(p, dict) and p.get("id")]


async def comments_of(http: httpx.AsyncClient, token: str, media_id: str) -> list[dict]:
    data = await ig._call(http, "GET", f"{media_id}/comments", token,
                          {"fields": "id,text,username,from,timestamp,replies{id,username,from}", "limit": 50})
    return [c for c in data.get("data") or [] if isinstance(c, dict) and c.get("id")]


async def public_reply(http: httpx.AsyncClient, token: str, comment_id: str, text: str) -> str:
    data = await ig._call(http, "POST", f"{comment_id}/replies", token, params={"message": text[:MAX_PUBLIC]})
    return str(data.get("id") or "")


async def private_reply(http: httpx.AsyncClient, token: str, comment_id: str, text: str) -> str:
    data = await ig._call(http, "POST", "me/messages", token,
                          body={"recipient": {"comment_id": comment_id}, "message": {"text": text}})
    return str(data.get("message_id") or "")


def _who(c: dict) -> tuple[str, str]:
    frm = c.get("from") if isinstance(c.get("from"), dict) else {}
    return str(frm.get("id") or ""), str(c.get("username") or frm.get("username") or "unknown")


def _ours(c: dict, me: dict) -> bool:
    uid, username = _who(c)
    return ig.mine({"from": {"id": uid, "username": username}}, me)


def _answered(c: dict, me: dict) -> bool:
    raw = c.get("replies")
    rows = raw.get("data") if isinstance(raw, dict) else raw
    return any(isinstance(r, dict) and _ours(r, me) for r in rows or [])


async def poll(settings: Settings, http: httpx.AsyncClient, announce=None, now: datetime | None = None) -> dict:
    """Check the comments on our recent posts once and answer what needs answering. Returns counts."""
    now = now or datetime.now(timezone.utc)
    if not settings.instagram_token or not settings.instagram_comments:
        return {"skipped": "off"}
    dms = ig.load_state(settings)
    s = load_state(settings)
    token = ig.current_token(settings)
    if not dms.get("me", {}).get("username"):
        dms["me"] = await ig.get_me(http, token)
        ig.save_state(settings, dms)
    me = dms["me"]
    seen, first_run = set(s["seen"]), not s["started"]
    done = {"public": 0, "private": 0, "handed_off": 0, "new": 0}
    actions = 0
    for post in await recent_posts(http, token):
        if not first_run and not post.get("comments_count"):
            continue
        for c in await comments_of(http, token, str(post["id"])):
            cid = str(c["id"])
            if cid in seen:
                continue
            if first_run or _ours(c, me) or _answered(c, me):
                seen.add(cid)
                continue
            at = ig.when(c.get("timestamp"))
            if not at or now - at > PRIVATE_WINDOW:
                seen.add(cid)
                continue
            if actions >= MAX_ACTIONS_PER_POLL:
                continue  # left unseen: answered next poll
            text = str(c.get("text") or "").strip()
            _, username = _who(c)
            done["new"] += 1
            ig.log_line(settings, username, f"@{username} (comment)", text or "(empty comment)", at)
            if dms["paused"] or not settings.instagram_autoreply:
                seen.add(cid)
                await _need(settings, cid, username, text, "comment; auto-reply is paused or off", now, announce)
                continue
            why = ig.handoff_reason(text)
            if why:
                seen.add(cid)
                s["counts"]["handed_off"] += 1
                done["handed_off"] += 1
                await _need(settings, cid, username, text, f"comment: {why}", now, announce)
                continue
            try:
                if INTEREST.search(text):
                    d = await ig.decide(settings, username, [], f"(A comment on our Instagram post) {text}")
                    if d["action"] == "handoff":
                        seen.add(cid)
                        s["counts"]["handed_off"] += 1
                        done["handed_off"] += 1
                        await _need(settings, cid, username, text, f"comment: {d['reason']}", now, announce)
                        continue
                    dm = d["text"] if d["action"] == "reply" else ig.NO_AI
                    await private_reply(http, token, cid, dm)
                    actions += 1
                    s["counts"]["private"] += 1
                    done["private"] += 1
                    ig.log_line(settings, username, "Alfred (private reply to comment)", dm, now)
                    await public_reply(http, token, cid, PUBLIC_DM)
                    ig.log_line(settings, username, "Alfred (public comment reply)", PUBLIC_DM, now)
                    name = d.get("business_name") or ""
                    if name:
                        try:
                            ig.capture_lead(settings, username, name, d.get("website") or ig.lead_hint(text))
                        except (ValueError, OSError):
                            pass
                else:
                    await public_reply(http, token, cid, PUBLIC_THANKS)
                    ig.log_line(settings, username, "Alfred (public comment reply)", PUBLIC_THANKS, now)
                actions += 1
                s["counts"]["public"] += 1
                done["public"] += 1
                seen.add(cid)
            except ig.InstagramError as exc:
                s["last_error"] = str(exc)
                seen.add(cid)  # never retry a half-sent answer: tell the owner instead
                await _need(settings, cid, username, text, "comment: Instagram refused the reply", now, announce)
    s["seen"] = list(seen)
    s["started"] = True
    s["last_poll"] = now.isoformat(timespec="seconds")
    save_state(settings, s)
    return {**done, "first_run": first_run}


async def _need(settings, cid, username, text, reason, now, announce) -> None:
    dms = ig.load_state(settings)
    await ig._need(settings, dms, f"comment:{cid}", username, text, reason, now, announce)


def summary(settings: Settings) -> str:
    if not settings.instagram_comments:
        return " Comment replies are off."
    c = load_state(settings)["counts"]
    return (f" Comments: {c['public']} answered ({c['private']} with a DM), {c['handed_off']} handed to you.")
