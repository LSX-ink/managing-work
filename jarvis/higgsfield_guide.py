"""Higgsfield guide: what every Higgsfield feature is for, and how to use it to make our videos and websites better.

The owner (31 Oct 2026): "have a bot analyse higgsfield features and work out how to use them to make our videos
better, even the websites, and download that into Alfred". This is that bot's findings, kept here so Alfred can
answer from them, plan a video or a site with them, and show them on the HUD.

Nothing here generates anything. Higgsfield credits are limited (Ultra plan, 3,000 a month) and the owner doesn't
want retakes, so the only live Higgsfield calls are free ones: the balance and a cost check (get_cost). Making a
clip still goes through mcp_bridge, after the user says yes to the exact cost.

Pop-ups use the "showme" kind (frontend/popup-showme.js): lists with "say" buttons that ask Alfred the next step.
"""

import asyncio
import json
import re

import screen
from config import Settings

NAMES = {"higgsfield_guide"}
ACTIONS = ["features", "feature", "video_plan", "site_plan", "rules", "cost", "balance"]
KIND = "showme"
screen.EXTRA_KINDS.add(KIND)

# The house rules for spending credits, from the owner and from what went wrong before.
RULES = [
    "Check the balance and the exact cost (get_cost, free) before any generation, and say the number to the user.",
    "Make one cheap test or draft first. Only pay for the full-quality render after the user likes the test.",
    "No retakes: get the prompt, frames and settings right before you press go. Never re-run a job whose outcome is unknown.",
    "Use the cheapest model that does the job: Kling 3.0 openings are about 8-10 credits, Seedance 2.5 720p 6 s is 42.",
    "Every lowkey.lore video still goes through the video quality checker (bot 'video_qc') before it is sent.",
    "Never use AI video for the 'how it works' cutaway: it invents insides (pipes, layers, gears). The 3D stays the core.",
    "Stays sites never show AI-invented interiors: only the owner's real photos (upscaled or relit is fine).",
    "Higgsfield result links can't be downloaded in the cloud; fetch them on the home PC.",
]

# Each feature: key, name, group, what it does, how we use it (lore = lowkey.lore videos, ads = Kinetic videos,
# sites = Kinetic websites), the tool or model, and a rough credit cost when we know it.
FEATURES = [
    # Video
    {"key": "kling", "group": "Video", "name": "Kling 3.0 / 3.0 Turbo",
     "what": "Realistic video from text or a start frame, multi-shot, motion transfer, synced audio.",
     "use": "lore: the cheap realistic opening shot (drone reveal, close-up) before the 3D cutaway. ads: quick b-roll.",
     "tool": "generate_video model kling3_0 (kling3_0_turbo for single start-frame clips)", "credits": "about 8-10"},
    {"key": "first_last_frame", "group": "Video", "name": "Start and end frame matching (seamless openings)",
     "what": "Makes a clip that ends exactly on a picture you give it (Seedance 2.0/2.5, Kling 3.0 / Omni Frames, "
             "Kling 4.0, Minimax Hailuo, MiniMax H3, FLUX 3 Video).",
     "use": "lore: end the real-world opening exactly on our first Blender frame, so it flows into the cutaway with no "
            "visible jump. Also chain clips with join_video_clips handoff (last frame -> next start).",
     "tool": "generate_video model kling_o3_flf or seedance_2_5 (end frame = our first 3D frame)",
     "credits": "Kling about 7.5-10, Seedance about 42 per 6 s"},
    {"key": "ending_clip", "group": "Video", "name": "Realistic ending clip",
     "what": "The same start/end frame trick at the end of the video.",
     "use": "lore: the modern real thing (a real dam, a bullet train) before \"Follow for more insight\".",
     "tool": "generate_video model kling3_0 / seedance_2_5", "credits": "same as an opening"},
    {"key": "multi_shot", "group": "Video", "name": "Multi-shot in one generation (Kling 3.0 Omni)",
     "what": "Several camera angles from one generation.",
     "use": "lore and ads: a few real-world angles for the price of one clip.",
     "tool": "generate_video model kling_o3_image_reference (multi_shots)", "credits": "per clip"},
    {"key": "seedance", "group": "Video", "name": "Seedance 2.5",
     "what": "Sharp general video, omni-reference, video edit and video extension.",
     "use": "lore: the hero opening when Kling isn't sharp enough. ads: product hero shots.",
     "tool": "generate_video model seedance_2_5", "credits": "42 for 720p 6 s, no audio"},
    {"key": "draft", "group": "Video", "name": "Draft mode, then finalise",
     "what": "Seedance 2.5 draft makes a cheap 480p preview; the same take is then finalised at 1080p. Turbo and mini "
             "models (Kling 3.0 Turbo, Seedance 2.0 Mini) are cheap previews too.",
     "use": "every video: check motion and framing on the draft and only pay full price for a take we like.",
     "tool": "seedance_2_5 draft, kling3_0_turbo, seedance_2_0_mini", "credits": "lowest"},
    {"key": "cinema", "group": "Video", "name": "Cinema Studio 3.0 / 4.0",
     "what": "Cinema-grade video with camera, lighting, genre, era and colour direction.",
     "use": "lore: era-accurate scenes (Victorian railway, 1930s dam) when realism matters most.",
     "tool": "cinematic_studio_3_0, cinematic_studio_video_4_0", "credits": "high, check cost"},
    {"key": "marketing_video", "group": "Video", "name": "Marketing Studio video",
     "what": "One-click product ads, TikTok/Reels ready, from a product page.",
     "use": "ads: Kinetic reels from a client's own site; Shopify makeover reels.",
     "tool": "generate_video model marketing_studio_video (aspect_ratio 9:16)", "credits": "check cost"},
    {"key": "genjutsu", "group": "Video", "name": "Genjutsu (motion copy and object swap)",
     "what": "Copy motion from a video onto a picture, or swap a product/object in a video.",
     "use": "ads: one ad template, many clients (swap the shop sign, the product, the laptop screen).",
     "tool": "hf_mult_motion_control, hf_mult_replace_object", "credits": "check cost"},
    {"key": "ad_multiplier", "group": "Video", "name": "Ad Multiplier",
     "what": "Many versions of one 4-30 s ad: new people, products, language or market.",
     "use": "ads: turn a winning Kinetic reel into versions per trade or per country.",
     "tool": "workflow ad-multiplier", "credits": "check cost"},
    # Finishing
    {"key": "upscale_video", "group": "Finishing", "name": "Video upscale (Topaz, 4K / 60 fps)",
     "what": "Sharper, smoother video: upscale to 4K and raise the frame rate; deflicker.",
     "use": "lore and ads: polish the opening clip so it matches the Blender render; fix flicker.",
     "tool": "upscale_video, video_deflicker, topaz_video, bytedance_video_upscale", "credits": "per second"},
    {"key": "hdr", "group": "Finishing", "name": "SDR to HDR (Topaz Hyperion)",
     "what": "Punchier colour on phones, same size and frame rate.",
     "use": "lore: the best videos only.", "tool": "topaz_hyperion_2_5", "credits": "per video"},
    {"key": "video_edit", "group": "Finishing", "name": "Video edit / restyle (FLUX 3 Video Edit, Kling Omni Edit)",
     "what": "Changes a clip from a text instruction.",
     "use": "lore: make a scenery shot photoreal. Never on the cutaway: the AI may change the mechanism.",
     "tool": "flux_3_video_edit (about 1 credit a second), kling_video_edit", "credits": "about 1 per second"},
    {"key": "upscale_image", "group": "Finishing", "name": "Image upscale and relight",
     "what": "Sharpen, upscale and relight photos.",
     "use": "sites: make a client's real (often blurry) photos crisp, without inventing anything.",
     "tool": "upscale_image, image_command (polish)", "credits": "check cost"},
    {"key": "reframe", "group": "Finishing", "name": "Reframe and outpaint",
     "what": "Turn 16:9 into 9:16 (or back) by extending the picture.",
     "use": "ads: one shoot for TikTok, Reels and the website hero. sites: wider hero photos.",
     "tool": "reframe, outpaint_image", "credits": "check cost"},
    {"key": "bg_remove", "group": "Finishing", "name": "Background remover (image and video)",
     "what": "Cuts out the subject.",
     "use": "sites: product cut-outs for shops. ads: a business owner over our own background.",
     "tool": "remove_background", "credits": "low"},
    {"key": "virality", "group": "Finishing", "name": "Virality predictor",
     "what": "Scores a finished video's hook, attention and retention risk.",
     "use": "lore and ads: check the first seconds before posting, alongside the quality checker.",
     "tool": "virality_predictor", "credits": "check cost"},
    {"key": "captions", "group": "Finishing", "name": "Video montage and captions",
     "what": "Joins clips, changes the soundtrack, burns styled captions.",
     "use": "ads: burned subtitles on the Kinetic series.",
     "tool": "workflow video-montage", "credits": "low"},
    # Sound
    {"key": "dubbing", "group": "Sound", "name": "Dubbing (18 languages)",
     "what": "Translates and re-voices a finished video.",
     "use": "lore: Spanish, Portuguese, Hindi versions for new audiences. ads: Kinetic reels for other countries.",
     "tool": "dubbing", "credits": "check cost"},
    {"key": "voices", "group": "Sound", "name": "Voices (Seed Audio, ElevenLabs v4)",
     "what": "Narration from preset voices or a cloned voice.",
     "use": "ads: Bella (feminine businesses) and Archie (masculine/neutral) if the free voices sound flat.",
     "tool": "generate_audio model seed_audio / elevenlabs_v4", "credits": "low"},
    {"key": "music", "group": "Sound", "name": "Music (Suno)",
     "what": "Music beds of any length.",
     "use": "lore: a quiet, grown-up bed under the narrator (never childish), mixed to -14 LUFS.",
     "tool": "generate_audio model suno_music", "credits": "check cost"},
    # Images
    {"key": "stills", "group": "Images", "name": "Stills (Nano Banana Pro, Seedream, GPT Image 2)",
     "what": "High-quality images, accurate text and diagrams, up to 4K.",
     "use": "lore: start frames and thumbnails. ads: hook cards. sites: section art (never fake interiors).",
     "tool": "generate_image model nano_banana_pro / seedream_v4_5 / gpt_image_2", "credits": "low"},
    {"key": "thumbnails", "group": "Images", "name": "Thumbnails and covers",
     "what": "Bold viral covers with clean text.",
     "use": "lore: a cover frame for every TikTok. ads: reel covers for the Kinetic grid.",
     "tool": "workflow thumbnail-generation", "credits": "low"},
    {"key": "3d", "group": "Images", "name": "Image to 3D (GLB)",
     "what": "Turns a photo of an object into a textured 3D model, with rigging.",
     "use": "lore: real-looking props (pumps, rollers, carts) for Blender instead of building them by hand.",
     "tool": "generate_3d (image_to_3d, multi_image_to_3d)", "credits": "check cost"},
    # Websites and brand
    {"key": "scroll_site", "group": "Websites", "name": "Scroll-scrub websites",
     "what": "A site where scrolling plays a generated film; full-stack (Cloudflare Worker, D1, R2).",
     "use": "sites: a premium tier for Kinetic: the client's hero film plays as the visitor scrolls.",
     "tool": "create_website template scroll-scrub (workflow website-builder-flow)", "credits": "film only"},
    {"key": "product_shoot", "group": "Websites", "name": "Product photoshoot",
     "what": "Packshots, lifestyle scenes, hero banners and carousels from a product photo.",
     "use": "sites: Shopify makeovers get studio product photos from the client's own phone pictures.",
     "tool": "workflow product-photoshoot", "credits": "low per image"},
    {"key": "brand_kit", "group": "Websites", "name": "Brand assets",
     "what": "Logos, brand kits, mockups, signage, social graphics; exact recolouring of real logos.",
     "use": "sites: tidy a client's logo and palette before the build; social graphics for launch.",
     "tool": "workflow brand-asset-creation", "credits": "low"},
    {"key": "ads_studio", "group": "Websites", "name": "Ads Studio",
     "what": "Static ad creatives (Meta, Instagram) for a brand or product, written and drawn.",
     "use": "Kinetic's own Instagram ads, and a launch ad pack for each client.",
     "tool": "ads_studio_* (workflow ads-studio)", "credits": "quoted first"},
    {"key": "tiktok_publish", "group": "Websites", "name": "TikTok publishing",
     "what": "Posts or saves drafts to a connected TikTok account.",
     "use": "lore: save drafts straight to the account; the owner still posts from the phone.",
     "tool": "tiktok_prepare_publish (UPLOAD_TO_DRAFT)", "credits": "free"},
]
GROUPS = ["Video", "Finishing", "Sound", "Images", "Websites"]

# Step-by-step plans. Each step names the feature it uses.
VIDEO_PLANS = {
    "lore": ("lowkey.lore 3D video", [
        ("first_last_frame", "A 6 s realistic opening whose END frame is our first 3D cutaway frame, so the cut is invisible."),
        ("kling", "Kling 3.0 by default (about 8-10 credits); Seedance 2.5 for showcase topics."),
        ("draft", "Always draft first (Seedance 2.5 draft at 480p), finalise only the take we like."),
        ("ending_clip", "Optional: a realistic ending of the modern thing before \"Follow for more insight\"."),
        ("upscale_video", "Best videos only: Topaz 4K / 60 fps upscale (charged per second)."),
        ("3d", "Need a real-looking prop? Turn a photo into a 3D model instead of modelling it."),
        ("music", "Quiet grown-up music bed under the narrator, mixed to -14 LUFS."),
        ("thumbnails", "A bold cover frame."),
        ("virality", "Score the hook, then run the video quality checker before it's sent."),
        ("dubbing", "Later: dubbed versions for new languages."),
    ]),
    "ad": ("Kinetic Web Designs reel", [
        ("draft", "Draft the hero shot cheaply first."),
        ("marketing_video", "Product-style reel from the client's own site, 9:16."),
        ("genjutsu", "Swap the shop, product or screen so one template serves every trade."),
        ("reframe", "Reframe for TikTok, Reels and the website hero."),
        ("voices", "Bella for feminine businesses, Archie for masculine or neutral ones."),
        ("captions", "Burned subtitles."),
        ("virality", "Score the hook before posting."),
        ("ad_multiplier", "Winning reel? Multiply it per trade or country."),
    ]),
}
SITE_STEPS = [
    ("brand_kit", "Tidy the logo and palette from the business's own branding (colours from their site and Instagram)."),
    ("upscale_image", "Upscale and relight their real photos. Never invent interiors."),
    ("product_shoot", "Shops: studio product photos from the owner's own pictures."),
    ("bg_remove", "Product cut-outs for the shop grid."),
    ("reframe", "Wider hero images where a photo is too tight."),
    ("scroll_site", "Premium tier: a scroll-played hero film (the client's own footage or an approved clip)."),
    ("ads_studio", "A launch ad pack for the client's Instagram."),
]

BY_KEY = {f["key"]: f for f in FEATURES}


def _feature_item(f: dict) -> dict:
    return {"label": f["name"], "note": f"{f['use']} Credits: {f['credits']}.",
            "say": f"Tell me more about the Higgsfield feature {f['key']}", "action": "More"}


def _board(text: str, card_id: str, title: str, sections: list[dict], buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(KIND, title, card_id, buttons=buttons, data={"sections": sections}))


def show_features() -> screen.Shown:
    sections = [{"type": "list", "title": g, "items": [_feature_item(f) for f in FEATURES if f["group"] == g]}
                for g in GROUPS]
    text = "Higgsfield features and how we use them:\n" + "\n".join(
        f"- {f['name']} ({f['group']}): {f['use']}" for f in FEATURES)
    return _board(text, "higgsfield-features", "Higgsfield features", sections, buttons=[
        {"label": "Plan a lore video", "say": "Plan a lowkey.lore video with Higgsfield"},
        {"label": "Plan a Kinetic reel", "say": "Plan a Kinetic reel with Higgsfield"},
        {"label": "Improve a website", "say": "How can Higgsfield improve a Kinetic website?"},
        {"label": "Credits", "say": "How many Higgsfield credits have I got?"},
    ])


def _find(name: str) -> dict:
    q = (name or "").strip().lower()
    if not q:
        raise ValueError("Which feature? Say one of: " + ", ".join(BY_KEY))
    if q in BY_KEY:
        return BY_KEY[q]
    for f in FEATURES:
        if q in f["name"].lower() or q in f["tool"].lower():
            return f
    raise ValueError(f"I don't know a Higgsfield feature called {name}. Try: " + ", ".join(BY_KEY))


def show_feature(name: str) -> screen.Shown:
    f = _find(name)
    text = (f"{f['name']}: {f['what']} How we use it: {f['use']} Tool: {f['tool']}. Credits: {f['credits']}.")
    return _board(text, f"higgsfield-{f['key']}", f["name"], [
        {"type": "text", "text": f["what"]},
        {"type": "list", "title": "How we use it", "items": [{"label": f["use"]}]},
        {"type": "table", "title": "Details", "columns": ["", ""],
         "rows": [["Group", f["group"]], ["Tool / model", f["tool"]], ["Credits", f["credits"]]]},
    ])


def _plan_board(title: str, card_id: str, steps: list[tuple[str, str]], topic: str) -> screen.Shown:
    items = [{"label": f"{i}. {line}", "note": f"{BY_KEY[key]['name']} · credits: {BY_KEY[key]['credits']}"}
             for i, (key, line) in enumerate(steps, 1)]
    head = f"{title}{f' for {topic}' if topic else ''}"
    text = head + ":\n" + "\n".join(f"{i}. {line} ({BY_KEY[k]['name']})" for i, (k, line) in enumerate(steps, 1))
    text += "\nRules: " + " ".join(RULES[:3])
    return _board(text, card_id, head, [
        {"type": "list", "title": "Steps", "items": items},
        {"type": "list", "title": "Credit rules", "items": [{"label": r} for r in RULES[:4]]},
    ])


def video_plan(kind: str, topic: str) -> screen.Shown:
    kind = (kind or "lore").strip().lower()
    kind = "ad" if kind in ("ad", "ads", "kinetic", "reel") else kind
    if kind not in VIDEO_PLANS:
        raise ValueError("kind is lore (lowkey.lore) or ad (a Kinetic reel).")
    title, steps = VIDEO_PLANS[kind]
    return _plan_board(f"Higgsfield plan: {title}", f"higgsfield-plan-{kind}", steps, (topic or "").strip()[:80])


def site_plan(business: str) -> screen.Shown:
    return _plan_board("Higgsfield plan: website", "higgsfield-plan-site", SITE_STEPS, (business or "").strip()[:80])


def show_rules() -> screen.Shown:
    return _board("Higgsfield credit rules:\n" + "\n".join(f"- {r}" for r in RULES), "higgsfield-rules",
                  "Higgsfield credit rules", [{"type": "list", "items": [{"label": r} for r in RULES]}])


def _call(tool: str, arguments: dict) -> str:
    import videojoin
    return videojoin.higgsfield(tool, arguments)


def balance() -> str:
    text = _call("balance", {})
    m = re.search(r'"(?:credits|balance|available_credits)"\s*:\s*([\d.]+)', text)
    return f"You have {m[1]} Higgsfield credits." if m else f"Higgsfield balance: {text.strip()[:400]}"


def cost(args: dict) -> str:
    """What one generation would cost, without making it (get_cost is free)."""
    model = (args.get("model") or "").strip()
    if not model:
        raise ValueError("Which model? For example kling3_0 or seedance_2_5.")
    params = {"model": model, "get_cost": True, "prompt": (args.get("prompt") or "cost check")[:500]}
    for key in ("duration", "aspect_ratio", "resolution"):
        if args.get(key):
            params[key] = args[key]
    kind = "generate_audio" if args.get("type") == "audio" else (
        "generate_image" if args.get("type") == "image" else "generate_video")
    text = _call(kind, {"params": params})
    m = re.search(r'"(?:credits|cost|total_credits)"\s*:\s*([\d.]+)', text)
    if m:
        return f"{model} would cost {m[1]} credits. Nothing was made; ask the user before generating."
    return f"Higgsfield's cost check for {model}: {text.strip()[:400]}"


def tool_definitions() -> list[dict]:
    return [{
        "name": "higgsfield_guide",
        "description": "Alfred's Higgsfield guide: every Higgsfield feature (video, finishing, sound, images, websites) "
                       "and how to use it to make the lowkey.lore videos, the Kinetic reels and the Kinetic websites "
                       "better, shown as a window on the screen. 'what can Higgsfield do', 'how do I use Higgsfield "
                       "to make my videos better', 'plan this video with Higgsfield'. features: the full list; feature "
                       "(name): one feature; video_plan (kind lore or ad, optional topic): the step-by-step plan; "
                       "site_plan (optional business): how it improves a website; rules: the credit rules; cost "
                       "(model, optional duration, aspect_ratio, resolution, type video/image/audio): the exact credit "
                       "cost without making anything; balance: credits left. This never generates. To make something, "
                       "check cost, tell the user the number, and use mcp_bridge only after they say yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "feature: its name or key, e.g. kling or dubbing."},
                "kind": {"type": "string", "description": "video_plan: lore (lowkey.lore) or ad (Kinetic reel)."},
                "topic": {"type": "string", "description": "video_plan: what the video is about."},
                "business": {"type": "string", "description": "site_plan: the client's business."},
                "model": {"type": "string", "description": "cost: the Higgsfield model id, e.g. kling3_0."},
                "type": {"type": "string", "enum": ["video", "image", "audio"]},
                "duration": {"type": "integer"},
                "aspect_ratio": {"type": "string"},
                "resolution": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "features":
        return show_features()
    if action == "feature":
        return show_feature(args.get("name") or "")
    if action == "video_plan":
        return video_plan(args.get("kind") or "lore", args.get("topic") or "")
    if action == "site_plan":
        return site_plan(args.get("business") or "")
    if action == "rules":
        return show_rules()
    if action == "balance":
        return await asyncio.to_thread(balance)
    if action == "cost":
        return await asyncio.to_thread(cost, args)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")


def catalogue_json() -> str:
    """The features as JSON, for the HUD or other tools."""
    return json.dumps(FEATURES)
