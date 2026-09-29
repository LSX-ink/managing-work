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
| `JARVIS_THEME` | `classic` | `classic` (plain orb) or a HUD dashboard: `hud` (blue), `hud-gold`, `hud-purple`, `hud-red`, `hud-green`, `hud-stars` (black and white on a starfield). The HUD's centre is a dotted wolf head that streams dots while he is thinking |
| `JARVIS_GREETING` | (empty) | A fixed line to say when woken, e.g. `Good {time_of_day}, sir.` (`{time_of_day}` becomes morning, afternoon or evening). Empty gives the weather-and-tasks greeting |
| `JARVIS_USER_NAME` / `JARVIS_USER_ADDRESS` | (empty) / `sir` | How Jarvis addresses you |
| `JARVIS_CITY` | (empty) | Home city for the weather |
| `JARVIS_TASKS_FILE` | (empty) | A Markdown file with `- [ ] task` lines, such as an Obsidian note |
| `JARVIS_SPEECH_LANG` | `en-GB` | Language code for speech recognition, the voice and the page text |
| `JARVIS_LANGUAGE` | `English` | The language Jarvis replies in |
| `JARVIS_ENABLE_WEB` / `JARVIS_ENABLE_SCREEN` | `true` | Turn web search or screen viewing off |
| `JARVIS_ENABLE_PC` | `true` | Open apps, folders and files; media and volume; find and read files |
| `JARVIS_NOW_PLAYING` | `true` | Pop-up card with the song, artist and cover when a new song starts (Windows) |
| `JARVIS_MUSIC_COUNTRY` | (from `JARVIS_SPEECH_LANG`) | Apple Music store country, e.g. `gb`, `za`, `us` |
| `JARVIS_ENABLE_COMPUTER` | `false` | Mouse and keyboard control, with your OK for every action (Opus 5 models) |
| `JARVIS_PASSWORD` | (empty) | When set, the page asks for this password first. A browser stays logged in for 30 days, or until you change the password |
| `JARVIS_EMAIL_ADDRESS` / `JARVIS_EMAIL_APP_PASSWORD` | (empty) | Your email and an app password, for delivery alerts. See [Deliveries and calls](#deliveries-and-calls) |
| `JARVIS_EMAIL_IMAP_HOST` / `JARVIS_EMAIL_CHECK_SECONDS` | picked from your address / `60` | Mail server (left blank or mistyped, it is picked from your email address), and how often to look for new mail |
| `JARVIS_PHONE_ALERTS` | `false` | Announce phone calls and delivery-app notifications that Phone Link shows (Windows) |
| `JARVIS_CALL_ALERTS` | `true` | Call alerts from your phone over the internet. See [Calls over the internet](#calls-over-the-internet-android) |
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
- "Pause the music", "Next song", "Turn the volume up", "Mute", "Lock my computer". These work with Apple Music, Spotify and most players.
- **Now playing:** when a new song starts in Apple Music, Spotify, YouTube or any player, a card with the cover, song and artist slides in at the top of the page for 8 seconds (Windows). Set `JARVIS_NOW_PLAYING=false` to turn it off.
- "Put on Bohemian Rhapsody on Apple Music", "Find Adele on Apple Music": opens the song, album or artist in the Apple Music app (from the Microsoft Store on Windows), or on music.apple.com if the app isn't installed. Press play there; Apple lets no outside app start a new song by itself. No Apple login is needed for this. Set `JARVIS_MUSIC_COUNTRY` (e.g. `gb`, `za`) if songs come from the wrong country's store.
- "Find my CV", "Read me the notes in shopping.txt", "Open the holiday photo": searches Desktop, Documents, Downloads, Pictures, Music and Videos.

File access is **read-only** and limited to your home folder. Anything that looks like a secret is refused, such as `.env`, key files, password stores, or `.ssh`. Only documents, pictures and media are opened, never programs or scripts.

**Mouse and keyboard** (`JARVIS_ENABLE_COMPUTER=true`, off by default). Alfred looks at your main screen and clicks and types like a person, for example "Reply to the last WhatsApp message saying I'm on my way". Safety:

- **You approve every click and keystroke.** A panel on the page lists what he wants to do, with **Allow**, **Allow for this task** or **Deny**. If you don't answer within 2 minutes, it counts as Deny. Looking at the screen doesn't need approval.
- **Emergency stop:** throw the mouse into any corner of the screen and the current action aborts.
- Text on web pages, in files or on screen is treated as information, never as instructions.
- This is slower and costs more than the other tools, because every step sends a screenshot. Alfred uses the simple tools first when they can do the job.
- It needs an Opus 5 model (`claude-opus-5`, the default) and the `pyautogui` package (in `requirements.txt`). Typing works for plain letters, numbers and symbols; accented characters may be skipped.

### Memory folders

On the HUD, click **MEMORY** at the top right. Each of the wolf's six parts is labelled as a folder: Ideas, Work, Music, Personal, Shopping and Reminders. Click a part to open its folder. There you can rename it, save a note, add files with **ADD FILE**, open what's inside, or delete something with **×**. Click **MEMORY** again to hide the labels.

The folders are real folders on your PC, in `jarvis\memory` (or wherever `JARVIS_MEMORY_DIR` points). Git ignores them, so updates never touch them. You can also ask, for example "Alfred, save 'buy milk' in my Shopping folder" or "What's in my Ideas folder?"

Say "Alfred, open my Work folder" and he opens it on the HUD, or "open my Work folder on the PC" for File Explorer.

Alfred can make new folders too: "Alfred, create a Fitness folder" makes one of his own, and "create an Invoices folder in Work" makes one inside the six. Then say "save this in Fitness", "download this into Work/Invoices" or "open Work/Invoices" (that one opens in File Explorer). Every folder you make also becomes a ringed star in the sky around the wolf: hover it to see its name, click it to open the folder on the PC. When Alfred opens one, its star flares. New folders also show at the top of their folder's panel.

To remove one, say "Alfred, delete the Work/Payslips folder". He asks you to confirm first, and only deletes empty folders he or you made, never the wolf's six.

Alfred can download files too: "Download this PDF into my Work folder" with a link, or "find the Python logo and save it in Ideas". He keeps the file's own name unless you give one. Downloads are limited to 200 MB, and he refuses links that point at your own PC or home network (your router, other devices).

### Alfred remembers you

Tell him things worth knowing ("Alfred, remember my sister Lebo's birthday is 3 May", "remember I don't eat pork") and he keeps them for every future conversation, even after a restart. He also saves things you mention in passing that are clearly worth knowing. "Forget the thing about pork" removes it. The facts are in `jarvis\memory\about-you.md`, one per line, so you can read or edit them yourself.

He also remembers your last ten exchanges, so after a restart or a page reload you can carry on where you left off ("what did you just say?"). They're kept in `jarvis\memory\.recent-chat.json`; delete that file to wipe them.

### Talking hands-free

Once you've clicked the orb, Alfred keeps listening. Say **"stop"**, **"quiet"** or **"that's enough"** while he's talking and he stops at once. With the TV on or friends round, say "Alfred, only listen when I say your name". After that he ignores anything that doesn't include "Alfred", except follow-ups within 20 seconds of his reply. "Answer everything again" turns it off. To start in that mode every time, set `JARVIS_WAKE_WORD=true` in `.env`.

### Moving the chat

Say "Alfred, move the chat to the bottom left" (or top left, top right, bottom right) to keep the centre free for the wolf. "Put the chat back in the middle" undoes it. Your browser remembers where you put it. On narrow windows it stays in the middle.

### Timers and breaks

"Alfred, set a timer for 10 minutes" (or "a pasta timer for 8 minutes"). When it ends he chimes and tells you, and it goes in the notifications. Ask "how long is left?" or "cancel the pasta timer". Say "Alfred, take a break" and he goes quiet, ignoring everything including his own announcements (they still appear in the notifications) until you say "Alfred" again or click the orb.

### Start with Windows

In PowerShell, in the jarvis folder, run `.\scripts\autostart.ps1` once. From then on Jarvis starts minimised when you log in, and the HUD opens in your browser. `.\scripts\autostart.ps1 -Remove` turns it off. You can also double-click `scripts\start-jarvis.cmd` to start him by hand. (If you changed `JARVIS_PORT`, change 8340 in that file too.)

### Calendar

Alfred can read your calendar: "what's on today?", "am I free Friday?", "what's my week like?". His greeting mentions today's events. He can only look, never change anything. Give him your calendar's private iCal address as `JARVIS_CALENDAR_URL=` in `.env`:
- **Google Calendar** (on a computer): Settings, click your calendar on the left, then *Integrate calendar*, then copy *Secret address in iCal format*.
- **Outlook.com**: Settings, Calendar, Shared calendars, *Publish a calendar*, then copy the ICS link.
- **iCloud** (iPhone calendar): in the Calendar app, tap the calendar's ⓘ, turn on *Public Calendar* and share the link. Anyone with the link can see it, so keep it private.

### Reading your documents

Alfred can open the PDFs, pictures and text files in his memory folders and answer questions about them: "how much tax did I pay on my last payslip?", "add up my net pay from the payslips in HS2", "what does that letter in Personal say?".

### PC health and setup check

"Why is my PC slow?" or "how much space have I got?" gets CPU, memory, disk and battery, plus which apps use the most memory. "What's set up?" or "is my email working?" lists which features are on and what's missing from `.env`. It never reads out passwords or keys.

### Inbox and shopping list

With email set up, "Alfred, anything important in my email today?" gets a summary that skips the adverts. "Add milk and eggs to the shopping list", "what's on my shopping list?", "tick off milk" and "clear the list" keep a list in `memory\Shopping\list.md`.

### Reminders

"Alfred, remind me at 7 pm to call Mum", "remind me tomorrow at 9 about the dentist" or "every weekday at 8 remind me to take my tablets". He says it with a chime at that time. Reminders are saved in `jarvis\memory\reminders.json`, so they survive a restart. If Jarvis is closed when one comes due, he says it (and when it was due) as soon as you open the page again. Ask "what reminders do I have?" or "cancel the dentist reminder".

### Filing emails automatically

With your email set up (see Deliveries below), say "Alfred, save every payslip email from VGC into my HS2 folder". He files matching emails from the last four months straight away and then every new one as it arrives: each attachment (the payslip PDF) and the email text, named by the date the email was sent, e.g. `VGC Payslip 2025-09-27.pdf`. A folder that doesn't exist is created (it shows as a star). Ask "what email rules do I have?" or "stop filing VGC emails". Your inbox is only read, never changed.

### New abilities

When you ask for something Alfred can't do yet ("Alfred, set a timer for ten minutes"), he doesn't just say no. He sends the request to Claude, the AI that builds him, as a GitHub issue labelled `alfred-wish`. Claude checks for new requests every few hours, builds each one as a pull request, and tells you in the project chat. Merge it, run `git pull` and restart, and Alfred can do it. You can also ask him to improve something ("Alfred, get better at…"). A copy of every request goes in `wishes.md` next to `server.py`.

To send requests automatically, make a fine-grained GitHub token at https://github.com/settings/personal-access-tokens/new with access to only this repository and **Issues: Read and write**, and put it in `.env` as `JARVIS_GITHUB_TOKEN`. Without a token, Alfred opens the request on GitHub in your browser and you click **Submit**.

### Deliveries and calls

Jarvis can speak up on his own when a delivery is on its way or your phone rings, for example "Sir, an email from Deliveroo: Your order is on its way" or "Sir, incoming call from Mum." The Jarvis page must be open to hear it. You can also ask "Is anything being delivered today?"

On the HUD, the **EMAILS** line in the SYSTEM panel shows how many unread emails are in your inbox, checked every minute.

Each alert also goes in the **Notifications** panel on the page, newest first. When there are more than fit, the panel scrolls down slowly by itself; put the mouse on it to stop it. Click **×** on a notification to remove it.

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

This works wherever your phone is, with no cable or Bluetooth. When a call comes in, a free app on your phone called MacroDroid sends it to [ntfy.sh](https://ntfy.sh), a free notification relay. Jarvis listens there and says "Sir, incoming call from Mum." Both the phone and the PC only need internet.

Jarvis makes up a private address for this the first time he starts, such as `https://ntfy.sh/jarvis-3f9a1c0b7d2e4a61...`. It appears in his messages on the page (and in the console) until your phone sends its first call. It is kept in the `.phone-topic` file, which git ignores. Keep the address private: anyone who knows it can read your call alerts or make Jarvis speak. To get a new one, delete `.phone-topic` and `.phone-linked` and restart Jarvis.

1. Start Jarvis and open the page. Copy the address from his message.
2. On your Android phone, install **MacroDroid** from the Play Store and add a macro:
   - **Trigger:** Phone > **Call Incoming**, any number.
   - **Action:** Connectivity > **HTTP Request**. Method `POST`. URL: the address from step 1. For the body, type `Incoming call from ` and then add the caller's name with the magic text button (it shows as `[call_name]`).
   - Save it, and allow the phone and contacts permissions MacroDroid asks for.
3. Call yourself from another phone. Jarvis says "Sir, incoming call from ..." and the setup message stops appearing.

You can make more macros the same way, for example a **Notification Received** trigger for Deliveroo, Just Eat or Uber Eats that sends the notification text.

iPhone can't do this: iOS doesn't let apps or Shortcuts react to incoming calls. On an iPhone, use Phone Link above.

Your caller's name passes through ntfy.sh on its way to Jarvis. If you'd rather not, [run your own ntfy server](https://docs.ntfy.sh/install/) and set `JARVIS_NTFY_SERVER`. Set `JARVIS_CALL_ALERTS=false` to turn this off.

### Double-clap to wake (optional)

```bash
pip install sounddevice numpy
python scripts/clap_trigger.py
```

Clap twice and it starts the server if it isn't running, then opens Jarvis in your browser. If it misses claps or fires on noise, adjust `THRESHOLD` in the script.

### TikTok studio and making money

Alfred runs TikTok accounts for you as their author and director. He starts with three, each in a different look:
**lowkey.lore** (moody black-and-white stories on a record-sleeve card), **mindglitch.fyi** (psychology
explainers on black, with a coloured keyword) and **karma.receipts** (realistic drama stories with a bold headline
box). Say "add a TikTok account", "rename lowkey.lore", or "give me Gen Z names for a horror account".

Every morning from `JARVIS_CREATOR_HOUR` he writes, pictures, voices and cuts each account's videos (3 a day, each
at least a minute long) and saves them in **Work/TikTok/<account>**. Say "show my TikTok studio" to watch them and
press **Approve** or **Skip**. Nothing is posted until you approve it.

- With a TikTok developer app (`TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` in `.env`), press **Connect**
  beside each account once. Approved videos then go to your TikTok inbox to post, or post straight away with
  `JARVIS_TIKTOK_MODE=direct`.
- Without one, approved videos stay in the folder with their caption, ready to upload by hand.
- Trends: before each account's first video of the day Alfred checks this week's TikTok trends for its niche
  (topics, hashtags, hooks, sounds) and writes with them, along with what did best on that account. Ask "what's
  trending for mindglitch.fyi?" to plan what to post next.
- Sequels: at 50k views Alfred makes part 2, then a new part every 100k more views, up to part 5, which ends on a
  shocking cliffhanger. He reads views from TikTok, or tell him: "that story has 80k views".

Ask "research ways I could make money" and he searches the web and saves a report in **Work/Money Research** as a
Markdown file and a web page, both with Download buttons. "Add faceless TikTok to my money ideas" and "log £12
from faceless TikTok" keep a board of what you're trying and what it earns.

## More abilities

Each page below lists what to say to Alfred:

- [Everyday lists, habits and money](docs/everyday.md)
- [Time and dates](docs/time-and-dates.md)
- [Calculators](docs/calculators.md)
- [Home and life](docs/home-and-life.md)
- [Games and fun](docs/fun.md)
- [Words](docs/words.md)
- [Live info](docs/live-info.md)
- [PC control](docs/pc-control.md)
- [Learning and goals](docs/learning-and-goals.md)

## Things to try

- "Jarvis, what's the weather like in Tokyo?"
- "What's on my list today?"
- "Look up the latest news on the James Webb telescope."
- "Open the BBC weather page."
- "What am I looking at?" (uses the screen)
- "Remember that the wifi password is on the router, in my Personal folder."

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
| `music.py` | Find and open songs, albums and artists on Apple Music |
| `nowplaying.py` | Reads the current song from Windows for the now-playing card |
| `computer.py` | Mouse and keyboard for Claude's computer toolset |
| `tts.py` | ElevenLabs text-to-speech |
| `config.py` | Settings from the environment |
| `frontend/` | Orb UI, speech in and out |
| `scripts/clap_trigger.py` | Double-clap launcher |
