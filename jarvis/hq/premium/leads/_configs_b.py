"""Configs for Vox Hairdressing, Hair In The City and Scammells Barber Shop (26 Oct 2026), from their own websites and Google."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _configs_a import reviews, hours, save  # noqa: E402

r, p = reviews("vox-hairdressing")
save("vox-hairdressing", {
    "name": "Vox Hairdressing", "short": "Vox", "kicker": "50 Port Street · Manchester's Northern Quarter",
    "h1": ["Precision cuts.", "Bespoke colour.", "Effortless blonde."],
    "lead": "A boutique salon in the heart of the Northern Quarter since 2013, specialising in precision cutting, bespoke colour and low-maintenance balayage. Kevin Murphy colour and styling, sulphate-free and cruelty-free.",
    "colours": {"bg": "#0e1615", "panel": "#15201f", "ink": "#f5eee8", "muted": "#a7b2ae", "gold": "#e08a5c", "second": "#c98b84"},
    "motif": "classic", "logo": "logo0.png", "logo_light": True, "brand_text": False,
    "hero": ["s/56.jpg", "s/38.jpg", "s/31.jpg", "s/07.jpg"],
    "experience": {"title": "Rebuilt with intention", "text": "Our salon was stripped back and rebuilt, from lighting and layout to bespoke handmade workstations and refreshment areas, to feel calm, welcoming and quietly luxurious. Every appointment begins with a detailed consultation.", "photos": ["s/46.jpg", "s/30.jpg"]},
    "services": [
        {"group": "Cutting", "items": [["Restyle (a big change)", "£66 / £51"], ["Mid to long (below the ears)", "£61 / £45"], ["Short creative (above the ears)", "£48 / £40"], ["Clipper cut", "£43"], ["Extra long (below the waist)", "£66 / £51"]]},
        {"group": "Styling & tint", "items": [["Wash & blow dry", "£40 / £30"], ["Hair up", "£44"], ["Regrowth tint", "£61 / £40"], ["Full head tint", "£67 / £50"]]},
        {"group": "Blonde packages", "items": [["Face framing highlights", "£100 / £85"], ["Half head, low-maintenance blonde", "£145 / £115"], ["Full head, low-maintenance blonde", "£175 / £145"]]}],
    "currency_note": "A genderless menu, priced by length, time and complexity. Senior stylist / graduate stylist. Cuts include wash & blow dry.",
    "special": {"kicker": "New to Vox?", "title": "10% off your first visit", "text": "New clients get 10% off. Tell us about your hair, your routine and what you want to achieve, and we'll design something that works with your lifestyle.", "cta": "Book your first visit"},
    "gallery": ["s/41.jpg", "s/53.jpg", "s/12.jpg", "s/45.jpg", "s/49.jpg", "s/27.jpg", "s/16.jpg", "s/21.jpg", "s/44.jpg"],
    "reviews": r, "stats": [["4.9", "Google rating"], ["711", "Google reviews"], ["2013", "established"], ["10%", "off for new clients"]],
    "hours": hours(p), "address": "50 Port Street, Manchester M1 2EQ", "phone": "0161 637 4077",
    "book_url": "https://www.voxhairdressing.com/bookings-manchester-hairdressers", "book_label": "Book online",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "voxhairdressing"})

r, p = reviews("hair-in-the-city")
save("hair-in-the-city", {
    "name": "Hair In The City", "short": "Hair In The City", "kicker": "14 High Street · Glasgow's Merchant City",
    "h1": ["Award-winning", "colour specialists.", "Since 2013."],
    "lead": "A Keune Gold Ambassador salon on Glasgow's oldest street, renowned for signature balayage, lived-in blondes, advanced colour rescues and the safest extensions.",
    "colours": {"bg": "#141313", "panel": "#1d1b1b", "ink": "#f4f1ef", "muted": "#ada4a0", "gold": "#cba894", "second": "#e8d2c4"},
    "motif": "classic", "logo": "logo0.png", "logo_light": True, "brand_text": False,
    "hero": ["g/00.jpg", "g/05.jpg", "g/04.jpg"],
    "experience": {"title": "Your hair's integrity comes first", "text": "Our passionate, highly trained team listen and guide you through a thorough consultation, giving you an honest, professional opinion. Led by Salon Director Louise Wilson, a former professional colour educator with over 25 years in hairdressing.", "photos": ["s/01.jpg", "g/04.jpg"]},
    "services": [
        {"group": "Cut & colour", "items": [["Consultation", "from £20"], ["Cut & style", "£23.50 – £50"], ["Balayage", "£97.50 – £145"], ["Signature balayage & blend", "from £110"], ["Foiling", "£65 – £145"], ["Tinting & toning", "£67.50 – £145"], ["Advanced colour correction", "on consultation"]]},
        {"group": "Treatments", "items": [["Keune hair treatments", "from £67.50"], ["Keune permanent straightening", "£200"], ["Keracalm smoothing", "£10 – £140"]]},
        {"group": "Extensions", "items": [["Remi Cachet flat bond extensions", "from £250"], ["Tape extension refits", "from £75"], ["Extension fitting only", "from £75"]]}],
    "currency_note": "All prices are from and confirmed on consultation.",
    "special": {"kicker": "For everyone", "title": "A private room, at no extra cost", "text": "Our fully enclosed private hairdressing room gives a secure, female-only space for hijab-friendly appointments, or simply for anyone who'd like more privacy.", "cta": "Book the private room"},
    "gallery": ["g/04.jpg", "g/09.jpg", "g/07.jpg", "g/08.jpg", "g/03.jpg", "s/00.jpg", "s/01.jpg", "g/05.jpg"],
    "reviews": r, "stats": [["4.9", "Google rating"], ["687", "Google reviews"], ["25+", "years' experience"], ["2013", "established"]],
    "hours": hours(p), "address": "14 High Street, Glasgow G1 1NL", "phone": "0141 552 2848",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "hairinthecity"})

r, p = reviews("scammells-barber-shop")
save("scammells-barber-shop", {
    "name": "Scammells Barber Shop", "short": "Scammells", "kicker": "47 Broad Street · Staple Hill, Bristol",
    "h1": ["Award-winning", "barbering.", "Since 1992."],
    "lead": "Expert haircuts, beard grooming and luxury hot towel shaves, with customers from all over the West Country. By appointment only.",
    "colours": {"bg": "#100f0e", "panel": "#191715", "ink": "#f3efe7", "muted": "#a59d90", "gold": "#d4b26a", "second": "#c8453b"},
    "motif": "classic", "logo": "logo0.png", "logo_light": True,
    "hero": ["g/00.jpg", "g/04.jpg", "s/01.jpg"],
    "experience": {"title": "From a son's first haircut to retired gentlemen", "text": "We welcome all ages. Our highly skilled barbers use top-quality products from around the world, including Reuzel, Layrite, Kent Brushes, Proraso and Mariner Jack, all available to buy after your visit.", "photos": ["s/01.jpg", "s/02.jpg"]},
    "services": [
        {"group": "Men", "items": [["Men's haircut", "£23"], ["Skin fade", "£26"], ["Restyle", "£26"], ["Long hair", "£27"], ["Buzz cut", "£14"], ["Head shave with electric foils", "£21"], ["Retired gentlemen (65+)", "£15"]]},
        {"group": "Boys", "items": [["Boys' haircut (under 15)", "£19"], ["Boys' skin fade", "£22"], ["Boys' restyle", "£22"], ["Boys' long haircut", "£24"]]},
        {"group": "Beards", "items": [["Beard trim", "£14"], ["Beard trim with hot towel line-out", "£21"], ["Beard trim & haircut", "£37"], ["Beard trim & skin fade", "£39"]]}],
    "currency_note": "Appointments only, so book ahead to secure your chair.",
    "special": {"kicker": "Since 1992", "title": "The hot towel line-out", "text": "Hot and cold towels, balms and a cut-throat razor: our beard trim with hot towel line-out is the finishing touch our regulars come back for.", "cta": "Book an appointment"},
    "gallery": ["g/07.jpg", "g/09.jpg", "g/04.jpg", "g/03.jpg", "s/02.jpg", "g/02.jpg", "g/05.jpg", "s/04.jpg"],
    "reviews": r, "stats": [["4.9", "Google rating"], ["675", "Google reviews"], ["1992", "established"], ["£14", "beard trims"]],
    "hours": hours(p), "address": "47 Broad Street, Staple Hill, Bristol BS16 5LS", "phone": "0117 957 1900",
    "book_url": "https://scammellsbarbershop.co.uk/", "book_label": "Book online",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "scammellsbarbershop"})
