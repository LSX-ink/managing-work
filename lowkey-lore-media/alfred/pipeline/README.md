# lowkey.lore production pipeline

One folder per video: `videos\NN-slug\`
- `script.json` – 14 steps. First words "Did you know", step 14 "And that's how X becomes Y.".
  `voice.py` appends the spoken outro "Follow for more insight." automatically.
- `scene.py` – Blender scene (imports `pipeline\ll.py`); `apply_state(t)` animates everything.
- `video.json` – title lines ("How X becomes Y"), caption keywords (yellow), labels, arrows, sfx cues, topic tag.
- generated: `audio\`, `timeline.json`, `frames\`, `cams\`, `out\*.mp4`, `out\*-contact-sheet.jpg`, `caption.txt`

Run everything (voice -> audio -> render -> encode -> phone -> sheet -> caption -> push):

    .venv\Scripts\python.exe pipeline\make.py videos\01-log-cabin

or single steps: `... make.py videos\01-log-cabin render encode`.
Test stills: `blender -b -P videos\NN\scene.py -- --video videos\NN --stills 3,20,60`.

Rules: 70–90 s, 10–14 steps simple -> modern, same v3 look (Poly Haven textures, cutaway at y=0,
one caption word centre-screen, label pills, arrows), Kokoro am_michael @1.2, quiet documentary bed.

Render speed (RX 6600, 1080x1920): ~0.8–1.1 s/frame at v3's quality settings, so ~40 min per 80 s video.
See the comment block at the top of `ll.py` for what was changed (tree shadow proxies, no point-light
shadows, one persistent animation render, visibility written only on change).
