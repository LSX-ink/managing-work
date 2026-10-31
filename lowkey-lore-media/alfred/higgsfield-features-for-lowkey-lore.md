# Higgsfield features: what we can use for lowkey.lore videos and Kinetic websites

*Analysed 31 Oct 2026 from the Higgsfield tools on this PC (read-only: no credits spent).*
Account: Ultra plan, 173 credits left. Last clip (6 s Seedance 2.5, the dam opening) cost 42 credits.

## The big one: seamless openings (fixes "high quality, then a drop")
Several video models take a **start frame and an end frame**: Seedance 2.0 / 2.5, Kling 3.0 / 3.0 Omni Frames, Kling 4.0, Minimax Hailuo, MiniMax H3 and FLUX 3 Video.
- Render our first 3D cutaway frame, then give it to Higgsfield as the **end frame** with a prompt like "real drone shot over a valley, flying down to this exact view".
- The AI clip then *lands exactly on our 3D shot*, so the cut is invisible: same angle, same light, same colours.
- **Draft mode** (Seedance 2.5 `draft`): a cheap 480p preview first, then finalise the same take at 1080p. No paid retakes on a bad idea.

## Ways to raise video quality

| Feature | Model / tool | What it does for us | Cost note |
|---|---|---|---|
| Realistic opening, ends on our frame | Seedance 2.5 / Kling 3.0 (start + end frame) | Hook in the first second with real-looking footage, then a seamless cut into the cutaway | Seedance about 42 cr per 6 s; Kling about 7.5–10 cr |
| Realistic ending clip | same | The modern real thing (a real dam, a real bullet train) before "Follow for more insight" | same |
| Cinema camera / lighting / era | Cinema Studio 4.0 | Choose film era, lens, lighting rig and colour palette, which suits history topics (e.g. a 1920s look for early fridges) | premium |
| Upscale to 4K / 60 fps | Topaz, Bytedance Video Upscale | Sharper, smoother final video (frame interpolation) | per second |
| Deflicker | Video Deflicker | Safety net for any shimmer | per second |
| Video edit / restyle | FLUX 3 Video Edit (about 1 cr/s), Kling Omni Edit, Seedance 2.5 video_edit | Could make a 3D shot look photoreal, **but** the AI may change the mechanism, so only use it on scenery shots, never on the "how it works" cutaway | cheap (FLUX) |
| SDR to HDR | Topaz Hyperion | Punchier colour on phones | per video |
| Dubbing (18 languages) | Dubbing | Same video for Spanish, Portuguese, Hindi, etc. TikTok audiences | per video |
| Thumbnails / covers | thumbnail-generation workflow | Scroll-stopping TikTok covers for each video | image credits |
| Multi-shot | Kling 3.0 Omni multi_shots | Several angles in one generation (cheaper than separate clips) | per clip |

**What Higgsfield should NOT do:** generate the explanation itself. It invents insides (pipes, layers, gears), so the accurate 3D cutaway stays the core of every video.

## For the Kinetic websites
- **website-builder-flow**: Higgsfield can build, host and deploy websites (custom-brand "website" type), with image-grounded design phases.
- **Ads Studio**: static Meta/Instagram ad creatives from a client's website or product.
- **brand-asset-creation**: logos, brand kits, mock-ups, social graphics.
- **product-photoshoot**: packshots and lifestyle images for client products.
- **Marketing Studio video**: 12–15 s TikTok/Reels product ads with avatars, hooks and settings.
- **video-montage**: assemble client clips with captions and soundtrack.

## Recommended plan
1. Every lowkey.lore video: a **6 s opening that ends on our first 3D frame**. Use Kling 3.0 (cheap) by default and Seedance 2.5 for showcase topics. Always draft first.
2. Optional: a realistic **ending clip** of the modern thing.
3. **Topaz 4K / 60 fps upscale** for the best videos only (credit cost per second).
4. Websites: use Higgsfield Ads Studio and brand assets for client mock-ups and ad packs.

## For Alfred
Alfred should know:
- The Higgsfield model list and the start + end frame trick for seamless openings.
- Draft-then-finalise to avoid paid retakes.
- Never use AI video for the "how it works" part.
- Check credits before generating.
- The website and ad workflows above.
