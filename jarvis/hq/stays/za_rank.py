"""Rank South African stays richest first (owner, 25 Oct 2026: "pick the best properties with a lot of photos ... more
pictures, more videos, more floor plans, the best of the best ... then work our way down from the rich to the middle").

Searches luxury areas first, then upmarket, then the middle. Keeps hosts rated 4.5+ with an Instagram account (still the
rule), skips chains, then reads their own website (home page and its own links) and counts real photos, videos (video
files, YouTube, Vimeo), 3D tours (Matterport and similar) and floor plans. Score = area tier + Google price level + media.
Writes the ranked list to za_state.json ("ranked") and prints it. za_scout.py <place id> then prepares the chosen ones.

Usage: python za_rank.py [tier ...]    (tiers 1 luxury, 2 upmarket, 3 middle; default 1 2)"""
import asyncio, json, re, sys
from urllib.parse import urljoin, urlparse

from za_scout import CHAIN, FIELDS, OTA, HERE, instagram_of, state, save_state, Settings, httpx

TIERS = {
    1: ["luxury villa Clifton Cape Town", "luxury villa Camps Bay", "luxury villa Bantry Bay", "luxury villa Llandudno Cape Town",
        "boutique hotel Constantia", "luxury guest house Constantia", "luxury villa Franschhoek", "luxury guest house Franschhoek",
        "private game lodge Sabi Sand", "luxury lodge Madikwe", "luxury villa Plettenberg Bay", "luxury guest house Hermanus",
        "luxury villa Zimbali", "luxury villa Umhlanga", "boutique hotel Sandhurst Sandton", "luxury guest house Stellenbosch wine estate",
        "luxury lodge Kruger private", "luxury villa Fresnaye Cape Town"],
    2: ["boutique guest house Camps Bay", "boutique guest house Sea Point", "boutique guest house Knysna", "boutique guest house Plettenberg Bay",
        "boutique guest house Stellenbosch", "boutique guest house Hermanus", "boutique lodge Hoedspruit", "boutique guest house Wilderness",
        "boutique guest house Umhlanga", "boutique guest house Ballito", "boutique hotel Franschhoek", "boutique guest house Paternoster"],
    3: ["guest house Clarens", "self catering Knysna", "guest house Mossel Bay", "guest house Dullstroom", "guest house Parys",
        "self catering Langebaan", "guest house Montagu", "guest house Graaff-Reinet"],
}
TIER_PTS = {1: 40, 2: 20, 3: 0}
PRICE_PTS = {"PRICE_LEVEL_VERY_EXPENSIVE": 15, "PRICE_LEVEL_EXPENSIVE": 10, "PRICE_LEVEL_MODERATE": 3}
IMG = re.compile(r"""(?:src|data-src|srcset|href|content)=["']([^"' ]+\.(?:jpe?g|webp|png))""", re.I)
SKIP_IMG = re.compile(r"logo|icon|favicon|sprite|badge|flag|avatar|tripadvisor|award|payment|thumb-?\d{2}x", re.I)
VIDEO = re.compile(r"<video|\.mp4|youtube\.com/(?:embed|watch)|youtu\.be/|player\.vimeo|vimeo\.com/\d", re.I)
TOUR = re.compile(r"matterport|my\.matterport|kuula\.co|virtual[- ]tour|360[- ]tour|cloudpano|3d tour", re.I)
PLAN = re.compile(r"floor[- ]?plan|floorplan|layout plan", re.I)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}


async def media(h: httpx.AsyncClient, url: str) -> dict:
    """Count the real media on their own site: home page plus up to 10 of its own pages."""
    got = {"photos": 0, "videos": 0, "tour": False, "plan": False, "pages": 0, "html": ""}
    if not url or OTA.search(url):
        return got
    try:
        r = await h.get(url, headers=UA, follow_redirects=True, timeout=20)
    except Exception:
        return got
    host = urlparse(str(r.url)).netloc.replace("www.", "")
    links = {urljoin(str(r.url), l).split("#")[0] for l in re.findall(r"""href=["']([^"']+)""", r.text)}
    pages = [str(r.url)] + [l for l in links if host in l and not re.search(r"\.(pdf|jpe?g|png|webp|css|js|xml|ico)(\?|$)|mailto:|tel:|wp-json|feed", l)][:10]
    imgs, vids, texts = set(), set(), [r.text]
    for i, u in enumerate(pages):
        if i:
            try:
                t = (await h.get(u, headers=UA, follow_redirects=True, timeout=15)).text
            except Exception:
                continue
            texts.append(t)
        got["pages"] += 1
    for t in texts:
        imgs |= {m.split("?")[0] for m in IMG.findall(t) if not SKIP_IMG.search(m) and not re.search(r"-\d{2,3}x\d{2,3}\.", m)}
        vids |= set(re.findall(r"(?:youtube\.com/embed/|youtu\.be/|player\.vimeo\.com/video/|vimeo\.com/)([\w-]{6,})", t)) | set(re.findall(r"[\w/-]+\.mp4", t))
        got["tour"] |= bool(TOUR.search(t)); got["plan"] |= bool(PLAN.search(t))
    got["photos"], got["videos"], got["html"] = len(imgs), len(vids) or (1 if any(VIDEO.search(t) for t in texts) else 0), " ".join(texts)[:400000]
    return got


async def rank(tiers: list[int]) -> list[dict]:
    settings, s = Settings(), state()
    seen, out = set(s.get("done", [])), []
    async with httpx.AsyncClient(timeout=40) as h:
        for tier in tiers:
            for q in TIERS[tier]:
                r = await h.post("https://places.googleapis.com/v1/places:searchText",
                                 headers={"X-Goog-Api-Key": settings.google_places_key, "X-Goog-FieldMask": FIELDS + ",places.priceLevel"},
                                 json={"textQuery": q, "maxResultCount": 20, "regionCode": "ZA"})
                cands = [p for p in r.json().get("places", []) if p["id"] not in seen and not CHAIN.search(p["displayName"]["text"] + " " + p.get("websiteUri", ""))
                         and (p.get("rating") or 0) >= 4.5 and (p.get("userRatingCount") or 0) >= 10]
                seen |= {p["id"] for p in cands}
                ms = await asyncio.gather(*(media(h, p.get("websiteUri", "")) for p in cands))
                for p, m in zip(cands, ms):
                    ig = instagram_of(p.get("websiteUri", "")) or instagram_of(m["html"])
                    if not ig:
                        continue  # still Instagram only
                    score = (TIER_PTS[tier] + PRICE_PTS.get(p.get("priceLevel"), 0) + min(m["photos"], 80) * 0.5 + min(m["videos"], 5) * 6
                             + (15 if m["tour"] else 0) + (12 if m["plan"] else 0) + len(p.get("photos", [])) + min(p.get("userRatingCount", 0), 300) / 30)
                    out.append({"id": p["id"], "name": p["displayName"]["text"], "tier": tier, "query": q, "score": round(score, 1),
                                "rating": p.get("rating"), "reviews": p.get("userRatingCount"), "price": p.get("priceLevel", ""),
                                "website": p.get("websiteUri", ""), "instagram": ig, "site_photos": m["photos"], "videos": m["videos"],
                                "tour": m["tour"], "floorplan": m["plan"], "google_photos": len(p.get("photos", [])),
                                "address": p.get("formattedAddress", "")})
                print(f"{q}: {len(cands)} checked, {len(out)} kept so far", file=sys.stderr)
    out.sort(key=lambda x: -x["score"])
    s["ranked"] = out; save_state(s)
    return out


if __name__ == "__main__":
    ranked = asyncio.run(rank([int(a) for a in sys.argv[1:]] or [1, 2]))
    print(json.dumps(ranked[:30], indent=1, ensure_ascii=False))
