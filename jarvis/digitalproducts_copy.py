"""Digital products part 3: listing copy drafts (titles, description, bullets, FAQ, tags), cover text ideas, licence
terms in plain words, the customer FAQ bank with reply drafts, and update or thank-you notes for buyers.

Drafts are worked out from the product's own details and saved in digitalproducts.json. Nothing is posted; the user
reads, edits and pastes them into wherever they sell. The licence text is a plain-words draft, not legal advice.
"""

import re

import digitalproducts_store as store
import homestore as hs
import screen
from config import Settings

ACTIONS = ["listing_draft", "title_options", "listing_show", "listing_check", "listing_export", "tags_make",
           "cover_ideas", "faq_draft", "licence_terms", "licence_file", "customer_faq_add", "customer_faq_list",
           "customer_faq_find", "customer_faq_remove", "customer_reply", "update_note", "thanks_note"]
DEFAULT_BENEFITS = {
    "printable planner": ["Print as many times as you need for yourself", "Clean layout with room to write",
                          "Instant download, ready to print at home"],
    "checklist": ["One clear page", "Tick things off as you go", "Print it or use it on a tablet"],
    "worksheet": ["Simple prompts that are quick to fill in", "Print and reuse", "Works for one person or a group"],
    "ebook": ["Short chapters you can read in one sitting", "Practical steps, not padding",
              "Read on your phone, tablet or computer"],
    "prompt pack": ["Ready-made prompts to copy and paste", "Organised by job", "Change the [brackets] to suit you"],
    "template": ["Fill in and use straight away", "Editable in common apps", "Saves you starting from a blank page"],
}
RISKY = ["guaranteed", "guarantee", "get rich", "make money", "passive income", "#1", "best seller", "bestseller",
         "cure", "lose weight fast", "no effort", "risk-free", "risk free", "official", "as seen on"]
LICENCES = {
    "personal": ("Personal use licence",
                 ["You may use this item for yourself and your household.", "You may print it as many times as you like "
                  "for your own use.", "You may not share, resell, give away or upload the files, changed or not.",
                  "You may not put it on a site or a course for others to download."]),
    "commercial": ("Commercial use licence",
                   ["You may use this item in your own business, for example in client work or in things you sell "
                    "that are made with it.", "You may not resell or give away the original files as they are.",
                    "You may not claim you made the original design.", "Say how many people or projects it covers "
                    "(for example one business)."]),
    "teacher": ("Classroom use licence",
                ["One purchase covers one teacher.", "You may print copies for your own students.",
                 "You may not share the files with other teachers or post them online.",
                 "You may not resell or give away the files."]),
}
LICENCE_END = "Files are digital and sent as a download. This is a plain-words summary, not legal advice."
DEFAULT_FAQ = [("How do I get my file?", "You download it straight after you buy. If the link does not work, message me."),
               ("Can I print it?", "Yes, as many times as you like for yourself under the personal licence."),
               ("What size is it?", "[A4 and US Letter, or say which]. Check the preview picture before buying."),
               ("Can I use it for my business or sell it?", "Not under the personal licence. Ask me about a commercial licence."),
               ("Something is wrong with the file. What now?", "Message me and I will fix it or sort out a refund, "
                                                                 "in line with the site's rules.")]


def _benefits(row: dict) -> list[str]:
    return row["benefits"] or DEFAULT_BENEFITS.get(row["format"], ["Simple to use", "Made with care", "Instant download"])


def _titles(row: dict) -> list[str]:
    name, fmt, who = row["name"], row["format"].title(), row["audience"]
    key = row["keywords"][0].title() if row["keywords"] else ""
    out = [f"{name} | {fmt}" + (f" for {who}" if who else ""), f"{key} {fmt} - {name}".strip() if key else f"{name} ({fmt})",
           f"{name} - Instant Digital Download"]
    return [t[:140] for t in dict.fromkeys(out)]


def _description(row: dict, benefits: list[str]) -> str:
    who = row["audience"] or "anyone who wants a simple way to get started"
    lines = [f"{row['name']} is a {row['format']} made for {who}.", "", "WHAT YOU GET"] + [f"- {b}" for b in
                                                                                       (row["files"] or [f"1 {row['format']} file"])]
    lines += ["", "WHY YOU MIGHT LIKE IT"] + [f"- {b}" for b in benefits]
    lines += ["", "GOOD TO KNOW", "- This is a digital download; nothing is posted to you.",
              "- Colours can look different on screen and on paper.", "- For personal use unless the licence says otherwise."]
    return "\n".join(lines)


def _tags(row: dict) -> list[str]:
    words = [row["format"], row["name"].lower()] + row["keywords"] + ([f"{row['format']} for {row['audience']}"]
                                                                      if row["audience"] else [])
    words += [f"digital {row['format']}", f"printable {row['format']}"] if "print" in row["format"] else [
        f"{row['format']} download", f"instant download {row['format']}"]
    return list(dict.fromkeys(w.lower()[:40] for w in words if w))[:13]


def _draft_card(row: dict, d: dict, lead: str) -> screen.Shown:
    body = "\n\n".join([f"TITLE OPTIONS\n" + "\n".join(f"- {t}" for t in d["titles"]), d["description"],
                        "BENEFITS\n" + "\n".join(f"- {b}" for b in d["bullets"]),
                        "FAQ\n" + "\n".join(f"Q: {q}\nA: {a}" for q, a in d["faq"]),
                        "TAGS\n" + ", ".join(d["tags"])])
    return screen.Shown(lead, screen.card("text", f"Listing draft: {row['name']}"[:80], f"digitalproducts-listing-{row['id']}",
                                          text=body, buttons=[{"label": "Check it", "say": f"Check the listing for {row['name']}."},
                                                              {"label": "Save as file", "say": f"Export the listing for {row['name']}."}]))


def listing_draft(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args)
    benefits = _benefits(row)
    d = {"titles": _titles(row), "description": _description(row, benefits), "bullets": benefits,
         "faq": [list(x) for x in DEFAULT_FAQ], "tags": _tags(row)}
    data["listings"][str(row["id"])] = d
    store.save(settings, data)
    return _draft_card(row, d, f"Drafted the listing for {row['name']}. Read it, make it sound like you, and check "
                              "the site's limits. " + store.PRICE_NOTE)


def title_options(settings: Settings, args: dict) -> screen.Shown:
    row = store.product(store.load(settings), args)
    titles = _titles(row)
    return screen.Shown("Title ideas: keep the main words first and read the site's title limit.",
                        screen.card("list", f"Titles for {row['name']}"[:80], f"digitalproducts-titles-{row['id']}",
                                    items=[{"label": t} for t in titles]))


def _saved(data: dict, row: dict) -> dict:
    d = data["listings"].get(str(row["id"]))
    if not d:
        raise ValueError(f"There is no listing draft for {row['name']} yet. Ask me to draft one.")
    return d


def listing_show(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args)
    return _draft_card(row, _saved(data, row), f"Here is the saved listing draft for {row['name']}.")


def listing_check(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args)
    d = _saved(data, row)
    text = " ".join([*d["titles"], d["description"], *d["bullets"]]).lower()
    flags = [w for w in RISKY if w in text]
    notes = [f"Risky wording: {w}. Avoid promises about money, results or rankings." for w in flags]
    if row["price"] is None:
        notes.append("No price set yet. Look at what similar products sell for.")
    if not row["files"]:
        notes.append("No files attached yet. Buyers see what you list, so make the product first.")
    if "[" in text:
        notes.append("There are still [brackets] to fill in.")
    if not row["audience"]:
        notes.append("Say who it is for; it helps buyers decide.")
    items = [{"label": n} for n in notes] or [{"label": "Nothing obvious to fix. Read it aloud once more.", "done": True}]
    return screen.Shown(f"{len(notes)} things to look at." if notes else "The draft looks tidy.",
                        screen.card("list", f"Listing check: {row['name']}"[:80], f"digitalproducts-check-{row['id']}", items=items))


def listing_export(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args)
    d = _saved(data, row)
    text = "\n\n".join([f"# {row['name']}", "## Title options", "\n".join(f"- {t}" for t in d["titles"]), "## Description",
                        d["description"], "## Benefits", "\n".join(f"- {b}" for b in d["bullets"]), "## FAQ",
                        "\n\n".join(f"**{q}**\n{a}" for q, a in d["faq"]), "## Tags", ", ".join(d["tags"])]) + "\n"
    path = store.unique(store.folder(settings, "listings"), f"{row['name']} listing", ".md")
    path.write_text(text, encoding="utf-8")
    return store.shown_file(settings, path, f"Saved the listing text for {row['name']} as a file to copy from.")


def tags_make(settings: Settings, args: dict) -> screen.Shown:
    row = store.product(store.load(settings), args)
    return screen.Shown("Keyword ideas. Check the site's own limit, and use words a buyer would type.",
                        screen.card("list", f"Tags for {row['name']}"[:80], f"digitalproducts-tags-{row['id']}",
                                    items=[{"label": t} for t in _tags(row)]))


def cover_ideas(settings: Settings, args: dict) -> screen.Shown:
    row = store.product(store.load(settings), args)
    name = row["name"]
    who = row["audience"]
    ideas = [f"Big title: {name}", f"Title plus a line: {row['format'].title()}" + (f" for {who}" if who else ""),
             "Three words only, very large, on a plain background", f"A tick-box look with '{name}' at the top",
             "Show the inside page as a mock-up with the title above", "Bold black and white, lots of space",
             "A small badge: Instant download"]
    return screen.Shown("Seven cover text ideas. Keep the text large enough to read as a small picture.",
                        screen.card("list", f"Cover ideas: {name}"[:80], f"digitalproducts-cover-{row['id']}",
                                    items=[{"label": i} for i in ideas],
                                    buttons=[{"label": "Make a cover", "say": f"Make a cover picture titled {name}."}]))


def faq_draft(settings: Settings, args: dict) -> screen.Shown:
    row = store.product(store.load(settings), args)
    return screen.Shown("Drafted five questions buyers often ask. Fill in the square brackets.",
                        screen.card("text", f"FAQ: {row['name']}"[:80], f"digitalproducts-faq-{row['id']}",
                                    text="\n\n".join(f"Q: {q}\nA: {a}" for q, a in DEFAULT_FAQ)))


# ---- Licence ---------------------------------------------------------------------------------------

def _licence(kind) -> tuple[str, list[str], str]:
    key = hs.find(LICENCES, hs.clean(kind).lower() or "personal")
    if key is None:
        raise ValueError("Licence kinds: " + ", ".join(LICENCES) + ".")
    title, lines = LICENCES[key]
    return key, [title] + lines, "\n".join(["# " + title, ""] + [f"- {ln}" for ln in lines] + ["", LICENCE_END, ""])


def licence_terms(settings: Settings, args: dict) -> screen.Shown:
    key, lines, _ = _licence(args.get("kind"))
    return screen.Shown(f"The {key} licence in plain words: {' '.join(lines[1:3])}",
                        screen.card("text", lines[0], f"digitalproducts-licence-{key}", text="\n".join(lines[1:]) + "\n\n" + LICENCE_END))


def licence_file(settings: Settings, args: dict) -> screen.Shown:
    key, _, md = _licence(args.get("kind"))
    path = store.unique(store.folder(settings, "licences"), f"{key} licence", ".md")
    path.write_text(md, encoding="utf-8")
    return store.shown_file(settings, path, f"Saved a {key} licence to put in your download. It is not legal advice.")


# ---- Customer FAQ bank -----------------------------------------------------------------------------

def customer_faq_add(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = {"id": store.new_id(data), "question": hs.need(args.get("question"), "question", 200),
           "answer": hs.need(args.get("answer"), "answer", 600), "product": hs.clean(args.get("product"), 80)}
    store.put(data["faq"], row)
    store.save(settings, data)
    return f"Saved question {row['id']} in your customer FAQ."


def customer_faq_list(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    rows = [f for f in data["faq"] if not args.get("product") or f["product"].lower() == str(args["product"]).lower()]
    items = [{"label": f"{f['id']}. {f['question']}", "say": f"Find my customer FAQ answer about {f['question']}"} for f in rows]
    return screen.Shown(f"{len(rows)} customer questions saved." if rows else "Your customer FAQ is empty.",
                        screen.card("list", "Customer FAQ", "digitalproducts-customer-faq", items=items or [{"label": "Nothing yet"}]))


def _match(rows: list, text: str) -> list[dict]:
    words = {w for w in re.findall(r"[a-z0-9']{3,}", text.lower())}
    scored = [(len(words & set(re.findall(r"[a-z0-9']{3,}", f"{f['question']} {f['answer']}".lower()))), f) for f in rows]
    return [f for score, f in sorted(scored, key=lambda x: -x[0]) if score]


def customer_faq_find(settings: Settings, args: dict) -> screen.Shown:
    found = _match(store.load(settings)["faq"], hs.need(args.get("question"), "question", 200))
    if not found:
        return screen.Shown("Nothing in your FAQ matches that yet. Want to save an answer?",
                            screen.card("text", "No match", "digitalproducts-faq-nomatch", text="No saved answer matches."))
    top = found[0]
    return screen.Shown(top["answer"], screen.card("text", top["question"][:80], "digitalproducts-faq-hit",
                                                   text=top["answer"]))


def customer_faq_remove(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    row = store.by_id(data["faq"], args, "question")
    if not args.get("confirmed"):
        return store.confirm_needed(f"question {row['id']}, {row['question']}")
    data["faq"].remove(row)
    store.save(settings, data)
    return "Removed it from your customer FAQ."


def customer_reply(settings: Settings, args: dict) -> screen.Shown:
    message = hs.need(args.get("message"), "customer message", 600)
    found = _match(store.load(settings)["faq"], message)
    answer = found[0]["answer"] if found else "[your answer here]"
    reply = f"Hi {hs.clean(args.get('customer'), 40) or '[name]'},\n\nThanks for getting in touch. {answer}\n\nBest wishes,\n[your name]"
    return screen.Shown("Drafted a reply for you to read and send yourself." + ("" if found else " Nothing in your FAQ matched, so fill in the answer."),
                        screen.card("text", "Reply draft", "digitalproducts-reply", text=reply))


# ---- Notes to buyers -------------------------------------------------------------------------------

def update_note(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    row = store.product(data, args)
    mine = [v for v in data["versions"] if v["product"] == row["name"]]
    latest = mine[-1] if mine else None
    what = args.get("change") or (latest["change"] if latest else "[what changed]")
    ver = latest["version"] if latest else "[version]"
    text = (f"Hi,\n\nI have updated {row['name']} ({ver}). What is new: {hs.clean(what, 200)}.\n\n"
            "Download the new file the same way you got the first one. If anything looks wrong, just reply.\n\n"
            "Thank you for buying,\n[your name]")
    return screen.Shown("Drafted an update note to send to your buyers yourself.",
                        screen.card("text", f"Update note: {row['name']}"[:80], f"digitalproducts-update-{row['id']}", text=text))


def thanks_note(settings: Settings, args: dict) -> screen.Shown:
    row = store.product(store.load(settings), args)
    text = (f"Thank you for buying {row['name']}!\n\nHow to use it: [one or two lines].\n\nThe licence is in the download. "
            "If you have a question, message me.\n\nIf you enjoy it, an honest review helps other people, but there is "
            "no pressure.\n\n[your name]")
    return screen.Shown("Drafted a thank-you note to go with the download.",
                        screen.card("text", f"Thank-you note: {row['name']}"[:80], f"digitalproducts-thanks-{row['id']}", text=text))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "digitalproducts_copy",
        "description": "Write drafts for selling digital products the user makes (nothing is posted). action: "
                      "listing_draft (product) = titles, description, bullets, FAQ, tags saved / title_options / "
                      "listing_show / listing_check = warns about risky claims and gaps / listing_export = text "
                      "file / tags_make / cover_ideas / faq_draft; licence_terms (kind personal, commercial, "
                      "teacher) / licence_file (kind) in plain words; customer_faq_add (question, answer, product) / "
                      "customer_faq_list / customer_faq_find (question) / customer_faq_remove (id, confirmed only "
                      "after yes) / customer_reply (message, customer) = draft reply from the FAQ; update_note "
                      "(product, change) / thanks_note (product). product is a name or number from the catalogue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "product": {"type": "string"},
                "id": {"type": "integer"},
                "kind": {"type": "string", "enum": list(LICENCES)},
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "message": {"type": "string"},
                "customer": {"type": "string"},
                "change": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"digitalproducts_copy"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"listing_draft": listing_draft, "title_options": title_options, "listing_show": listing_show,
             "listing_check": listing_check, "listing_export": listing_export, "tags_make": tags_make,
             "cover_ideas": cover_ideas, "faq_draft": faq_draft, "licence_terms": licence_terms,
             "licence_file": licence_file, "customer_faq_add": customer_faq_add,
             "customer_faq_list": customer_faq_list, "customer_faq_find": customer_faq_find,
             "customer_faq_remove": customer_faq_remove, "customer_reply": customer_reply,
             "update_note": update_note, "thanks_note": thanks_note}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
