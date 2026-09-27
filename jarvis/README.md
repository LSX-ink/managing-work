# J.A.R.V.I.S. — personal voice assistant

A local voice assistant with a dry British butler's manners. You talk to it in the browser. It thinks with Claude, answers out loud, searches the web, checks the weather and your to-do list, opens pages for you, and can look at your screen.

Inspired by [Julian-Ivanov/jarvis-voice-assistant](https://github.com/Julian-Ivanov/jarvis-voice-assistant) and written from scratch here, with these changes:

| | Original | This version |
|---|---|---|
| Platform | Windows only (PowerShell, Win32) | Windows, macOS, Linux |
| Language | German | English or Afrikaans, and other languages through settings |
| Actions | `[ACTION:...]` tags parsed out of the reply with a regex | Claude's native tool use, with parallel calls and error results |
| Web search | Playwright scraping DuckDuckGo | Claude's server-side `web_search` / `web_fetch`, so no browser automation is needed |
| Voice | ElevenLabs required | ElevenLabs optional; otherwise the browser's own voice |
| Config | `config.json`, name hard-coded in the prompt | `.env` / environment variables |
| Network | Listens on `0.0.0.0` | Listens on `127.0.0.1` and rejects WebSockets from other origins, because it can see your screen |
| Typing | Voice only | Voice, or type in the box (works in any browser) |

## How it works

```
You speak ─▶ browser (Web Speech API, speech → text)
                 │  WebSocket
                 ▼
          server.py (FastAPI, on your machine)
                 │
                 ▼
          brain.py ── Claude ──┬─ web_search / web_fetch   (run by Anthropic)
                               ├─ get_weather              (Open-Meteo, no key)
                               ├─ get_tasks                (your Markdown file)
                               ├─ open_url                 (your default browser)
                               └─ look_at_screen           (screenshot → Claude vision)
                 │
                 ▼
          tts.py (ElevenLabs MP3)  or  the browser's speechSynthesis
                 │
                 ▼
          You hear the answer
```

Jarvis speaks each step as it comes. You hear "One moment, sir." before a search, not only once the whole turn is finished.

## Setup

Requirements: Python 3.10+. Use Chrome or Edge for voice input. Other browsers can use the text box.

```bash
cd jarvis
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in ANTHROPIC_API_KEY and the rest
python server.py
```

Open <http://127.0.0.1:8340>, click the orb, and allow the microphone. Jarvis greets you with the weather and your tasks, then listens.

- Click the orb to pause or resume listening.
- Click it while Jarvis is talking to cut him off.

### Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | From [console.anthropic.com](https://console.anthropic.com) |
| `JARVIS_MODEL` | `claude-opus-5` | Any Claude model. `claude-haiku-4-5` is cheaper and faster, but less capable. |
| `JARVIS_EFFORT` | `low` | Thinking effort. `low` keeps voice replies fast. |
| `ELEVENLABS_API_KEY` | (empty) | Optional, for a better voice. When empty, the browser's voice is used. |
| `ELEVENLABS_VOICE_ID` | George | Any ElevenLabs voice ID |
| `ELEVENLABS_MODEL` | (auto) | Empty picks `eleven_turbo_v2_5` for languages it speaks, otherwise `eleven_v3` |
| `JARVIS_PERSONA` | `jarvis` | `jarvis` (Iron Man's AI) or `alfred` (Batman's butler) |
| `JARVIS_THEME` | `classic` | `classic` (plain orb) or a HUD dashboard: `hud` (blue), `hud-gold`, `hud-purple`, `hud-red`, `hud-green` |
| `JARVIS_GREETING` | (empty) | A fixed line to say when woken, e.g. `Good {time_of_day}, sir.` (`{time_of_day}` becomes morning, afternoon or evening). Empty gives the weather-and-tasks greeting |
| `JARVIS_USER_NAME` / `JARVIS_USER_ADDRESS` | (empty) / `sir` | How Jarvis addresses you |
| `JARVIS_CITY` | (empty) | Home city for the weather |
| `JARVIS_TASKS_FILE` | (empty) | A Markdown file with `- [ ] task` lines, such as an Obsidian note |
| `JARVIS_SPEECH_LANG` | `en-GB` | Language code for speech recognition, the voice and the page text |
| `JARVIS_LANGUAGE` | `English` | The language Jarvis replies in |
| `JARVIS_ENABLE_WEB` / `JARVIS_ENABLE_SCREEN` | `true` | Turn web search or screen viewing off |
| `JARVIS_ENABLE_PC` | `true` | Open apps, folders and files; media and volume; find and read files |
| `JARVIS_ENABLE_COMPUTER` | `false` | Mouse and keyboard control, with your OK for every action (Opus 5 models) |
| `JARVIS_PASSWORD` | (empty) | When set, the page asks for this password first. A browser stays logged in for 30 days, or until you change the password |
| `JARVIS_EMAIL_ADDRESS` / `JARVIS_EMAIL_APP_PASSWORD` | (empty) | Your email and an app password, for delivery alerts. See [Deliveries and calls](#deliveries-and-calls) |
| `JARVIS_EMAIL_IMAP_HOST` / `JARVIS_EMAIL_CHECK_SECONDS` | `imap.gmail.com` / `60` | Mail server, and how often to look for new mail |
| `JARVIS_PHONE_ALERTS` | `false` | Announce phone calls and delivery-app notifications that Phone Link shows (Windows) |
| `JARVIS_NTFY_TOPIC` | (empty) | Secret topic name for call alerts over the internet. See [Calls over the internet](#calls-over-the-internet-android) |
| `JARVIS_HOST` / `JARVIS_PORT` | `127.0.0.1` / `8340` | Where the server listens |

On Opus 5 the server turns on the API's `fallbacks: "default"`. If a safety classifier declines a request, it is retried on a suitable model instead of failing.

### Your own colours

Updates replace `style.css` and `hud.css`, so don't put your colours there. Put them in `frontend/custom.css` instead. Git ignores that file, so updates never touch it, and it loads last, so it wins over any theme.

Start from the example (in PowerShell, from the `jarvis` folder):

```
Copy-Item frontend\custom.example.css frontend\custom.css
```

Then change the colours in `frontend/custom.css` and refresh the page. `JARVIS_THEME` still picks the look (`classic` or a `hud` layout), and your colours go on top. Without a `custom.css`, the page looks as usual and the server logs a harmless `404` for it.

### Alfred (Batman's butler)

Put these in `.env`:

```
JARVIS_PERSONA=alfred
JARVIS_USER_ADDRESS=Master Bruce      # or "Master" plus your own name, or "sir"
JARVIS_SPEECH_LANG=en-GB
JARVIS_LANGUAGE=English
```

- **Personality:** a warm, dignified English butler who fusses kindly about late nights and skipped meals, with dry humour. He speaks in his own words, not lines from the films.
- **Page:** the page, tab title and transcript show "Alfred".
- **Voice with ElevenLabs:** the default George voice is a warm, older British voice that suits him. For something closer, search the ElevenLabs Voice Library for "English butler" or "old British gentleman" and put the voice ID in `ELEVENLABS_VOICE_ID`. The voice isn't a copy of any Batman actor's real voice: cloning a real person's voice needs their permission.
- **Voice without ElevenLabs:** the browser picks a British male voice when it has one, such as "Google UK English Male" in Chrome.

Alfred works in Afrikaans too: keep the Afrikaans settings below and add `JARVIS_PERSONA=alfred`.

### Afrikaans

Put these in `.env`:

```
JARVIS_SPEECH_LANG=af-ZA
JARVIS_LANGUAGE=Afrikaans
JARVIS_USER_ADDRESS=meneer
ELEVENLABS_API_KEY=...
```

- **Listening:** Chrome and Edge understand Afrikaans (`af-ZA`).
- **Replies:** Claude answers in Afrikaans. The page text and Jarvis's fixed lines ("something went wrong") switch to Afrikaans too.
- **Voice:** use ElevenLabs. Most desktop browsers have no Afrikaans voice, and without one the browser reads Afrikaans with an English voice (the page tells you when this happens). ElevenLabs' fast Turbo model doesn't speak Afrikaans, so Jarvis switches to `eleven_v3` by itself. It sounds natural but takes a little longer per reply. Chrome on Android usually does have a Google Afrikaans voice, so there it can work without ElevenLabs.
- **Accent:** the default voice (George) speaks Afrikaans with an English accent. For a local accent, pick a South African voice in the ElevenLabs Voice Library and put its ID in `ELEVENLABS_VOICE_ID`.

### Controlling your computer

**Everyday control** (`JARVIS_ENABLE_PC=true`, on by default):

- "Open Spotify", "Open my Downloads folder": any installed app, including Microsoft Store apps.
- "Pause the music", "Next song", "Turn the volume up", "Mute", "Lock my computer".
- "Find my CV", "Read me the notes in shopping.txt", "Open the holiday photo": searches Desktop, Documents, Downloads, Pictures, Music and Videos.

File access is **read-only** and limited to your home folder. Anything that looks like a secret is refused, such as `.env`, key files, password stores, or `.ssh`. Only documents, pictures and media are opened, never programs or scripts.

**Mouse and keyboard** (`JARVIS_ENABLE_COMPUTER=true`, off by default). Alfred looks at your main screen and clicks and types like a person, for example "Reply to the last WhatsApp message saying I'm on my way". Safety:

- **You approve every click and keystroke.** A panel on the page lists what he wants to do, with **Allow**, **Allow for this task** or **Deny**. If you don't answer within 2 minutes, it counts as Deny. Looking at the screen doesn't need approval.
- **Emergency stop:** throw the mouse into any corner of the screen and the current action aborts.
- Text on web pages, in files or on screen is treated as information, never as instructions.
- This is slower and costs more than the other tools, because every step sends a screenshot. Alfred uses the simple tools first when they can do the job.
- It needs an Opus 5 model (`claude-opus-5`, the default) and the `pyautogui` package (in `requirements.txt`). Typing works for plain letters, numbers and symbols; accented characters may be skipped.

### Deliveries and calls

Jarvis can speak up on his own when a delivery is on its way or your phone rings, for example "Sir, an email from Deliveroo: Your order is on its way" or "Sir, incoming call from Mum." The Jarvis page must be open to hear it. You can also ask "Is anything being delivered today?"

Deliveroo, Just Eat and Uber Eats have no way for personal apps to log in, so Jarvis doesn't use your accounts with them. He reads the emails and phone notifications they already send you.

**Delivery emails (Gmail).** Jarvis checks your inbox every minute and announces order and delivery emails from Deliveroo, Just Eat, Uber Eats, Amazon, Royal Mail, Evri, DPD, DHL, UPS, FedEx and Yodel. Adverts ("50% off") are skipped. He only reads the sender, subject and date, and never marks anything as read.

1. Turn on 2-Step Verification for your Google account, if it isn't on: <https://myaccount.google.com/signinoptions/twosv>
2. Make an app password at <https://myaccount.google.com/apppasswords>. Call it "Jarvis". Google shows a 16-letter password once, so copy it.
3. Put these in `.env` and restart Jarvis:

```
JARVIS_EMAIL_ADDRESS=you@gmail.com
JARVIS_EMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

The console then says `Watching you@gmail.com for delivery emails.` Only mail that arrives after that is announced. To stop it, delete the app password on the same Google page. Other providers work too: set `JARVIS_EMAIL_IMAP_HOST` (Outlook is `outlook.office365.com`).

**Phone calls (Windows with Phone Link).** Phone Link shows your phone's calls and notifications on your PC. Jarvis reads those notifications and announces incoming calls, plus Deliveroo, Just Eat and Uber Eats app notifications such as "Your rider is nearby".

1. Link your phone in the **Phone Link** app on Windows (Android or iPhone). In Phone Link's settings, turn on calls and notifications from your phone.
2. Put `JARVIS_PHONE_ALERTS=true` in `.env`.
3. Install the extra Windows packages, from the `jarvis` folder:

```
pip install -r requirements.txt
```

4. Start Jarvis. If Windows asks whether Python may read your notifications, allow it. If the console says Windows blocked it, open **Settings > Privacy & security > Notifications**, turn on notification access for apps, and restart Jarvis.

Phone Link must be running, and calls only come through while the phone is connected over Bluetooth. Jarvis says who is calling but can't answer or reject the call.

### Calls over the internet (Android)

This works wherever your phone is, with no cable or Bluetooth. When a call comes in, a free app on your phone called MacroDroid posts it to [ntfy.sh](https://ntfy.sh), a free notification relay. Jarvis listens there and says "Sir, incoming call from Mum." Both the phone and the PC only need internet.

1. Make a secret topic name. In PowerShell, run:

```
python -c "import secrets; print('jarvis-' + secrets.token_hex(8))"
```

2. Put what it prints in `.env`, for example `JARVIS_NTFY_TOPIC=jarvis-3f9a1c0b7d2e4a61`. Treat it like a password: anyone who knows it can read your call alerts or make Jarvis speak.
3. Restart Jarvis. The console says `Listening for phone alerts over the internet.`
4. Test it from a second PowerShell window, with your topic in place of the example:

```
curl.exe -d "Incoming call from Test" https://ntfy.sh/jarvis-3f9a1c0b7d2e4a61
```

   Jarvis should say "Sir, incoming call from Test."

5. On your Android phone, install **MacroDroid** from the Play Store and add a macro:
   - **Trigger:** Phone > **Call Incoming**, any number.
   - **Action:** Connectivity > **HTTP Request**. Method `POST`. URL `https://ntfy.sh/` followed by your topic. For the body, type `Incoming call from ` and then add the caller's name with the magic text button (it shows as `[call_name]`).
   - Save it, and allow the phone and contacts permissions MacroDroid asks for.

Call yourself from another phone to try it. You can make more macros the same way, for example a **Notification Received** trigger for Deliveroo, Just Eat or Uber Eats that posts the notification text.

iPhone can't do this: iOS doesn't let apps or Shortcuts react to incoming calls. On an iPhone, use Phone Link above.

Your caller's name passes through ntfy.sh on its way to Jarvis. If you'd rather not, [run your own ntfy server](https://docs.ntfy.sh/install/) and set `JARVIS_NTFY_SERVER`.

### Double-clap to wake (optional)

```bash
pip install sounddevice numpy
python scripts/clap_trigger.py
```

Clap twice and it starts the server if it isn't running, then opens Jarvis in your browser. If it misses claps or fires on noise, adjust `THRESHOLD` in the script.

## Things to try

- "Jarvis, what's the weather like in Tokyo?"
- "What's on my list today?"
- "Look up the latest news on the James Webb telescope."
- "Open the BBC weather page."
- "What am I looking at?" (uses the screen)

## Costs and privacy

- Each reply is one or more Claude API calls. Web searches are billed per search, and screenshots are billed as image input.
- "What am I looking at?" sends a screenshot of your whole screen to Anthropic. Set `JARVIS_ENABLE_SCREEN=false` if you don't want that.
- Chrome's speech recognition sends your audio to Google.
- With delivery or call alerts on, the subjects of delivery emails and what Jarvis announced (such as who called) are sent to Claude with your next message. Other emails are never sent anywhere.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

The tests stand in a fake Claude client, so they need no API key or network.

| File | Purpose |
|---|---|
| `server.py` | FastAPI app: page, `/config`, `/ws` WebSocket |
| `brain.py` | System prompt, model-specific options, tool loop, history trimming |
| `tools.py` | Weather, tasks, open URL, screenshot, deliveries |
| `alerts.py` | Delivery emails (IMAP) and phone calls (Phone Link or ntfy) announced on their own |
| `pc.py` | Apps, folders, media keys, find/read/open files |
| `computer.py` | Mouse and keyboard for Claude's computer toolset |
| `tts.py` | ElevenLabs text-to-speech |
| `config.py` | Settings from the environment |
| `frontend/` | Orb UI, speech in and out |
| `scripts/clap_trigger.py` | Double-clap launcher |
