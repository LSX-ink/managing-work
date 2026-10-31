# lowkey.lore quality bot: how to run it

There are two checks.
- **Scene lint** runs inside Blender before rendering.
- **qc.py** runs on the finished mp4 after encoding.

A video is only published when both pass **and** a visual review has approved that exact file.

Project root: `C:\Users\Thato\OneDrive\Desktop\lowkey-lore-ref`. Each video lives in its own folder, `videos\NN-slug\`, which holds `scene.py`, `video.json` and `script.json`.

## Environment
- **Python:** `lowkey-lore-ref\.venv\Scripts\python.exe` (3.x). It needs `numpy`, `scipy`, `soundfile`, `Pillow` and `imageio-ffmpeg` (which provides ffmpeg). Kokoro TTS is needed only for the voice step, not for QC.
- **Blender:** Blender 5.2 at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`. The lint runs in Blender's own Python, using `pipeline\ll.py`, which `scene.py` imports.
- **qc.py imports these sibling modules:** `overlay.py`, `audio.py`, `pause.py` and `voice.py`. Run it from `pipeline\`, or call it by its full path.
- **Never run a lint at the same time as a render.** EEVEE has crashed when two Blenders run together.

## 1. Scene lint (before render)

```
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P videos\NN-slug\scene.py -- --video videos\NN-slug --lint
```

**What it checks.** It steps the animation (every 10 frames, and every 3 frames for labels) and looks for:
- camera snaps
- objects blinking in or out
- coplanar faces on the cut plane (z-fighting)
- transparent objects cutting through solids
- wheels or rollers that slide, spin in place, pivot, float or sink
- label anchors outside the frame

**Output.** It writes `videos\NN-slug\qc\lint.json`, a JSON list sorted with fails first:

```json
[
 {"kind": "label-off-screen", "severity": "fail", "objects": ["CRUSHED STONE"],
  "note": "label anchor at [1.5, 0.0, 0.14] is outside the frame (0.05, 0.31)",
  "t0": 35.6, "t1": 39.3, "count": 38}
]
```

- `severity` is either `fail` or `review`.
- `kind` is one of: `camera-snap`, `visibility-flicker`, `coplanar`, `transparent-cut`, `roller-slide`, `roller-spin`, `roller-float`, `label-off-screen`.
- It also prints a summary line on stdout, for example `LINT 6 fail, 0 review`.

**Exit code.** Blender exits 0 even when the lint finds problems. **Pass means `lint.json` contains no item with `"severity": "fail"`.** A non-zero exit, or a missing or stale `lint.json`, means an error: the scene crashed, so read the stdout traceback. `make.py lint` applies this rule and exits with the message `scene lint failed: fix the scene before rendering`.

## 2. qc.py (after encode + pause)

```
.venv\Scripts\python.exe pipeline\qc.py videos\NN-slug
```

| Exit code | Meaning |
|---|---|
| `0` | Automatic QC **PASS** |
| `1` | Automatic QC **FAIL**: send it back to be fixed |
| Any other non-zero code, or a Python traceback | **Error**: a file is missing (mp4, `audio\mix.wav`, `pause.json`), or ffmpeg failed |

**Checks:**
- **Scene lint result:** fails are copied in from `qc\lint.json`, and a missing lint counts as a fail.
- **Picture:** black frames, frozen stretches, one-frame flicker or pops, and unplanned hard cuts.
- **Audio:**
  - loudness -14 LUFS ±1
  - true peak ≤ -1 dBTP
  - no silence gaps, except the planned pause hold
  - narrator ≥ 8 dB above the sound effects
- **Script:** the video starts with "Did you know", ends with "Follow for more insight", and the mid-video pause has a ~3 s hold followed by a thank-you.
- **Overlay:** labels are on screen, and label pills don't overlap each other or the caption.
- **Delivery:**
  - 70–90 s long, not counting the pause
  - 1080×1920 at 30 fps
  - phone copy under 30 MB

**Outputs, all in `videos\NN-slug\qc\`:**
- `result.json`, in JSON:

  ```json
  {"file": "lowkey-lore-footpath-to-highway.mp4", "sha": "c5ebe9ffd2a31ba2",
   "passed_automatic": false,
   "fails": ["frozen picture from 87.37s", "flicker / pop at 16.37s (block jump 19)",
             "unplanned hard cut at 32.30s (mean change 28)"],
   "warnings": [], "review": [], "loudness": -14.1, "true_peak": -1.8, "duration": 88.4,
   "sheets": ["sheet_01_000.0s.jpg", "..."]}
  ```

- `report.md`, a human-readable report:

  ```
  # QC report: lowkey-lore-footpath-to-highway
  file lowkey-lore-footpath-to-highway.mp4  sha c5ebe9ffd2a31ba2  88.4s  -14.1 LUFS  -1.8 dBTP
  ## Automatic: FAIL
  - FAIL frozen picture from 87.37s
  - FAIL flicker / pop at 16.37s (block jump 19)
  ## Needs review
  ## Visual / real-life checklist (sign off with --approve)
  - [ ] Every object looks like the real thing from that era ...
  ```

- `sheet_NN_<start>s.jpg`: contact sheets at 4 frames per second, 60 frames each, used for the visual review.
- The script also prints a summary line on stdout, for example `QC FAIL <name>: 20 fails, 0 warnings, 0 to review`.

## 3. Visual approval + gate

```
.venv\Scripts\python.exe pipeline\qc.py videos\NN-slug --approve "checked sheets: rollers roll, no pops, labels correct"
```

This writes `qc\approval.json` (`sha`, `notes`, `checklist`).
- It refuses with an `AssertionError` and a non-zero exit if the automatic QC has not passed, or if the mp4 changed since QC ran.
- Before approving, the reviewer works through `REVIEW_CHECKLIST` in qc.py, which checks for things that differ from real life: rollers spinning, floating, clipping, pops, camera snaps, and wrong labels.

`qc.gate(vdir)` in Python returns True only when `result.json` passed **and** both `result.json` and `approval.json` match the current mp4's sha. `make.py push` refuses to publish otherwise.

## Full pipeline (what wraps all of this)

```
.venv\Scripts\python.exe pipeline\make.py videos\NN-slug voice audio lint render encode pause phone sheet caption qc
.venv\Scripts\python.exe pipeline\qc.py videos\NN-slug --approve "..."
.venv\Scripts\python.exe pipeline\make.py videos\NN-slug push
```

`pipeline\queue.sh name1 name2 ...` (Git Bash) renders a list of videos one at a time and logs to `out\queue_log.txt`. Adding `:resume` to a name keeps the frames already rendered.
