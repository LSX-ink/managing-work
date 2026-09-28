# Alfred's voice

If Alfred sounds robotic, change his voice. The voices come from your browser and Windows, and the choice is
remembered in that browser.

- **Pick a voice**: "Change your voice." / "You sound like a robot." A window pops up with every voice for
  Alfred's language, the most natural ones first and marked NATURAL. Press **Try** to hear one and **Use** to
  pick it.
- **Speed**: "Speak a bit faster." / "Slow down." (or the Speed slider)
- **Pitch**: "Make your voice deeper." / "Speak a bit higher." (or the Pitch slider)
- **Back to normal**: "Reset your voice."

The most human-sounding free voices are Microsoft's "Online (Natural)" voices, such as Ryan or Thomas
(British men). They only show up when you open Alfred in **Microsoft Edge**. In Chrome, "Google UK English Male"
is the best choice.

With `ELEVENLABS_API_KEY` in the `.env` file, Alfred uses an ElevenLabs voice instead, which sounds the most
natural of all but is a paid service. Change `ELEVENLABS_VOICE_ID` there to pick a different ElevenLabs voice.
