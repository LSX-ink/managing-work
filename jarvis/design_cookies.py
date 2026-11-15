"""Cookie banners: the "can we use cookies?" bar a UK or EU client site needs, done the fair way, in the brand colours.

make_cookie_banner writes one paste-in block (HTML, CSS and a little JavaScript, no outside libraries) that follows
what the UK ICO and EU rules ask for: "Accept all" and "Reject all" are the same size and equally easy, nothing but
strictly necessary cookies runs until the visitor says yes, each kind (analytics, marketing, preferences) can be
switched on separately under "Choose", and a small "Cookie settings" link lets people change their mind later. Scripts
are held back by writing them as <script type="text/plain" data-cookies="analytics"> and they only run once that kind
is allowed. The choice is remembered for 6 months (in the visitor's browser), the banner is keyboard and screen-reader
friendly (a labelled region, focus moves to it, real buttons and checkboxes) and every colour pair passes WCAG AA.
Saves cookie-banner.html (the block plus a how-to at the top) and cookie-demo.html (a page to try it) in
Kinetic Web Designs/<name>/web. This is not legal advice; the client's privacy page still has to list their cookies.
"""

import html
import re

import memory
from config import Settings
from design_contrast import AA, colour, fix, ratio
from design_extract import FOLDER
from design_palette import on

NAMES = {"make_cookie_banner"}
KINDS = {
    "analytics": ("Analytics", "Helps us see which pages people use, so we can improve the site."),
    "marketing": ("Marketing", "Lets ads and social media show you things you may like."),
    "preferences": ("Preferences", "Remembers choices such as language or region."),
}
POSITIONS = ("bottom", "corner")


def css(brand: str, position: str) -> str:
    paper, ink, muted = "#ffffff", "#18181b", "#52525b"
    button = brand if ratio(on(brand), brand) >= AA else fix(brand, on(brand), AA)
    accent = brand if ratio(brand, paper) >= AA else fix(brand, paper, AA)
    place = ("left: 16px; right: 16px; bottom: 16px; max-width: 960px; margin: 0 auto;" if position == "bottom"
             else "right: 16px; bottom: 16px; left: 16px; max-width: 420px; margin-left: auto;")
    return f"""<style>
  .ck {{ position: fixed; {place} z-index: 2147483000; background: {paper}; color: {ink};
        border: 1px solid #e4e4e7; border-radius: 16px; box-shadow: 0 12px 40px rgb(0 0 0 / .18); padding: 20px;
        font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  .ck:focus {{ outline: none; }}
  .ck[hidden], .ck [hidden] {{ display: none !important; }}
  .ck h2 {{ font-size: 17px; margin: 0 0 6px; }}
  .ck p {{ margin: 0 0 14px; color: {muted}; }}
  .ck a {{ color: {accent}; }}
  .ck-row {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .ck button {{ flex: 1 1 140px; min-height: 44px; padding: 10px 16px; border-radius: 10px; font: inherit;
               font-weight: 650; cursor: pointer; border: 2px solid {button}; }}
  .ck .ck-yes, .ck .ck-no {{ background: {button}; color: {on(button)}; }}
  .ck .ck-pick {{ background: {paper}; color: {accent}; border-color: {accent}; }}
  .ck button:focus-visible, .ck input:focus-visible, .ck-open:focus-visible {{ outline: 3px solid {accent};
               outline-offset: 2px; }}
  .ck fieldset {{ border: 0; margin: 0 0 14px; padding: 0; }}
  .ck label {{ display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-top: 1px solid #f4f4f5; }}
  .ck input {{ width: 20px; height: 20px; margin-top: 2px; accent-color: {accent}; flex: none; }}
  .ck small {{ display: block; color: {muted}; }}
  .ck-open {{ position: fixed; left: 12px; bottom: 12px; z-index: 2147482999; background: {paper}; color: {accent};
             border: 1px solid #e4e4e7; border-radius: 999px; padding: 8px 14px; font: 600 13px system-ui,
             sans-serif; cursor: pointer; }}
  @media (prefers-reduced-motion: no-preference) {{ .ck {{ animation: ck-in .25s ease-out; }} }}
  @keyframes ck-in {{ from {{ opacity: 0; transform: translateY(12px); }} }}
</style>"""


def block(name: str, brand: str, kinds: list[str], policy: str, position: str) -> str:
    e = html.escape
    boxes = "\n".join(
        f'      <label><input type="checkbox" data-kind="{k}"><span><strong>{KINDS[k][0]}</strong>'
        f"<small>{KINDS[k][1]}</small></span></label>" for k in kinds)
    more = f' <a href="{e(policy)}">Cookie policy</a>' if policy else ""
    return f"""{css(brand, position)}
<section class="ck" id="ck" role="region" aria-labelledby="ck-title" tabindex="-1" hidden>
  <h2 id="ck-title">Cookies on {e(name)}</h2>
  <p>We use cookies that the site needs to work. With your OK we'd also like to use optional ones; press Choose to
     pick which. You can change your mind at any time.{more}</p>
  <fieldset id="ck-pick" hidden>
    <legend class="ck-sr" style="position:absolute;left:-9999px">Optional cookies</legend>
      <label><input type="checkbox" checked disabled><span><strong>Strictly necessary</strong>
      <small>Keeps the site working and secure. Always on.</small></span></label>
{boxes}
  </fieldset>
  <div class="ck-row">
    <button type="button" class="ck-yes" data-ck="all">Accept all</button>
    <button type="button" class="ck-no" data-ck="none">Reject all</button>
    <button type="button" class="ck-pick" data-ck="pick" aria-expanded="false" aria-controls="ck-pick">Choose</button>
  </div>
</section>
<button type="button" class="ck-open" id="ck-open" hidden>Cookie settings</button>
<script>
(() => {{
  const KEY = "cookie-choice", KINDS = {kinds!r}, MONTHS = 6;
  const box = document.getElementById("ck"), pick = document.getElementById("ck-pick");
  const open = document.getElementById("ck-open"), more = box.querySelector('[data-ck="pick"]');
  const read = () => {{
    try {{
      const c = JSON.parse(localStorage.getItem(KEY));
      return c && c.until > Date.now() ? c : null;
    }} catch (e) {{ return null; }}
  }};
  const run = (allowed) => {{
    document.querySelectorAll('script[type="text/plain"][data-cookies]').forEach((old) => {{
      if (!allowed.includes(old.dataset.cookies) || old.dataset.ran) return;
      const s = document.createElement("script");
      for (const a of old.attributes) if (!["type", "data-cookies"].includes(a.name)) s.setAttribute(a.name, a.value);
      s.text = old.text;
      old.dataset.ran = "1";
      old.after(s);
    }});
  }};
  const save = (allowed) => {{
    const until = Date.now() + MONTHS * 30 * 24 * 3600 * 1000;
    try {{ localStorage.setItem(KEY, JSON.stringify({{ allowed, until }})); }} catch (e) {{}}
    box.hidden = true;
    open.hidden = false;
    run(allowed);
    document.dispatchEvent(new CustomEvent("cookies-chosen", {{ detail: {{ allowed }} }}));
  }};
  const show = () => {{
    const c = read();
    pick.querySelectorAll("input[data-kind]").forEach((i) => (i.checked = !!c && c.allowed.includes(i.dataset.kind)));
    box.hidden = false;
    open.hidden = true;
    box.focus();
  }};
  box.addEventListener("click", (ev) => {{
    const what = ev.target.dataset.ck;
    if (what === "all") save(KINDS);
    if (what === "none") save([]);
    if (what === "pick") {{
      if (pick.hidden) {{
        pick.hidden = false;
        more.setAttribute("aria-expanded", "true");
        more.textContent = "Save choices";
      }} else {{
        save([...pick.querySelectorAll("input[data-kind]:checked")].map((i) => i.dataset.kind));
      }}
    }}
  }});
  open.addEventListener("click", show);
  const c = read();
  if (c) {{ open.hidden = false; run(c.allowed); }} else {{ show(); }}
}})();
</script>"""


def run(settings: Settings, args: dict) -> str:
    clean = lambda v: " ".join(str(v or "").split())  # noqa: E731
    name = clean(args.get("name"))
    if not name:
        raise ValueError("Give the business name for the cookie banner.")
    brand = colour(args.get("colour") or "")
    kinds = [k.lower() for k in (args.get("kinds") or ["analytics"])]
    bad = [k for k in kinds if k not in KINDS]
    if bad or not kinds:
        raise ValueError(f"Cookie kinds can be {', '.join(KINDS)}.")
    kinds = list(dict.fromkeys(kinds))
    policy = clean(args.get("policy_url"))
    if policy and not re.match(r"^(https://[^\s\"'<>]+|/[^\s\"'<>]*)$", policy):
        raise ValueError("Give the cookie policy as a https:// address or a path like /cookies.")
    position = clean(args.get("position")).lower() or "bottom"
    if position not in POSITIONS:
        raise ValueError(f"Position can be {' or '.join(POSITIONS)}.")
    code = block(name, brand, kinds, policy, position)
    how = (f"<!-- Cookie banner for {html.escape(name)}. Paste everything below just before </body> on every page.\n"
           "     Hold back any script that sets optional cookies by changing its opening tag, e.g. Google Analytics:\n"
           '       <script type="text/plain" data-cookies="analytics" async\n'
           '               src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script>\n'
           f"     Kinds on this site: {', '.join(kinds)}. Scripts run only after the visitor allows that kind.\n"
           "     Not legal advice: list the cookies the site really uses on its privacy or cookie page. -->\n")
    demo = (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{html.escape(name)} | Cookie banner demo</title>\n</head>\n<body style=\"font-family:system-ui;"
            "padding:24px\">\n<h1>Cookie banner demo</h1>\n<p id=\"state\">Analytics: not running.</p>\n"
            "<script type=\"text/plain\" data-cookies=\"analytics\">document.getElementById('state').textContent = "
            "'Analytics: running.';</script>\n"
            "<p>Clear this site's storage to see the banner again.</p>\n" + code + "\n</body>\n</html>\n")
    (memory.root(settings) / FOLDER).mkdir(parents=True, exist_ok=True)
    path = memory.folder(settings, f"{FOLDER}/{memory.safe_name(name, 'folder name')}/web", create=True)
    (path / "cookie-banner.html").write_text(how + code + "\n", encoding="utf-8")
    (path / "cookie-demo.html").write_text(demo, encoding="utf-8")
    where = path.relative_to(memory.root(settings)).as_posix()
    return (f"Made a cookie banner for {name} in {where}: cookie-banner.html to paste before </body> on every page, "
            f"and cookie-demo.html to try it. Accept and Reject are equally easy, optional cookies "
            f"({', '.join(kinds)}) wait for a yes, and a 'Cookie settings' button lets visitors change their mind. "
            "Change each optional script's tag to type=\"text/plain\" data-cookies=\"<kind>\" as the note at the top "
            "shows. It isn't legal advice: the client's cookie page must still list what the site uses.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "make_cookie_banner",
        "description": "Make a fair, accessible cookie consent banner for a UK/EU client site in the brand colour: "
                       "equal Accept all and Reject all buttons, Choose per kind (analytics, marketing, "
                       "preferences), optional scripts held back until allowed, a Cookie settings button to change "
                       "it later, remembered 6 months, no outside libraries. Saves cookie-banner.html (paste-in) and "
                       "cookie-demo.html in Kinetic Web Designs/<name>/web. Answer in plain words.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Business name (banner title and folder)."},
                "colour": {"type": "string", "description": "Brand colour, e.g. '#c2410c'."},
                "kinds": {"type": "array", "items": {"type": "string", "enum": list(KINDS)},
                          "description": "Optional cookie kinds the site uses (default analytics)."},
                "policy_url": {"type": "string", "description": "Cookie policy page, https://... or /cookies."},
                "position": {"type": "string", "enum": list(POSITIONS), "description": "Default bottom bar."},
            },
            "required": ["name", "colour"],
            "additionalProperties": False,
        },
    }]


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    try:
        return run(settings, args)
    except (TypeError, ValueError) as e:
        return str(e)
