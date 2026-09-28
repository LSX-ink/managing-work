"""Show me: the user's own lists, logs and trackers popped up on the Alfred screen as interactive windows.

Nothing new is stored here: every window reads what the other abilities already keep (shopping list, to-do list,
reminders, timers, calendar, habits, money, wellbeing, fitness, goals, bills, meals, recipes, dates, reading,
flashcards). Buttons and list items carry "say" lines, so clicking one asks Alfred to do it.

Windows that need more than one chart, table or list use the "showme" pop-up kind (frontend/popup-showme.js):
its card's data is {"sections": [...]}, each section one of
  {"type": "list", "title", "items": [{label, note?, done?, say?, action?}], "checks"?}
  {"type": "table", "title", "columns", "rows"}     {"type": "chart", "title", "chart"}
  {"type": "bars", "title", "items": [{label, pct, note}]}     {"type": "timer", "label", "ends_at", "say"}
  {"type": "flashcard", "front", "back"}            {"type": "text", "text"}
"""

import asyncio
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

import httpx

import agenda
import dates_saved
import growth_goals
import growth_media
import growth_store
import growth_study
import habits
import homehouse
import homekitchen
import homestore
import homewellbeing
import money
import reminders
import screen
import shopping
import timers
import todo
from config import Settings

KIND = "showme"
screen.EXTRA_KINDS.add(KIND)
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TICK = "✓"
ACTIONS = ["shopping", "todo", "reminders", "timers", "calendar", "weather", "habits", "payslips", "spending",
           "wellbeing", "fitness", "goals", "bills", "meals", "recipe", "dates", "reading", "watching", "flashcards"]


def _board(text: str, action: str, title: str, sections: list[dict], buttons=None) -> screen.Shown:
    return screen.Shown(text, screen.card(KIND, title, f"showme-{action}", buttons=buttons,
                                          data={"sections": [s for s in sections if s]}))


def _chart(title: str, kind: str, pairs: list[tuple[str, float]], unit: str = "") -> dict:
    return {"type": "chart", "title": title,
            "chart": {"type": kind, "labels": [p[0] for p in pairs][-60:], "values": [round(float(p[1]), 2) for p in pairs][-60:],
                      "unit": unit}}


def _money(n: float, settings: Settings) -> str:
    return money._money(n, settings.currency)


def _short(day: date) -> str:
    return f"{day:%a} {day.day}"


# ---- lists ---------------------------------------------------------------------------------

def show_shopping(settings: Settings) -> screen.Shown:
    found = shopping.items(settings)
    c = screen.card("list", "Shopping list", "showme-shopping", checks=True,
                    items=[{"label": i, "say": f"Tick off {i} from the shopping list."} for i in found],
                    buttons=[{"label": "Add item", "say": "Add something to my shopping list."},
                             {"label": "Clear", "say": "Clear the shopping list."}])
    return screen.Shown(f"Your shopping list is on the screen: {len(found)} items." if found
                        else "The shopping list is empty; it's on the screen.", c)


def show_todo(settings: Settings) -> screen.Shown:
    found = todo.open_items(settings)
    c = screen.card("list", "To-do list", "showme-todo", checks=True,
                    items=[{"label": j, "say": f"Tick off {j} on my to-do list."} for j in found],
                    buttons=[{"label": "Add job", "say": "Add a job to my to-do list."}])
    return screen.Shown(f"Your to-do list is on the screen: {len(found)} open jobs." if found
                        else "No open jobs; the list is on the screen.", c)


def show_reminders(settings: Settings, now: datetime | None = None) -> screen.Shown:
    now = now or datetime.now()
    items = []
    for r in reminders.load(settings):
        repeat = r.get("repeat", "once")
        items.append({"label": r["text"], "note": reminders.spoken_time(reminders.parse_when(r["at"]), now)
                      + ("" if repeat == "once" else f", repeats {repeat}"),
                      "say": f"Cancel the reminder about {r['text']}.", "action": "Cancel"})
    return _board(f"{len(items)} reminders on the screen." if items else "No reminders are set.", "reminders",
                  "Reminders", [{"type": "list", "items": items}],
                  [{"label": "New reminder", "say": "Set a reminder for me."}])


def show_timers(settings: Settings) -> screen.Shown:
    now_ms, now = time.time() * 1000, time.monotonic()
    running = sorted(timers.timers.values(), key=lambda t: t.ends)
    new = {"label": "New timer", "say": "Set a timer for me."}
    if len(running) == 1:
        t = running[0]
        name = "Timer" if t.label == "timer" else f"{t.label.capitalize()} timer"
        c = screen.card("timer", name, "showme-timers", ends_at=now_ms + (t.ends - now) * 1000,
                        buttons=[{"label": "Cancel", "say": f"Cancel the {t.label} timer."}, new])
        return screen.Shown(f"The {t.label} timer is on the screen, {timers.spoken(t.ends - now)} left.", c)
    sections = [{"type": "timer", "label": t.label, "ends_at": int(now_ms + (t.ends - now) * 1000),
                 "say": f"Cancel the {t.label} timer."} for t in running]
    text = f"{len(running)} timers on the screen." if running else "No timers are running."
    return _board(text, "timers", "Timers", sections or [{"type": "text", "text": "No timers running."}], [new])


# ---- calendar and weather --------------------------------------------------------------------

async def show_calendar(http: httpx.AsyncClient, settings: Settings, now: datetime | None = None) -> screen.Shown:
    if not agenda.configured(settings):
        return screen.Shown(await agenda.upcoming(http, settings), screen.card(
            "text", "Calendar", "showme-calendar", text="No calendar is connected yet (JARVIS_CALENDAR_URL)."))
    now = now or datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        events = agenda.events_between(await agenda._calendar(http, settings), start, start + timedelta(days=7))
    except httpx.HTTPError:
        raise ValueError("I couldn't reach the calendar just now.") from None
    today = [e for e in events if e["start"].date() == now.date()]
    rows = [["Today" if e["start"].date() == now.date() else _short(e["start"].date()),
             "all day" if e["all_day"] else e["start"].strftime("%H:%M"), e["title"], e["where"]] for e in events]
    c = screen.card("table", "This week", "showme-calendar", columns=["Day", "Time", "Event", "Where"], rows=rows,
                    text=f"Today: {len(today)} event{'s' if len(today) != 1 else ''}. This week: {len(events)}.",
                    buttons=[{"label": "Today", "say": "What's on today?"},
                             {"label": "Next week", "say": "What's in my calendar in the next fortnight?"}])
    return screen.Shown(f"Your week is on the screen: {len(today)} today, {len(events)} this week.", c)


async def show_weather(http: httpx.AsyncClient, settings: Settings, city: str) -> screen.Shown:
    import tools  # weather words live there; imported late because tools imports this module
    city = homestore.clean(city, 80) or settings.city
    if not city:
        raise ValueError("Which city? No home city is set (JARVIS_CITY).")
    try:
        geo = await http.get(GEO_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
        geo.raise_for_status()
        places = geo.json().get("results") or []
        if not places:
            raise ValueError(f"I couldn't find a place called {city}.")
        place = places[0]
        r = await http.get(FORECAST_URL, timeout=10, params={
            "latitude": place["latitude"], "longitude": place["longitude"], "forecast_days": 7, "timezone": "auto",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"})
        r.raise_for_status()
        daily = r.json()["daily"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise ValueError(str(e) if isinstance(e, ValueError) else "The weather service didn't answer.") from None
    days = [date.fromisoformat(d) for d in daily["time"]]
    labels = ["Today" if i == 0 else f"{d:%a}" for i, d in enumerate(days)]
    highs, lows = daily["temperature_2m_max"], daily["temperature_2m_min"]
    rain = daily.get("precipitation_probability_max") or [None] * len(days)
    rows = [[labels[i], tools.WEATHER_CODES.get(daily["weather_code"][i], "unknown"), f"{highs[i]:g}°C",
             f"{lows[i]:g}°C", "" if rain[i] is None else f"{rain[i]}%"] for i in range(len(days))]
    name = place["name"]
    return _board(f"This week's weather for {name} is on the screen; today's high is {highs[0]:g} degrees.",
                  "weather", f"Weather: {name}",
                  [_chart("Highs", "line", list(zip(labels, highs)), "°"),
                   {"type": "table", "columns": ["Day", "Sky", "High", "Low", "Rain"], "rows": rows}],
                  [{"label": "Weekend", "say": f"What's the weather like this weekend in {name}?"}])


# ---- trackers --------------------------------------------------------------------------------

def show_habits(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    found = habits.load(settings)
    if not found:
        return _board("No habits tracked yet.", "habits", "Habits", [{"type": "text", "text": "No habits yet."}],
                      [{"label": "Start one", "say": "I want to track a new habit."}])
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    week = {(today - timedelta(days=i)).isoformat() for i in range(7)}
    streaks = [[name, str(habits.streak(d, today)), f"{len(week & set(d))}/7",
                TICK if today.isoformat() in d else ""] for name, d in found.items()]
    grid = [[name] + [TICK if day.isoformat() in d else "·" for day in days] for name, d in found.items()]
    todo_items = [{"label": name, "say": f"I did {name} today.", "action": "Done"}
                  for name, d in found.items() if today.isoformat() not in d]
    return _board(f"{len(found)} habits on the screen.", "habits", "Habits", [
        {"type": "table", "title": "Streaks", "columns": ["Habit", "Streak", "Week", "Today"], "rows": streaks},
        {"type": "table", "title": "Last 14 days", "columns": [""] + [f"{d:%a}"[0] for d in days], "rows": grid},
        {"type": "list", "title": "Not done yet today", "items": todo_items} if todo_items else None])


def show_payslips(settings: Settings) -> screen.Shown:
    slips = money.load(settings)["payslips"]
    if not slips:
        return _board("No payslips logged yet.", "payslips", "Payslips", [{"type": "text", "text": "No payslips yet."}],
                      [{"label": "Log payslip", "say": "I want to log a payslip."}])
    by_month = defaultdict(float)
    for p in slips:
        by_month[p["month"]] += p["net"]
    months = sorted(by_month)[-24:]
    pairs = [(datetime.strptime(m, "%Y-%m").strftime("%b %y"), by_month[m]) for m in months]
    rows = [[p["month"], p.get("employer", ""), _money(p["net"], settings),
             _money(p["gross"], settings) if "gross" in p else "", _money(p["tax"], settings) if "tax" in p else ""]
            for p in reversed(slips[-24:])]
    avg = sum(by_month[m] for m in months) / len(months)
    return _board(f"Your take-home pay is on the screen; it averages {_money(avg, settings)} a month.", "payslips",
                  "Payslips", [_chart(f"Take-home ({settings.currency})", "line", pairs),
                               {"type": "table", "columns": ["Month", "Employer", "Take-home", "Gross", "Tax"],
                                "rows": rows}],
                  [{"label": "Log payslip", "say": "I want to log a payslip."}])


def _months_back(today: date, n: int) -> list[str]:
    year, month, out = today.year, today.month, []
    for _ in range(n):
        out.append(f"{year}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return out[::-1]


def show_spending(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    spends = money.load(settings)["spending"]
    month = today.strftime("%Y-%m")
    by_cat = defaultdict(float)
    for s in spends:
        if s.get("date", "").startswith(month):
            by_cat[s.get("category") or "other"] += s["amount"]
    totals = [(datetime.strptime(m, "%Y-%m").strftime("%b"),
               sum(s["amount"] for s in spends if s.get("date", "").startswith(m))) for m in _months_back(today, 6)]
    cats = sorted(by_cat.items(), key=lambda kv: -kv[1])
    total = sum(by_cat.values())
    return _board(f"You've spent {_money(total, settings)} so far this month; it's on the screen.", "spending",
                  "Spending", [
                      _chart(f"This month by category ({settings.currency})", "bar", cats) if cats
                      else {"type": "text", "text": "Nothing logged this month yet."},
                      _chart(f"Last 6 months ({settings.currency})", "bar", totals)],
                  [{"label": "Log spending", "say": "I want to log some spending."},
                   {"label": "Undo last", "say": "Remove the last spending entry."}])


def _days(today: date, n: int) -> list[date]:
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _empty(what: str) -> dict:
    return {"type": "text", "text": f"No {what} logged in the last 14 days."}


def show_wellbeing(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    data = homewellbeing.load(settings)
    days = _days(today, 14)
    sleep = [(_short(d), data["sleep"][d.isoformat()]) for d in days if d.isoformat() in data["sleep"]]
    water = [(_short(d), data["water"].get(d.isoformat(), 0)) for d in days]
    moods = defaultdict(list)
    for m in data["mood"]:
        moods[m.get("date", "")].append(m.get("mood", 0))
    mood = [(_short(d), sum(moods[d.isoformat()]) / len(moods[d.isoformat()])) for d in days if moods.get(d.isoformat())]
    avg = f" You've averaged {sum(v for _, v in sleep) / len(sleep):.1f} hours of sleep." if sleep else ""
    return _board(f"Your last two weeks of sleep, water and mood are on the screen.{avg}", "wellbeing", "Wellbeing", [
        _chart("Sleep (hours)", "line", sleep, "h") if sleep else _empty("sleep"),
        _chart(f"Water (glasses, goal {data['goal']})", "bar", water),
        _chart("Mood (1 to 5)", "line", mood) if mood else _empty("moods")],
        [{"label": "Log sleep", "say": "I want to log my sleep."},
         {"label": "Glass of water", "say": "I've had a glass of water."},
         {"label": "Log mood", "say": "I want to log my mood."}])


def show_fitness(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    steps = growth_goals._steps(settings)
    days = _days(today, 14)
    step_pairs = [(_short(d), steps["days"].get(d.isoformat(), {}).get("steps", 0)) for d in days]
    workouts = growth_store.load(settings, "workouts", [])
    minutes = defaultdict(float)
    for w in workouts:
        minutes[w.get("date", "")] += w.get("minutes", 0)
    recent = [w for w in workouts if w.get("date", "") >= days[0].isoformat()]
    rows = [[_short(date.fromisoformat(w["date"])), w["exercise"], growth_goals._workout_text(w)]
            for w in reversed(recent[-30:])]
    return _board(growth_goals.steps_week(settings, today) + " It's on the screen.", "fitness", "Steps and workouts", [
        _chart("Steps", "bar", step_pairs),
        _chart("Workout minutes", "bar", [(_short(d), minutes.get(d.isoformat(), 0)) for d in days]),
        {"type": "table", "title": "Workouts, last 14 days", "columns": ["Day", "Exercise", "What"], "rows": rows}
        if rows else {"type": "text", "text": "No workouts in the last 14 days."}],
        [{"label": "Log steps", "say": "I want to log my steps."},
         {"label": "Log workout", "say": "I want to log a workout."}])


def show_goals(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    open_goals = [g for g in growth_store.load(settings, "goals", []) if not g.get("achieved")]
    bars = [{"label": g["name"], "pct": min(100, round(100 * g["progress"] / g["target"])) if g.get("target") else None,
             "note": growth_goals.progress_text(g) + growth_goals._deadline_text(g, today)} for g in open_goals]
    items = [{"label": g["name"], "say": f"Add progress to my goal {g['name']}.", "action": "Log"} for g in open_goals]
    return _board(f"{len(open_goals)} goals on the screen." if open_goals else "No open goals yet.", "goals", "Goals", [
        {"type": "bars", "items": bars} if bars else {"type": "text", "text": "No open goals."},
        {"type": "list", "title": "Log progress", "items": items} if items else None],
        [{"label": "New goal", "say": "I want to set a new goal."}])


def show_bills(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    bills = homehouse._rows(settings, homehouse.BILLS)
    subs = homehouse._rows(settings, homehouse.SUBS)
    rows = []
    for name, b in bills.items():
        when = homehouse._bill_date(int(b["day"]), today.year, today.month)
        if when < today:
            y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            when = homehouse._bill_date(int(b["day"]), y, m)
        rows.append((when, [name, "bill", _money(b["amount"], settings), f"{_short(when)} {when:%b}",
                            str((when - today).days)]))
    rows.sort(key=lambda r: r[0])
    sub_rows = [[name, "subscription", _money(s["price"], settings) + (" a year" if s["period"] == "yearly" else ""),
                 "", ""] for name, s in subs.items()]
    monthly = sum(b["amount"] for b in bills.values()) + sum(
        s["price"] / 12 if s["period"] == "yearly" else s["price"] for s in subs.values())
    c = screen.card("table", "Bills and subscriptions", "showme-bills", text=f"Monthly total: {_money(monthly, settings)}",
                    columns=["Name", "Type", "Amount", "Next due", "Days"], rows=[r for _, r in rows] + sub_rows,
                    buttons=[{"label": "Add bill", "say": "I want to add a bill."},
                             {"label": "Add subscription", "say": "I want to add a subscription."}])
    return screen.Shown(f"Your bills and subscriptions come to {_money(monthly, settings)} a month; they're on the screen."
                        if rows or sub_rows else "No bills or subscriptions saved yet.", c)


# ---- kitchen, dates, reading, flashcards -------------------------------------------------------

def show_meals(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    plan = homestore.load(settings, homekitchen.MEALS, {})
    start = homestore.week_start(today)
    rows, planned = [], 0
    for i in range(7):
        day = start + timedelta(days=i)
        meals = plan.get(day.isoformat()) if isinstance(plan.get(day.isoformat()), dict) else {}
        planned += len(meals)
        rows.append([("Today" if day == today else f"{day:%A}")] + [meals.get(s, "") for s in homekitchen.SLOTS])
    c = screen.card("table", "Meals this week", "showme-meals", columns=["Day", "Breakfast", "Lunch", "Dinner"], rows=rows,
                    buttons=[{"label": "Plan a meal", "say": "I want to plan a meal this week."},
                             {"label": "Clear plan", "say": "Clear this week's meal plan."}])
    return screen.Shown(f"This week's meal plan is on the screen: {planned} meals planned.", c)


def _method(text: str) -> list[str]:
    steps, inside = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = line.strip("# ").lower() == "method"
        elif inside and line.strip():
            steps.append(line.split(". ", 1)[-1].strip() if line[:1].isdigit() else line.strip())
    return steps


def show_recipe(settings: Settings, name: str) -> screen.Shown:
    p = homekitchen._recipe(settings, name)
    text = p.read_text(encoding="utf-8")
    ingredients, steps = homekitchen.recipe_ingredients(text), _method(text)
    return _board(f"The {p.stem} recipe is on the screen.", "recipe", p.stem, [
        {"type": "list", "title": "Ingredients", "items": [{"label": i} for i in ingredients]},
        {"type": "list", "title": "Method", "items": [{"label": f"{n}. {s}"} for n, s in enumerate(steps, 1)]}
        if steps else None],
        [{"label": "Add ingredients to shopping list", "say": f"Add the {p.stem} ingredients to my shopping list."},
         {"label": "Read it to me", "say": f"Read me the {p.stem} recipe."}])


def _days_left(n: int) -> str:
    return "today" if n == 0 else "tomorrow" if n == 1 else f"in {n} days" if n > 0 else f"{-n} days ago"


def show_dates(settings: Settings, today: date | None = None) -> screen.Shown:
    today = today or date.today()
    births = []
    for name, value in dates_saved.load(settings, "birthday").items():
        when, age = dates_saved._next_birthday(value, today)
        births.append((when, {"label": name + (f", turning {age}" if age is not None else ""),
                              "note": f"{_short(when)} {when:%b}, {_days_left((when - today).days)}"}))
    counts = []
    for name, value in dates_saved.load(settings, "countdown").items():
        when = date.fromisoformat(value)
        counts.append((when, {"label": name, "note": f"{_short(when)} {when:%b %Y}, {_days_left((when - today).days)}"}))
    births.sort(key=lambda b: b[0])
    counts.sort(key=lambda c: c[0])
    soonest = min(births + counts, key=lambda x: x[0] if x[0] >= today else date.max, default=None)
    text = (f"Next up: {soonest[1]['label']}, {_days_left((soonest[0] - today).days)}." if soonest
            else "No birthdays or countdowns saved.")
    return _board(text, "dates", "Birthdays and countdowns", [
        {"type": "list", "title": "Birthdays", "items": [b for _, b in births]},
        {"type": "list", "title": "Countdowns", "items": [c for _, c in counts]}],
        [{"label": "Add birthday", "say": "I want to save a birthday."},
         {"label": "Add countdown", "say": "I want to add a countdown."}])


def show_reading(settings: Settings) -> screen.Shown:
    books = growth_store.load(settings, "books", [])
    by = growth_media._by
    now = [{"label": by(b), "say": f"I finished reading {b['title']}.", "action": "Finished"}
           for b in books if b["status"] == "reading"]
    waiting = [{"label": by(b), "say": f"I'm starting to read {b['title']}.", "action": "Start"}
               for b in books if b["status"] == "to read"]
    done = [{"label": by(b), "note": f"{b['rating']}/5" if b.get("rating") else "", "done": True}
            for b in books if b["status"] == "finished"][-10:]
    return _board(f"Your reading list is on the screen: {len(now)} on the go, {len(waiting)} waiting.", "reading",
                  "Reading list", [{"type": "list", "title": "Reading now", "items": now},
                                   {"type": "list", "title": "To read", "items": waiting},
                                   {"type": "list", "title": "Finished lately", "items": done[::-1]} if done else None],
                  [{"label": "Add a book", "say": "Add a book to my reading list."}])


def show_watching(settings: Settings) -> screen.Shown:
    items = [i for i in growth_store.load(settings, "watch", []) if not i.get("watched")]
    sections = [{"type": "list", "title": title, "items": [
        {"label": i["title"], "say": f"Mark {i['title']} as watched.", "action": "Watched"}
        for i in items if i["kind"] == kind]} for title, kind in (("Films", "film"), ("Series", "series"))]
    return _board(f"Your watch list is on the screen: {len(items)} to watch.", "watching", "Watch list", sections,
                  [{"label": "Pick for tonight", "say": "Pick something from my watch list for tonight."},
                   {"label": "Add something", "say": "Add something to my watch list."}])


def show_flashcard(settings: Settings, deck: str, today: date | None = None) -> screen.Shown:
    today = today or growth_store.today()
    said = growth_study.quiz(settings, deck, today)
    data = growth_study._decks(settings)
    pending = data.get("pending")
    if said.startswith("Nothing due") or not pending:
        return _board(said, "flashcards", "Flashcards", [{"type": "text", "text": said}],
                      [{"label": "Deck stats", "say": "How are my flashcards going?"}])
    deck_row = growth_store.find(data["decks"], "name", pending["deck"])
    card = next(c for c in deck_row["cards"] if c["front"] == pending["front"])
    return _board(f"A {deck_row['name']} card is on the screen: {card['front']} (Answer, keep it hidden until they reveal "
                  f"or answer: {card['back']})", "flashcards", f"Flashcards: {deck_row['name']}",
                  [{"type": "flashcard", "front": card["front"], "back": card["back"]}],
                  [{"label": "I got it right", "say": "I got that flashcard right."},
                   {"label": "I got it wrong", "say": "I got that flashcard wrong."},
                   {"label": "Next card", "say": f"Show me the next {deck_row['name']} flashcard."}])


# ---- the tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "show_my",
        "description": "Show the user's own lists and trackers as a window on the Alfred screen, for 'show me my "
                       "…', 'put my … on the screen', 'pop up my …'. action: shopping list, todo list, reminders, "
                       "running timers, calendar (today and this week), weather (this week's forecast chart, "
                       "optional city), habits (streaks and a 14-day grid), payslips (take-home chart), spending "
                       "(by category and last 6 months), wellbeing (sleep, water, mood charts), fitness (steps and "
                       "workouts), goals (progress bars), bills (bills and subscriptions due), meals (this week's "
                       "meal plan), recipe (a recipe card by name), dates (birthdays and countdowns), reading "
                       "(reading list), watching (watch list), flashcards (next due card, optional deck).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "city": {"type": "string", "description": "weather: a city; leave out for home."},
                "name": {"type": "string", "description": "recipe: its name."},
                "deck": {"type": "string", "description": "flashcards: which deck."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"show_my"}
PLAIN = {"shopping": show_shopping, "todo": show_todo, "reminders": show_reminders, "timers": show_timers,
         "habits": show_habits, "payslips": show_payslips, "spending": show_spending, "wellbeing": show_wellbeing,
         "fitness": show_fitness, "goals": show_goals, "bills": show_bills, "meals": show_meals, "dates": show_dates,
         "reading": show_reading, "watching": show_watching}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> screen.Shown:
    action = args.get("action")
    if action == "calendar":
        return await show_calendar(http, settings)
    if action == "weather":
        return await show_weather(http, settings, args.get("city") or "")
    if action == "recipe":
        return await asyncio.to_thread(show_recipe, settings, args.get("name") or "")
    if action == "flashcards":
        return await asyncio.to_thread(show_flashcard, settings, args.get("deck") or "")
    if action == "timers":
        return show_timers(settings)
    if action in PLAIN:
        return await asyncio.to_thread(PLAIN[action], settings)
    raise ValueError(f"I can't show {action} yet.")
