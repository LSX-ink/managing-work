"""The free home page mock-up that goes with every DM and email: a premium, finished-looking concept for the lead.

The owner (23 Oct 2026) saw the old template ("Swap this line for what you do best", wrong services) and said it
wasn't good enough. Rules for this one:
- no placeholder words anywhere: everything is either their real details (name, area, phone, address, Google
  rating and review count) or confident copy that fits their trade
- the right services for the trade, never made-up prices, staff, awards or reviews
- the Kinetic standard: bold type, movement on load and on scroll, works on any phone
"""

import re
from html import escape
from urllib.parse import quote_plus

# Raise this whenever the design gains something: Iris then rebuilds every mock-up already sent out, so what's added
# to one is added to all (owner, 23 Oct 2026).
VERSION = 5

TRADES = {  # trade: (palette (bg, ink, accent, soft), headline, intro, services [(name, line)], book word)
    "barber": (("#0e0d0c", "#f4efe6", "#c9a24d", "#1b1916"),
               "Sharp cuts.<br><em>Every single time.</em>",
               "Precision fades, classic cuts and proper beard work from barbers who take their time with you.",
               [("Skin fades", "Seamless, clean fades blended to suit your head shape and your style."),
                ("Classic cuts", "Scissor and clipper cuts, from a tidy trim to a full restyle."),
                ("Beard sculpting", "Shaped, lined up and finished so it looks right for days."),
                ("Hot towel shave", "The full ritual: hot towels, a straight razor and a smooth finish."),
                ("Kids' cuts", "Patient, quick and smart, so the little ones leave looking sharp."),
                ("Line-ups & designs", "Crisp edges and freehand designs, done properly.")],
               "Book a cut"),
    "hair": (("#f6f1ec", "#1d1716", "#b0785a", "#ebe2da"),
             "Hair you'll<br><em>love to wear.</em>",
             "Cuts, colour and care from stylists who listen first, then make it effortless to look your best.",
             [("Cut & finish", "A cut shaped for you, finished with a blow-dry that lasts."),
              ("Colour", "From subtle gloss to a full change, matched to your skin tone."),
              ("Balayage & highlights", "Soft, natural-looking light that grows out beautifully."),
              ("Treatments", "Repair and shine for hair that's been through a lot."),
              ("Occasion hair", "Weddings, events and nights out, styled to stay put."),
              ("Men's cuts", "Clean, modern cuts and restyles.")],
             "Book an appointment"),
    "beauty": (("#fbf4f2", "#24181b", "#b5476b", "#f3e4e3"),
               "Feel good.<br><em>Look even better.</em>",
               "Treatments that leave you glowing, in a calm space where you can actually switch off.",
               [("Brows & lashes", "Shaped, tinted and lifted to frame your face."),
                ("Nails", "Long-lasting manicures and pedicures, neat every time."),
                ("Facials", "Skin treatments tailored to what your skin needs right now."),
                ("Waxing", "Quick, comfortable and thorough."),
                ("Massage", "Time out for tired muscles and busy minds."),
                ("Bridal & events", "Make-up and prep for the days that matter.")],
               "Book a treatment"),
    "business": (("#0f1115", "#f2f2f0", "#e2b04a", "#1a1d23"),
                 "Brilliant service.<br><em>Easy to book.</em>",
                 "Independent, trusted and proud of the work. Everything you need to know, in one place.",
                 [("What we do", "Our core service, done properly by people who care about it."),
                  ("How it works", "Simple steps from your first message to a job done well."),
                  ("Why us", "Local, reliable and recommended by the people we've worked for."),
                  ("Get in touch", "Call or message and we'll come straight back to you.")],
                 "Get in touch"),
}


def trade_for(p: dict) -> str:
    text = f"{p.get('kind', '')} {p.get('name', '')}".lower()
    if re.search(r"barber|groom|fade|gents|men'?s hair", text):
        return "barber"
    if re.search(r"hair|salon|stylist|wig|braid|loc", text):
        return "hair"
    if re.search(r"beauty|nail|lash|brow|spa|aesthetic|skin|wax", text):
        return "beauty"
    return "business"


def clean_name(p: dict) -> str:
    name = re.split(r"\s+[|\-–]\s+|\s*\|\s*", str(p.get("name") or ""))[0].strip()
    town = str(p.get("town") or "").strip()
    if town and name.lower().endswith(" " + town.lower()):
        name = name[: -len(town) - 1].strip()
    return name or "Your business"


def html_for(p: dict, maker: str = "Kinetic Web Designs", extra: dict | None = None) -> str:
    """extra (from hq/designer.py, all real): photos (paths next to the page), hours, reviews [{author, text,
    rating}], fixes [(their site today, this design)] and fixes_title."""
    e = escape
    trade = trade_for(p)
    (bg, ink, accent, soft), headline, intro, services, book = TRADES[trade]
    brand = (extra or {}).get("brand") or {}  # their own look, read off their website (owner, 23 Oct 2026)
    bg, ink, accent, soft = (brand.get(k) or d for k, d in (("bg", bg), ("ink", ink), ("accent", accent), ("soft", soft)))
    fonts = [f for f in brand.get("fonts") or [] if re.fullmatch(r"[A-Za-z0-9 ]{2,40}", f)][:2]
    head_font = f"'{fonts[0]}',Georgia,serif" if fonts else "'Fraunces',Georgia,serif"
    body_font = f"'{fonts[-1]}',system-ui,sans-serif" if len(fonts) > 1 else "'Inter',system-ui,sans-serif"
    font_link = ("https://fonts.googleapis.com/css2?" + "&".join(
        "family=" + quote_plus(f) + ":wght@400;500;600;700" for f in (fonts + ["Inter"] if len(fonts) == 1 else fonts))
        + "&display=swap") if fonts else (
        "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500"
        "&family=Inter:wght@400;500;600&display=swap")
    logo = brand.get("logo") or ""
    name, town = clean_name(p), str(p.get("town") or "").strip()
    phone = str(p.get("phone") or "").strip()
    tel = re.sub(r"[^\d+]", "", phone)
    address = str(p.get("address") or "").strip()
    rating, reviews = p.get("rating"), int(p.get("reviews") or 0)
    maps = p.get("maps") or ("https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{name} {address or town}"))
    call = f'<a class="btn" href="tel:{e(tel)}">{e(book)}</a>' if tel else f'<a class="btn" href="#visit">{e(book)}</a>'
    stars = ""
    if rating and reviews:
        stars = (f'<div class="rating reveal"><span class="stars">{"★" * round(float(rating))}</span>'
                 f'<b>{float(rating):.1f}</b> from {reviews:,} Google reviews</div>')
    where = f" in {e(town)}" if town else ""
    cards = "".join(f'<article class="card reveal" style="--d:{i * 70}ms"><span class="n">{i + 1:02d}</span>'
                    f'<h3>{e(s)}</h3><p>{e(line)}</p></article>' for i, (s, line) in enumerate(services))
    proof = (f'<section class="proof"><div class="wrap reveal"><p class="big">{float(rating):.1f}<span>/5</span></p>'
             f'<p>Rated by {reviews:,} customers on Google. People don\'t just come back; they bring their friends.</p>'
             f'<a class="link" href="{e(maps)}" target="_blank" rel="noopener">Read the reviews on Google &rarr;</a>'
             f'</div></section>') if rating and reviews else ""
    visit = (f'<p>{e(address)}</p>' if address else f'<p>Right here{where}.</p>') + \
        (f'<p class="phone"><a href="tel:{e(tel)}">{e(phone)}</a></p>' if tel else "")
    marquee = " &middot; ".join(e(s) for s, _ in services) + " &middot; "
    x = extra or {}
    photos = [ph for ph in x.get("photos") or [] if ph][:4]
    gallery = ("<section class='gallery'><div class='wrap'><h2 class='reveal'>Inside " + e(name) + ".</h2><div class='shots'>"
               + "".join(f'<figure class="reveal" style="--d:{i * 90}ms"><img src="{e(ph)}" alt="{e(name)}" loading="lazy"></figure>'
                         for i, ph in enumerate(photos))
               + "</div><p class='credit'>Photos from " + e(name) + "'s Google listing.</p></div></section>") if photos else ""
    hero_img = (f'<div class="hero-photo load"><img src="{e(photos[0])}" alt="" fetchpriority="high"></div>') if photos else ""
    said = [r for r in x.get("reviews") or [] if r.get("text")][:3]
    quotes = ("<section class='quotes'><div class='wrap'><h2 class='reveal'>In their words.</h2><div class='grid'>"
              + "".join(f'<blockquote class="card reveal" style="--d:{i * 80}ms"><span class="stars">{"★" * int(r.get("rating") or 5)}</span>'
                        f'<p>&ldquo;{e(r["text"][:260].rstrip())}{"…" if len(r["text"]) > 260 else ""}&rdquo;</p>'
                        f'<cite>{e(r.get("author") or "Google review")}</cite></blockquote>' for i, r in enumerate(said))
              + "</div></div></section>") if said else ""
    hours = x.get("hours") or []
    hours_html = ("<ul class='hours'>" + "".join(f"<li>{e(h)}</li>" for h in hours[:7]) + "</ul>") if hours else ""
    ba = ("<section class='ba'><div class='wrap'><p class='kicker reveal'>Before and after</p><h2 class='reveal'>"
          "Your website today, and with us.</h2><div class='cmp reveal' style='--x:50%'>"
          f"<img src='{e(x['after'])}' alt='This design on a phone'><div class='b'><img src='{e(x['before'])}' "
          "alt='Your current website on a phone'></div><i class='bar'></i><span class='l'>Today</span>"
          "<span class='r'>This design</span><input type='range' min='0' max='100' value='50' "
          "aria-label='Slide to compare'></div><p class='credit'>Slide to compare. Both shown on a phone.</p></div>"
          "</section>") if x.get("before") and x.get("after") else ""
    speed, ours = x.get("speed"), x.get("design_speed")
    if not (isinstance(speed, int) and speed < 60):  # only worth showing when their site is clearly slow
        speed = None
    if not (isinstance(ours, int) and isinstance(speed, int) and ours >= speed + 15):
        ours = None
    speed_html = (f"<div class='speed reveal'><div><b>{int(speed)}</b><span>/100</span><p>Your site's Google speed score "
                  f"on phones today</p></div>" + (f"<div class='ours'><b>{int(ours)}</b><span>/100</span><p>This design, "
                  f"tested the same way</p></div>" if ours else "") + "</div>") if isinstance(speed, int) else ""
    fixes = x.get("fixes") or []
    fix_html = (f"<section class='fixes'><div class='wrap'><p class='kicker reveal'>A note for {e(name)} from {e(maker)}</p><h2 class='reveal'>"
                + e(x.get("fixes_title") or "Built to win you more customers.") + "</h2>" + speed_html + "<div class='rows'>"
                + "".join(f'<div class="row reveal" style="--d:{i * 70}ms"><div><span>Today</span><p>{e(a)}</p></div>'
                          f'<div><span>This design</span><p>{e(b)}</p></div></div>' for i, (a, b) in enumerate(fixes[:5]))
                + "</div></div></section>") if (fixes or speed_html) else ""
    return f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{e(name)}{where} | concept home page</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{e(font_link)}" rel="stylesheet" media="print" onload="this.media='all'">
<style>
:root{{--bg:{bg};--ink:{ink};--accent:{accent};--soft:{soft};--on:{brand.get('on_accent') or bg};--head:{head_font};--body:{body_font}}}
*{{box-sizing:border-box;margin:0}}html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--ink);font:16px/1.6 var(--body);-webkit-font-smoothing:antialiased;overflow-x:hidden;overflow-wrap:break-word}}
a{{color:inherit}}.wrap{{max-width:1120px;margin:0 auto;padding:0 22px}}
nav{{position:sticky;top:0;z-index:5;backdrop-filter:blur(12px);background:color-mix(in srgb,var(--bg) 80%,transparent);border-bottom:1px solid color-mix(in srgb,var(--ink) 10%,transparent)}}
nav .wrap{{display:flex;justify-content:space-between;align-items:center;height:68px;gap:14px}}
.logo{{font-family:var(--head);font-weight:700;font-size:1.3rem;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.logo i{{color:var(--accent);font-style:normal}}.logo{{display:flex;align-items:center;gap:10px}}.mark{{height:38px;width:auto;max-width:120px;object-fit:contain}}.mark.pill{{background:var(--accent);padding:6px 12px;border-radius:12px;height:46px}}
.btn{{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:var(--on);padding:14px 26px;border-radius:999px;text-decoration:none;font-weight:600;
transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s;box-shadow:0 10px 30px -12px var(--accent)}}.btn:hover{{transform:translateY(-2px)}}
nav .btn{{padding:10px 18px;font-size:.92rem}}
.hero{{position:relative;min-height:calc(100svh - 68px);display:grid;align-items:center;padding:60px 0 90px;isolation:isolate;overflow:hidden}}.hero .wrap{{width:100%}}
.hero::before{{content:"";position:absolute;inset:-20% -10% auto auto;width:70vmax;height:70vmax;border-radius:50%;z-index:-1;
background:radial-gradient(circle,color-mix(in srgb,var(--accent) 34%,transparent),transparent 62%);animation:drift 14s ease-in-out infinite alternate}}
@keyframes drift{{to{{transform:translate(-8vw,6vh) scale(1.08)}}}}
.kicker{{text-transform:uppercase;letter-spacing:.22em;font-size:.78rem;font-weight:600;color:var(--accent);margin-bottom:22px}}
h1{{font-family:var(--head);font-weight:500;font-size:clamp(2.8rem,8.4vw,6.4rem);line-height:.98;letter-spacing:-.03em;max-width:12ch}}
h1 em{{font-style:italic;color:var(--accent)}}
.lead{{font-size:clamp(1.05rem,2vw,1.25rem);max-width:46ch;opacity:.82;margin:26px 0 34px}}
.rating{{display:inline-flex;gap:10px;align-items:center;margin-top:34px;padding:10px 16px;border-radius:999px;border:1px solid color-mix(in srgb,var(--ink) 16%,transparent);font-size:.95rem}}
.stars{{color:var(--accent);letter-spacing:2px}}
.load{{opacity:0;transform:translateY(24px);animation:up .9s cubic-bezier(.2,.8,.2,1) forwards}}
.hero-photo.load{{animation-delay:.3s}}.load:nth-child(2){{animation-delay:.12s}}.load:nth-child(3){{animation-delay:.24s}}.load:nth-child(4){{animation-delay:.36s}}.load:nth-child(5){{animation-delay:.48s}}
@keyframes up{{to{{opacity:1;transform:none}}}}
.marquee{{border-block:1px solid color-mix(in srgb,var(--ink) 12%,transparent);overflow:hidden;white-space:nowrap;padding:18px 0;font-family:var(--head);font-size:1.5rem}}
.marquee div{{display:inline-block;animation:slide 26s linear infinite}}@keyframes slide{{to{{transform:translateX(-50%)}}}}
section{{padding:110px 0}}h2{{font-family:var(--head);font-weight:500;font-size:clamp(2rem,5vw,3.4rem);letter-spacing:-.02em;line-height:1.05;max-width:16ch;margin-bottom:48px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}}
.card{{background:var(--soft);border-radius:22px;padding:30px;border:1px solid color-mix(in srgb,var(--ink) 8%,transparent);transition:transform .35s cubic-bezier(.2,.8,.2,1)}}
.card:hover{{transform:translateY(-6px)}}.card .n{{font-size:.8rem;letter-spacing:.2em;color:var(--accent);font-weight:600}}
.card h3{{font-family:var(--head);font-weight:500;font-size:1.5rem;margin:14px 0 8px}}.card p{{opacity:.75}}
.proof{{background:var(--accent);color:var(--on)}}.proof .big{{font-family:var(--head);font-size:clamp(5rem,16vw,10rem);line-height:.9}}
.proof .big span{{font-size:.35em;opacity:.7}}.proof p{{font-size:1.25rem;max-width:40ch;margin-top:14px}}.link{{display:inline-block;margin-top:22px;font-weight:600}}
#visit .wrap{{display:grid;grid-template-columns:1.2fr 1fr;gap:40px;align-items:end}}#visit p{{font-size:1.15rem;opacity:.85}}.phone a{{font-family:var(--head);font-size:2rem;text-decoration:none}}
footer{{padding:34px 0;font-size:.82rem;opacity:.55;border-top:1px solid color-mix(in srgb,var(--ink) 10%,transparent)}}
.js .reveal{{opacity:0;transform:translateY(30px);transition:opacity .8s,transform .8s cubic-bezier(.2,.8,.2,1);transition-delay:var(--d,0ms)}}.js .reveal.in{{opacity:1;transform:none}}
.hero.has-photo .wrap{{display:grid;grid-template-columns:1.15fr .85fr;gap:48px;align-items:center}}
.hero-photo{{border-radius:28px;overflow:hidden;aspect-ratio:4/5;box-shadow:0 40px 80px -30px rgba(0,0,0,.6);transform:rotate(1.5deg)}}
.hero-photo img,.shots img{{width:100%;height:100%;object-fit:cover;display:block}}
.shots{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.shots figure{{margin:0;border-radius:18px;overflow:hidden;aspect-ratio:1}}
.credit{{font-size:.8rem;opacity:.55;margin-top:14px}}
blockquote.card{{margin:0}}blockquote p{{font-size:1.05rem;margin:12px 0 16px;opacity:.9}}blockquote cite{{font-style:normal;font-weight:600;opacity:.7}}
.hours{{list-style:none;padding:0;margin:18px 0 0;columns:2;gap:24px;font-size:.98rem;opacity:.85}}.hours li{{padding:3px 0;break-inside:avoid}}
.cmp{{position:relative;max-width:400px;aspect-ratio:390/760;border-radius:30px;overflow:hidden;margin:0 auto;
box-shadow:0 40px 80px -30px rgba(0,0,0,.55);border:8px solid #0b0b0b}}
.cmp img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:top}}
.cmp .b{{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--x)) 0 0)}}
.cmp .bar{{position:absolute;top:0;bottom:0;left:var(--x);width:3px;margin-left:-1.5px;background:var(--accent);box-shadow:0 0 18px var(--accent)}}
.cmp .bar::after{{content:"\\2194";position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:42px;height:42px;
border-radius:50%;background:var(--accent);color:var(--bg);display:grid;place-items:center;font-size:20px;font-style:normal}}
.cmp span{{position:absolute;top:14px;padding:5px 12px;border-radius:999px;font-size:.75rem;font-weight:600;background:rgba(0,0,0,.65);color:#fff}}
.cmp .l{{left:14px}}.cmp .r{{right:14px}}.cmp input{{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:ew-resize;margin:0}}
.ba .credit{{text-align:center}}.ba h2{{margin-left:auto;margin-right:auto;text-align:center}}.ba .kicker{{text-align:center}}
.speed{{display:flex;gap:16px;flex-wrap:wrap;margin:0 0 28px}}.speed>div{{flex:1 1 240px;border-radius:22px;padding:26px;background:var(--bg)}}
.speed b{{font-family:var(--head);font-size:4.4rem;line-height:1;font-weight:500;color:#d64545}}.speed .ours b{{color:#2f9e63}}
.speed span{{font-size:1.2rem;opacity:.6}}.speed p{{margin-top:8px;opacity:.75}}
.fixes{{background:var(--soft)}}.rows{{display:grid;gap:14px}}
.row{{display:grid;grid-template-columns:1fr 1fr;border-radius:20px;overflow:hidden;border:1px solid color-mix(in srgb,var(--ink) 10%,transparent)}}
.row>div{{padding:22px 24px}}.row>div:first-child{{opacity:.72}}.row>div:last-child{{background:color-mix(in srgb,var(--accent) 16%,var(--bg))}}
.row span{{display:block;text-transform:uppercase;letter-spacing:.18em;font-size:.72rem;font-weight:600;color:var(--accent);margin-bottom:6px}}
@media (max-width:760px){{#visit .wrap,.hero.has-photo .wrap,.row{{grid-template-columns:1fr}}.hero-photo{{aspect-ratio:4/3;transform:none}}.hours{{columns:1}}nav .btn{{display:none}}section{{padding:80px 0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}.load,.reveal{{opacity:1;transform:none}}}}
</style></head><body>
<nav><div class="wrap"><span class="logo">{(f'<img src="{e(logo)}" alt="{e(name)}" class="mark{" pill" if brand.get("logo_pill") else ""}">' if logo else f"{e(name)}<i>.</i>")}</span>{call}</div></nav>
<header class="hero{' has-photo' if photos else ''}"><div class="wrap"><div>
<p class="kicker load">{e(name)}{where}</p>
<h1 class="load">{headline}</h1>
<p class="lead load">{e(intro)}</p>
<div class="load">{call}</div>
<div class="load">{stars}</div>
</div>{hero_img}</div></header>
<div class="marquee" aria-hidden="true"><div>{marquee * 4}</div></div>
<section id="services"><div class="wrap"><h2 class="reveal">What we do best.</h2><div class="grid">{cards}</div></div></section>
{gallery}
{proof}
{quotes}
{ba}
{fix_html}
<section id="visit"><div class="wrap"><div><h2 class="reveal">Come and see us.</h2>{visit}{hours_html}</div>
<div class="reveal">{call}<p style="margin-top:16px"><a class="link" href="{e(maps)}" target="_blank" rel="noopener">Get directions &rarr;</a></p></div></div></section>
<footer><div class="wrap">A free concept home page for {e(name)}, designed by {e(maker)}. Not the live site.</div></footer>
<script>
document.documentElement.classList.add('js');
const io=new IntersectionObserver(es=>es.forEach(x=>{{if(x.isIntersecting){{x.target.classList.add('in');io.unobserve(x.target)}}}}),{{threshold:.12}});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
document.querySelectorAll('.cmp').forEach(c=>{{const r=c.querySelector('input');const set=v=>{{c.style.setProperty('--x',v+'%');r.value=v}};
r.addEventListener('input',()=>set(r.value));
new IntersectionObserver((es,o)=>{{if(es[0].isIntersecting){{o.disconnect();let t=0;const s=()=>{{t+=.02;set(50+38*Math.sin(t*Math.PI));if(t<2)requestAnimationFrame(s);else set(50)}};setTimeout(s,500)}}}},{{threshold:.4}}).observe(c)}});
</script>
</body></html>
"""
