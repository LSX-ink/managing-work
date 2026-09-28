# Writing

A writing studio for novels, short stories, blogs, song lyrics and poem collections, plus offline creative
helpers. Each project's chapters or pieces are Markdown files in `Writing/<project>` in your memory folder;
everything else (goals, deadlines, characters, world notes, the plot planner, daily word counts and the blog
planner) is kept in `writing.json` and `writing-log.json` alongside them. Nothing goes online. A project defaults
to the one you last worked on, so you can usually leave its name out.

## Projects and chapters

- **Start a project**: "Start a new novel called Ashes, 80,000 words by December." Kinds: novel, short story, blog,
  song lyrics, poem collection. Pops up the project dashboard.
- **Update it**: "Change Ashes' deadline to next March." (goal, deadline or kind)
- **List projects**: "What are my writing projects?" Pops up with each one's word count and how it's doing against
  its deadline.
- **Add a chapter or piece**: "Add a new chapter to Ashes called The Fire." Can include text you've already
  written.
- **Write into it**: "Add to The Fire: it was a cold night..." / "Replace The Fire with..." Adds to the end, or
  replaces it entirely.
- **Show a piece**: "Show me The Fire." Pops up the file with Alfred reading back the start of it.
- **Rename, reorder, delete**: "Rename The Fire to The Blaze." / "Move The Fire to chapter 3." / "Delete The Fire."
  (Alfred asks you to confirm deleting; a copy is kept in the hidden `.versions` folder.)
- **Outline**: "Show the outline of Ashes." A table of every chapter or piece with its word count and a running
  total.
- **Compile**: "Compile the manuscript of Ashes." Joins every piece in order into one Markdown file and a PDF in
  `Writing/<project>/Manuscript`, which pops up.
- **Dashboard**: "Show my writing dashboard for Ashes." Words vs goal, chapters, writing streak, days to the
  deadline (and words a day needed to make it), a chart of words per chapter and the last 14 days written.

## Story bible

- **Characters**: "Add a character to Ashes: Mira, a runaway blacksmith, sharp-tongued and loyal." (name, role,
  traits, appearance, notes — say it again to update) / "List the characters in Ashes." / "Show the character card
  for Mira." / "Delete the character Mira." (confirmed first)
- **World and setting**: "Add a place to Ashes' world: the Iron Quarter, a slum built on an old forge." (or "lore"
  for background) / "Show Ashes' world notes." / "Delete the world note the Iron Quarter."
- **Plot planner**: "Add a scene to Ashes: Mira steals the map, act 1, what happens: ..." / "Move that scene to
  act 2." / "Show the plot of Ashes." A table per act pops up. / "Delete the scene Mira steals the map."

## Daily words and sprints

- **Daily goal**: "Set my daily writing goal to 500 words."
- **Log words**: "I wrote 800 words today." Leave the number out and Alfred counts what's new in your stored
  chapters since the last time it counted.
- **Progress**: "How's my writing going today?" Today's total, streak and a chart of the last 14 days pop up.
- **Writing sprint**: "Start a 20 minute writing sprint." A countdown timer pops up; "Finish my sprint" logs the
  words written (from what you say, a before/after count, or counted from the chapters) and shows the pace.

## Blog planner

- **Add a post**: "Add a blog post called 10 Tips for Baking, drafting, publish 1st of October." (status: idea,
  drafting or published)
- **Update it**: "Mark 10 Tips for Baking as published." / add notes or a new date.
- **List and delete**: "Show my blog planner." Pops up grouped by status with the next one due. / "Remove 10 Tips
  for Baking from the planner." (confirmed first)

## Creative helpers (all offline)

- **Writing prompt**: "Give me a fantasy writing prompt." Pops up with a button to start a piece from it straight
  away.
- **Name generator**: "Give me some fantasy names." (or sci-fi, English or place names)
- **Poem forms**: "What poem forms do you know?" / "Tell me the rules of a haiku." Rules, rhyme scheme and syllable
  pattern for haiku, limerick, sonnet, villanelle, cinquain, tanka and more.
- **Syllable checker**: "Check the syllables of my haiku: ..." Counts syllables per line and checks it against a
  form's pattern (English rule of thumb, so it can be a syllable out).
- **Readability**: "Check the readability of The Fire in Ashes." (or paste text, or leave the piece out for the
  whole project) Reading ease score, sentences, average sentence length, most repeated words and -ly adverbs pop up.
- **Song lyrics**: "Start a new song called Neon Nights." (verse-chorus shape by default, or say another shape)
  Lays the song out as a piece with a section per part. "Write the chorus for Neon Nights: ..." fills in one
  section; "Show Neon Nights" pops up every section written so far.
