# Bots for Alfred (lowkey.lore video pipeline)

These are all the bots built for the lowkey.lore TikTok videos. The full current code is in `pipeline/`. To run them, the files go in `lowkey-lore-ref\pipeline\` next to the `videos\NN-slug\` folders. The Python environment is described in `qc-usage.md`.

| Bot | File | What it does | Command |
|---|---|---|---|
| **Video maker** | `make.py` | Runs every step for one video, in order. Refuses to render if the lint fails, and refuses to push if QC hasn't passed and the file hasn't been approved. | `python make.py ..\videos\NN-slug [voice audio lint render encode pause phone sheet caption qc push]` |
| **Quality checker** | `qc.py` | Checks the finished video: picture, audio, script, pause, labels and length. Writes `qc\report.md`, `qc\result.json` and 4 fps contact sheets. Exit code 0 = pass, 1 = fail. | `python qc.py ..\videos\NN-slug` / `--approve "notes"` |
| **Scene lint** | `ll.py` (`lint()`) | Checks the 3D scene before rendering: camera snaps, objects blinking, z-fighting, things clipping, rollers sliding or spinning, labels off screen. Writes `qc\lint.json`. | `blender -b -P scene.py -- --video <dir> --lint` |
| **Render queue** | `queue.sh` | Renders a list of videos one after another, with encode and QC running in the background. Adding `:resume` to a name keeps frames already rendered. Logs to `out\queue_log.txt`. Renders run in 600-frame chunks, and a crash retries automatically. | `sh pipeline/queue.sh 06-hydro-dam 09-footpath-to-highway` |
| **Narrator** | `voice.py` | Kokoro TTS (voice `am_michael`, speed 1.2) reads `script.json` and adds the "Follow for more insight" outro. | via `make.py voice` |
| **Sound mixer** | `audio.py` | Music and sound effects, with the narrator louder than the effects. Masters to -14 LUFS with a -1 dBTP ceiling. | via `make.py audio` |
| **Editor** | `overlay.py` | Labels, arrows, captions, colour grade and warm look. Splices in the Higgsfield intro clip (`video.json` `"intro"`). Makes the phone copy (<30 MB) and the contact sheet. | via `make.py encode phone sheet` |
| **Follow pause** | `pause.py` | Mid-video freeze in the centre of the screen. Plays a cheeky line and some banter, holds for 3 s, says "Thank you…", then carries on. | via `make.py pause` |
| **Publisher** | `make.py push`, `ship.sh` | Pushes the phone copy and contact sheet to `lowkey-lore-media/` through a temporary worktree, then copies the video and caption to `Desktop\lowkey-lore-videos`. | `sh pipeline/ship.sh NN-slug` |
| **3D model kits** | `machines.py`, `machines_extra.py`, `trains.py` | Realistic machines with correct physics: rollers roll and don't spin in place. Includes steam roller, vibratory roller, cars, pump set, generator, vacuum truck, Rocket locomotive, coal wagon and high-speed train. | imported by `scene.py` |
| **Asset fetcher** | `fetch_assets.py` | Downloads the Poly Haven textures, HDRIs and models. | `python fetch_assets.py` |

Also in this folder:
- `higgsfield-features-for-lowkey-lore.md`: what Higgsfield can add, and how. The main idea is openings whose last frame is our first 3D frame, made in draft mode first with no paid retakes.
- `qc-usage.md`: exact commands, exit codes, report formats and dependencies for the quality checker.

**Rules the bots enforce:**
- First words are "Did you know"; the video ends with "Follow for more insight".
- Length is 70–90 s.
- Nothing is published without passing QC plus a visual approval of that exact file.
- No Higgsfield generation without the owner's OK.
