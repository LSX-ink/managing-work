# Track anything

Make your own trackers for anything you like (coffees, back pain, meditation, push-ups, "did I floss?") and log
them by voice. Most answers pop a window up on the Alfred screen: a chart, a grid of squares, a table or a
dashboard. Everything is saved on this PC in your memory folder (the `trackers-*.json` files), nowhere else.

Water, sleep, mood, weight, blood pressure, calories, spending, steps and habits already have their own logs (see
everyday.md, home-and-life.md and health-plus.md). Charts, comparisons, correlations and the dashboard can read
water, sleep, mood, steps, spending and habits too.

## Your trackers

1. **Create a tracker**: "Track coffees as a count, at most 3 a day." / "Track back pain as a 1 to 5 rating." /
   "Track meditation time with a goal of 10 minutes." / "Track my weight in kg, keep the latest each day."
   Types: number (with a unit), yes or no, 1 to 5 rating, count, time (duration) and text note. A goal is
   optional; "at most" goals suit things you want to cut down.
2. **List them**: "What am I tracking?"
   Pops up a table: each tracker, its type, daily goal, today's value and goal streak.
3. **Delete one**: "Delete my coffee tracker." Alfred says how many days it holds and asks you to confirm first.
4. **Log by voice**: "Log 3 coffees." / "I meditated 10 minutes." / "Rate my back pain 2." / "I flossed." /
   "Journal: good walk by the river." / "Log 5 km run yesterday."
   Names don't need to be exact ("coffee", "my coffees" and "coffees" all find Coffee). Counts, times and numbers
   add up through the day; ratings and yes/no replace. The reply says if you met the goal.
5. **Milestones**: when a running total passes a round number (100 km, 250 push-ups, 10 hours of meditation), the
   log reply tells you.

## Counters

6. **Tap counters**: "Make a push-ups counter." / "Show my counters." / "Add one to cigarettes."
   Pops up your counters with today's count. Tap one to add 1; the window updates. Counts start again at zero each
   day, and the old days stay in the tracker for charts.

## Charts and reviews

7. **Chart with stats**: "Show my coffee chart." / "Show meditation for the last 90 days."
   Pops up a chart of the last 7, 30 or 90 days with a dashed goal line, and a stats table: total, average, lowest,
   highest, days logged, days the goal was met and the goal streak. Buttons switch between 7, 30 and 90 days.
8. **Year in pixels**: "Show my back pain year in pixels."
   Pops up a year of little squares, one per day, brighter for higher values (or yes). Click a square to see that
   day's value and note.
9. **Compare periods**: "Compare my coffees this week with last week." / "Running this month versus last month."
   Pops up a table of last and this period: total, average a day, days logged, goal met, and the change.
10. **Do two things go together?**: "Is my sleep linked to my back pain?" / "Correlate coffee and sleep."
    Pops up the days where both were logged and says whether they tend to move together (a correlation from -1 to
    +1), with a reminder that this doesn't mean one causes the other. It needs at least 5 days with both.
11. **Monthly review**: "Show my trackers' monthly review." / "Review August 2026."
    Pops up one table with every tracker's month: days logged, total, average, goal met and top day.

## Dashboard

12. **Choose the dashboard**: "Put coffee, meditation, water, habits and spending on my dashboard."
    Up to 6 items: your trackers plus water, sleep, mood, steps, spending and habits.
13. **Show the dashboard**: "Show my dashboard."
    Pops up a tile for each: today's value, a mini chart of the last 14 days with the goal line, and extras like
    spending this month or your best habit streak. Tap a tile for its full chart.

## Challenges and life in weeks

14. **Start a streak challenge**: "Start a no sugar challenge for 30 days." / "Start a no alcohol challenge from
    2026-10-01."
15. **Daily check**: "I kept my no sugar challenge today." / "I slipped on no sugar yesterday."
    Alfred says your streak and how many days are left.
16. **Challenge calendar**: "Show my no sugar challenge." (or "Show my challenges" for all of them)
    Pops up a calendar: bright days kept, dark days missed, empty days still to come. **Kept it today** is a button.
17. **Stop a challenge**: "Stop the no sugar challenge." Alfred asks you to confirm first.
18. **Life in weeks**: "Show my life in weeks. I was born on 1990-09-14."
    Pops up a grid where each row is a year and each square a week, to age 90: filled squares are weeks lived.
    Your birth date is saved on this PC so next time just say "Show my life in weeks."

## Reminders and files

19. **Reminder to log**: "Remind me to log my back pain at 9 pm every day."
    Adds a daily reminder (it shows in your normal reminders list and can be cancelled there).
20. **Export to CSV**: "Export my coffee tracker."
    Saves `Personal/Trackers/Coffee.csv` (date, value, note) and pops it up as a table. Say another folder to save
    it there.
21. **Import a CSV**: "Import old-steps.csv from Personal into my walking tracker."
    Reads date,value rows (a header row is fine). Days you've already logged are kept unless you confirm you want
    them overwritten.
