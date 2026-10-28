---
name: scroll-assembly-3d
description: Award-level scroll-driven 3D for websites, learned from studying igloo.inc (Awwwards site of the day, built by Abeto for Bureaux) - a hero object that builds itself from pieces, glowing seams, fog and bokeh depth, text inside the 3D scene, compressed assets, sound. Use when a site or mock-up should feel like igloo.inc, when asked for "assemble on scroll", "exploding 3D", "cinematic 3D hero", or a premium 3D first screen. Our own notes and code; nothing of igloo.inc's is copied.
---

# Scroll-assembly 3D (the igloo.inc way, in our own code)

Studied on 28 Oct 2026 by looking at the live site and the files it loads (names and types only). Their models,
textures, code and sounds are theirs: never download or reuse them. Rebuild the ideas with our own code and the
business's own assets (logo, photos, colours).

## What the site does
1. **One hero object that assembles as you scroll.** The igloo is made of separate ice blocks. Scrolling flies them
   in and locks them into place; scrolling on breaks them apart into the next scene. Scroll position drives the
   animation directly (scrubbed), it is not a one-off timer.
2. **Seams that glow.** Gaps between blocks light up while pieces are apart and fade once they lock: the light
   tells the eye where the pieces meet.
3. **Depth without clutter.** Soft volumetric fog (small 3D noise textures, 32-64 px cubes), bokeh sprites, caustic
   light on surfaces, a monochrome palette with one accent. The scene stays quiet so the motion reads.
4. **Text lives in the scene.** Numbers and labels are rendered inside WebGL with MSDF fonts (crisp at any size) and
   a data texture for counters, so they move with the camera instead of floating over it.
5. **Everything compressed.** Three.js r165; textures as KTX2 (Basis Universal, transcoded in a worker), meshes as
   Draco (.drc), HDR lighting decoded in a worker. Big scenes still load fast.
6. **Sound design.** Short sounds for each event (block lock, shard, enter/leave project, UI ticks) plus ambient
   wind/room loops, mixed in an audio worker, off until the visitor turns it on.
7. **Three scenes, one story.** Igloo (who we are) to cubes/portfolio (what we make) to manifesto; the camera moves
   between scenes instead of the page cutting.

## Our recipe (Three.js)
- **Pieces:** split the hero into parts that share one texture mapping, so the image lines up exactly when they
  meet. A disc logo: `CylinderGeometry(r, r, h, segs, 1, false, thetaStart, thetaLength)` wedges; their caps all use
  the same disc UVs. For a word or block shape: pre-split the mesh once, keep each part's home position.
- **Per piece:** store an outward offset (radial, random 1.4-3.6), a random rotation and a small random delay.
- **Drive:** `k = (1 - easeOutCubic((t - 0.2 - delay) / 1.8)) + scrollProgress * 0.85`;
  `position = offset * k`, `rotation = rot * k`. One value assembles on load and breaks apart on scroll.
- **Glow:** a shared emissive on the edge material, `intensity = min(1.4, maxK * 1.6)`; a short flash when it locks.
- **Read scroll inside the render loop** (`scrollY` once per drawn frame), never in a scroll listener; stop drawing
  when the hero is off screen (IntersectionObserver) or the tab is hidden.
- **Fade the canvas as pieces spread** (`opacity = 1 - progress * 1.25`) so they never cover the next section's words.
- **Place per layout** so the headline stays clear: over the photo where there is one, beside the words on a
  computer, a free corner on a phone.
- **Respect people:** reduced motion gets one assembled still frame; no WebGL means no canvas and the page still
  works; pixel ratio capped (1.5 phone, 1.75 desktop); sound only after a click.
- **Assets:** compress our own models with gltf-transform + Draco and textures to KTX2
  (see threejs-agents-model-optimizer); keep the first screen under ~1.5 MB.

## In Kinetic mock-ups
hq/premium/depth3d.py does the medallion version automatically for every new mock-up: the business's logo on a
disc of wedge shards that fly in and lock with glowing seams, then break apart and fade as the visitor scrolls.

## Ideas to take further (by hand, per client)
- A barber's pole or chair assembling from pieces; a salon's bottle forming from glass shards.
- Prices and opening hours as MSDF text inside the scene.
- A second scene the camera travels to (the work / gallery), igloo-style, instead of a page cut.
- A one-tap sound toggle with soft lock clicks.
