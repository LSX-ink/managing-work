# Documents and spreadsheets

Alfred can write documents, letters, a CV, invoices and simple spreadsheets for you. They're ordinary files in a
`Documents` folder in your memory folders (it appears the first time you use it), unless you name another folder,
such as "in my Work folder". Each one pops up in a window on the Alfred screen when it's made or changed.

## Documents

Documents are Markdown files (`.md`): plain text with `#` headings, `-` lists and `**bold**`.

- **New document**: "Write a document called Trip plan with a day-by-day plan for three days in Edinburgh."
  Alfred writes it and the document pops up.
- **Add to a section**: "Add 'book the train' to the Day 1 section of my trip plan." With no section named, the text
  goes at the end; a new section is made if there isn't one with that heading.
- **Replace a section**: "Rewrite the Day 2 section of the trip plan: rest day, then fly home."
- **Show or read aloud**: "Show me the trip plan." / "Read me my trip plan." The document pops up and Alfred reads it.
- **Word count**: "How many words are in my essay?" A small table pops up with words, characters, paragraphs,
  reading time and time to read it aloud.
- **Find and replace**: "In my essay, replace 'colour' with 'color'." Alfred tells you how many he changed. If there
  are more than 20, he asks you first.
- **Table of contents**: "Add a table of contents to my guide." A Contents list made from the headings goes at the
  top (doing it again updates it).
- **Web page copy**: "Export my trip plan as HTML." A styled `.html` file is saved next to the document (open it in
  your web browser); the document pops up and Alfred tells you where the file is.
- **PDF**: "Make a PDF of my trip plan." The PDF (A4 pages) is saved next to the document and pops up.
- **Compare two documents**: "What's different between my CV draft and my CV?" The changes pop up, lines taken away
  marked `-` and lines added marked `+`.

## Undo and templates

- **Earlier versions**: "Show me the versions of my trip plan." Every change keeps the copy from before it (the last
  20), in a hidden `.versions` folder. A list pops up; click one to ask for it back.
- **Restore a version**: "Put my trip plan back to version 1." Alfred checks with you first. The text you're
  replacing is kept as a version too, so this can be undone as well.
- **Save as a template**: "Save my thank-you note as a template." Write blanks in double curly brackets, such as
  `{{name}}` or `{{gift}}`, to fill in each time. Templates are in `Documents/Templates`.
- **List templates**: "What templates have I got?" A list pops up; click one to use it.
- **New from a template**: "Make a thank-you note for Gran from the template; the gift was a scarf." Alfred fills
  the blanks and tells you about any he couldn't fill.

## Letters, CV and invoices

Each is saved as a document plus a PDF copy, and the PDF pops up.

- **Formal letter**: "Write a formal letter to the council asking to renew my parking permit." Alfred lays out your
  address, the date, their address, the subject, the letter and the sign-off. Saved in `Documents/Letters`.
- **CV: add or change a section**: "Put this in the skills section of my CV: Excel, driving licence, first aid." /
  "Add my job at VGC to my CV experience." Sections are contact, profile, experience, education, skills, interests
  and references. The sections are kept in `cv.json`, so one can be changed without redoing the rest.
- **CV: show it**: "Show me my CV." Alfred builds it fresh in `Documents/CV` and says which main sections are empty.
- **Invoice**: "Make an invoice to Bob's Cafe for two window cleans at 15 pounds each, plus VAT." Invoices are
  numbered in order (INV-0001, INV-0002...), with subtotal, VAT and total, and a due date 30 days on. Saved in
  `Documents/Invoices`; the numbers are kept in `invoices.json`.

## Spreadsheets

Spreadsheets are CSV files, which Excel opens too. Row 1 is the first row under the column names.

- **New spreadsheet**: "Make a spreadsheet called Spending with columns item, category and cost."
- **Add a row**: "Add to Spending: bread, food, 1.20."
- **Change a cell**: "In Spending, change row 3's cost to 2.50."
- **Delete a row**: "Delete row 2 of Spending." Alfred reads the row back and asks you first.
- **Show it**: "Show me my Spending spreadsheet." It pops up as a table.
- **Totals**: "What's the total cost in Spending?" A table pops up with the sum, average, lowest, highest and count.
- **Totals by group**: "Total up Spending by category." A bar chart and a table of each category's total pop up.
- **Sort or filter**: "Sort Spending by cost, highest first." / "Show only food in Spending." The result is saved as a
  new spreadsheet next to the old one (which is left as it was) and pops up.

Changes to spreadsheets are kept as versions too, so "Put Spending back to version 1" works for them as well.
Everything stays on this PC; nothing is sent anywhere.
