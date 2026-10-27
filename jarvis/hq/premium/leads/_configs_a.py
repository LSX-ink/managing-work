"""Configs for 281 Hair, Prestige Hair & Beauty and Fade barber (26 Oct 2026), from their own websites and Google listings."""
import json
from pathlib import Path

L = Path(__file__).parent


def reviews(slug, n=4, cut=2):
    p = json.load(open(L / slug / "place.json", encoding="utf-8"))
    out = []
    for v in p.get("reviews", []):
        t = (v.get("originalText") or v.get("text") or {}).get("text", "").replace("\n", " ").strip()
        if v.get("rating") == 5 and t:
            out.append([". ".join(t.split(". ")[:cut]).rstrip(".") + ".", v["authorAttribution"]["displayName"]])
    return out[:n], p


def hours(p):
    return [d.replace(" ", " ").replace(" ", " ").split(": ", 1) for d in (p.get("regularOpeningHours") or {}).get("weekdayDescriptions", [])]


def save(slug, cfg):
    json.dump(cfg, open(L / slug / "config.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(slug, "ok")



def _run():
    r, p = reviews("281-hair-hairdressers-glasgow")
    save("281-hair-hairdressers-glasgow", {
        "name": "281 Hair", "short": "281 Hair", "kicker": "Sauchiehall Street · Glasgow city centre",
        "h1": ["Fabulous colour.", "Fantastic styles.", "Feel transformed."],
        "lead": "A Glasgow city-centre salon for cuts, blow-drys and bespoke colour, with colour correction as our speciality. L'Oréal Professionnel, Olaplex, Milkshake and Wella.",
        "colours": {"bg": "#110f0d", "panel": "#1a1714", "ink": "#f4efe6", "muted": "#a99c88", "gold": "#cfa851", "second": "#b65a43"},
        "motif": "classic", "logo": "logo.png", "brand_text": False,
        "hero": ["g/00.jpg", "g/02.jpg", "s/03.jpg", "g/01.jpg"],
        "experience": {"title": "Total care for your hair", "text": "Our experienced stylists offer everything from cuts and blow-drys to full-scale bespoke colour. Every new look starts with a free consultation, so the treatment suits you, and we go the extra mile to get you what you really want.", "photos": ["g/00.jpg", "g/04.jpg"]},
        "services": [
            {"group": "Colour", "items": [["Root tint & blow dry", "from £80"], ["Full head tint with partial foils & blow dry", "£110"], ["Vivid or fashion colour add-on", "£35"]]},
            {"group": "Blonde & bleach", "items": [["Bleach roots, tone & blow dry", "from £100"], ["Roots at 6–8 weeks", "from £115"], ["Short hair or pixie, full head bleach & tone", "from £125"], ["Global full head bleach & tone", "from £160"]]},
            {"group": "Treatments", "items": [["Goldwell deep conditioning mask (add-on)", "£16.50"], ["Olaplex treatment (add-on)", "£30"]]}],
        "currency_note": "10% student discount on selected services. Prices may vary with length and thickness; colour starts with a free consultation.",
        "special": {"kicker": "Our speciality", "title": "Colour correction", "text": "Bespoke colour and colour correction are what we do best. Book a free consultation and we'll work out exactly what your hair needs before we start.", "cta": "Book a free consultation"},
        "gallery": ["g/09.jpg", "g/08.jpg", "g/06.jpg", "g/04.jpg", "g/00.jpg", "s/03.jpg", "g/01.jpg"],
        "reviews": r, "stats": [["4.9", "Google rating"], ["1,539", "Google reviews"], ["Free", "consultations"], ["7", "days a week"]],
        "hours": hours(p), "address": "First Floor, 281 Sauchiehall Street, Glasgow G2 3HQ", "phone": "0141 332 0707",
        "book_url": "https://281hair.co.uk/book/", "book_label": "Book online",
        "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "281hair"})

    r, p = reviews("prestige-hair-beauty-west-croydon")
    save("prestige-hair-beauty-west-croydon", {
        "name": "Prestige Hair & Beauty", "short": "Prestige", "kicker": "22 London Road · West Croydon",
        "h1": ["Brows, lashes,", "nails and hair.", "Make it Prestige."],
        "lead": "A family-run South London salon for more than 10 years. Threading, lashes, facials, nails and hair, all done by highly trained specialists.",
        "colours": {"bg": "#170e1d", "panel": "#21162a", "ink": "#f6eff4", "muted": "#b3a2b9", "gold": "#e8cd95", "second": "#a487b4"},
        "motif": "classic", "logo": "logo.png",
        "hero": ["s/10.jpg", "s/02.jpg", "g/02.jpg", "s/21.jpg"],
        "experience": {"title": "Everyone is beautiful in their own way", "text": "We celebrate diversity and inclusivity, with a team of warm and inviting specialists here for all of your beauty needs. From a simple, subtle manicure to a glamorous blow-dry, we've got you covered, so you leave feeling Prestige.", "photos": ["s/01.jpg", "g/03.jpg"]},
        "services": [
            {"group": "Brows & threading", "items": [["Eyebrow threading", "from £6"], ["Upper lip", "from £4"], ["Full face (includes eyebrows)", "from £22"], ["Henna brows", "£30"], ["HD brows", "£42"]]},
            {"group": "Lashes", "items": [["Eyelash lift", "from £35"], ["Pro lash extensions, natural", "from £35"], ["Mink lashes", "from £60"], ["Russian lashes", "from £80"]]},
            {"group": "Facials", "items": [["Deep cleansing facial", "from £35"], ["Gold facial", "from £50"], ["LED facial", "from £80"], ["BB Glow facial, face & neck", "from £150"]]}],
        "currency_note": "Prices for the 22 London Road branch. Also in Thornton Heath and Kingston.",
        "special": {"kicker": "Since 2014", "title": "Family-run, South London proud", "text": "For more than 10 years we've been a trusted choice in the South London community, now in Croydon, Thornton Heath and Kingston, with the latest technology and highly specialised staff.", "cta": "Book your visit"},
        "gallery": ["g/03.jpg", "g/05.jpg", "g/06.jpg", "s/17.jpg", "s/04.jpg", "g/04.jpg", "s/19.jpg", "g/09.jpg", "g/02.jpg"],
        "reviews": r, "stats": [["4.8", "Google rating"], ["2,539", "Google reviews"], ["3", "South London salons"], ["7", "days a week"]],
        "hours": hours(p), "address": "22 London Road, Croydon CR0 2TA", "phone": "020 8667 0066",
        "book_url": "https://www.prestigehairandbeauty.co.uk/price-list", "book_label": "Book online",
        "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": ""})

    r, p = reviews("fade-barber")
    save("fade-barber", {
        "name": "Fade Barber", "short": "Fade Barber", "kicker": "389 Humberstone Road · Leicester",
        "h1": ["Clean fades.", "Sharp lines.", "Every time."],
        "lead": "Skin fades with precision and attention to detail, friendly barbers and a great atmosphere. Walk in on Humberstone Road, seven days a week.",
        "colours": {"bg": "#0b0b0b", "panel": "#141311", "ink": "#f2efe8", "muted": "#9d988d", "gold": "#cba557", "second": "#e8e2d4"},
        "motif": "classic", "logo": "",
        "hero": ["g/05.jpg", "g/09.jpg", "g/03.jpg", "g/06.jpg"],
        "experience": {"title": "Finding a new barber is never easy", "text": "That's what our customers say before they find us. Our barbers take their time, even at closing, and deliver skin fades that are super clean, sharp and exactly what you asked for. Parents trust us with their kids too.", "photos": ["g/09.jpg", "g/08.jpg"]},
        "services": [
            {"group": "Cuts", "items": [["Skin fades", ""], ["Tapers & classic cuts", ""], ["Kids' cuts", ""]]},
            {"group": "Extras", "items": [["Face masks", ""], ["Line-ups", ""]]}],
        "currency_note": "Walk-ins welcome. Ask in store for today's prices.",
        "special": None,
        "gallery": ["g/09.jpg", "g/08.jpg", "g/01.jpg", "g/07.jpg", "g/02.jpg", "g/04.jpg", "g/06.jpg", "g/03.jpg"],
        "reviews": r, "stats": [["5.0", "Google rating"], ["726", "Google reviews"], ["7", "days a week"], ["9am", "doors open"]],
        "hours": hours(p), "address": "389 Humberstone Road, Leicester LE5 3DF", "phone": "07763 636398",
        "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "fade.barberlc_"})


if __name__ == "__main__":
    _run()
