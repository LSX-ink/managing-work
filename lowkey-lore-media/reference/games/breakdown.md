# Reference: statbolthq reel (Instagram DfN5YwzIHEp)

Liverpool 0–1 Arsenal, told through numbers. 63 s, 720×1280 vertical, 30 fps. About 105K likes in a day.
The source file (`statbolt_reel.mp4`) stays local and is not pushed; `contact_1fps.jpg` has one frame per second.

## What it is
It's a **football match data story**, not a video-game video. It contains no real match footage: everything is a
stylised 3D animation with real stats laid on top.

## Format, shot by shot (one frame per second)
- **Hook, 0–4 s:** "Liverpool touched the ball 48 times in Arsenal's box…" over a low, tilted 3D pitch. Each touch
  is an orange dot popping onto the grass while a big counter ticks up (29 → 48), with "touches in Arsenal's box"
  in small text underneath.
- **Payoff:** "and didn't hit the target once." Cut to a stadium scoreboard under floodlights showing 0 shots on
  target vs 3, then the league table on the scoreboard ("they're top").
- **The goal:** a paper tactics sheet on a clipboard with numbered red and white player tokens. A hand-drawn arrow
  traces the move (Ødegaard → Madueke → Rice overlapping → low cross → tapped in at the back post). A player photo
  card slides in for the scorer.
- **Stats montage:** back to the 3D pitch, where dots and numbers count up (56% possession, 17 shots, 9 blocked,
  xG 1.15 → 0.58, 0.79 vs 0.17).
- **Defender story:** a team-sheet notebook on a wooden desk. A pen writes tally marks for each stat
  (8 clearances, 5 tackles, 8 duels won), then "Arsenal cleared the ball 36 times".
- **Controversy:** a tactics-sheet close-up of a penalty-box incident (Isak and Timber), captioned "No penalty."
- **Context:** a notebook ticks off "first league win at Anfield since 2012", the season's results list and
  "sixth clean sheet in nine games".
- **Ending:** back to the opening shot: "48 touches in the box. Zero on target. Send this to the Liverpool fan who
  says they were unlucky." The end is a share CTA, not a follow CTA.

## Style
- **Captions:** word-by-word karaoke at the top in thin white text, with keywords highlighted in a teal box
  (48, box, post, Saka, Konsa…).
- **Look:** dark vignette all round, in club colours (red vs white/cream), with green grass and a red stadium.
  Big, clean numbers with small labels.
- **Camera:** slow pushes, tilts and orbits. Every 2–4 s it cuts or moves to a new "object": pitch, scoreboard,
  clipboard, notebook, seat.
- **Voice:** one calm, dry, confident narrator, fast but clear, with no music under the stats.
- **Hook:** a surprising number plus a contradiction ("48 touches… zero on target").

## Can we make this? Yes, it suits our Blender pipeline
Every element is something we already build: a 3D pitch and stadium, dots and counters, a scoreboard, paper
tactics sheets with tokens and drawn arrows, a notebook with a pen writing tallies, karaoke captions (our labels
system), a narrator at -14 LUFS, and our QC.
- **What's new:**
  1. a data layer, i.e. per-match stats in JSON driving the dots and counters
  2. a caption style with highlighted keywords
  3. a "paper props" kit (clipboard, notebook, pen, photo cards)
- **Speed:** once the kit exists, each match is mostly data plus script, so it's faster than our cutaway videos.
  It also renders faster: flat lighting, few objects.

## Copyright and rights
- **Stats and facts:** fine to use, since facts aren't copyrighted. We should cite the source in the caption
  (e.g. FBref, the BBC match report), and not scrape or resell a paid provider's (Opta's) database.
- **Player photos (the photo cards):** these are the risky part. Agency photos (Getty, PA) are actively enforced.
  Use stylised cards instead (name, number, a kit-coloured silhouette), or our own illustrations.
- **Club badges and league logos:** trademarks, so we shouldn't use them. Use club names and kit colours instead,
  which the reference does too (no badges visible).
- **Broadcast footage:** none in the reference, and we shouldn't use any. Premier League and UEFA clips get
  taken down fast.
- **Player names and likeness in commentary:** fine.

## "Every major game, then vs now"
1. **Today's big match:** posted the day after, with the 3–4 numbers that tell the story, a hook contradiction and
   a share CTA.
2. **Then vs now:** a historic classic replayed with the same kit, e.g. "Istanbul 2005: down 3–0 at half-time" or
   "Aguero 93:20". Split the pitch or compare the numbers of an old game with today's equivalent fixture.
3. **Series idea:** "The numbers behind…" (finals, derbies, title deciders), one a day, mixed with our How-It-Works
   videos or as a second account.

## Graphics: matching the reel and beating it
**What the reel's graphics are:** simple stylised 3D. The pitch is flat green with mowing stripes, the stadium is
blocky red stands, and the props are paper, pen and clipboard. Lighting is soft and flat with a heavy vignette. No
real players, no crowd detail, low-poly everywhere. Its appeal comes from the clean motion design and the pacing,
not from rendering quality.

**How we beat it, all in our existing Blender/EEVEE pipeline:**
- **Pitch:** real grass (PBR texture plus blades in the close-ups), proper floodlight lighting with soft shadows,
  depth of field and motion blur. Night games get light bloom and haze in the floodlights.
- **Stadium:** tiered stands with seat rows, a roof truss, an LED ad board ring (our own text, no brand logos) and
  an instanced low-poly crowd.
- **Players:** stylised kit-coloured mannequins with real-length runs and passes along tracked lines, instead of
  dots only.
- **Props:** a richer paper kit with paper texture, pencil-line arrows that draw on, a real pen tip and desk lighting.
- **Data graphics:** heat maps glowing on the grass, shot maps with xG-sized bubbles, pass networks as light trails.
- **Captions:** our karaoke captions plus keyword highlights, with the same QC (no flicker, labels on-screen,
  -14 LUFS).

## If "games" means VIDEO games: graphics then vs now
This fits our "How X becomes Y" format perfectly ("how Mario's 16 pixels became 4K", "how a game character went
from 300 polygons to 300,000").
- **How we'd show it:** we build ONE original character or scene and re-render it in each era's style:
  1. 8-bit pixels (tiny sprite, 4 colours)
  2. 16-bit
  3. early 3D (about 300 polygons, flat shading, wobbly textures, fog)
  4. PS2-era (normal-ish textures, baked light)
  5. PS4-era (PBR materials, shadows)
  6. today (ray-traced lighting, millions of polygons)
  Each era is labelled with real numbers: resolution, polygon count, texture size, frame rate, engine name.
- **Explainer cutaways:** wireframe overlays, a texture-mipmap explainer, the lighting pipeline. That's our
  strength, and it looks better than screenshots.
- **Copyright:** real game footage, characters (Mario, Kratos…), logos and screenshots belong to the publishers.
  TikTok often tolerates short clips used for commentary, but takedowns and muted audio are common, and Nintendo
  enforces hard. The safe route is our own lookalike-free character, with game names and stats as facts (names are
  fine to say; don't copy the art).
