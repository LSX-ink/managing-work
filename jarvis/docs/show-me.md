# Show me: your stuff on the screen

Ask Alfred to "show me" something you already keep with him and it pops up as a window on the Alfred screen.
Alfred says one short line and the rest is in the window. Nothing new is saved: the windows read the lists and
logs you already have.

In most windows you can click things. A tick box, a small button next to an item (**Cancel**, **Done**,
**Finished**, **Watched**) or a button along the bottom sends Alfred a line as if you'd said it, for example
"Tick off milk from the shopping list." You can drag a window by its title bar, resize it from the corner, and
close it with × or Esc. If you ask for the same window again, the one already open is updated.

| Say | What pops up |
| --- | --- |
| "Show me my shopping list." | Your shopping list with tick boxes. Ticking an item takes it off the list. Buttons: **Add item**, **Clear**. |
| "Put my to-do list on the screen." | Your open jobs with tick boxes. Ticking a job marks it done. Button: **Add job**. |
| "Show my reminders." | Each reminder with when it's due and whether it repeats, plus a **Cancel** button on each one. |
| "Show my timers." | A live countdown for each running timer, with **Cancel**. |
| "Show me my calendar." | A table of today's and this week's events (day, time, event, place). Buttons: **Today**, **Next week**. |
| "Show me the weather this week." (or "...in Leeds") | A line chart of each day's high, and a table with the sky, high, low and chance of rain. |
| "Show my habits." | A streaks table, a 14-day grid with ✓ for each day you did a habit, and a **Done** button for habits you haven't done yet today. |
| "Show my payslips." | A line chart of your take-home pay each month, and a table with employer, take-home, gross and tax. |
| "Show my spending." | A bar chart of this month's spending by category, and a bar chart of your total for each of the last 6 months. Buttons: **Log spending**, **Undo last**. |
| "Show my sleep, water and mood." | Charts for the last 14 days: hours slept, glasses of water and mood from 1 to 5. |
| "Show my steps and workouts." | Bar charts of your steps and workout minutes over the last 14 days, and a table of recent workouts. |
| "Show my goals." | A progress bar for each open goal, with how far along you are and the time left, plus a **Log** button on each. |
| "Show my bills." | A table of your bills (with when each is next due) and your subscriptions, with the monthly total at the top. |
| "Show this week's meal plan." | A table of breakfast, lunch and dinner for each day this week. |
| "Show me the pancake recipe." | A recipe card with the ingredients and method. Button: **Add ingredients to shopping list**. |
| "Show my birthdays and countdowns." | Upcoming birthdays (with the age they're turning) and countdowns, each with the days left. |
| "Show my reading list." | What you're reading now (with a **Finished** button), what's waiting (with **Start**) and what you finished lately. |
| "Show my watch list." | Films and series still to watch, each with a **Watched** button. Button: **Pick for tonight**. |
| "Show me a flashcard." (or "...from my Spanish deck") | The next card that's due. Press **Reveal** to see the answer, then **I got it right** or **I got it wrong**. **Next card** shows another. |

Only the weather window goes online. It sends the name of the city to Open-Meteo, which is free and needs no
sign-up. If you don't name a city, it uses your home city (`JARVIS_CITY`). The calendar window reads the
calendar address you set up in `JARVIS_CALENDAR_URL`. Everything else stays on this PC.
