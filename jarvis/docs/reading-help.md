# Reading help

Alfred helps you read and understand any public web page, some pasted text, or a text file in your memory folders.
It is an accessibility aid: big clear text, a voice that reads to you, and plain-English explanations. The reading
itself happens in your browser using the voice you chose in Alfred's voice picker, so Alfred's own spoken reply
stays one short sentence. Pages are fetched only if they are on the public internet (never your home network),
nothing is sent anywhere except the word in a dictionary lookup, and your saved places and reader look live in
`reading.json` in your memory folder.

Already in Alfred, and not repeated here: showing a page in a plain reader window, saving it as a note and link
previews ([web in Alfred](web-in-alfred.md)), the writing-studio readability check for your own pieces
([writing](writing.md)), and dictionary definitions in [words](words.md).

## The reader window (a big-text pop-up)

1. **Read a web page aloud**: "Read https://example.com/story aloud." A cream, big-text reader pops up with the
   article only (menus, adverts, cookie banners and scripts left out). Press **Read aloud**; it reads paragraph by
   paragraph and highlights the one being read, scrolling to keep it in view.
2. **Read some text aloud**: "Read this aloud: ..." (paste anything). The same reader pops up.
3. **Read a file aloud**: "Read my diary note in Ideas aloud." Works for `.txt` and `.md` files in your memory
   folders. PDFs can't be read aloud (they have no plain text Alfred can pull out).
4. **Start from a heading or paragraph**: "Read that page from the heading What happens next." or "...from
   paragraph 5."
5. **Pause, skip and speed**: in the reader, **Pause / Resume**, **Back**, **Skip**, **Stop**, and a speed menu
   (0.7x to 1.5x). Click any paragraph to start from it. Space, left and right arrows work too.
6. **Text size and line spacing**: **A-** and **A+**, **Gap-** and **Gap+** in the reader.
7. **Background tint**: five round buttons: cream, blue, yellow, white and dark.
8. **Reading ruler**: press **Ruler**; everything but the line under your pointer is dimmed so you keep your place.
9. **Remember my look**: "Make the reader text bigger, yellow, with the ruler on." Saves size (14 to 48), spacing,
   tint, ruler and speed as your defaults. Changes you make in the window are also remembered in this browser.

## Keeping your place

10. **Save my place**: press **Save my place** in the reader, or say "Remember I stopped at paragraph 12."
11. **Carry on where I stopped**: "Carry on reading." (or "Carry on reading Big Story.") The reader reopens at that
    paragraph.
12. **Where did I stop?**: "Where did I stop reading?" A list of saved places; tap one to carry on.
13. **Forget a place**: "Forget my place in Big Story." Alfred asks you to confirm first.

## Understanding it

14. **Simple version**: "Make https://example.com/story simple to read." (or paste text, or name a file) Alfred
    rewrites it in plain, easy English and pops the result up.
15. **Three-point summary**: "Summarise that page in three bullet points." A short list pops up.
16. **How easy is it to read?**: "How readable is https://example.com/story?" A table with reading ease, school
    grade, reading age, words, reading time, and the long sentences (over 25 words) flagged.
17. **Hard words**: "Which are the hard words on that page?" A list of tricky words; tap one for its meaning.
18. **What does this word mean?**: "What does extraordinary mean?" The definition pops up with a **Say it simply**
    button.

## The shape of a page

19. **Outline**: "Show me the headings on that page." A list to tap; tapping one reads the page from there.
20. **Links in plain words**: "List the links on that page." Each link with its site; vague ones like "click here"
    are flagged, and menu links come last.
21. **Describe the pictures**: "Describe the pictures on that page." A table of each picture's description, with
    pictures that have none marked **NO DESCRIPTION**.
22. **Page at a glance**: "Tell me about that page." Words, reading time, language, headings, pictures (and how
    many have no description) and links.
