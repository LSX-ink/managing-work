---
name: igloo-style-3d
description: "Award-level immersive 3D (the igloo.inc school): real-time intro, ice/glass objects, particle shapes, WebGL text effects, frost and chromatic transitions, fast loading. Our own techniques, no copied code or assets."
---

# Igloo-style 3D: award-level immersive scenes

Studied from the public Awwwards case study of igloo.inc (Sept 2024) and the three.js forum showcase.
This guide describes the **techniques** only, written in our own words. Never copy another
site's code, models, textures, sounds or fonts: build every asset fresh for the client.

Their stack, for reference: Three.js, three-mesh-bvh, GSAP, Vite, a light UI framework (Svelte),
Houdini and Blender for 3D, custom exporters. Use the same kind of open tools: three.js, GSAP
ScrollTrigger, Blender, glTF.

## 1. Plan like a film
- Grey-box the scroll journey first: one "shot" per section, with the camera path drawn as previs
  (untextured renders or a plain three.js scene). Agree the shots before any detail.
- Build art and code together in the browser, with live-reload for shaders, textures and
  models, and profile performance at every step, not at the end.

## 2. Real-time intro, not a video
- Animate the opening in the engine with code and shaders (camera dolly, light sweep, object
  reveal) instead of an MP4: it is smaller, matches the rest of the scene, and can be changed instantly.
- Keep it short (2 to 4 s), skippable on scroll, and let the first frame look finished, so there is
  no flash of an empty canvas.

## 3. Ice and glass objects
- Material: `MeshPhysicalMaterial` with `transmission` 1, `thickness` 0.5 to 2, `ior` about 1.31
  (ice) or 1.5 (glass), `roughness` 0.05 to 0.25, a little `iridescence` or `dispersion` for colour
  fringes, and an HDR environment map. That alone sells "ice".
- Inner detail ("grown" crystals): fill a base shape (cube, cylinder, the client's logo extruded)
  with procedural shards. Scatter points inside the shape (use three-mesh-bvh to test inside or
  outside), grow thin elongated boxes or cones along random but clustered directions, merge them
  into one geometry, and render them with the same transmissive material plus a faint emissive rim.
  Each object gets a different seed, so no two look the same.
- Cheap fallback for phones: a normal map of cracks and a fresnel rim shader instead of real
  transmission.

## 4. Particle shapes (the "swirl into a logo" effect)
- Store each target shape as a set of points: sample the surface of a mesh, a logo outline or
  text (`MeshSurfaceSampler`) into a float texture or attribute.
- Move particles on the GPU: each one blends from its current position to the next target with
  curl noise added on top, so they swirl before settling. Use GPGPU (`GPUComputationRenderer`) for
  more than 50k particles; a vertex-shader mix between two attributes is enough for fewer.
- Colour by speed (calm = brand colour, fast = brighter tint) and add additive blending plus a
  soft bloom so moving particles glow.
- Swap targets on hover or scroll (for example one shape per service or social link), and time
  sound effects to the morph if the site has audio (start audio only after a tap).
- Keep the data tiny: quantise the positions (16-bit) and compress them, so a shape costs less
  than a normal image.

## 5. Transitions between sections
- Combine three post-processing passes, each driven by one progress uniform (0 to 1) from GSAP
  ScrollTrigger:
  - chromatic aberration: offset the R and B channels along the screen direction
  - "tech" displacement: shift UVs in horizontal bands using a stepped noise
  - frost: a noise mask that grows in from the edges, blurring and whitening what it covers
- Ramp up the effect, swap the scene or camera at the peak, then ramp down. Keep each one under a second.

## 6. Text rendered in WebGL
- For glitch and scramble effects, render headings as SDF/MSDF text (troika-three-text) rather
  than HTML. A scramble then only changes which glyph each letter draws (cheap), and a glitch is
  a small shader (band offsets plus RGB split). HTML equivalents force layout recalculation on every frame.
- Keep a real HTML copy of all text for accessibility and SEO, hidden visually behind the canvas,
  and honour `prefers-reduced-motion` (no scrambles or glitches; show the text plainly).

## 7. Fast first load
- Compress everything: glTF with Draco or Meshopt geometry, KTX2 (Basis) textures, and an
  HDR environment at 1k.
- Warm the GPU during the loader: `renderer.compileAsync(scene, camera)` for the shaders, and
  upload the first section's textures. Load later sections in the background while the user reads.
- Budget: first view interactive in under 3 s on 4G, about 2 MB before the first frame.

## 8. Phones and low-end devices (required for Kinetic)
- Tier the device on start-up (GPU name, `devicePixelRatio`, a 1 s frame-time probe): high, mid, low.
- On mid and low tiers: cap the pixel ratio at 1.5 (or 1), halve the particles, swap transmission for
  the fresnel fallback, drop to one post pass, and pause rendering when the tab is hidden or the canvas is off screen.
- With reduced motion or the low tier: show a still render of the hero (a pre-rendered image of
  the same scene), so the page never feels broken.
- Test on a real mid-range Android and an iPhone, not just a desktop.

## 9. Checklist before shipping
- [ ] Every asset is our own or properly licensed. Nothing is lifted from another site.
- [ ] The intro is real-time, skippable, and its first frame looks finished.
- [ ] The ice and glass look right on desktop, with a fallback on phones.
- [ ] Particle shapes use the client's own logo or services.
- [ ] Each transition lasts under 1 s, and every effect has a reduced-motion version.
- [ ] Text is readable in HTML for SEO and screen readers.
- [ ] The page stays at 60 fps on desktop and at least 30 fps on a mid-range phone, with the first view in under 3 s on 4G.
