# South Africa stays: daily build (2 per day)

The owner (Kinetic Web Designs) asked on 24 Oct 2026 for 2 South African short-let concepts a day ("Yes 2 per day").
Prices stay the same: websites from £395, half when we start building, half once complete. Never mention Klarna or
monthly payments. Say "pounds", never "quid". Never sign as Thato. South Africa's POPIA rules mean **no cold emails**:
the owner sends every message himself by Instagram or Facebook DM, so the job ends with a ready-to-send message.

Python: `C:\Users\Thato\managing-work\jarvis\.venv\Scripts\python.exe` (call it PY). Folder: `C:\Users\Thato\managing-work\jarvis\hq\stays` (call it STAYS).
Live site root: `C:\Users\Thato\kinetic-repo\kinetic-live\m\<slug>\` → `https://kineticwebdesigns.co.uk/m/<slug>/`.
Do not open windows on the PC. Never print keys or read .env files.

## 1. Leads: richest first, most media first
Owner, 25 Oct 2026: "pick the best properties with a lot of photos ... more pictures, more videos, more floor plans, the best
of the best. We target them as they can afford this, then we work our way down from the rich to the middle."
**Instagram only** still applies (no Instagram, no concept). Big groups with their own agencies (Singita, Londolozi, Sabi Sabi,
Virgin, Last Word, &Beyond...) are skipped by CHAIN in za_scout.py; target independent owner-run luxury stays.
1. Pending first: any `STAYS\leads\<slug>\lead.json` without a `built.txt` next to it is a lead already scouted; build it.
2. Then take the next 2 from `za_state.json` "ranked" (highest score first, skipping ids in "done"). If fewer than 10 are left,
   run `PY STAYS\za_rank.py 1 2` (luxury areas, then upmarket); once those are used up, `za_rank.py 3` (the middle).
   The score favours luxury areas, Google price level, and how many real photos, videos, 3D tours and floor plans their site has.
3. Prepare them with `PY STAYS\za_scout.py <place id> <place id>` (keeps up to 80 of their own site photos plus Google photos).
   Before building, look at the sheet: if it is thin (under ~25 good photos), skip to the next ranked one.
4. A proper website of their own is fine now: the before/after (4b) is the pitch.

## 2. Curate (per lead)
- Read `sheet.jpg` (labelled photos) and `lead.json` (their own page titles and text, Instagram/Facebook, Google data).
- Write `<folder>\rooms.json`: 2–8 rooms or units, each `{"slug","name","floor","summary","story":[2 lines],"photos":[files],"cover"}`, using
  their own words from the page text. At most 4 per floor; floor 0 = ground. Leave out photos of other businesses, maps, posters, promos.
- Write `<folder>\config.json` (see the docstring in `stays_build.py` for every field): their area for `intro`/`kicker`, an
  honest h2 and lead from what they actually offer, two extra `stats`, `kind` (guesthouse/lodge/villa/cottage/apartment),
  `unit`, `heading`, `where`, `floors`, `sea` true only if they're on the sea, `pool` label only if they have one,
  `markers` (e.g. "Reception", "Braai area", "Hot tub"), `platforms` ("Airbnb and Booking.com" unless you know better),
  and `colours` taken from their logo or site (accent must be readable on white).
- `hero.json`: `["<best exterior>"]`; copy the best wide exterior/view photo to `<folder>\exterior.jpg`.
- If there is no `logo.png`, stays_build makes a wordmark.
- Optional upgrades every concept gets when the files are there: `plan.png` + `plan.json` {"title","text","note"} adds a
  "built on the real floor plan" section (use real public plans when a council has them; never invent one), and
  `airbnb.json` {"rating","note"} adds their Airbnb rating card to Book direct (only with numbers read from their own listing).
- The 3D house is a real 3D floor plan automatically: solid walls, oak/tile/deck floors, furniture by room type, their own
  photo framed above each bed, glowing lamps, studio lighting and a camera fly-in. Nothing to do per lead.

## 3. Walkthrough video (only if Higgsfield credits allow)
- Check the Higgsfield `balance` tool. If credits < 100, skip the video (the page uses exterior.jpg as the hero) and say so.
- Otherwise make 5 clips with `generate_video`: model `kling3_0`, mode `pro`, duration 5, aspect `16:9`, sound `off`,
  `declined_preset_id` "in-the-dark", medias `start_image` + `end_image`, prompts "Smooth cinematic gimbal walkthrough ... Photorealistic,
  natural light, no people, no text." Route: arrival/exterior → entrance or deck/pool → living or main room → bedroom → view/sunset.
  Upload frames with `media_import_url` (https URLs of their own site photos; `src` in lead.json) or media_upload + PUT + media_confirm for local files.
- `jobs_wait` until done, download to `STAYS\leads\<slug>\clips\c0..c4.mp4`, check a frame sheet, then
  `PY STAYS\restitch.py <folder> STAYS\leads\<slug>\clips 0 1 2 3 4` and re-encode to ~8 MB:
  ffmpeg (from `tiktokstudio_video.ffmpeg()` in jarvis) `-vf scale=1600:-2 -c:v libx264 -preset slow -crf 27 -an -movflags +faststart`.

## 3b. The "from a line to a home" scroll story (about 3 credits)
- Pick their best whole-building exterior photo (a 3/4 or aerial view works best) and import it to Higgsfield.
- Make 3 images with `generate_image` (model `gpt_image_2_5`, quality high, resolution 2k, aspect 16:9, that photo as `image_references`),
  each "Turn this exact building into ... seen from exactly the same camera angle and framing ...":
  1 an architect's early-stage model (thin white walls rising from a white slab, black linework, plain off-white studio background);
  2 an unfinished white architectural model (all floors and walls in matte white, open window gaps);
  3 a detailed presentation model with its real materials applied (studio backdrop).
- NEVER generate interiors, cutaways or anything inside the building (owner, 24 Oct 2026: we don't know how it looks inside).
  Step 4 of the story is automatic: a mosaic of their REAL room photos ("Every room, exactly as it is.").
- Save them as `<folder>uild.jpg`..`3.jpg` (1920 wide). `build.json`: {"final": "<their real photo>", "lines": [5 headlines, last "Welcome to <short name>."]}.
- The "one line, an entire home" opening: look at `build/3.jpg` and write `door.json` {"path": [[x%, y%], ...]} — 4 or 5 points
  in percent of that image, starting at the bottom edge and following the real ground/steps/path up to their real front
  (or garden) door. stays_build then opens the hero on the model, draws a glowing gold line to the door and dives in to
  the walkthrough video, with their room photos in a strip along the bottom. No door.json = no opening (never guess a door
  that isn't visible).
- The scroll journey (always, when there is a walkthrough): write `journey.json` {"chapters": [[i/n, "kicker", "line"] one per
  walkthrough clip in order], "facts": [["Rooms", "..."], ["Google", "4.9★ from 68 reviews"], ...], "end": "Your view is waiting."}.
  Lines are short, editorial and TRUE to what that clip shows ("Breakfast with the bay.", "Live above it all."). The maker
  makes scrub.mp4 itself; scrolling then drives their film forward and back with a gold line and ends on the facts + Book direct.
- The drone fly-in (about 17.5 credits, only while credits allow): ONE `generate_video` clip, kling3_0, pro, duration 10, sound off,
  start_image = their best aerial/exterior photo, end_image = their best interior photo, prompt "One continuous, unbroken
  cinematic drone fly-in, no cuts: begin high above <their area>, descend to the <building>, ... straight through the
  <door> and settle inside the <room>". Re-encode to `<folder>lyin.mp4` (1600 wide, crf 24, no sound). The opening
  plays it once after the gold line reaches the door, then the walkthrough loops.
- stays_build adds the pinned scroll section automatically; the 3D house also builds itself out of the floor plan on first view.

- The neighbourhood section is automatic from place.json "loc" (Google's own satellite map + Street View embeds, which Google
  allows; never download or copy their imagery). If Street View has no imagery there, set "streetview": false in place.json
  (check with the Street View metadata endpoint).

## 4. Build, check, publish
- `PY STAYS\stays_build.py <folder>` (needs place.json, rooms.json, config.json, hero.json, exterior.jpg).
- Check it: serve `C:\Users\Thato\kinetic-repo\kinetic-live\m` on 127.0.0.1:8765 (`python -m http.server 8765 -d ...`, in the background) and
  run `PY STAYS\shot_stay.py http://127.0.0.1:8765/<slug>/ STAYS\leads\<slug>` (s1-s7 screenshots; prints errors and phone overflow), or use Playwright (msedge, `--use-angle=d3d11`)
  to screenshot the hero and the 3D section on desktop (1440×900) and phone (390×844). No script errors except favicon,
  no sideways scroll on phones, the 3D house shows rooms with photos. Fix anything broken.
- Publish: `cd C:\Users\Thato\managing-work\jarvis` then `PY -c "from hq import outbox; outbox.deploy_site()"`; confirm the URL returns 200.
- Write `STAYS\leads\<slug>\built.txt` with the live URL, and run `PY -c "import sys; sys.path.insert(0, r'STAYS'); import za_scout; za_scout.mark_done('<place id>', '<slug>')"`.

## 5. The message for the owner
- Make the DM with `outbox.dm_text(Settings(), p, link)` where p = {"id", "name" (their short name), "rating", "reviews",
  "website", "kind": "guest house" (or lodge/villa...), "town", "country": "ZA"}. It is signed "Kinetic Web Designs".
- Append to `C:\Users\Thato\OneDrive\Desktop\South Africa stays\South Africa stays DMs YYYY-MM-DD.md`: name, rating, town,
  where to send it (Instagram @handle, else Facebook page URL, else "search their name on Instagram/Facebook"), the live link, the message.
- Copy the walkthrough to the Desktop folder as `<Name> walkthrough.mp4`.

## 6. Report
Send the owner one short update (send_message to @parent with visibility posted_to_shared_channel if that tool is available,
else just finish with the summary): the 2 concepts with links, where to message each, credits used and credits left.

## 4b. Before and after (only when they have their own website)
Owner, 25 Oct 2026: "show the before and after if they already have a website". If place.json has a "website" that is
their own site (not an Airbnb/Booking.com/Facebook page), after the first publish run
`PY STAYS\beforeafter.py <folder> <their website> https://kineticwebdesigns.co.uk/m/<slug>/` (it declines cookie banners,
shoots their homepage as before.jpg and our page after the opening as after.jpg), then rebuild and publish again. The page
gets a "Your website today, and what it could be." drag slider above the rooms. No website = no section.

Note (owner, 26 Oct 2026): every stays DM now says the concept uses representative imagery (the model and the drone
fly-in) and that if they send more photos we'll make the site look exactly like their place, done professionally.
outbox.dm_text adds this automatically for stays; don't remove it.
