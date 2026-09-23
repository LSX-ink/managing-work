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
| `JARVIS_USER_NAME` / `JARVIS_USER_ADDRESS` | (empty) / `sir` | How Jarvis addresses you |
| `JARVIS_CITY` | (empty) | Home city for the weather |
| `JARVIS_TASKS_FILE` | (empty) | A Markdown file with `- [ ] task` lines, such as an Obsidian note |
| `JARVIS_SPEECH_LANG` | `en-GB` | Language code for speech recognition, the voice and the page text |
| `JARVIS_LANGUAGE` | `English` | The language Jarvis replies in |
| `JARVIS_ENABLE_WEB` / `JARVIS_ENABLE_SCREEN` | `true` | Turn web search or screen viewing off |
| `JARVIS_HOST` / `JARVIS_PORT` | `127.0.0.1` / `8340` | Where the server listens |

On Opus 5 the server turns on the API's `fallbacks: "default"`. If a safety classifier declines a request, it is retried on a suitable model instead of failing.

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
| `tools.py` | Weather, tasks, open URL, screenshot |
| `tts.py` | ElevenLabs text-to-speech |
| `config.py` | Settings from the environment |
| `frontend/` | Orb UI, speech in and out |
| `scripts/clap_trigger.py` | Double-clap launcher |
