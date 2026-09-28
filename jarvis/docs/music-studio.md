# Music studio

Playable music tools and music theory, plus a practice diary. Nothing goes online: every sound is synthesised in
the page with WebAudio, and the theory (chords, scales, keys, progressions, transposing, guitar shapes and note
frequencies) is worked out on your PC. Your practice log, song list and saved drum patterns are kept in
`studio-practice.json`, `studio-songs.json` and `studio-drums.json` in your memory folder.

## Play

- **Piano**: "Open the piano." A two-octave keyboard pops up; play with the mouse, or click it and type — the Z row
  and Q row are the two octaves, arrow keys shift up and down.
- **Drum machine**: "Open the drum machine." / "Load my drum pattern Rock groove." A 16-step beat maker pops up
  with kick, snare, hi-hat and clap, three ready-made presets (Rock, Four on the floor, Hip hop) and any patterns
  you've saved. Say a name to load a saved pattern, and a tempo if you like.
- **Tuner**: "Tune my guitar." (or bass, ukulele, violin, viola, cello) Reference tones for each string pop up to
  click and hold while you tune by ear.
- **Tap tempo**: "Help me find the tempo of this song." Tap the button (or press space) in time and it works out
  the BPM.
- **Circle of fifths**: "Show me the circle of fifths." / "Open the circle of fifths at G." Click a key to see its
  chords: major on the outside, the relative minor inside.
- **Ear training**: "Give me an interval quiz." (easy, medium or hard) Listen to two notes and pick the interval.
- **Note quiz**: "Quiz me on the treble clef." (or bass) Name the note shown on the staff.

## Theory

- **Chord notes**: "What notes are in C sharp minor seven?" Pops up the notes, their intervals from the root, and
  a plain-English name; chords are spelled properly (F major has Bb, not A#).
- **Guitar chords**: "Show me how to play a G chord." (or several at once, e.g. "G, C and D") Fretboard diagram(s)
  pop up with a strum.
- **Scales**: "Show me the D dorian scale." (major, minors, pentatonics, blues, modes) Notes and the whole/half
  step pattern pop up.
- **Chord progressions**: "Play I V vi IV in G." / "Play the twelve-bar blues." Roman numerals in any key, or one
  of ten famous progressions by name; "List famous chord progressions" shows all ten.
- **Transpose**: "Transpose G D Em C up 2 semitones." / "Transpose these chords into the key of D." Moves a song's
  chords by semitones or into a new key (taking the first chord as the old key).
- **Note info**: "What's the frequency of A4?" / "What note is 445 Hz?" / "What note is MIDI 60?" Frequency in Hz
  and MIDI number, either way, with how many cents off a given frequency is (A4 = 440 Hz).

## Practice diary

- **Log practice**: "I practised guitar for 20 minutes, working on scales." Logged against today unless you say
  another day; keeps a practice streak.
- **This week**: "Show my practice this week." A bar chart of minutes per day, the split by instrument, and the
  current streak pop up.

## Songs to learn

- **Add a song**: "Add Wonderwall by Oasis to my songs to learn."
- **Update it**: "Mark Wonderwall as can play." (to learn, learning, can play, mastered) / add notes like "capo 2".
- **List and remove**: "Show my songs to learn." A table pops up, sorted by status. / "Remove Wonderwall from my
  songs." (confirmed first)

## Saved drum patterns

- **Save a pattern**: press **Save pattern** on the drum machine (it sends the pattern and a name you type), or
  say "Save this drum pattern as Rock groove at 110 BPM: kick x...x...x...x... snare ....x.......x... hat
  x.x.x.x.x.x.x.x. clap ................" (16 steps a track, x or o = a hit).
- **List and load**: "Show my saved drum patterns." / "Load my drum pattern Rock groove in the drum machine."
- **Delete**: "Delete the drum pattern Rock groove." (confirmed first)
