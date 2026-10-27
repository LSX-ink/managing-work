"""Premium mock-up for barbers, salons and other walk-in businesses (owner, 26 Oct 2026: "websites don't move, there
isn't any extravagance ... match the company, a deep dive into their website plus Instagram ... don't use credits").

Everything moves with code alone (no AI video, no credits): a logo intro, a Ken Burns hero made from their own photos
with drifting gold dust, headline lines rising in, a services marquee, arch-masked parallax photos, a tabbed price
menu, a shimmering VIP card, a draggable gallery, auto-scrolling reviews, counters, a magnetic cursor glow and a
sticky booking button. Colours, logo, prices, hours and words all come from the business's own website, Instagram
and Google listing, written into config.json by hand after the deep dive.

config.json: {"name", "short", "kicker", "h1": [line, line, italic line], "lead", "colours": {"bg", "panel", "ink",
"muted", "gold", "second" (optional second brand colour, e.g. their uniform)}, "motif": "moroccan" | "classic", "logo": "logo.png", "hero": [photos], "experience": {"title",
"text", "photos": [2]}, "services": [{"group", "items": [[name, price]]}], "special": {"kicker", "title", "text",
"cta"}, "gallery": [photos], "reviews": [[text, author]], "stats": [[value, label]], "hours": [[day, time]],
"address", "phone", "whatsapp", "email", "loc": [lat, lng], "instagram", "currency_note"}

Usage: python premium_page.py <source folder with config.json and photos> <site folder>"""
import json, shutil, sys
from html import escape as e
from pathlib import Path

from PIL import Image


def slim(src: Path, dst: Path, width: int = 1600) -> None:
    im = Image.open(src).convert("RGB")
    im.thumbnail((width, width)); dst.parent.mkdir(parents=True, exist_ok=True); im.save(dst, quality=82, optimize=True)


def zellige(gold: str) -> str:
    """A Moroccan eight-point star tile as an inline SVG data URI (for the 'moroccan' motif)."""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'><g fill='none' stroke='{gold}' "
           "stroke-opacity='.16' stroke-width='1'><path d='M40 6 L49 31 L74 40 L49 49 L40 74 L31 49 L6 40 L31 31 Z'/>"
           "<rect x='22' y='22' width='36' height='36' transform='rotate(45 40 40)'/><circle cx='40' cy='40' r='6'/></g></svg>")
    return "url(\"data:image/svg+xml," + svg.replace("#", "%23").replace("<", "%3C").replace(">", "%3E") + "\")"


def build(src: Path, out: Path) -> None:
    c = json.load(open(src / "config.json", encoding="utf-8"))
    col = c["colours"]
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):  # a fresh page each time (their old mock-up files go)
        if old.is_file():
            old.unlink()
    if (out / "p").exists():
        shutil.rmtree(out / "p")
    photos = {}
    def ph(f):
        if f not in photos:
            name = f"p/{len(photos):02d}.jpg"; slim(src / f, out / name); photos[f] = name
        return photos[f]
    logo = ""
    if c.get("logo"):
        im = Image.open(src / c["logo"]).convert("RGBA"); im.thumbnail((420, 420))
        if c.get("logo_light"):  # a dark logo on a dark page: knock out a white background, then paint it in the ink colour
            tone = col.get("text", col["ink"]) if c.get("layout") == "editorial" else col["ink"]  # dark logo on the light editorial page
            ink = tuple(int(tone[i:i + 2], 16) for i in (1, 3, 5))
            white_bg = im.getpixel((1, 1))[3] > 200 and min(im.getpixel((1, 1))[:3]) > 235
            px = [(*ink, 0 if (white_bg and r > 235 and g > 235 and b > 235) else a) for r, g, b, a in im.getdata()]
            im.putdata(px)
        im = im.crop(im.getbbox() or (0, 0, *im.size)); im.save(out / "logo.png"); logo = "logo.png"
    hero = [ph(f) for f in c["hero"]]
    exp = [ph(f) for f in c["experience"]["photos"]]
    gal = [ph(f) for f in c["gallery"]]
    pattern = zellige(col["gold"]) if c.get("motif") == "moroccan" else "none"
    h1 = c["h1"]
    tabs = "".join(f'<button type="button" class="tab{" on" if not i else ""}" data-i="{i}">{e(g["group"])}</button>' for i, g in enumerate(c["services"]))
    menus = "".join(f'<ul class="menu{" on" if not i else ""}" data-i="{i}">' + "".join(
        f'<li style="--d:{j * 60}ms"><span>{e(n)}</span>' + (f'<i></i><b>{e(p)}</b>' if p else '') + '</li>' for j, (n, p) in enumerate(g["items"])) + "</ul>"
        for i, g in enumerate(c["services"]))
    marquee = " &nbsp;✦&nbsp; ".join(e(n) for g in c["services"] for n, _ in g["items"][:4])
    reviews = "".join(f'<figure class="rev"><div class="stars">★★★★★</div><blockquote>{e(t)}</blockquote><figcaption>{e(a)}</figcaption></figure>' for t, a in c["reviews"])
    stats = "".join(f'<div><b data-to="{e(v)}">{e(v)}</b><span>{e(l)}</span></div>' for v, l in c["stats"])
    hours = "".join(f"<li><span>{e(d)}</span><b>{e(t)}</b></li>" for d, t in c["hours"])
    lat, lng = c["loc"]
    book = c.get("book_url") or (f"https://wa.me/{c['whatsapp']}" if c.get("whatsapp") else f"tel:{c['phone'].replace(' ', '')}")
    book_label = c.get("book_label") or ("Book on WhatsApp" if c.get("whatsapp") else "Call to book")
    sp = c.get("special") or None
    special = (f'<section class="vip"><div class="wrap"><div class="card rv"><p class="kick">{e(sp["kicker"])}</p><h2>{e(sp["title"])}</h2>'
               f'<p>{e(sp["text"])}</p><a class="btn mag" href="#visit">{e(sp["cta"])}</a></div></div></section>') if sp else ""
    from layouts import FONTS, LAYOUTS
    if c.get("layout") in LAYOUTS:  # a different design per business (owner, 26 Oct 2026)
        html = LAYOUTS[c["layout"]]({"c": c, "col": col, "logo": logo, "hero": hero, "exp": exp, "gal": gal, "book": book, "book_label": book_label,
                                       "lat": lat, "lng": lng, "fonts": FONTS[c.get("fonts", c["layout"])]})
        from compare import add as add_compare; html = add_compare(html, c, src, out)
        (out / "index.html").write_text(html, encoding="utf-8")
        print("written", c["layout"], len(html) // 1024, "KB,", len(photos), "photos")
        return
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(c['name'])} | concept website</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600&family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:{col['bg']};--panel:{col['panel']};--ink:{col['ink']};--muted:{col['muted']};--gold:{col['gold']};--two:{col.get('second', col['gold'])};--line:color-mix(in srgb,var(--gold) 22%,transparent);
--head:"Cinzel",Georgia,serif;--serif:"Cormorant Garamond",Georgia,serif;--body:"Manrope",system-ui,sans-serif}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--body);overflow-x:hidden}}
body::before{{content:"";position:fixed;inset:0;background-image:{pattern};pointer-events:none;z-index:0}}
img{{max-width:100%;display:block}}a{{color:inherit}}.wrap{{width:min(1180px,100% - 40px);margin:0 auto;position:relative;z-index:1}}
.kick{{font:600 .72rem var(--body);letter-spacing:.34em;text-transform:uppercase;color:var(--two);margin:0 0 14px}}
h2{{font:500 clamp(2rem,4.6vw,3.6rem)/1.05 var(--head);margin:0 0 18px;letter-spacing:.02em}}
.btn{{display:inline-flex;align-items:center;gap:10px;padding:15px 28px;border-radius:999px;background:var(--gold);color:#14110d;font:700 .82rem var(--body);letter-spacing:.14em;text-transform:uppercase;text-decoration:none;border:0;cursor:pointer;transition:transform .25s,box-shadow .25s;box-shadow:0 10px 40px color-mix(in srgb,var(--gold) 35%,transparent)}}
.btn.ghost{{background:transparent;color:var(--ink);border:1px solid var(--two);box-shadow:none}}
/* intro */
#intro{{position:fixed;inset:0;z-index:50;background:var(--bg);display:grid;place-items:center;transition:clip-path 1.1s cubic-bezier(.7,0,.2,1);clip-path:inset(0 0 0 0)}}
#intro.go{{clip-path:inset(0 0 100% 0)}}#intro img{{width:min(170px,40vw);opacity:0;transform:scale(.86);animation:logo 1.4s .2s forwards}}
#intro p{{position:absolute;bottom:18vh;font:500 .8rem var(--head);letter-spacing:.5em;color:var(--gold);opacity:0;animation:fade 1s .9s forwards}}
@keyframes logo{{to{{opacity:1;transform:none;filter:drop-shadow(0 0 30px color-mix(in srgb,var(--gold) 45%,transparent))}}}}@keyframes fade{{to{{opacity:1}}}}
/* nav */
nav{{position:fixed;top:0;left:0;right:0;z-index:20;transition:background .4s,padding .4s;padding:22px 0}}nav.solid{{background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(12px);padding:12px 0;border-bottom:1px solid var(--line)}}
nav .wrap{{display:flex;align-items:center;justify-content:space-between;gap:20px}}nav .brand{{display:flex;align-items:center;gap:12px;text-decoration:none;font:600 .9rem var(--head);letter-spacing:.18em}}
nav .brand img{{height:44px;width:auto}}nav .links{{display:flex;gap:26px;font-size:.86rem}}nav .links a{{text-decoration:none;opacity:.8}}nav .links a:hover{{opacity:1;color:var(--gold)}}
/* hero */
.hero{{position:relative;height:100svh;min-height:640px;overflow:hidden;display:grid;align-items:end}}
.hero .slide{{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.12);transition:opacity 1.6s ease}}
.hero .slide.on{{opacity:1;animation:kb 9s linear forwards}}@keyframes kb{{from{{transform:scale(1.14) translate(1%,1%)}}to{{transform:scale(1.02) translate(-1%,-1%)}}}}
.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35),rgba(0,0,0,.15) 40%,var(--bg) 98%),radial-gradient(ellipse at 20% 80%,rgba(0,0,0,.55),transparent 60%)}}
#dust{{position:absolute;inset:0;z-index:1;pointer-events:none}}
.hero .wrap{{z-index:2;padding-bottom:12vh}}.hero h1{{font:500 clamp(2.6rem,7.4vw,6.4rem)/.98 var(--head);margin:0 0 22px;letter-spacing:.01em}}
.hero h1 span{{display:block;overflow:hidden}}.hero h1 span i{{display:block;font-style:normal;transform:translateY(110%);transition:transform 1.1s cubic-bezier(.2,.8,.2,1)}}
.hero h1 span:nth-child(3) i{{font:italic 500 1.08em var(--serif);color:var(--gold)}}.ready .hero h1 span i{{transform:none}}
.ready .hero h1 span:nth-child(2) i{{transition-delay:.12s}}.ready .hero h1 span:nth-child(3) i{{transition-delay:.24s}}
.hero .lead{{max-width:560px;color:color-mix(in srgb,var(--ink) 82%,transparent);margin:0 0 30px;opacity:0;transform:translateY(20px);transition:1s .5s}}
.hero .cta{{display:flex;gap:14px;flex-wrap:wrap;opacity:0;transform:translateY(20px);transition:1s .65s}}.ready .hero .lead,.ready .hero .cta{{opacity:1;transform:none}}
.hero .rating{{position:absolute;right:max(20px,calc((100% - 1180px)/2));bottom:12vh;z-index:2;text-align:right;font:500 .8rem var(--body);letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}}
.hero .rating b{{display:block;font:500 3.4rem/1 var(--head);color:var(--gold);letter-spacing:0}}
.cue{{position:absolute;left:50%;bottom:26px;z-index:2;width:1px;height:54px;background:linear-gradient(var(--gold),transparent);animation:cue 2s infinite}}@keyframes cue{{0%{{transform:scaleY(0);transform-origin:top}}50%{{transform:scaleY(1);transform-origin:top}}51%{{transform-origin:bottom}}100%{{transform:scaleY(0);transform-origin:bottom}}}}
/* marquee */
.marquee{{border-block:1px solid var(--line);overflow:hidden;padding:20px 0;position:relative;z-index:1;background:var(--panel)}}.marquee div{{display:flex;width:max-content;animation:mq 38s linear infinite;font:500 1.3rem var(--serif);font-style:italic;color:var(--gold);white-space:nowrap}}
.marquee span{{padding-right:40px}}@keyframes mq{{to{{transform:translateX(-50%)}}}}
section{{padding:130px 0;position:relative}}
/* experience */
.exp .wrap{{display:grid;grid-template-columns:1.05fr 1fr;gap:70px;align-items:center}}.exp p{{color:var(--muted);max-width:520px}}
.arches{{position:relative;height:620px}}.arch{{position:absolute;overflow:hidden;border-radius:999px 999px 18px 18px;border:1px solid var(--line);box-shadow:0 30px 80px rgba(0,0,0,.45)}}
.arch img{{width:100%;height:120%;object-fit:cover;will-change:transform}}.arch.a{{width:62%;height:88%;left:0;top:0}}.arch.b{{width:46%;height:62%;right:0;bottom:0}}
/* services */
.svc{{background:var(--panel)}}.svc .head{{display:flex;justify-content:space-between;align-items:end;gap:30px;flex-wrap:wrap;margin-bottom:40px}}
.tabs{{display:flex;gap:10px;flex-wrap:wrap}}.tab{{padding:11px 20px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--ink);font:600 .78rem var(--body);letter-spacing:.12em;text-transform:uppercase;cursor:pointer;transition:.3s}}
.tab.on{{background:var(--gold);color:#14110d;border-color:var(--gold)}}.tab:hover{{border-color:var(--two)}}
.menu{{display:none;list-style:none;margin:0;padding:0;columns:2;column-gap:70px}}.menu.on{{display:block}}
.menu li{{display:flex;align-items:baseline;gap:14px;padding:16px 0;border-bottom:1px solid var(--line);break-inside:avoid;opacity:0;transform:translateY(14px);animation:up .6s var(--d) forwards}}
.menu li span{{font:500 1.35rem var(--serif)}}.menu li i{{flex:1;border-bottom:1px dotted var(--line);transform:translateY(-4px)}}.menu li b{{font:600 1rem var(--body);color:var(--gold)}}
@keyframes up{{to{{opacity:1;transform:none}}}}.note{{color:var(--muted);font-size:.85rem;margin-top:26px}}
/* vip */
.vip .card{{position:relative;padding:70px min(8vw,80px);border-radius:28px;text-align:center;overflow:hidden;background:radial-gradient(ellipse at top,color-mix(in srgb,var(--gold) 16%,var(--panel)),var(--panel));border:1px solid var(--line)}}
.vip .card::before{{content:"";position:absolute;inset:-1px;border-radius:28px;padding:1px;background:conic-gradient(from var(--a,0deg),transparent 0 55%,var(--two) 65%,var(--gold) 75%,transparent 85%);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:spin 6s linear infinite}}
@property --a{{syntax:'<angle>';initial-value:0deg;inherits:false}}@keyframes spin{{to{{--a:360deg}}}}.vip p{{color:var(--muted);max-width:640px;margin:0 auto 30px}}
/* gallery */
.gal .track{{display:flex;gap:18px;overflow-x:auto;scroll-snap-type:x mandatory;padding:10px 20px 30px;cursor:grab;scrollbar-width:none}}.gal .track::-webkit-scrollbar{{display:none}}
.gal figure{{flex:0 0 min(380px,78vw);aspect-ratio:4/5;margin:0;border-radius:20px;overflow:hidden;scroll-snap-align:center;border:1px solid var(--line)}}
.gal figure img{{width:100%;height:100%;object-fit:cover;transition:transform 1.2s cubic-bezier(.2,.8,.2,1)}}.gal figure:hover img{{transform:scale(1.08)}}
/* reviews */
.revs{{overflow:hidden;background:var(--panel)}}.revs .row{{display:flex;gap:22px;width:max-content;animation:mq 60s linear infinite}}.revs:hover .row{{animation-play-state:paused}}
.rev{{width:min(420px,82vw);margin:0;padding:30px;border-radius:22px;border:1px solid var(--line);background:var(--bg)}}.stars{{color:var(--two);letter-spacing:.2em}}
.rev blockquote{{margin:14px 0;font:500 1.25rem/1.4 var(--serif)}}.rev figcaption{{color:var(--muted);font-size:.85rem}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:30px;margin-top:70px;text-align:center}}.stats b{{display:block;font:500 3rem var(--head);color:var(--gold)}}.stats span{{color:var(--muted);font-size:.85rem;letter-spacing:.1em;text-transform:uppercase}}
/* visit */
.visit .wrap{{display:grid;grid-template-columns:1fr 1.1fr;gap:60px;align-items:start}}.hours{{list-style:none;padding:0;margin:24px 0}}.hours li{{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid var(--line)}}.hours b{{font-weight:500;color:var(--gold)}}
.map{{border-radius:24px;overflow:hidden;border:1px solid var(--line);height:460px}}.map iframe{{width:100%;height:100%;border:0;filter:grayscale(.4) contrast(1.05)}}
footer{{padding:50px 0 120px;color:var(--muted);font-size:.82rem;text-align:center;border-top:1px solid var(--line);position:relative;z-index:1}}
.float{{position:fixed;right:20px;bottom:20px;z-index:30;transform:translateY(140%);transition:transform .5s}}.float.on{{transform:none}}
.rv{{opacity:0;transform:translateY(40px);transition:opacity 1s,transform 1s cubic-bezier(.2,.8,.2,1)}}.rv.in{{opacity:1;transform:none}}
#glow{{position:fixed;width:420px;height:420px;border-radius:50%;pointer-events:none;z-index:2;background:radial-gradient(circle,color-mix(in srgb,var(--gold) 12%,transparent),transparent 65%);transform:translate(-50%,-50%);left:-500px;top:-500px;mix-blend-mode:screen}}
@media (max-width:600px){{nav .brand span{{font-size:.72rem}}nav .brand img{{height:34px}}nav .btn{{padding:10px 16px;font-size:.7rem;white-space:nowrap}}.hero h1{{font-size:clamp(2.2rem,10.5vw,3rem)}}.hero .lead{{font-size:.92rem;margin-bottom:22px}}.hero .wrap{{padding-bottom:9vh}}.float{{right:14px;bottom:14px}}}}
@media (max-width:900px){{nav .links{{display:none}}.exp .wrap,.visit .wrap{{grid-template-columns:1fr}}.arches{{height:460px}}.menu{{columns:1}}section{{padding:90px 0}}.hero .rating{{display:none}}#glow{{display:none}}}}
@media (prefers-reduced-motion:reduce){{*,*::before{{animation:none!important;transition:none!important}}.rv,.hero h1 span i,.hero .lead,.hero .cta,.menu li{{opacity:1;transform:none}}}}
</style></head><body>
<div id="intro">{f'<img src="{logo}" alt="">' if logo else ''}<p>{e(c['short'].upper())}</p></div>
<div id="glow"></div>
<nav><div class="wrap"><a class="brand" href="#top">{f'<img src="{logo}" alt="{e(c["name"])}">' if logo else ''}{f"<span>{e(c['short'].upper())}</span>" if c.get('brand_text', True) or not logo else ''}</a>
<span class="links"><a href="#experience">Experience</a><a href="#services">Services</a><a href="#gallery">Gallery</a><a href="#reviews">Reviews</a><a href="#visit">Visit</a></span>
<a class="btn mag" href="#visit">Book now</a></div></nav>
<header class="hero" id="top">{''.join(f'<div class="slide{" on" if not i else ""}" style="background-image:url({h})"></div>' for i, h in enumerate(hero))}
<canvas id="dust"></canvas>
<div class="wrap"><p class="kick">{e(c['kicker'])}</p><h1>{''.join(f'<span><i>{e(x)}</i></span>' for x in h1)}</h1>
<p class="lead">{e(c['lead'])}</p><div class="cta"><a class="btn mag" href="#visit">Book your chair</a><a class="btn ghost mag" href="#services">See prices</a></div></div>
<div class="rating"><b>{e(c['stats'][0][0])}★</b>{e(c['stats'][1][0])} Google reviews</div><span class="cue"></span></header>
<div class="marquee"><div><span>{marquee}</span><span>{marquee}</span></div></div>
<section class="exp" id="experience"><div class="wrap"><div class="rv"><p class="kick">The experience</p><h2>{e(c['experience']['title'])}</h2><p>{e(c['experience']['text'])}</p></div>
<div class="arches"><div class="arch a"><img src="{exp[0]}" alt="" data-par=".12"></div><div class="arch b"><img src="{exp[1]}" alt="" data-par="-.1"></div></div></div></section>
<section class="svc" id="services"><div class="wrap"><div class="head rv"><div><p class="kick">Services &amp; prices</p><h2>The menu</h2></div><div class="tabs">{tabs}</div></div>{menus}
<p class="note">{e(c.get('currency_note', ''))}</p></div></section>
{special}
<section class="gal" id="gallery"><div class="wrap rv"><p class="kick">Inside the shop</p><h2>Step inside</h2></div><div class="track">{''.join(f'<figure><img src="{g}" alt="" loading="lazy"></figure>' for g in gal)}</div></section>
<section class="revs" id="reviews"><div class="wrap rv"><p class="kick">{e(c['stats'][0][0])}★ from {e(c['stats'][1][0])} Google reviews</p><h2>In their words</h2></div>
<div class="row">{reviews}{reviews}</div><div class="wrap"><div class="stats">{stats}</div></div></section>
<section class="visit" id="visit"><div class="wrap"><div class="rv"><p class="kick">Visit &amp; book</p><h2>Find us</h2><p style="color:var(--muted)">{e(c['address'])}</p>
<ul class="hours">{hours}</ul><div class="cta" style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn mag" href="{e(book)}">{e(book_label)}</a><a class="btn ghost mag" href="tel:{e(c['phone'].replace(' ', ''))}">{e(c['phone'])}</a></div></div>
<div class="map rv"><iframe loading="lazy" title="Map" src="https://maps.google.com/maps?q={lat},{lng}&z=16&output=embed"></iframe></div></div></section>
<footer>{e(c['name'])} · {e(c['address'])} · {f'Instagram @{e(c["instagram"])}' if c.get('instagram') else ''}<br>A free concept home page designed by Kinetic Web Designs, made from {e(c['short'])}'s own photos, prices and reviews. Not the live site.</footer>
<a class="btn float mag" href="{e(book)}">Book now</a>
<script>
const intro=document.getElementById('intro');setTimeout(()=>{{intro.classList.add('go');document.body.classList.add('ready')}},1900);setTimeout(()=>intro.remove(),3100);
const slides=[...document.querySelectorAll('.hero .slide')];let si=0;setInterval(()=>{{slides[si].classList.remove('on');si=(si+1)%slides.length;const s=slides[si];s.classList.remove('on');void s.offsetWidth;s.classList.add('on')}},6000);
const nav=document.querySelector('nav'),fl=document.querySelector('.float');addEventListener('scroll',()=>{{nav.classList.toggle('solid',scrollY>60);fl.classList.toggle('on',scrollY>innerHeight*.8);
document.querySelectorAll('[data-par]').forEach(i=>{{const r=i.parentElement.getBoundingClientRect();i.style.transform=`translateY(${{(r.top-innerHeight/2)*+i.dataset.par}}px)`}})}},{{passive:true}});
const io=new IntersectionObserver(es=>es.forEach(x=>{{if(x.isIntersecting){{x.target.classList.add('in');io.unobserve(x.target)}}}}),{{threshold:.15}});document.querySelectorAll('.rv').forEach(x=>io.observe(x));
setTimeout(()=>document.querySelectorAll('.rv').forEach(x=>x.classList.add('in')),9000);
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{{document.querySelectorAll('.tab,.menu').forEach(x=>x.classList.toggle('on',x.dataset.i===t.dataset.i))}});
const so=new IntersectionObserver(es=>es.forEach(x=>{{if(!x.isIntersecting)return;const b=x.target,txt=b.dataset.to,n=parseFloat(txt.replace(/[^0-9.]/g,''));if(isNaN(n))return;const dec=(txt.split('.')[1]||'').replace(/[^0-9]/g,'').length,t0=performance.now();
(function f(t){{const k=Math.min(1,(t-t0)/1600),v=(n*(1-Math.pow(1-k,3)));b.textContent=txt.replace(/[0-9][0-9,.]*/,v.toLocaleString('en-GB',{{minimumFractionDigits:dec,maximumFractionDigits:dec,useGrouping:txt.includes(',')}}));if(k<1)requestAnimationFrame(f)}})(t0);so.unobserve(b)}}));document.querySelectorAll('.stats b').forEach(b=>so.observe(b));
const g=document.getElementById('glow');addEventListener('pointermove',ev=>{{g.style.left=ev.clientX+'px';g.style.top=ev.clientY+'px'}});
document.querySelectorAll('.mag').forEach(b=>{{b.addEventListener('pointermove',ev=>{{const r=b.getBoundingClientRect();b.style.transform=`translate(${{(ev.clientX-r.left-r.width/2)*.18}}px,${{(ev.clientY-r.top-r.height/2)*.25}}px)`}});b.addEventListener('pointerleave',()=>b.style.transform='')}});
const tr=document.querySelector('.gal .track');let dn=false,sx=0,sl=0;tr.addEventListener('pointerdown',ev=>{{dn=true;sx=ev.clientX;sl=tr.scrollLeft}});addEventListener('pointerup',()=>dn=false);tr.addEventListener('pointermove',ev=>{{if(dn)tr.scrollLeft=sl-(ev.clientX-sx)}});
const cv=document.getElementById('dust'),cx=cv.getContext('2d');let W,H,P=[];function rs(){{W=cv.width=cv.offsetWidth;H=cv.height=cv.offsetHeight;P=Array.from({{length:Math.round(W/14)}},()=>({{x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.8+.4,s:Math.random()*.35+.08,o:Math.random()*.6+.2}}))}}rs();addEventListener('resize',rs);
const gc=getComputedStyle(document.documentElement).getPropertyValue('--gold').trim(),g2=getComputedStyle(document.documentElement).getPropertyValue('--two').trim();(function d(){{cx.clearRect(0,0,W,H);P.forEach((p,i)=>{{cx.fillStyle=i%3?gc:g2;p.y-=p.s;p.x+=Math.sin(p.y/60)*.2;if(p.y<-5){{p.y=H+5;p.x=Math.random()*W}}cx.globalAlpha=p.o*(.5+.5*Math.sin(p.y/40));cx.beginPath();cx.arc(p.x,p.y,p.r,0,7);cx.fill()}});requestAnimationFrame(d)}})();
</script></body></html>"""
    from compare import add as add_compare; html = add_compare(html, c, src, out)
    (out / "index.html").write_text(html, encoding="utf-8")
    print("written", len(html) // 1024, "KB,", len(photos), "photos")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
