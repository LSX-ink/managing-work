# Knowledge base: linked notes, tags and mind maps

Alfred can keep a personal wiki for you: notes that link to each other, #tags, a daily note, a map of how your notes
connect, and mind maps. Everything is ordinary Markdown in a `Notes` folder in your memory folders (it appears the
first time you use it), so you can also open and edit the notes in any text editor, or in an app like Obsidian.

- A note's **title** is its file name: the note "Gardening" is `Notes/Gardening.md`.
- **Link** to another note by writing its title in double square brackets: `[[Tomatoes]]`. `[[Tomatoes|my toms]]`
  shows "my toms" but still links to Tomatoes.
- **Tag** a note by writing a word with `#` in front, anywhere in it: `#garden`.
- Daily notes are in `Notes/Daily`, templates in `Notes/Templates`, and merged notes keep a copy in
  `Notes/.merged`. Mind maps are kept in `knowledge-mindmaps.json` in the memory folder.

## Notes

- **New note**: "Make a note called Gardening: grow tomatoes and basil, link it to Tomatoes, tag it garden."
  The note pops up. Headings, lists, **bold** and links are drawn properly; click a `[[link]]` and Alfred opens that
  note (a link to a note that doesn't exist yet is dashed, and clicking it asks Alfred to create it). Click a #tag to
  see every note with that tag.
- **Open a note**: "Open my note Tomatoes." The note pops up; at the bottom are the notes that link to it (its
  backlinks), which you can click too. The window has buttons to open the file on your PC or see its note graph.
- **Add to a note**: "Add 'get quotes' to the Next steps section of my Kitchen note." With no section, it goes at
  the end.
- **Daily note**: "Open today's note." / "Add 'fixed the fence' to my daily note." Today's note is made from a
  template the first time: the date as a heading, then Plan, Notes, Grateful for and Done today, with a link to the
  previous daily note.
- **Templates**: "What note templates are there?" A list pops up (meeting, book, recipe, person, project); click
  one to start a note from it. You can edit the templates in `Notes/Templates`, where `{title}` and `{date}` are
  filled in for you, or add your own `.md` files there.
- **New note from a template**: "Make a new meeting note called Budget review." / "Start a recipe idea note for
  Thai green curry."
- **Reading highlights**: "Save this highlight from Atomic Habits by James Clear, page 27: you do not rise to the
  level of your goals." The quote goes under Highlights in the book's own notes page (made from the book template
  if it's new), with the author, page and date. The page pops up.
- **Rename a note**: "Rename my note Tomatoes to Cherry tomatoes." Every `[[link]]` to it in other notes is updated
  too. If that changes more than 10 notes, Alfred checks with you first.
- **Merge two notes**: "Merge my Toms note into Gardening." Alfred always checks with you first. The text of the
  first note is added to the end of the second under "From ...", links to it point at the second note, and the old
  file is kept in `Notes/.merged`.

## Exploring your notes

- **Backlinks**: "Which notes link to Gardening?" A list pops up; click one to open it.
- **Tags**: "List my note tags." A list of tags with how many notes use each pops up; click one to see its notes.
- **Notes with a tag**: "Show my notes tagged garden."
- **Note graph**: "Show my note graph." / "Show the notes around Gardening." A map pops up: each note is a dot
  (bigger when it has more links) and each line is a link. Click a dot to open that note. It shows up to 150 notes,
  the most linked first; "around" shows the note plus the notes up to two links away.
- **Orphan notes**: "Which of my notes are orphans?" Notes with no links in or out pop up, to open and link up.
- **Broken links**: "Show broken links in my notes." Links to notes that don't exist yet pop up with the notes they
  are in; click one to create that note.
- **Table of all notes**: "Show a table of all my notes." Title, tags, how many links it has, how many notes link to
  it, and when it was last changed.
- **Resurface an old note**: "Show me an old note." Alfred picks the note you haven't looked at (or changed) for
  longest, as long as that's 30 days or more, and it pops up.
- **What do I know about...**: "What do I know about composting?" Alfred searches your notes (titles count most,
  then tags, then the text), tells you what the best matches say, and the list pops up to click.

## Mind maps

- **New mind map**: "Make a mind map about Holiday with branches Places (Rome, Oslo) and Budget." A round mind map
  pops up with Holiday in the middle, branches around it and sub-branches further out.
- **Show one**: "Show my Holiday mind map." With no name, it's the last one you changed.
- **List them**: "List my mind maps." Click one to show it.
- **Add a branch**: "Add Paris under Places in my mind map."
- **Remove a branch**: "Remove Oslo from the mind map." If it has branches under it, Alfred checks with you first.
- **Rename a branch**: "Rename Budget to Money in the Holiday mind map." Renaming the middle renames the map.
- **Mind map to outline**: "Turn my Holiday mind map into an outline note." It's saved as the note
  "Holiday mind map": a heading and an indented bullet list, which pops up.
- **Outline to mind map**: "Make a mind map from my Party note." The note's headings and bullet lists become the
  branches (indent a bullet two spaces to make it a sub-branch).
