"""Different designs for premium mock-ups (owner, 26 Oct 2026: "don't use the same design for every creation, be creative
... so the websites for all look different"). Each layout is its own structure, typography and motion, fed by the same
config.json. premium_page.py keeps the original "atelier" layout; these are "editorial", "split", "bold" and "cinema".

Each render(a) gets a dict with: c (config), col (colours), logo, hero, exp, gal (photo paths), book, book_label,
lat, lng, fonts (head, body, link). CSS and JS are plain strings; colours and fonts arrive as CSS variables."""
from html import escape as e

FONTS = {  # head, body, Google Fonts query
    "editorial": ("'Playfair Display', Georgia, serif", "'Inter', system-ui, sans-serif", "Playfair+Display:ital,wght@0,500;0,700;1,500&family=Inter:wght@400;500;600"),
    "split": ("'Bodoni Moda', Georgia, serif", "'Jost', system-ui, sans-serif", "Bodoni+Moda:ital,wght@0,500;1,500&family=Jost:wght@400;500;600"),
    "bold": ("'Syne', system-ui, sans-serif", "'Space Grotesk', system-ui, sans-serif", "Syne:wght@600;800&family=Space+Grotesk:wght@400;500;700"),
    "cinema": ("'Oswald', Impact, sans-serif", "'DM Sans', system-ui, sans-serif", "Oswald:wght@400;600&family=DM+Sans:wght@400;500;700"),
    "vintage": ("'Rye', Georgia, serif", "'Libre Baskerville', Georgia, serif", "Rye&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400"),
    "fashion": ("'Italiana', Georgia, serif", "'Montserrat', system-ui, sans-serif", "Italiana&family=Montserrat:wght@400;500;600"),
    "script": ("'Marcellus', Georgia, serif", "'Nunito Sans', system-ui, sans-serif", "Marcellus&family=Nunito+Sans:wght@400;600;700"),
}

COMMON_JS = """
const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.14});
document.querySelectorAll('.rv,.wr').forEach(x=>io.observe(x));setTimeout(()=>document.querySelectorAll('.rv,.wr').forEach(x=>x.classList.add('in')),9000);
document.querySelectorAll('[data-tab]').forEach(t=>t.onclick=()=>{const g=t.closest('[data-tabs]');g.querySelectorAll('[data-tab],[data-pane]').forEach(x=>x.classList.toggle('on',(x.dataset.tab||x.dataset.pane)===t.dataset.tab))});
const so=new IntersectionObserver(es=>es.forEach(x=>{if(!x.isIntersecting)return;const b=x.target,txt=b.dataset.to||'',n=parseFloat(txt.replace(/[^0-9.]/g,''));so.unobserve(b);if(isNaN(n)||!/^[0-9.,]+/.test(txt))return;
const dec=(txt.split('.')[1]||'').replace(/[^0-9]/g,'').length,t0=performance.now();(function f(t){const k=Math.min(1,(t-t0)/1500),v=n*(1-Math.pow(1-k,3));
b.textContent=txt.replace(/[0-9][0-9,.]*/,v.toLocaleString('en-GB',{minimumFractionDigits:dec,maximumFractionDigits:dec,useGrouping:txt.includes(',')}));if(k<1)requestAnimationFrame(f)})(t0)}));
document.querySelectorAll('[data-to]').forEach(b=>so.observe(b));
document.querySelectorAll('.wr').forEach(h=>{h.innerHTML=h.textContent.split(' ').map((w,i)=>`<span><i style="transition-delay:${i*55}ms">${w}</i></span>`).join(' ')});
"""

BASE_CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth;overflow-x:clip}body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--body);overflow-x:clip}
img{max-width:100%;display:block}a{color:inherit}.wrap{width:min(1200px,100% - 40px);margin:0 auto;position:relative}
.rv{opacity:0;transform:translateY(36px);transition:opacity 1s,transform 1s cubic-bezier(.2,.8,.2,1)}.rv.in{opacity:1;transform:none}
.wr span{display:inline-block;overflow:hidden;vertical-align:top}.wr i{display:inline-block;font-style:inherit;transform:translateY(105%);transition:transform .9s cubic-bezier(.2,.8,.2,1)}.wr.in i{transform:none}
[data-pane]{display:none}[data-pane].on{display:block}
.mapf{border:0;width:100%;height:100%;filter:grayscale(.35)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.rv,.wr i{opacity:1;transform:none}}
"""


def head(a, title_suffix="concept website"):
    c, col, (fh, fb, link) = a["c"], a["col"], a["fonts"]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(c["name"])} | {title_suffix}</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link href="https://fonts.googleapis.com/css2?family={link}&display=swap" rel="stylesheet">'
            f'<style>:root{{--bg:{col["bg"]};--panel:{col["panel"]};--ink:{col["ink"]};--muted:{col["muted"]};--gold:{col["gold"]};--two:{col.get("second", col["gold"])};'
            f'--head:{fh};--body:{fb};')


def menu_html(c, cls="menu"):
    tabs = "".join(f'<button type="button" data-tab="{i}" class="{"on" if not i else ""}">{e(g["group"])}</button>' for i, g in enumerate(c["services"]))
    panes = "".join(f'<ul data-pane="{i}" class="{cls}{" on" if not i else ""}">' + "".join(
        f'<li><span>{e(n)}</span>' + (f'<em></em><b>{e(p)}</b>' if p else '') + '</li>' for n, p in g["items"]) + "</ul>" for i, g in enumerate(c["services"]))
    return tabs, panes


def footer_line(c):
    return f'A free concept home page designed by Kinetic Web Designs, made from {e(c["short"])}\'s own photos and reviews. Not the live site.'


# ---------------------------------------------------------------------------------------------------- editorial
EDITORIAL_CSS = """
body{background:var(--paper);color:var(--text)}
nav{position:fixed;inset:0 0 auto;z-index:20;display:flex;justify-content:space-between;align-items:center;padding:18px max(20px,4vw);background:color-mix(in srgb,var(--paper) 86%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--rule)}
nav img{height:38px;width:auto}nav .nm{font:700 1.05rem var(--head);letter-spacing:.02em}nav .ln{display:flex;gap:26px;font-size:.88rem}nav .ln a{text-decoration:none}
.pill{display:inline-flex;align-items:center;gap:10px;padding:13px 24px;border-radius:999px;background:var(--text);color:var(--paper);text-decoration:none;font:600 .82rem var(--body);letter-spacing:.06em;transition:transform .3s,background .3s}.pill:hover{background:var(--gold);transform:translateY(-2px)}
.pill.o{background:transparent;color:var(--text);border:1px solid var(--text)}
.hero{min-height:100svh;display:grid;grid-template-columns:1.1fr .9fr;gap:5vw;align-items:center;padding:120px max(20px,4vw) 60px}
.hero .no{font:600 .75rem var(--body);letter-spacing:.3em;text-transform:uppercase;color:var(--gold)}
.hero h1{font:500 clamp(3rem,7.6vw,7.4rem)/.95 var(--head);margin:18px 0 26px;letter-spacing:-.02em}.hero h1 em{font-style:italic;color:var(--gold)}
.hero p{max-width:470px;color:var(--soft);font-size:1.05rem}.hero .cta{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
.frame{position:relative;height:min(78vh,720px);border-radius:300px 300px 24px 24px;overflow:hidden;clip-path:inset(100% 0 0 0 round 300px 300px 24px 24px);transition:clip-path 1.6s cubic-bezier(.7,0,.2,1)}
.ready .frame{clip-path:inset(0 0 0 0 round 300px 300px 24px 24px)}.frame img{width:100%;height:100%;object-fit:cover;transform:scale(1.25);transition:transform 2.4s cubic-bezier(.2,.8,.2,1)}.ready .frame img{transform:scale(1)}
.badge{position:absolute;left:-30px;bottom:40px;background:var(--paper);border-radius:20px;padding:16px 20px;box-shadow:0 20px 50px rgba(0,0,0,.12);font-size:.85rem}.badge b{display:block;font:500 2rem var(--head);color:var(--gold)}
.ticker{border-block:1px solid var(--rule);overflow:hidden;padding:18px 0}.ticker div{display:flex;width:max-content;animation:tk 40s linear infinite;font:italic 500 1.6rem var(--head)}.ticker span{padding-right:50px}
@keyframes tk{to{transform:translateX(-50%)}}
section{padding:120px 0}.sec-h{display:grid;grid-template-columns:120px 1fr;gap:30px;margin-bottom:60px}.sec-h .n{font:500 4rem/1 var(--head);color:var(--gold)}
.sec-h h2{font:500 clamp(2.2rem,5vw,4.2rem)/1 var(--head);margin:0;letter-spacing:-.01em}.sec-h p{color:var(--soft);max-width:560px;margin:14px 0 0}
.story{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:center}.story img{border-radius:20px;height:560px;width:100%;object-fit:cover}
.story .duo{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;align-items:end}.story .duo img:last-child{height:380px}
[data-tabs] .tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:30px}[data-tabs] .tabs button{border:1px solid var(--rule);background:transparent;color:var(--text);border-radius:999px;padding:10px 18px;font:500 .85rem var(--body);cursor:pointer}
[data-tabs] .tabs button.on{background:var(--text);color:var(--paper)}
.menu{list-style:none;margin:0;padding:0;columns:2;column-gap:60px}.menu.on{display:block}.menu li{display:flex;align-items:baseline;gap:12px;padding:18px 0;border-bottom:1px solid var(--rule);break-inside:avoid;font-size:1.05rem}
.menu em{flex:1;border-bottom:1px dashed var(--rule)}.menu b{font:500 1.2rem var(--head);color:var(--gold)}
.hz{height:300vh;position:relative}.hz .pin{position:sticky;top:0;height:100svh;overflow:hidden;display:flex;align-items:center}
.hz .row{display:flex;gap:28px;padding-left:max(20px,4vw);will-change:transform}.hz figure{margin:0;flex:0 0 auto;width:min(420px,70vw);height:62vh;border-radius:18px;overflow:hidden}
.hz figure:nth-child(even){height:48vh;align-self:flex-end}.hz img{width:100%;height:100%;object-fit:cover}
.hz .lab{position:absolute;top:110px;left:max(20px,4vw);font:500 clamp(2rem,5vw,4rem) var(--head)}
.quote{text-align:center;max-width:900px;margin:0 auto;min-height:300px}.quote blockquote{font:italic 500 clamp(1.6rem,3.4vw,2.6rem)/1.3 var(--head);margin:0 0 20px;transition:opacity .6s}
.quote cite{font-style:normal;color:var(--soft);letter-spacing:.2em;text-transform:uppercase;font-size:.78rem}
.nums{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--rule);margin-top:80px}.nums div{padding:30px 10px;border-right:1px solid var(--rule)}.nums div:last-child{border:0}
.nums b{display:block;font:500 3.2rem var(--head)}.nums span{color:var(--soft);font-size:.85rem}
.special{background:var(--text);color:var(--paper);border-radius:28px;padding:80px min(7vw,80px);display:grid;grid-template-columns:1fr auto;gap:40px;align-items:center}
.special h2{font:500 clamp(2rem,4.4vw,3.6rem)/1.05 var(--head);margin:10px 0 14px}.special p{opacity:.75;max-width:620px;margin:0}.special .pill{background:var(--gold);color:var(--text)}
.visit{display:grid;grid-template-columns:1fr 1.1fr;gap:60px}.hours{list-style:none;padding:0;margin:20px 0 30px}.hours li{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--rule)}
.map{height:480px;border-radius:24px;overflow:hidden}
footer{padding:100px 0 60px;text-align:center}footer .big{font:500 clamp(3rem,12vw,11rem)/.9 var(--head);letter-spacing:-.03em;color:var(--gold)}footer p{color:var(--soft);font-size:.82rem}
@media (max-width:900px){nav .ln{display:none}.hero,.story,.visit,.special{grid-template-columns:1fr}.frame{height:62vh}.menu{columns:1}.sec-h{grid-template-columns:1fr}.nums{grid-template-columns:repeat(2,1fr)}.badge{left:12px}section{padding:80px 0}}
"""
EDITORIAL_JS = """
setTimeout(()=>document.body.classList.add('ready'),150);
const hz=document.querySelector('.hz'),row=hz.querySelector('.row');addEventListener('scroll',()=>{const r=hz.getBoundingClientRect(),p=Math.min(1,Math.max(0,-r.top/(r.height-innerHeight)));
row.style.transform=`translateX(${-p*(row.scrollWidth-innerWidth+80)}px)`},{passive:true});
const Q=JSON.parse(document.querySelector('.quote').dataset.q),bq=document.querySelector('.quote blockquote'),ct=document.querySelector('.quote cite');let qi=0;
setInterval(()=>{bq.style.opacity=0;ct.style.opacity=0;setTimeout(()=>{qi=(qi+1)%Q.length;bq.textContent='“'+Q[qi][0]+'”';ct.textContent=Q[qi][1];bq.style.opacity=1;ct.style.opacity=1},600)},6500);
"""


def editorial(a):
    import json
    c, col = a["c"], a["col"]
    light = col.get("paper", "#f6f1ea"), col.get("text", "#1d1a17"), col.get("soft", "#6c645b"), col.get("rule", "#ddd3c6")
    tabs, panes = menu_html(c)
    h1 = c["h1"]
    q = [[t, a_] for t, a_ in c["reviews"]]
    gal = "".join(f'<figure><img src="{g}" alt="" loading="lazy"></figure>' for g in a["gal"])
    nums = "".join(f'<div><b data-to="{e(v)}">{e(v)}</b><span>{e(l)}</span></div>' for v, l in c["stats"])
    hours = "".join(f"<li><span>{e(d)}</span><b>{e(t)}</b></li>" for d, t in c["hours"])
    sp = c.get("special")
    special = (f'<section><div class="wrap"><div class="special rv"><div><p style="letter-spacing:.3em;text-transform:uppercase;font-size:.75rem;color:var(--gold);margin:0">{e(sp["kicker"])}</p>'
               f'<h2>{e(sp["title"])}</h2><p>{e(sp["text"])}</p></div><a class="pill" href="{e(a["book"])}">{e(sp["cta"])}</a></div></div></section>') if sp else ""
    marquee = "  ·  ".join(e(n) for g in c["services"] for n, _ in g["items"][:4])
    logo = f'<img src="{a["logo"]}" alt="{e(c["name"])}">' if a["logo"] else f'<span class="nm">{e(c["short"])}</span>'
    return (head(a) + f"--paper:{light[0]};--text:{light[1]};--soft:{light[2]};--rule:{light[3]}}}" + BASE_CSS + EDITORIAL_CSS + "</style></head><body>"
            f'<nav><a href="#top">{logo}</a><span class="ln"><a href="#story">Story</a><a href="#menu">Services</a><a href="#work">Work</a><a href="#visit">Visit</a></span><a class="pill" href="{e(a["book"])}">{e(a["book_label"])}</a></nav>'
            f'<header class="hero" id="top"><div><p class="no">{e(c["kicker"])}</p><h1>{e(h1[0])} {e(h1[1])} <em>{e(h1[2])}</em></h1><p>{e(c["lead"])}</p>'
            f'<div class="cta"><a class="pill" href="{e(a["book"])}">{e(a["book_label"])}</a><a class="pill o" href="#menu">Services</a></div></div>'
            f'<div style="position:relative"><div class="frame"><img src="{a["hero"][0]}" alt=""></div><div class="badge"><b>{e(c["stats"][0][0])}★</b>{e(c["stats"][1][0])} Google reviews</div></div></header>'
            f'<div class="ticker"><div><span>{marquee}</span><span>{marquee}</span></div></div>'
            f'<section id="story"><div class="wrap"><div class="story"><div class="duo rv"><img src="{a["exp"][0]}" alt=""><img src="{a["exp"][1]}" alt=""></div>'
            f'<div><div class="sec-h" style="grid-template-columns:1fr;margin-bottom:20px"><span class="n">01</span><h2 class="wr">{e(c["experience"]["title"])}</h2></div><p class="rv" style="color:var(--soft)">{e(c["experience"]["text"])}</p></div></div></div></section>'
            f'<section id="menu" style="background:color-mix(in srgb,var(--text) 4%,var(--paper))"><div class="wrap" data-tabs><div class="sec-h"><span class="n">02</span><div><h2 class="wr">Services &amp; prices</h2><p>{e(c.get("currency_note", ""))}</p></div></div>'
            f'<div class="tabs">{tabs}</div>{panes}</div></section>'
            f'<section class="hz" id="work"><div class="pin"><span class="lab">03 — The work</span><div class="row">{gal}</div></div></section>'
            f'<section><div class="wrap"><div class="quote rv" data-q="{e(json.dumps(q))}"><blockquote>“{e(q[0][0])}”</blockquote><cite>{e(q[0][1])}</cite></div><div class="nums">{nums}</div></div></section>'
            + special +
            f'<section id="visit"><div class="wrap visit"><div class="rv"><div class="sec-h" style="grid-template-columns:1fr;margin-bottom:10px"><span class="n">04</span><h2>Visit us</h2></div>'
            f'<p style="color:var(--soft)">{e(c["address"])}</p><ul class="hours">{hours}</ul><a class="pill" href="{e(a["book"])}">{e(a["book_label"])}</a> <a class="pill o" href="tel:{e(c["phone"].replace(" ", ""))}">{e(c["phone"])}</a></div>'
            f'<div class="map rv"><iframe class="mapf" loading="lazy" title="Map" src="https://maps.google.com/maps?q={a["lat"]},{a["lng"]}&z=16&output=embed"></iframe></div></div></section>'
            f'<footer><div class="big">{e(c["short"])}</div><p>{footer_line(c)}</p></footer>'
            "<script>" + COMMON_JS + EDITORIAL_JS + "</script></body></html>")


# ---------------------------------------------------------------------------------------------------- split
SPLIT_CSS = """
.media{position:fixed;left:0;top:0;width:50vw;height:100svh;overflow:hidden;z-index:1}.media img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transform:scale(1.08);transition:opacity 1.1s,transform 6s linear}
.media img.on{opacity:1;transform:scale(1)}.media::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent 60%,var(--bg))}
.media .tag{position:absolute;left:28px;bottom:28px;z-index:2;font:500 .75rem var(--body);letter-spacing:.3em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.35);padding:8px 14px;border-radius:999px;backdrop-filter:blur(6px)}
.media .bar{position:absolute;left:0;top:0;width:3px;height:0;background:var(--gold);z-index:2}
main{margin-left:50vw;position:relative;z-index:2}main>section{min-height:100svh;padding:120px 7vw 90px;display:flex;flex-direction:column;justify-content:center;border-bottom:1px solid color-mix(in srgb,var(--gold) 18%,transparent)}
.top{position:fixed;top:24px;right:28px;z-index:30;display:flex;gap:10px;align-items:center}
.btn{display:inline-flex;align-items:center;padding:14px 26px;border:1px solid var(--gold);color:var(--ink);text-decoration:none;font:500 .78rem var(--body);letter-spacing:.2em;text-transform:uppercase;position:relative;overflow:hidden;background:transparent;z-index:0}
.btn::before{content:"";position:absolute;inset:0;background:var(--gold);transform:translateY(101%);transition:transform .45s cubic-bezier(.7,0,.2,1);z-index:-1}.btn:hover::before{transform:none}.btn:hover{color:var(--bg)}
.btn.f{background:var(--gold);color:var(--bg)}
.brandmark{position:fixed;top:24px;left:28px;z-index:30}.brandmark img{height:46px;width:auto;filter:drop-shadow(0 2px 10px rgba(0,0,0,.4))}.brandmark span{font:500 1.2rem var(--head);color:#fff}
.k{font:500 .74rem var(--body);letter-spacing:.34em;text-transform:uppercase;color:var(--gold);margin:0 0 18px}
h1{font:500 clamp(3rem,6vw,6.2rem)/.98 var(--head);margin:0 0 26px}h1 em,h2 em{color:var(--gold)}h2{font:500 clamp(2.2rem,4vw,3.8rem)/1.02 var(--head);margin:0 0 22px}
p.l{color:var(--muted);max-width:520px;font-size:1.05rem}
.acc details{border-bottom:1px solid color-mix(in srgb,var(--gold) 25%,transparent)}.acc summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;padding:22px 0;font:500 1.6rem var(--head)}
.acc summary::after{content:"+";font:300 1.8rem var(--body);color:var(--gold);transition:transform .4s}.acc details[open] summary::after{transform:rotate(45deg)}
.acc ul{list-style:none;margin:0 0 20px;padding:0}.acc li{display:flex;justify-content:space-between;gap:20px;padding:10px 0;color:var(--muted)}.acc li b{color:var(--ink);font-weight:500}
.stack{display:grid;gap:22px}.rq{border-left:2px solid var(--gold);padding:4px 0 4px 22px}.rq p{font:italic 500 1.35rem/1.4 var(--head);margin:0 0 8px}.rq span{color:var(--muted);font-size:.85rem}
.figs{display:flex;gap:40px;flex-wrap:wrap;margin-top:40px}.figs b{display:block;font:500 2.8rem var(--head);color:var(--gold)}.figs span{color:var(--muted);font-size:.8rem;letter-spacing:.1em;text-transform:uppercase}
.thumbs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.thumbs img{aspect-ratio:1;object-fit:cover;width:100%;filter:grayscale(.6);transition:filter .5s,transform .5s}.thumbs img:hover{filter:none;transform:scale(1.03)}
.hrs{list-style:none;padding:0;margin:24px 0}.hrs li{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid color-mix(in srgb,var(--gold) 18%,transparent);color:var(--muted)}.hrs b{color:var(--ink);font-weight:500}
.map{height:300px;margin-top:20px}footer{padding:40px 7vw;color:var(--muted);font-size:.8rem}
.cur{position:fixed;width:12px;height:12px;border-radius:50%;background:var(--gold);pointer-events:none;z-index:99;transform:translate(-50%,-50%);transition:width .3s,height .3s,opacity .3s;mix-blend-mode:difference;left:-40px}
@media (max-width:900px){.media{position:relative;width:100%;height:62svh}.media::after{background:linear-gradient(180deg,transparent 50%,var(--bg))}main{margin:0}main>section{min-height:auto;padding:80px 22px}
.top{top:auto;bottom:16px;right:16px;transform:translateY(170%);transition:transform .5s cubic-bezier(.2,.8,.2,1)}.top.on{transform:none}.top{}.brandmark{position:absolute}.cur{display:none}.thumbs{grid-template-columns:repeat(2,1fr)}}
"""
SPLIT_JS = """
const imgs=[...document.querySelectorAll('.media img')],tag=document.querySelector('.media .tag'),bar=document.querySelector('.media .bar'),secs=[...document.querySelectorAll('main>section')];
const so2=new IntersectionObserver(es=>es.forEach(x=>{if(!x.isIntersecting)return;const i=+x.target.dataset.m;imgs.forEach((m,j)=>m.classList.toggle('on',j===i));tag.textContent=x.target.dataset.t}),{threshold:.45});
secs.forEach(s=>so2.observe(s));addEventListener('scroll',()=>{bar.style.height=(scrollY/(document.body.scrollHeight-innerHeight)*100)+'%'},{passive:true});
const cu=document.querySelector('.cur');addEventListener('pointermove',ev=>{cu.style.left=ev.clientX+'px';cu.style.top=ev.clientY+'px'});
document.querySelectorAll('a,summary,button').forEach(x=>{x.addEventListener('pointerenter',()=>{cu.style.width=cu.style.height='54px'});x.addEventListener('pointerleave',()=>{cu.style.width=cu.style.height='12px'})});
document.querySelector('.acc details').open=true;
const tp=document.querySelector('.top'),tpOn=()=>tp&&tp.classList.toggle('on',scrollY>innerHeight*.6);addEventListener('scroll',tpOn,{passive:true});tpOn();
"""


def split(a):
    c = a["c"]
    pics = [a["hero"][0], a["exp"][0], a["exp"][1] if len(a["exp"]) > 1 else a["hero"][-1], a["gal"][0], a["hero"][-1]]
    acc = "".join(f'<details><summary>{e(g["group"])}</summary><ul>' + "".join(f'<li><span>{e(n)}</span>{f"<b>{e(p)}</b>" if p else ""}</li>' for n, p in g["items"]) + "</ul></details>" for g in c["services"])
    revs = "".join(f'<div class="rq rv"><p>“{e(t)}”</p><span>{e(au)}</span></div>' for t, au in c["reviews"][:3])
    figs = "".join(f'<div><b data-to="{e(v)}">{e(v)}</b><span>{e(l)}</span></div>' for v, l in c["stats"])
    hours = "".join(f"<li><span>{e(d)}</span><b>{e(t)}</b></li>" for d, t in c["hours"])
    thumbs = "".join(f'<img src="{g}" alt="" loading="lazy">' for g in a["gal"][:9])
    sp = c.get("special")
    logo = f'<img src="{a["logo"]}" alt="{e(c["name"])}">' if a["logo"] else f'<span>{e(c["short"])}</span>'
    h1 = c["h1"]
    return (head(a) + "}" + BASE_CSS + SPLIT_CSS + "</style></head><body><div class=\"cur\"></div>"
            f'<a class="brandmark" href="#top">{logo}</a><div class="top"><a class="btn f" href="{e(a["book"])}">{e(a["book_label"])}</a></div>'
            '<div class="media">' + "".join(f'<img src="{p}" alt=""{" class=on" if not i else ""}>' for i, p in enumerate(pics)) + '<span class="tag">Welcome</span><span class="bar"></span></div><main>'
            f'<section id="top" data-m="0" data-t="Welcome"><p class="k">{e(c["kicker"])}</p><h1 class="wr">{e(h1[0])} {e(h1[1])} {e(h1[2])}</h1><p class="l rv">{e(c["lead"])}</p>'
            f'<div class="rv" style="display:flex;gap:12px;flex-wrap:wrap;margin-top:30px"><a class="btn f" href="{e(a["book"])}">{e(a["book_label"])}</a><a class="btn" href="#menu">Services</a></div></section>'
            f'<section data-m="1" data-t="The experience"><p class="k">The experience</p><h2 class="wr">{e(c["experience"]["title"])}</h2><p class="l rv">{e(c["experience"]["text"])}</p><div class="figs">{figs}</div></section>'
            f'<section id="menu" data-m="2" data-t="Services"><p class="k">Services &amp; prices</p><h2>The menu</h2><div class="acc rv">{acc}</div><p class="l" style="font-size:.88rem;margin-top:22px">{e(c.get("currency_note", ""))}</p></section>'
            + (f'<section data-m="3" data-t="{e(sp["kicker"])}"><p class="k">{e(sp["kicker"])}</p><h2 class="wr">{e(sp["title"])}</h2><p class="l rv">{e(sp["text"])}</p><div class="thumbs rv" style="margin-top:30px">{thumbs}</div></section>' if sp else
               f'<section data-m="3" data-t="The work"><p class="k">The work</p><h2>Fresh out the chair</h2><div class="thumbs rv">{thumbs}</div></section>') +
            f'<section data-m="4" data-t="Reviews"><p class="k">{e(c["stats"][0][0])}★ · {e(c["stats"][1][0])} Google reviews</p><h2>In their words</h2><div class="stack">{revs}</div></section>'
            f'<section id="visit" data-m="0" data-t="Visit"><p class="k">Visit</p><h2>Find us</h2><p class="l">{e(c["address"])}</p><ul class="hrs">{hours}</ul>'
            f'<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn f" href="{e(a["book"])}">{e(a["book_label"])}</a><a class="btn" href="tel:{e(c["phone"].replace(" ", ""))}">{e(c["phone"])}</a></div>'
            f'<div class="map"><iframe class="mapf" loading="lazy" title="Map" src="https://maps.google.com/maps?q={a["lat"]},{a["lng"]}&z=16&output=embed"></iframe></div></section>'
            f'<footer>{footer_line(c)}</footer></main><script>' + COMMON_JS + SPLIT_JS + "</script></body></html>")


# ---------------------------------------------------------------------------------------------------- bold
BOLD_CSS = """
nav{position:fixed;inset:16px 16px auto;z-index:20;display:flex;justify-content:space-between;align-items:center;padding:12px 14px 12px 22px;border-radius:999px;background:color-mix(in srgb,var(--bg) 80%,transparent);backdrop-filter:blur(14px);border:1px solid color-mix(in srgb,var(--ink) 12%,transparent)}
nav img{height:34px;width:auto}nav .nm{font:800 1.1rem var(--head)}nav .ln{display:flex;gap:22px;font-size:.88rem;font-weight:500}nav .ln a{text-decoration:none}
.go{display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border-radius:999px;background:var(--gold);color:var(--bg);font:700 .85rem var(--body);text-decoration:none;transition:transform .2s}.go:hover{transform:scale(1.05)}
.go.alt{background:var(--ink);color:var(--bg)}
.hero{min-height:100svh;padding:130px 22px 40px;display:grid;align-content:center;position:relative;overflow:hidden}
.hero h1{font:800 clamp(2.8rem,var(--h1s,13vw),13rem)/.88 var(--head);max-width:72%;margin:0;letter-spacing:-.04em;text-transform:uppercase}@media (max-width:900px){.hero h1{font-size:min(clamp(2.2rem,var(--h1s,13vw),13rem),var(--h1p,13vw))}}/* on a phone the longest word sets the size, so none runs off the screen (Paris Barber, 28 Oct 2026) */.hero h1 .o{-webkit-text-stroke:2px var(--ink);color:transparent}.hero h1 .c{color:var(--gold)}
.hero .row{display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:end;margin-top:36px}.hero p{max-width:480px;color:var(--muted);font-size:1.1rem;margin:0}
.hero .ph{position:absolute;right:6vw;top:18vh;width:min(30vw,380px);aspect-ratio:3/4;border-radius:24px;overflow:hidden;transform:rotate(6deg);box-shadow:0 30px 80px rgba(0,0,0,.4);z-index:-1}
.hero .ph img{width:100%;height:100%;object-fit:cover}
.spin{position:absolute;right:max(22px,8vw);bottom:60px;width:140px;height:140px;animation:sp 14s linear infinite}.spin text{font:700 13px var(--body);letter-spacing:4px;fill:var(--ink)}@keyframes sp{to{transform:rotate(360deg)}}
.spin+span{position:absolute;right:calc(max(22px,8vw) + 52px);bottom:112px;width:36px;height:36px;border-radius:50%;background:var(--gold)}
.mq{background:var(--gold);color:var(--bg);overflow:hidden;padding:20px 0;transform:rotate(-2deg);margin:40px -20px}.mq div{display:flex;width:max-content;font:800 2.4rem var(--head);text-transform:uppercase;animation:tk 22s linear infinite}
.mq span{padding-right:40px}@keyframes tk{to{transform:translateX(-50%)}}
section{padding:110px 22px}.blk{background:var(--panel);border-radius:40px;margin:0 12px}
h2{font:800 clamp(2.6rem,7vw,6rem)/.9 var(--head);margin:0 0 40px;letter-spacing:-.03em;text-transform:uppercase}h2 .c{color:var(--gold)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}.card{background:var(--bg);border-radius:26px;padding:28px;border:1px solid color-mix(in srgb,var(--ink) 10%,transparent);transition:transform .35s,border-color .35s}
.card:hover{transform:translateY(-6px);border-color:var(--gold)}.card h3{font:800 1.5rem var(--head);margin:0 0 16px;text-transform:uppercase;color:var(--gold)}.card li{display:flex;justify-content:space-between;gap:14px;padding:8px 0;border-bottom:1px solid color-mix(in srgb,var(--ink) 8%,transparent)}
.card ul{list-style:none;margin:0;padding:0}.card b{white-space:nowrap}
.tilts{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;perspective:1000px}.tilts figure{margin:0;border-radius:24px;overflow:hidden;aspect-ratio:3/4;transition:transform .2s;transform-style:preserve-3d}
.tilts figure:nth-child(4n+2){margin-top:60px}.tilts figure:nth-child(4n+4){margin-top:30px}.tilts img{width:100%;height:100%;object-fit:cover}
.big{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px}.big div{background:var(--gold);color:var(--bg);border-radius:30px;padding:30px}.big div:nth-child(even){background:var(--two)}
.big b{display:block;font:800 clamp(2.2rem,4.2vw,3.6rem)/1 var(--head);white-space:nowrap}.big span{font-weight:700}
.rv2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}.rv2 div{border:2px solid var(--ink);border-radius:26px;padding:26px;font-size:1.05rem}.rv2 span{display:block;margin-top:14px;font-weight:700;color:var(--gold)}
.sp{display:grid;grid-template-columns:1.3fr 1fr;gap:40px;align-items:center}.sp p{color:var(--muted);font-size:1.1rem}
.visit{display:grid;grid-template-columns:1fr 1fr;gap:30px}.hr{list-style:none;padding:0;margin:0 0 26px}.hr li{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px dashed color-mix(in srgb,var(--ink) 20%,transparent)}
.map{height:420px;border-radius:30px;overflow:hidden}footer{padding:40px 22px 100px;color:var(--muted);font-size:.82rem}
@media (max-width:900px){nav .ln{display:none}.hero h1{max-width:none}.hero .row,.sp,.visit{grid-template-columns:1fr}.hero .ph{position:relative;right:auto;top:auto;width:70%;margin:20px auto 48px;z-index:0}.tilts{grid-template-columns:repeat(2,1fr)}.spin,.spin+span{display:none}}
"""
BOLD_JS = """
document.querySelectorAll('.tilts figure').forEach(f=>{f.addEventListener('pointermove',ev=>{const r=f.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width-.5,y=(ev.clientY-r.top)/r.height-.5;f.style.transform=`rotateY(${x*14}deg) rotateX(${-y*14}deg) scale(1.03)`});f.addEventListener('pointerleave',()=>f.style.transform='')});
let lastY=scrollY,sk=0;const mq=document.querySelector('.mq div');(function t(){const d=scrollY-lastY;lastY=scrollY;sk+=(Math.max(-12,Math.min(12,d*.4))-sk)*.12;mq.style.transform=`skewX(${-sk}deg)`;requestAnimationFrame(t)})();
"""


def bold(a):
    c = a["c"]
    h1 = c["h1"]
    cards = "".join(f'<div class="card rv"><h3>{e(g["group"])}</h3><ul>' + "".join(f'<li><span>{e(n)}</span>{f"<b>{e(p)}</b>" if p else ""}</li>' for n, p in g["items"]) + "</ul></div>" for g in c["services"])
    tilts = "".join(f'<figure class="rv"><img src="{g}" alt="" loading="lazy"></figure>' for g in a["gal"][:8])
    big = "".join(f'<div class="rv"><b data-to="{e(v)}">{e(v)}</b><span>{e(l)}</span></div>' for v, l in c["stats"])
    revs = "".join(f'<div class="rv">“{e(t)}”<span>{e(au)}</span></div>' for t, au in c["reviews"][:3])
    hours = "".join(f"<li><span>{e(d)}</span><b>{e(t)}</b></li>" for d, t in c["hours"])
    words = "  ✶  ".join(e(n) for g in c["services"] for n, _ in g["items"][:3])
    sp = c.get("special")
    logo = f'<img src="{a["logo"]}" alt="{e(c["name"])}">' if a["logo"] else f'<span class="nm">{e(c["short"])}</span>'
    circ = e((c["book_label"] if c.get("book_label") else "Book now").upper() + " • " + c["short"].upper() + " • ")
    return (head(a) + "}" + BASE_CSS + BOLD_CSS + "</style></head><body>"
            f'<nav><a href="#top">{logo}</a><span class="ln"><a href="#services">Services</a><a href="#work">Work</a><a href="#reviews">Reviews</a><a href="#visit">Visit</a></span><a class="go" href="{e(a["book"])}">{e(a["book_label"])}</a></nav>'
            f'<header class="hero" id="top" style="--h1s:{min(13, round(125 / max(len(x) for x in h1), 1))}vw;--h1p:{min(13, round(88 / max(len(w) for x in h1 for w in x.split()), 1))}vw"><div class="ph"><img src="{a["hero"][0]}" alt=""></div><h1><span class="wr">{e(h1[0])}</span><br><span class="o">{e(h1[1])}</span><br><span class="c">{e(h1[2])}</span></h1>'
            f'<div class="row"><p class="rv">{e(c["lead"])}</p><div class="rv" style="display:flex;gap:10px;flex-wrap:wrap"><a class="go" href="{e(a["book"])}">{e(a["book_label"])}</a><a class="go alt" href="#services">Services</a></div></div>'
            f'<svg class="spin" viewBox="0 0 140 140"><defs><path id="cp" d="M70,70 m-55,0 a55,55 0 1,1 110,0 a55,55 0 1,1 -110,0"/></defs><text><textPath href="#cp">{circ}</textPath></text></svg><span></span></header>'
            f'<div class="mq"><div><span>{words}</span><span>{words}</span></div></div>'
            f'<section id="services" class="blk"><div class="wrap"><h2 class="wr">Services <span class="c">&amp; prices</span></h2><div class="cards">{cards}</div><p style="color:var(--muted);margin-top:22px">{e(c.get("currency_note", ""))}</p></div></section>'
            f'<section id="work"><div class="wrap"><h2>{e(c["experience"]["title"])}</h2><div class="sp" style="margin-bottom:60px"><p class="rv">{e(c["experience"]["text"])}</p></div><div class="tilts">{tilts}</div></div></section>'
            f'<section><div class="wrap"><div class="big">{big}</div></div></section>'
            + (f'<section class="blk"><div class="wrap sp"><div><h2 class="wr">{e(sp["title"])}</h2><p class="rv">{e(sp["text"])}</p></div><div class="rv"><a class="go" href="{e(a["book"])}">{e(sp["cta"])}</a></div></div></section>' if sp else "") +
            f'<section id="reviews"><div class="wrap"><h2>{e(c["stats"][0][0])}★ <span class="c">reviews</span></h2><div class="rv2">{revs}</div></div></section>'
            f'<section id="visit" class="blk"><div class="wrap visit"><div><h2>Find <span class="c">us</span></h2><p style="color:var(--muted)">{e(c["address"])}</p><ul class="hr">{hours}</ul>'
            f'<a class="go" href="{e(a["book"])}">{e(a["book_label"])}</a> <a class="go alt" href="tel:{e(c["phone"].replace(" ", ""))}">{e(c["phone"])}</a></div>'
            f'<div class="map"><iframe class="mapf" loading="lazy" title="Map" src="https://maps.google.com/maps?q={a["lat"]},{a["lng"]}&z=16&output=embed"></iframe></div></div></section>'
            f'<footer class="wrap">{footer_line(c)}</footer><script>' + COMMON_JS + BOLD_JS + "</script></body></html>")


# ---------------------------------------------------------------------------------------------------- cinema
CINEMA_CSS = """
html{scroll-snap-type:y mandatory}body{background:#000}
.scene{height:100svh;scroll-snap-align:start;position:relative;overflow:hidden;display:grid;align-items:end}
.scene .bg{position:absolute;inset:0;background-size:cover;background-position:center;transform:scale(1.18);filter:brightness(.55) blur(6px);transition:transform 2.2s cubic-bezier(.2,.8,.2,1),filter 1.6s}
.scene.live .bg{transform:scale(1.02);filter:brightness(.55) blur(0)}.scene::after{content:"";position:absolute;inset:0;background:linear-gradient(0deg,rgba(0,0,0,.85),transparent 60%)}
.scene .in{position:relative;z-index:2;padding:0 max(22px,6vw) 12vh;max-width:1100px}
.scene .n{font:600 .8rem var(--body);letter-spacing:.4em;color:var(--gold);text-transform:uppercase}
.scene h1,.scene h2{font:600 clamp(3rem,9vw,8.4rem)/.92 var(--head);text-transform:uppercase;margin:14px 0 20px;letter-spacing:.01em;color:#fff}
.scene h2{font-size:clamp(2.4rem,6.5vw,6rem)}.scene h1 em,.scene h2 em{font-style:normal;color:var(--gold)}
.scene p{color:rgba(255,255,255,.78);max-width:560px;font-size:1.08rem;margin:0 0 26px}
.scene .t{opacity:0;transform:translateY(60px);transition:opacity 1s .3s,transform 1.1s .3s cubic-bezier(.2,.8,.2,1)}.scene.live .t{opacity:1;transform:none}.scene.live .t+.t{transition-delay:.5s}
.cta{display:inline-flex;padding:16px 30px;background:var(--gold);color:#111;font:700 .85rem var(--body);letter-spacing:.18em;text-transform:uppercase;text-decoration:none;clip-path:polygon(0 0,100% 0,92% 100%,0 100%);transition:padding .3s}
.cta:hover{padding-right:44px}.cta.ghost{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.4);clip-path:none}
.dots{position:fixed;right:22px;top:50%;transform:translateY(-50%);z-index:30;display:grid;gap:12px}.dots a{width:9px;height:9px;border-radius:50%;background:rgba(255,255,255,.35);display:block;transition:transform .3s,background .3s}.dots a.on{background:var(--gold);transform:scale(1.6)}
.logo{position:fixed;left:max(22px,6vw);top:24px;z-index:30}.logo img{height:44px;width:auto}.logo span{font:600 1.3rem var(--head);color:#fff;letter-spacing:.1em;text-transform:uppercase}@media (max-width:600px){.logo span{display:block;font-size:.95rem;letter-spacing:.05em;line-height:1.15;max-width:calc(100vw - 190px)}}
.bk{position:fixed;right:22px;top:20px;z-index:30}
.glass{background:rgba(10,10,10,.55);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.12);border-radius:22px;padding:26px 28px;max-width:720px}
.glass .tb{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.glass .tb button{background:transparent;border:1px solid rgba(255,255,255,.25);color:#fff;padding:9px 16px;border-radius:999px;font:600 .75rem var(--body);letter-spacing:.12em;text-transform:uppercase;cursor:pointer}
.glass .tb button.on{background:var(--gold);color:#111;border-color:var(--gold)}.glass ul{list-style:none;margin:0;padding:0}.glass li{display:flex;justify-content:space-between;gap:20px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.1);color:#fff}
.glass li b{color:var(--gold)}.glass li em{display:none}
.strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}.strip img{height:30vh;width:auto;border-radius:12px}
.qs{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.qs div{color:#fff;font-size:.98rem}.qs span{display:block;color:var(--gold);font-size:.8rem;margin-top:6px;letter-spacing:.1em;text-transform:uppercase}
.st{display:flex;gap:44px;flex-wrap:wrap;margin-top:30px}.st b{display:block;font:600 3rem var(--head);color:var(--gold)}.st span{color:rgba(255,255,255,.65);font-size:.8rem;letter-spacing:.14em;text-transform:uppercase}
.vis{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:end}.vis ul{list-style:none;padding:0;margin:0 0 20px;color:#fff}.vis li{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.12);font-size:.92rem}
.vis .map{height:300px;border-radius:18px;overflow:hidden}.foot{color:rgba(255,255,255,.5);font-size:.75rem;margin-top:24px}
@media (max-width:900px){.vis{grid-template-columns:1fr}.dots{display:none}.scene .in{padding-bottom:9vh}.strip img{height:24vh}.vis .map{height:200px}}
@media (max-height:740px){.scene h1,.scene h2{font-size:clamp(2.2rem,7vw,5rem)}}
"""
CINEMA_JS = """
const sc=[...document.querySelectorAll('.scene')],dt=document.querySelector('.dots');sc.forEach((s,i)=>{const a=document.createElement('a');a.href='#'+s.id;dt.appendChild(a)});
const so3=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){sc.forEach(s=>s.classList.toggle('live',s===x.target));[...dt.children].forEach((d,i)=>d.classList.toggle('on',sc[i]===x.target))}}),{threshold:.55});sc.forEach(s=>so3.observe(s));
setTimeout(()=>sc[0].classList.add('live'),200);
"""


def cinema(a):
    c = a["c"]
    h1 = c["h1"]
    tabs, panes = menu_html(c, "m")
    strip = "".join(f'<img src="{g}" alt="" loading="lazy">' for g in a["gal"])
    qs = "".join(f'<div>“{e(t)}”<span>{e(au)}</span></div>' for t, au in c["reviews"][:3])
    st = "".join(f'<div><b data-to="{e(v)}">{e(v)}</b><span>{e(l)}</span></div>' for v, l in c["stats"])
    hours = "".join(f"<li><span>{e(d)}</span><b>{e(t)}</b></li>" for d, t in c["hours"])
    sp = c.get("special")
    logo = f'<img src="{a["logo"]}" alt="{e(c["name"])}">' if a["logo"] else f'<span>{e(c["short"])}</span>'
    bgs = a["hero"] + a["exp"] + a["gal"]
    def bg(i):
        return f'<div class="bg" style="background-image:url({bgs[i % len(bgs)]})"></div>'
    scenes = [
        f'<section class="scene" id="s1">{bg(0)}<div class="in"><p class="n t">{e(c["kicker"])}</p><h1 class="t">{e(h1[0])}<br>{e(h1[1])}<br><em>{e(h1[2])}</em></h1><p class="t">{e(c["lead"])}</p>'
        f'<div class="t" style="display:flex;gap:12px;flex-wrap:wrap"><a class="cta" href="{e(a["book"])}">{e(a["book_label"])}</a><a class="cta ghost" href="#s3">Services</a></div></div></section>',
        f'<section class="scene" id="s2">{bg(len(a["hero"]))}<div class="in"><p class="n t">01 · The experience</p><h2 class="t">{e(c["experience"]["title"])}</h2><p class="t">{e(c["experience"]["text"])}</p><div class="st t">{st}</div></div></section>',
        f'<section class="scene" id="s3">{bg(1)}<div class="in"><p class="n t">02 · Services</p><div class="glass t" data-tabs><div class="tb">{tabs}</div>{panes}<p style="color:rgba(255,255,255,.6);font-size:.82rem;margin:14px 0 0">{e(c.get("currency_note", ""))}</p></div></div></section>',
    ]
    if sp:
        scenes.append(f'<section class="scene" id="s4">{bg(len(a["hero"]) + 1)}<div class="in"><p class="n t">03 · {e(sp["kicker"])}</p><h2 class="t">{e(sp["title"])}</h2><p class="t">{e(sp["text"])}</p><a class="cta t" href="{e(a["book"])}">{e(sp["cta"])}</a></div></section>')
    scenes += [
        f'<section class="scene" id="s5">{bg(2)}<div class="in" style="max-width:none"><p class="n t">The work</p><div class="strip t">{strip}</div><div class="qs t" style="margin-top:26px">{qs}</div></div></section>',
        f'<section class="scene" id="s6">{bg(len(a["hero"]) + 2)}<div class="in" style="max-width:none"><p class="n t">Visit</p><h2 class="t">Find <em>us</em></h2><div class="vis t"><div><p>{e(c["address"])}</p><ul>{hours}</ul>'
        f'<a class="cta" href="{e(a["book"])}">{e(a["book_label"])}</a> <a class="cta ghost" href="tel:{e(c["phone"].replace(" ", ""))}">{e(c["phone"])}</a></div>'
        f'<div class="map"><iframe class="mapf" loading="lazy" title="Map" src="https://maps.google.com/maps?q={a["lat"]},{a["lng"]}&z=16&output=embed"></iframe></div></div><p class="foot">{footer_line(c)}</p></div></section>']
    return (head(a) + "}" + BASE_CSS + CINEMA_CSS + "</style></head><body>"
            f'<a class="logo" href="#s1">{logo}</a><a class="cta bk" href="{e(a["book"])}">{e(a["book_label"])}</a><nav class="dots"></nav>' + "".join(scenes) +
            "<script>" + COMMON_JS + CINEMA_JS + "</script></body></html>")


LAYOUTS = {"editorial": editorial, "split": split, "bold": bold, "cinema": cinema}
