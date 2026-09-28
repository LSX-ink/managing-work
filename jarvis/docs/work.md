# Work: projects, a kanban board, time and meetings

Things to say to Alfred. Everything is saved in your memory folder on this PC (files called `worktools-...`), and
meeting notes and timesheets go into your Work folder as ordinary files you can open. Nothing is sent anywhere.
Most answers also pop up a window on the Alfred screen.

Removing a card or a parked idea always asks you to confirm first. Your to-do list, timers and pomodoro, documents
and priorities are separate abilities; these work alongside them.

## Projects

- **Add a project**: "Add a work project called Website, due 5 October." Pops up: a table of your projects with
  status, due date, open cards and hours this week.
- **List projects**: "List my work projects." / "Show my archived projects." Pops up: the same table.
- **Update a project**: "Put the Website project on hold." / "Add a note to Website: waiting for the copy."
  Status can be planning, active, on hold or done.
- **Archive a project**: "Archive the Payroll project." It's hidden, not deleted. "Bring back Payroll" restores it.
- **Ideas parking lot**: "Park an idea for Website: dark mode." / "Show the ideas for Website."
  Pops up: a list of ideas; clicking one turns it into a card on that project's board.
- **Remove an idea**: "Remove the dark mode idea from Website." (asks first)
- **Deadlines**: "What's due in the next two weeks?" Pops up: a table of project deadlines and card due dates in the
  next 14 days, with a countdown for each (overdue ones show too).
- **Project summary**: "Give me a summary of the Website project." Pops up: card counts per column, hours this week
  and all time, then deadlines, notes and parked ideas.
- **Weekly work report**: "Show my weekly work report." / "...for last week." Pops up: hours, cards finished,
  meetings held and open action items, with a short list under each.

## The kanban board

- **Show the board**: "Show the Website board." Pops up: the board with To do, Doing and Done columns.
  In the window you can:
  - drag a card to another column (or focus it and press the left/right arrow keys); Alfred moves it and redraws,
  - type into the box at the bottom and press Add card,
  - click a card to see its notes and due date, with a Remove card button.
- **Add a card**: "Add a card 'Design logo' to the Website board, due 1 October."
- **Move a card**: "Move the logo card to Doing." Moving into the last column counts it as finished.
- **Remove a card**: "Remove the logo card." (asks first)
- **Card notes**: "Add a note to the logo card: use the black version." / "What are the notes on the logo card?"
  Pops up: the card's column, due date and notes.
- **Card due dates**: "The logo card is due on Friday." / "Clear the due date on the logo card."
- **Your own columns**: "Change the Website board's columns to Backlog, Doing, Review, Shipped." The last column is
  the done one; cards in a column that no longer exists move to the first.

## Time

- **Project timer**: "Start timing the Website project." / "Stop my work timer." / "What am I timing?"
  Pops up: a live count-up with a Stop button. Starting a new one stops the old one and logs it.
- **Log time by hand**: "Log two hours on Payroll for yesterday."
- **Totals**: "How many hours have I done this week?" Alfred says today's totals; pops up: a bar chart of this
  week's hours per project.
- **Timesheet**: "Show my timesheet." / "...for last week." Pops up: a table of hours per project per day, with totals.
- **Export the timesheet**: "Export my timesheet." Saves `Timesheet week of <date>.csv` into Work/Timesheets and pops
  it up as a table (it opens in Excel too).
- **Focus log**: "Log a 50 minute focus session on Website." / "Show my focus this week." Pops up: a bar chart of focus
  minutes per day, with the split by project.
- **Working hours**: "My working hours are nine till half five, Monday to Friday." (add "I'm contracted for 37.5
  hours" if that's different from the span).
- **Home time**: "How long until I finish work?" Pops up: a live countdown to your finish time.
- **Overtime**: "Am I doing overtime?" Pops up: a table of expected and actual hours for the last four weeks and the
  running balance. Without working hours set it assumes 37.5 hours a week.

## Meetings and stand-ups

- **Meeting notes**: "Take meeting notes: Sprint planning with Sam and Jo, agenda scope and dates, we agreed the
  scope, Sam to send the budget." Saved as a Markdown file in Work/Meetings. Pops up: the notes. Only first names are
  kept for attendees.
- **Add to a meeting**: "Add to the sprint planning notes: Jo to book the room."
- **Show a meeting / list meetings**: "Show the sprint planning notes." / "List my meetings." Pops up: the notes, or a
  list of meetings you can click.
- **Action items**: "Show my meeting action items." Pops up: a tick list. Ticking one tells Alfred it's done (and the
  Markdown file is updated); each has a To-do button that copies it to your to-do list.
- **Tick an action by voice**: "Sam sent the budget, tick that off." / "Untick the budget action."
- **Stand-up**: "Save my stand-up: yesterday the logo, today the copy, no blockers."
- **Read back the stand-up**: "What was my last stand-up?" Alfred reads it out; pops up: yesterday, today and
  blockers.
