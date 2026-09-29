"""Freelance work in progress: project tracker with milestones and due dates, a start/stop time tracker per client and
project, the weekly timesheet, unbilled time, a scope creep log with change-request drafts, and retainers (hours used
against hours included).

Pop-ups: "freelance-timesheet", "freelance-meter" (retainers), "timer" and tables. Data: freelance-projects.json,
-time.json, -scope.json, -retainers.json. Nothing is sent anywhere.
"""

from datetime import date, datetime, timedelta

import freelance_store as st
import screen
from config import Settings

NAMES = {"freelance_work"}
STATUSES = ["planned", "active", "waiting on client", "in review", "paused", "done"]
SCOPE_STATUSES = ["open", "quoted", "approved", "declined", "absorbed"]
RETAINER = "Retainer"
ACTIONS = ["project_add", "projects", "project_update", "project_remove", "milestone_add", "milestones", "milestone_done",
           "due_soon", "timer_start", "timer_stop", "timer_status", "time_log", "timesheet", "time_summary", "unbilled", "mark_billed",
           "scope_add", "scope_list", "scope_update", "change_request", "retainer_add", "retainer_log", "retainers"]


def _status(value) -> str:
    if value not in STATUSES:
        raise ValueError("A project's status is one of " + ", ".join(STATUSES) + ".")
    return value


def project_add(settings: Settings, args: dict) -> screen.Shown:
    rows = st.projects(settings)
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The project list is full.")
    due = st.parse_date(args.get("due"), "due date")
    project = {"id": st.next_id(rows), "name": st.need(args.get("project"), "project", 80),
               "client": st.client_name(settings, args.get("client")), "status": _status(args.get("status") or "active"),
               "fee": st.number(args["fee"], "fee", True) if args.get("fee") is not None else 0.0,
               "est_hours": st.number(args["est_hours"], "estimated hours") if args.get("est_hours") is not None else 0.0,
               "due": due.isoformat() if due else "", "notes": st.clean(args.get("note"), 200), "milestones": [],
               "created": st.today().isoformat()}
    rows.append(project)
    st.save(settings, st.PROJECTS, rows)
    return projects(settings, {}, f"Added project {project['id']}: {project['name']}.")


def _logged(settings: Settings, p: dict) -> float:
    return sum(e["hours"] for e in st.entries(settings) if e["project"].lower() == p["name"].lower()
               and e["client"].lower() == p["client"].lower())


def projects(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = st.projects(settings)
    if args.get("status"):
        rows = [p for p in rows if p["status"] == _status(args["status"])]
    elif not args.get("all"):
        rows = [p for p in rows if p["status"] != "done"]
    if args.get("client"):
        rows = [p for p in rows if args["client"].lower() in p["client"].lower()]
    if not rows:
        raise ValueError("No projects to show. Tell me about a job.")
    table = []
    for p in sorted(rows, key=lambda p: p["due"] or "9999"):
        ms = p["milestones"]
        hours = round(_logged(settings, p), 1)
        table.append([str(p["id"]), p["name"], p["client"], p["status"], p["due"] or "-",
                      f"{sum(m['done'] for m in ms)}/{len(ms)}" if ms else "-",
                      f"{st.num(hours)}/{st.num(p['est_hours'])}h" if p["est_hours"] else f"{st.num(hours)}h"])
    return st.table(f"{prefix} {len(rows)} project{'s' if len(rows) != 1 else ''}.".strip(), "Freelance projects",
                    ["#", "Project", "Client", "Status", "Due", "Steps", "Hours"], table,
                    [{"label": "Due soon", "say": "What freelance work is due soon?"}])


def project_update(settings: Settings, args: dict) -> screen.Shown:
    rows = st.projects(settings)
    p = next(r for r in rows if r["id"] == st.pick_project(settings, args)["id"])
    if args.get("status"):
        p["status"] = _status(args["status"])
        if p["status"] == "done":
            p["done"] = st.today().isoformat()
    for key, what in (("fee", "fee"), ("est_hours", "estimated hours")):
        if args.get(key) is not None:
            p[key] = st.number(args[key], what, True)
    if args.get("due"):
        p["due"] = st.parse_date(args["due"], "due date").isoformat()
    if args.get("note"):
        p["notes"] = st.clean(args["note"], 200)
    st.save(settings, st.PROJECTS, rows)
    return projects(settings, {"all": True}, f"Updated {p['name']}.")


def project_remove(settings: Settings, args: dict) -> str:
    rows = st.projects(settings)
    p = st.pick_project(settings, args)
    if not args.get("confirmed"):
        return f"Remove project {p['id']}, {p['name']}, with its milestones? Say yes to confirm. Logged time stays."
    st.save(settings, st.PROJECTS, [r for r in rows if r["id"] != p["id"]])
    return f"Removed {p['name']}."


def milestone_add(settings: Settings, args: dict) -> screen.Shown:
    rows = st.projects(settings)
    p = next(r for r in rows if r["id"] == st.pick_project(settings, args)["id"])
    if len(p["milestones"]) >= 30:
        raise ValueError("That project has plenty of milestones already.")
    due = st.parse_date(args.get("due"), "due date")
    p["milestones"].append({"title": st.need(args.get("title"), "milestone", 80), "due": due.isoformat() if due else "",
                            "amount": st.number(args["amount"], "amount", True) if args.get("amount") is not None else 0.0, "done": False})
    st.save(settings, st.PROJECTS, rows)
    return _steps(p, f"Added a milestone to {p['name']}.")


def _steps(p: dict, prefix: str = "") -> screen.Shown:
    items = [{"label": f"{i}. {m['title']}" + (f" (due {m['due']})" if m["due"] else "") + (f", {st.gbp(m['amount'])}" if m["amount"] else ""),
              "done": m["done"], "say": f"{'Reopen' if m['done'] else 'Finish'} milestone {i} of {p['name']}."}
             for i, m in enumerate(p["milestones"], 1)]
    done = sum(m["done"] for m in p["milestones"])
    return screen.Shown(f"{prefix} {done} of {len(items)} milestones done.".strip(),
                        screen.card("list", f"Milestones: {p['name']}", f"freelance-steps-{p['id']}", items=items, checks=True))


def milestones(settings: Settings, args: dict) -> screen.Shown:
    p = st.pick_project(settings, args)
    if not p["milestones"]:
        raise ValueError(f"{p['name']} has no milestones yet.")
    return _steps(p)


def milestone_done(settings: Settings, args: dict) -> screen.Shown:
    rows = st.projects(settings)
    p = next(r for r in rows if r["id"] == st.pick_project(settings, args)["id"])
    ref = st.need(args.get("milestone"), "milestone number or name", 80)
    ms = p["milestones"]
    hit = ms[int(ref) - 1] if ref.isdigit() and 0 < int(ref) <= len(ms) else next(
        (m for m in ms if ref.lower() in m["title"].lower()), None)
    if hit is None:
        raise ValueError(f"I can't find that milestone on {p['name']}.")
    hit["done"] = args.get("reopen") is not True
    st.save(settings, st.PROJECTS, rows)
    return _steps(p, f"{'Ticked' if hit['done'] else 'Reopened'} {hit['title']}.")


def due_soon(settings: Settings, args: dict) -> screen.Shown:
    horizon = st.today() + timedelta(days=int(args.get("days") or 14))
    found = []
    for p in st.projects(settings):
        if p["status"] == "done":
            continue
        if p["due"] and date.fromisoformat(p["due"]) <= horizon:
            found.append((p["due"], f"{p['name']} ({p['client']}) is due {st.until(date.fromisoformat(p['due']))}",
                          f"Show the milestones for {p['name']}."))
        for i, m in enumerate(p["milestones"], 1):
            if not m["done"] and m["due"] and date.fromisoformat(m["due"]) <= horizon:
                found.append((m["due"], f"{p['name']}: {m['title']} {st.until(date.fromisoformat(m['due']))}",
                              f"Finish milestone {i} of {p['name']}."))
    if not found:
        return "Nothing freelance is due in that time."
    items = [{"label": text, "say": say} for _, text, say in sorted(found)]
    return screen.Shown(f"{len(items)} freelance deadline{'s' if len(items) != 1 else ''} coming up.",
                        screen.card("list", "Freelance due soon", "freelance-due", items=items))


def _timer_card(run: dict) -> dict:
    started = datetime.fromisoformat(run["started"])
    return screen.card("timer", f"Timing {run['project']}", "freelance-timer", started_at=int(started.timestamp() * 1000),
                       buttons=[{"label": "Stop", "say": "Stop my freelance timer."}])


def _stop(settings: Settings, data: dict):
    run = data.pop("running", None)
    if not run:
        return None
    hours = max((datetime.now() - datetime.fromisoformat(run["started"])).total_seconds() / 3600, 1 / 60)
    st.save(settings, st.TIME, data)
    entry = st.add_time(settings, run["client"], run["project"], hours, datetime.fromisoformat(run["started"]).date(),
                        run.get("note", ""), run.get("billable", True))
    return entry


def _who(settings: Settings, args: dict) -> tuple[str, str]:
    """(client, project) from the arguments; a saved project fills in its client."""
    if args.get("project"):
        try:
            p = st.pick_project(settings, args)
            return p["client"], p["name"]
        except ValueError:
            pass
    client = st.client_name(settings, args.get("client"))
    return client, st.clean(args.get("project"), 80) or "General"


def timer_start(settings: Settings, args: dict) -> screen.Shown:
    client, project = _who(settings, args)
    data = st.time_data(settings)
    old = _stop(settings, data)
    data = st.time_data(settings)
    data["running"] = {"client": client, "project": project, "started": datetime.now().isoformat(timespec="seconds"),
                       "billable": args.get("billable") is not False, "note": st.clean(args.get("note"), 120)}
    st.save(settings, st.TIME, data)
    said = f"Stopped {old['project']} after {st.hm(old['hours'])}. " if old else ""
    return screen.Shown(said + f"Timing {project} for {client}.", _timer_card(data["running"]))


def timer_stop(settings: Settings, args: dict) -> str:
    entry = _stop(settings, st.time_data(settings))
    if not entry:
        return "No freelance timer is running."
    return f"Stopped. Logged {st.hm(entry['hours'])} on {entry['project']} for {entry['client']}."


def timer_status(settings: Settings, args: dict):
    run = st.time_data(settings).get("running")
    if not run:
        return "No freelance timer is running."
    mins = (datetime.now() - datetime.fromisoformat(run["started"])).total_seconds() / 3600
    return screen.Shown(f"Timing {run['project']} for {run['client']}, {st.hm(mins)} so far.", _timer_card(run))


def time_log(settings: Settings, args: dict) -> str:
    client, project = _who(settings, args)
    hours = st.number(args.get("hours"), "hours", top=24)
    day = st.parse_date(args.get("date"), "date")
    st.add_time(settings, client, project, hours, day, st.clean(args.get("note"), 120), args.get("billable") is not False)
    return f"Logged {st.hm(hours)} on {project} for {client}."


def timesheet(settings: Settings, args: dict) -> screen.Shown:
    start = st.week_start(args.get("week"))
    end = start + timedelta(days=6)
    rows: dict[tuple[str, str], list[float]] = {}
    for e in st.entries(settings, start, end, args.get("client")):
        rows.setdefault((e["client"], e["project"]), [0.0] * 7)[(date.fromisoformat(e["date"]) - start).days] += e["hours"]
    if not rows:
        raise ValueError(f"No time logged for the week of {st.short(start)}.")
    days = [(start + timedelta(days=i)).strftime("%a %d") for i in range(7)]
    out = [{"label": f"{c}: {p}", "hours": [round(h, 2) for h in v], "total": round(sum(v), 2)} for (c, p), v in sorted(rows.items())]
    totals = [round(sum(r["hours"][i] for r in out), 2) for i in range(7)]
    total = round(sum(totals), 2)
    return screen.Shown(f"{st.hm(total)} logged for the week of {st.short(start)}.", screen.card(
        st.SHEET, f"Timesheet: week of {st.short(start)}", f"freelance-sheet-{start.isoformat()}",
        data={"days": days, "rows": out, "totals": totals, "total": total},
        buttons=[{"label": "Last week", "say": "Show my freelance timesheet for last week."}]))


def time_summary(settings: Settings, args: dict) -> screen.Shown:
    first, last = st.month_bounds(args.get("month"))
    groups: dict[str, dict] = {}
    for e in st.entries(settings, first, last):
        g = groups.setdefault(e["client"], {"hours": 0.0, "billable": 0.0})
        g["hours"] += e["hours"]
        g["billable"] += e["hours"] if e["billable"] else 0
    if not groups:
        raise ValueError(f"No time logged in {first.strftime('%B %Y')}.")
    total = sum(g["hours"] for g in groups.values())
    table = [[c, st.num(round(g["hours"], 2)), f"{round(100 * g['hours'] / total)}%", st.num(round(g["billable"], 2))]
             for c, g in sorted(groups.items(), key=lambda kv: -kv[1]["hours"])]
    return st.table(f"{st.hm(total)} logged in {first.strftime('%B')}.", f"Hours by client: {first.strftime('%B %Y')}",
                    ["Client", "Hours", "Share", "Billable"], table)


def _rate(settings: Settings, args: dict) -> float | None:
    if args.get("rate") is not None:
        return st.number(args["rate"], "hourly rate")
    return st.profile(settings).get("hourly_rate")


def unbilled(settings: Settings, args: dict) -> screen.Shown:
    groups: dict[tuple[str, str], float] = {}
    for e in st.entries(settings, client=args.get("client")):
        if e["billable"] and not e["billed"]:
            groups[(e["client"], e["project"])] = groups.get((e["client"], e["project"]), 0.0) + e["hours"]
    if not groups:
        return "All your logged time has been billed."
    rate = _rate(settings, args)
    total = sum(groups.values())
    table = [[c, p, st.num(round(h, 2)), st.gbp(round(h * rate, 2)) if rate else "-"] for (c, p), h in sorted(groups.items())]
    value = f" That is about {st.gbp(round(total * rate, 2))} at {st.gbp(rate)} an hour." if rate else ""
    return st.table(f"{st.hm(total)} of logged time hasn't been billed.{value}", "Unbilled time", ["Client", "Project", "Hours", "Worth"], table)


def mark_billed(settings: Settings, args: dict) -> str:
    client = st.need(args.get("client"), "client", 60).lower()
    data = st.time_data(settings)
    hours = count = 0
    for e in data["entries"]:
        if client in e["client"].lower() and not e["billed"] and (not args.get("project") or args["project"].lower() in e["project"].lower()):
            e["billed"] = True
            hours += e["hours"]
            count += 1
    if not count:
        return "There is no unbilled time for that."
    st.save(settings, st.TIME, data)
    return f"Marked {st.hm(hours)} ({count} entries) as billed."


def _scope(settings: Settings) -> list[dict]:
    return st.rows_of(settings, st.SCOPE)


def scope_add(settings: Settings, args: dict) -> screen.Shown:
    rows = _scope(settings)
    if len(rows) >= st.MAX_ROWS:
        raise ValueError("The scope log is full.")
    client, project = _who(settings, args)
    hours = st.number(args["extra_hours"], "extra hours", True) if args.get("extra_hours") is not None else 0.0
    rate = _rate(settings, args)
    price = st.number(args["price"], "price", True) if args.get("price") is not None else (round(hours * rate, 2) if rate else 0.0)
    rows.append({"id": st.next_id(rows), "client": client, "project": project, "request": st.need(args.get("request"), "request", 200),
                 "extra_hours": hours, "price": price, "status": "open", "date": st.today().isoformat()})
    st.save(settings, st.SCOPE, rows)
    return scope_list(settings, {"project": project}, "Logged it as outside the agreed scope.")


def scope_list(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = _scope(settings)
    if args.get("project"):
        rows = [r for r in rows if args["project"].lower() in r["project"].lower()]
    if not rows:
        raise ValueError("Nothing in the scope log yet.")
    free = sum(r["extra_hours"] for r in rows if r["status"] in ("open", "absorbed"))
    table = [[str(r["id"]), r["project"], r["request"][:60], st.num(r["extra_hours"]) + "h", st.gbp(r["price"]) if r["price"] else "-", r["status"]] for r in rows]
    return st.table(f"{prefix} {st.num(round(free, 2))} extra hours are open or unpaid.".strip(), "Scope creep log",
                    ["#", "Project", "Extra ask", "Hours", "Price", "Status"], table)


def scope_update(settings: Settings, args: dict) -> screen.Shown:
    rows = _scope(settings)
    hit = next((r for r in rows if r["id"] == int(args.get("scope_id") or 0)), None)
    if not hit:
        raise ValueError("Give the scope log number.")
    if args.get("status") not in SCOPE_STATUSES:
        raise ValueError("A scope item's status is one of " + ", ".join(SCOPE_STATUSES) + ".")
    hit["status"] = args["status"]
    if args.get("price") is not None:
        hit["price"] = st.number(args["price"], "price", True)
    st.save(settings, st.SCOPE, rows)
    return scope_list(settings, {}, f"Scope item {hit['id']} is now {hit['status']}.")


def change_request(settings: Settings, args: dict) -> screen.Shown:
    hit = next((r for r in _scope(settings) if r["id"] == int(args.get("scope_id") or 0)), None)
    if not hit:
        raise ValueError("Give the scope log number to write the change request for.")
    cost = f"{st.gbp(hit['price'])}" if hit["price"] else "[price]"
    hours = f"about {st.num(hit['extra_hours'])} extra hours" if hit["extra_hours"] else "some extra time"
    who = st.clean(args.get("contact_name"), 40) or hit["client"]
    body = (f"Change request: {hit['project']}\n\nHi {who},\n\nThanks for the new request: \"{hit['request']}\".\n\n"
            f"This is outside what we agreed for {hit['project']}, so I'd like to treat it as a change to the scope.\n\n"
            f"- Extra work: {hours}\n- Extra cost: {cost}\n- Effect on the deadline: [add or say none]\n\n"
            "If you'd like me to go ahead, please reply to confirm and I'll add it to the plan. If you'd rather keep to the "
            "original scope, that's fine too and we carry on as agreed.\n\nThanks,\n" + (st.clean(args.get("my_name"), 40) or "[Your name]"))
    return st.draft(settings, f"Change request {hit['id']}", body, f"Here is a polite change request for {hit['project']}.",
                    f"Change request - {st.slug(hit['project'])} {hit['id']}")


def retainer_add(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.RETAINERS)
    client = st.client_name(settings, args.get("client"))
    row = next((r for r in rows if r["client"].lower() == client.lower()), None)
    if row is None:
        row = {"client": client}
        rows.append(row)
    row["hours"] = st.number(args.get("hours_included"), "hours included per month")
    row["fee"] = st.number(args["fee"], "monthly fee", True) if args.get("fee") is not None else row.get("fee", 0.0)
    st.save(settings, st.RETAINERS, rows)
    return retainers(settings, {}, f"Saved the retainer for {client}.")


def retainer_log(settings: Settings, args: dict) -> screen.Shown:
    rows = st.rows_of(settings, st.RETAINERS)
    key = st.find([r["client"] for r in rows], st.need(args.get("client"), "client", 60))
    if key is None:
        raise ValueError("That client doesn't have a retainer yet.")
    st.add_time(settings, key, RETAINER, st.number(args.get("hours"), "hours", top=24), st.parse_date(args.get("date")),
                st.clean(args.get("note"), 120))
    return retainers(settings, {}, f"Logged against {key}'s retainer.")


def retainers(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    rows = st.rows_of(settings, st.RETAINERS)
    if not rows:
        raise ValueError("No retainers yet. Say which client and how many hours a month they pay for.")
    first, last = st.month_bounds(args.get("month"))
    meters = []
    for r in rows:
        used = sum(e["hours"] for e in st.entries(settings, first, last, r["client"]) if e["project"].lower() == RETAINER.lower())
        left = r["hours"] - used
        meters.append({"label": r["client"], "used": round(used, 2), "max": r["hours"],
                       "text": f"{st.num(round(used, 2))} of {st.num(r['hours'])}h used, "
                               + (f"{st.num(round(left, 2))}h left" if left >= 0 else f"{st.num(round(-left, 2))}h over"),
                       "say": f"Log time on {r['client']}'s retainer."})
    over = [m["label"] for m in meters if m["used"] > m["max"]]
    said = f"{prefix} Retainers for {first.strftime('%B')}." + (f" {', '.join(over)} over their hours." if over else "")
    return st.meter(said.strip(), f"Retainers: {first.strftime('%B %Y')}", meters,
                    "Retainer time is anything logged under the project name Retainer.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "freelance_work",
        "description": "Freelance project tracker and time: projects with milestones and due dates, start/stop timer per client and "
                       "project, log time, weekly timesheet pop-up, hours by client, unbilled time, scope creep log and change-request "
                       "drafts, retainers (hours used vs included). Removal needs confirmed true only after the user says yes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "client": {"type": "string"}, "project": {"type": "string", "description": "Project name (or Retainer)."},
                "project_id": {"type": "integer"}, "status": {"type": "string", "enum": STATUSES + [s for s in SCOPE_STATUSES if s not in STATUSES]},
                "fee": {"type": "number"}, "est_hours": {"type": "number"}, "due": {"type": "string", "description": "YYYY-MM-DD, today, tomorrow."},
                "note": {"type": "string"}, "title": {"type": "string", "description": "Milestone title."},
                "amount": {"type": "number", "description": "Milestone payment."}, "milestone": {"type": "string", "description": "Milestone number or words."},
                "reopen": {"type": "boolean"}, "days": {"type": "integer"}, "all": {"type": "boolean", "description": "Include finished projects."},
                "hours": {"type": "number"}, "date": {"type": "string"}, "billable": {"type": "boolean"},
                "week": {"type": "string", "description": "this, last, or any date in the week (YYYY-MM-DD)."},
                "month": {"type": "string", "description": "YYYY-MM."}, "rate": {"type": "number", "description": "Hourly rate in pounds."},
                "request": {"type": "string", "description": "What the client asked for beyond the scope."},
                "extra_hours": {"type": "number"}, "price": {"type": "number"}, "scope_id": {"type": "integer"},
                "contact_name": {"type": "string"}, "my_name": {"type": "string"},
                "hours_included": {"type": "number", "description": "Retainer hours per month."},
                "confirmed": {"type": "boolean", "description": "Set true only after the user confirms a removal."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"project_add": project_add, "projects": projects, "project_update": project_update,
                "project_remove": project_remove, "milestone_add": milestone_add, "milestones": milestones, "milestone_done": milestone_done,
                "due_soon": due_soon, "timer_start": timer_start, "timer_stop": timer_stop, "timer_status": timer_status,
                "time_log": time_log, "timesheet": timesheet, "time_summary": time_summary, "unbilled": unbilled,
                "mark_billed": mark_billed, "scope_add": scope_add, "scope_list": scope_list, "scope_update": scope_update,
                "change_request": change_request, "retainer_add": retainer_add, "retainer_log": retainer_log,
                "retainers": retainers}
    return st.dispatch(handlers, args.get("action"), settings, args, "freelance work")
