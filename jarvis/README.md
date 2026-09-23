# J.A.R.V.I.S. — personal voice assistant

A local voice assistant with a dry British butler's manners. You talk to it in the browser. It thinks with Claude, answers out loud, searches the web, checks the weather and your to-do list, opens pages for you, and can look at your screen.

Inspired by [Julian-Ivanov/jarvis-voice-assistant](https://github.com/Julian-Ivanov/jarvis-voice-assistant) and written from scratch here, with these changes:

| | Original | This version |
|---|---|---|
| Platform | Windows only (PowerShell, Win32) | Windows, macOS, Linux |
| Language | German | English (any language via `JARVIS_SPEECH_LANG`) |
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
| `JARVIS_USER_NAME` / `JARVIS_USER_ADDRESS` | (empty) / `sir` | How Jarvis addresses you |
| `JARVIS_CITY` | (empty) | Home city for the weather |
| `JARVIS_TASKS_FILE` | (empty) | A Markdown file with `- [ ] task` lines, such as an Obsidian note |
| `JARVIS_SPEECH_LANG` | `en-GB` | Speech recognition and browser voice language |
| `JARVIS_ENABLE_WEB` / `JARVIS_ENABLE_SCREEN` | `true` | Turn web search or screen viewing off |
| `JARVIS_HOST` / `JARVIS_PORT` | `127.0.0.1` / `8340` | Where the server listens |

On Opus 5 the server turns on the API's `fallbacks: "default"`. If a safety classifier declines a request, it is retried on a suitable model instead of failing.

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
