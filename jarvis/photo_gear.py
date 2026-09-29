"""Camera gear list with lens details, what to pack for a shoot, and which of your lenses suits a subject.

The gear list (photo-gear.json) keeps cameras, lenses, flashes, tripods and the rest. A lens's field of view uses
your first camera that has a sensor. Removing gear needs confirmed true. Packing lists pop up as a tick list.
"""

import math

import homestore as hs
import photo_data
import photo_store as ps
import screen
from config import Settings

GEAR = "photo-gear.json"
KINDS = ("camera", "lens", "flash", "tripod", "filter", "battery", "card", "bag", "remote", "reflector", "other")
MAX_GEAR = 200
ACTIONS = ("gear_add", "gear_list", "gear_show", "gear_update", "gear_remove", "pack_list", "lens_for")
FIELDS = ("kind", "sensor", "megapixels", "focal_min", "focal_max", "max_aperture", "mount", "weight_g", "notes")


def _load(settings: Settings) -> dict:
    return {k: v for k, v in hs.load(settings, GEAR, {}).items() if isinstance(v, dict)}


def _key(found: dict, name) -> str:
    k = hs.find(found, hs.need(name, "item of gear"))
    if k is None:
        raise ValueError(f"I haven't got {hs.clean(name)} in your gear list.")
    return k


def _fields(a) -> dict:
    out = {}
    if a("kind") is not None:
        kind = hs.clean(a("kind")).lower()
        if kind not in KINDS:
            raise ValueError(f"The kind is one of: {', '.join(KINDS)}.")
        out["kind"] = kind
    for key, low, high in (("megapixels", 1, 500), ("focal_min", 1, 3000), ("focal_max", 1, 3000),
                           ("max_aperture", 0.7, 64), ("weight_g", 1, 50_000)):
        if a(key) is not None:
            out[key] = hs.number(a(key), key.replace("_", " "), low, high)
    for key in ("sensor", "mount", "notes"):
        if a(key) is not None:
            out[key] = hs.clean(a(key), 120)
    if "sensor" in out and out["sensor"]:
        ps.sensor({"sensor": out["sensor"]}.get)
    return out


def _range(item: dict) -> str:
    lo, hi = item.get("focal_min"), item.get("focal_max") or item.get("focal_min")
    if not lo:
        return ""
    return f"{lo:g} mm" if lo == hi else f"{lo:g} to {hi:g} mm"


def _summary(item: dict) -> str:
    bits = [_range(item), f"f/{item['max_aperture']:g}" if item.get("max_aperture") else "", item.get("sensor", ""),
            f"{item['megapixels']:g} MP" if item.get("megapixels") else "", item.get("mount", "")]
    return ", ".join(b for b in bits if b)


def _body_crop(found: dict) -> tuple[str, float]:
    for name, item in found.items():
        if item.get("kind") == "camera" and item.get("sensor"):
            return name, ps.sensor({"sensor": item["sensor"]}.get)[3]
    return "", 1.0


def gear_add(settings: Settings, name, a) -> screen.Shown:
    found = _load(settings)
    label = hs.need(name, "item of gear", 60)
    fields = _fields(a)
    if hs.find(found, label) and hs.find(found, label).lower() == label.lower():
        raise ValueError(f"{label} is already in your gear list; use update to change it.")
    if len(found) >= MAX_GEAR:
        raise ValueError("Your gear list is full.")
    found[label] = {"kind": fields.pop("kind", "other"), **fields}
    hs.save(settings, GEAR, found)
    return screen.Shown(f"Added {label} to your gear list.", _list_card(found))


def _list_card(found: dict) -> dict:
    rows = [[k, v.get("kind", "other"), _summary(v)] for k, v in sorted(found.items(), key=lambda kv: (KINDS.index(kv[1].get("kind", "other")), kv[0]))]
    return ps.table("Camera gear", ["Item", "Type", "Details"], rows, "photo-gear")


def gear_list(settings: Settings, kind) -> screen.Shown:
    found = _load(settings)
    kind = hs.clean(kind).lower()
    if kind:
        found = {k: v for k, v in found.items() if v.get("kind") == kind}
    if not found:
        return screen.Shown("Your gear list is empty. Tell me what you own, like 'add my 50 mm f/1.8 lens'.",
                            _list_card({}))
    return screen.Shown(f"You have {hs.plural(len(found), 'item')} of gear.", _list_card(found))


def gear_show(settings: Settings, name) -> screen.Shown:
    found = _load(settings)
    k = _key(found, name)
    item = found[k]
    rows = [["Type", item.get("kind", "other")]]
    for label, key in (("Mount", "mount"), ("Sensor", "sensor"), ("Notes", "notes")):
        if item.get(key):
            rows.append([label, item[key]])
    if item.get("megapixels"):
        rows.append(["Resolution", f"{item['megapixels']:g} MP"])
    if item.get("weight_g"):
        rows.append(["Weight", f"{item['weight_g']:g} g"])
    spoken = f"{k}: {item.get('kind', 'other')}."
    if item.get("focal_min"):
        rows.append(["Focal length", _range(item)])
        if item.get("max_aperture"):
            rows.append(["Widest aperture", f"f/{item['max_aperture']:g}"])
        body, crop = _body_crop(found)
        lo = item["focal_min"]
        hi = item.get("focal_max") or lo
        wide = math.degrees(2 * math.atan(36 / crop / (2 * lo)))
        rows.append(["Widest view" + (f" on {body}" if body else " (full frame)"), f"{wide:.0f}° across"])
        if crop != 1:
            rows.append(["Equivalent", f"{lo * crop:.0f} to {hi * crop:.0f} mm on full frame"])
        spoken = f"{k}: {_summary(item)}."
    return screen.Shown(spoken, ps.table(k, ["Detail", "Value"], rows, f"photo-gear-{k}"))


def gear_update(settings: Settings, name, a) -> screen.Shown:
    found = _load(settings)
    k = _key(found, name)
    fields = _fields(a)
    if not fields:
        raise ValueError("What should I change about it?")
    found[k].update(fields)
    hs.save(settings, GEAR, found)
    return gear_show(settings, k)


def gear_remove(settings: Settings, name, confirmed) -> str:
    found = _load(settings)
    k = _key(found, name)
    if confirmed is not True:
        return f"Removing {k} from your gear list can't be undone. Ask the user to confirm, then call again with confirmed true."
    del found[k]
    hs.save(settings, GEAR, found)
    return f"Removed {k} from your gear list."


def _owned(found: dict, keyword: str) -> list[str]:
    return [k for k, v in found.items() if keyword and (v.get("kind") == keyword or keyword in k.lower())]


def pack_list(settings: Settings, kind) -> screen.Shown:
    kind = hs.clean(kind).lower()
    if kind not in photo_data.SHOOTS:
        raise ValueError(f"I can pack for: {', '.join(photo_data.SHOOTS)}.")
    found = _load(settings)
    items, have = [], 0
    for label, keyword in photo_data.SHOOTS[kind]["pack"]:
        mine = _owned(found, keyword)
        have += bool(mine)
        note = f" (yours: {', '.join(mine[:2])})" if mine else " (not in your gear list)" if keyword else ""
        items.append({"label": label + note})
    card = screen.card("list", f"Pack for a {kind} shoot", f"photo-pack-{kind}", items=items, checks=True)
    return screen.Shown(f"A {kind} shoot needs {len(items)} things; {have} are in your gear list.", card)


def lens_for(settings: Settings, subject) -> screen.Shown:
    subject = hs.clean(subject).lower()
    if subject not in photo_data.LENS_ROLES:
        rows = [[k, f"{lo} to {hi} mm", why] for k, (lo, hi, why) in photo_data.LENS_ROLES.items()]
        return screen.Shown("Here is which focal lengths suit each kind of photo.",
                            ps.table("Lens guide", ["Subject", "Full-frame focal length", "Why"], rows, "photo-lens-guide"))
    lo, hi, why = photo_data.LENS_ROLES[subject]
    found = _load(settings)
    _, crop = _body_crop(found)
    rows = []
    for k, v in found.items():
        if v.get("kind") != "lens" or not v.get("focal_min"):
            continue
        a, b = v["focal_min"] * crop, (v.get("focal_max") or v["focal_min"]) * crop
        if a <= hi and b >= lo:
            fast = f", f/{v['max_aperture']:g}" if v.get("max_aperture") else ""
            rows.append([k, f"{a:.0f} to {b:.0f} mm on full frame" + fast, "Covers it" if a <= lo and b >= hi else "Partly covers it"])
    table = ps.table(f"Lens for {subject}", ["Lens", "Range", "Fit"], rows or [["None of your lenses", "", ""]],
                     f"photo-lens-{subject}")
    if rows:
        return screen.Shown(f"For {subject}, try {rows[0][0]}. {why}", table)
    return screen.Shown(f"None of your lenses suit {subject}; you'd want about {lo} to {hi} mm. {why}", table)


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [{
        "name": "photo_gear",
        "description": "The user's camera gear list. gear_add (name, kind camera, lens, flash, tripod, filter, battery, "
                       "card, bag, remote, reflector, other; lens focal_min, focal_max, max_aperture, mount; camera "
                       "sensor, megapixels), gear_list (optionally by kind), gear_show (lens details and field of view), "
                       "gear_update, gear_remove, pack_list (what to pack for a shoot type, ticked against the gear "
                       "list), lens_for (which of the user's lenses suits a subject). Set confirmed true on gear_remove "
                       "only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "name": {"type": "string"}, "kind": {"type": "string", "enum": list(KINDS)},
                "sensor": {"type": "string", "description": "full frame, aps-c, micro four thirds, 1 inch, phone..."},
                "megapixels": num, "focal_min": num, "focal_max": num, "max_aperture": num,
                "mount": {"type": "string"}, "weight_g": num, "notes": {"type": "string"},
                "shoot": {"type": "string", "enum": list(photo_data.SHOOTS)},
                "subject": {"type": "string", "enum": list(photo_data.LENS_ROLES)},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"photo_gear"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    table = {
        "gear_add": lambda: gear_add(settings, a("name"), a),
        "gear_list": lambda: gear_list(settings, a("kind")),
        "gear_show": lambda: gear_show(settings, a("name")),
        "gear_update": lambda: gear_update(settings, a("name"), a),
        "gear_remove": lambda: gear_remove(settings, a("name"), a("confirmed")),
        "pack_list": lambda: pack_list(settings, a("shoot")),
        "lens_for": lambda: lens_for(settings, a("subject")),
    }
    if a("action") not in table:
        raise ValueError(f"I can't do {a('action')}. Try: {', '.join(ACTIONS)}.")
    return table[a("action")]()
