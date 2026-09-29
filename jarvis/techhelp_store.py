"""Shared bits for the tech helper: small JSON files in the memory folder, and the step-by-step checklist pop-up.

Guides and checklists keep their ticked steps in techhelp-progress.json. Nothing goes online.
The "techhelp-steps" pop-up (frontend/popup-techhelp.js) shows the steps with the current one opened out.
"""

import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.update({"techhelp-steps", "techhelp-meter"})

PROGRESS = "techhelp-progress.json"
MAX_ROWS = 100


def rows(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, (dict, list))}


def put(settings: Settings, name: str, found: dict, key: str, value) -> None:
    if key not in found and len(found) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    found[key] = value
    hs.save(settings, name, found)


def key_for(found: dict, label, what: str) -> str:
    k = hs.find(found, hs.need(label, what))
    if k is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(label)}.")
    return k


def remove(settings: Settings, name: str, label, what: str, confirmed: bool) -> str:
    found = rows(settings, name)
    k = key_for(found, label, what)
    if not confirmed:
        return f"Ask the user to confirm removing {k}, then call again with confirmed true."
    del found[k]
    hs.save(settings, name, found)
    return f"Removed {k}."


def done_steps(settings: Settings, pid: str, total: int) -> set[int]:
    saved = hs.load(settings, PROGRESS, {}).get(pid, [])
    return {i for i in saved if isinstance(i, int) and 0 <= i < total}


def _save_done(settings: Settings, pid: str, done: set[int]) -> None:
    every = hs.load(settings, PROGRESS, {})
    every[pid] = sorted(done)
    hs.save(settings, PROGRESS, every)


def _current(steps: list, done: set[int]) -> int | None:
    return next((i for i in range(len(steps)) if i not in done), None)


def steps_card(pid: str, title: str, steps: list, done: set[int], ask_about: str) -> dict:
    cur = _current(steps, done)
    data = {"steps": [{"n": i + 1, "title": t, "detail": d, "done": i in done,
                       "say": f"Tick step {i + 1} of {ask_about}." if i not in done
                       else f"Untick step {i + 1} of {ask_about}."} for i, (t, d) in enumerate(steps)],
            "current": cur, "done": len(done), "total": len(steps)}
    buttons = [{"label": "Done, next step", "say": f"Tick the current step of {ask_about} and read me the next one."}
               if cur is not None else {"label": "Start again", "say": f"Reset {ask_about}."}]
    if cur is not None:
        buttons.append({"label": "Read it out", "say": f"Read me the current step of {ask_about}."})
    return screen.card("techhelp-steps", title, f"techhelp-{pid}", buttons=buttons, data=data)


def spoken(title: str, steps: list, done: set[int], lead: str = "") -> str:
    cur = _current(steps, done)
    if cur is None:
        return f"{lead}All {len(steps)} steps of {title} are ticked off."
    t, d = steps[cur]
    return f"{lead}{title}, step {cur + 1} of {len(steps)}: {t}. {d}"


def show(settings: Settings, pid: str, title: str, steps: list, ask_about: str, lead: str = "") -> screen.Shown:
    done = done_steps(settings, pid, len(steps))
    return screen.Shown(spoken(title, steps, done, lead), steps_card(pid, title, steps, done, ask_about))


def tick(settings: Settings, pid: str, title: str, steps: list, ask_about: str, step=None, done_flag=True) -> screen.Shown:
    done = done_steps(settings, pid, len(steps))
    if step in (None, ""):
        cur = _current(steps, done)
        if cur is None:
            return show(settings, pid, title, steps, ask_about)
        index = cur
    else:
        index = int(hs.number(step, "step number", 1, len(steps))) - 1
    (done.add if done_flag else done.discard)(index)
    _save_done(settings, pid, done)
    lead = f"Ticked {steps[index][0]}. " if done_flag else f"Unticked {steps[index][0]}. "
    return screen.Shown(spoken(title, steps, done, lead), steps_card(pid, title, steps, done, ask_about))


def reset(settings: Settings, pid: str, title: str, steps: list, ask_about: str) -> screen.Shown:
    _save_done(settings, pid, set())
    return show(settings, pid, title, steps, ask_about, "Starting again. ")
