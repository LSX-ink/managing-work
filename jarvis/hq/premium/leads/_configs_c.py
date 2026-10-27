"""Configs for Melissa Timperley Salons, Sans Barber and The Dandy Gent Nottingham (26 Oct 2026), from their own sites and Google.
None of the three publish prices on their websites, so services are listed without prices (never invented)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _configs_a import reviews, hours, save  # noqa: E402

r, p = reviews("melissa-timperley-hair-salon")
save("melissa-timperley-hair-salon", {
    "name": "Melissa Timperley Salons", "short": "Melissa Timperley", "kicker": "67 Tib Street · Manchester city centre",
    "h1": ["Best Salon", "in the UK.", "Twice."],
    "lead": "A stylish three-floor salon in Manchester city centre, renowned for exceptional client experiences and led by some of the UK's best stylists.",
    "colours": {"bg": "#0f1724", "panel": "#162033", "ink": "#f3f6fa", "muted": "#9fadc2", "gold": "#5fc9c1", "second": "#eab3c2"},
    "motif": "classic", "logo": "logo10.png", "brand_text": True,
    "hero": ["s/00.jpg", "s/13.jpg", "s/24.jpg"],
    "experience": {"title": "Exceptional, for everyone", "text": "A super-precise cut and styling that complements your features. Afro and curly hair specialists, a hijab-friendly private space, an LGBTQ+ friendly salon, and discreet appointments for high-profile clients.", "photos": ["s/31.jpg", "s/02.jpg"]},
    "services": [
        {"group": "Cut & style", "items": [["Precision cut & style", ""], ["Men's hair", ""], ["Curly hair", ""], ["Afro hair", ""]]},
        {"group": "Colour", "items": [["Colour", ""], ["Balayage", ""], ["Highlights", ""], ["Grey blending", ""]]},
        {"group": "Treatments", "items": [["Fabriq smoothing treatment", ""], ["K18 treatment", ""]]}],
    "currency_note": "See the full price list and book online.",
    "special": {"kicker": "Multi-award-winning", "title": "Best Salon in the UK, 2021 & 2023", "text": "British Hairdressing Business Awards. Plus Best Customer Service, Best Client Experience, Best Salon Team of the Year, Afro Hairdresser of the Year and Independent Salon of the Year.", "cta": "Book an appointment"},
    "gallery": ["s/46.jpg", "s/40.jpg", "s/45.jpg", "s/56.jpg", "s/51.jpg", "s/35.jpg", "s/05.jpg", "s/39.jpg", "s/49.jpg"],
    "reviews": r, "stats": [["4.9", "Google rating"], ["674", "Google reviews"], ["3", "floors of salon"], ["2×", "Best Salon in the UK"]],
    "hours": hours(p), "address": "67 Tib Street, Manchester M4 1LS", "phone": "0161 834 5945",
    "book_url": "https://www.melissa-salons.com/", "book_label": "Book online",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "melissasalons"})

r, p = reviews("sans-barber")
save("sans-barber", {
    "name": "Sans Barber", "short": "Sans Barber", "kicker": "150 Mansfield Road · Nottingham",
    "h1": ["Smooth fades.", "Clean cuts.", "Impeccable service."],
    "lead": "A Nottingham barbers with years of experience and the latest tools. Walk in, take a seat, grab a drink, and leave looking fresh and clean.",
    "colours": {"bg": "#061014", "panel": "#0c1a1f", "ink": "#f2ece4", "muted": "#9aa6a8", "gold": "#e8d2b8", "second": "#c99a5b"},
    "motif": "classic", "logo": "logo0.png", "brand_text": False,
    "hero": ["g/00.jpg", "g/03.jpg", "g/04.jpg"],
    "experience": {"title": "We take pride in what we do", "text": "Our years of experience have put us in a legendary position in Nottingham. We've worked on all types of hair and styles, and we want you treated well and comfortably while you wait, with snacks and drinks on us.", "photos": ["s/05.jpg", "s/04.jpg"]},
    "services": [
        {"group": "Cuts", "items": [["Skin fades", ""], ["Clean cuts & tapers", ""], ["Kids' cuts", ""]]},
        {"group": "Finish", "items": [["Hot towel", ""], ["Line-ups", ""]]}],
    "currency_note": "Walk-ins only, no appointments. Last entry 30 minutes before closing.",
    "special": {"kicker": "The finishing touch", "title": "The hot towel", "text": "The ultimate way to end your cut with us: a relaxing, sensational experience that softens the beard, opens the pores and leaves your face clean.", "cta": "Find us"},
    "gallery": ["s/03.jpg", "s/10.jpg", "g/09.jpg", "g/08.jpg", "s/06.jpg", "s/11.jpg", "g/02.jpg", "s/09.jpg"],
    "reviews": r, "stats": [["4.9", "Google rating"], ["673", "Google reviews"], ["9pm", "open till, Mon–Sat"], ["Walk-ins", "only, no booking"]],
    "hours": hours(p), "address": "150 Mansfield Road, Nottingham NG1 3HW", "phone": "07870 703090",
    "book_url": "https://maps.google.com/?q=Sans+Barber+150+Mansfield+Road+Nottingham", "book_label": "Get directions",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "sansbarbers"})

r, p = reviews("the-dandy-gent-barber-shop-nottm")
save("the-dandy-gent-barber-shop-nottm", {
    "name": "The Dandy Gent", "short": "The Dandy Gent", "kicker": "5 Heathcoat Street · Hockley, Nottingham",
    "h1": ["Traditional", "barbershop.", "Handmade in Britain."],
    "lead": "A relaxed, second-to-none barbershop experience and the makers of handmade beard oils, moustache wax, colognes and wet-shave goods, chosen by barbers across the UK.",
    "colours": {"bg": "#101411", "panel": "#171d18", "ink": "#f2efe6", "muted": "#a3a693", "gold": "#c9ad7f", "second": "#c0453f"},
    "motif": "classic", "logo": "logo0.png", "logo_light": True,
    "hero": ["g/09.jpg", "g/03.jpg", "g/02.jpg"],
    "experience": {"title": "Our barbershop heritage", "text": "At just 10 years old, Shane O'Shaughnessy began his barber apprenticeship under his beloved grandad, David Keithley. Today the quality of our barbers and our relaxed experience earn 5-star ratings at all three of our East Midlands shops.", "photos": ["g/03.jpg", "g/00.jpg"]},
    "services": [
        {"group": "Barbering", "items": [["Haircuts", ""], ["Low fades", ""], ["Beard grooming", ""], ["Traditional wet shave", ""]]},
        {"group": "Our products", "items": [["Beard oils & balms", ""], ["Moustache wax", "from £8.99"], ["Colognes & aftershaves", ""], ["Wet-shave essentials", ""]]}],
    "currency_note": "Book online in seconds. Free UK delivery on product orders over £25.",
    "special": {"kicker": "Made by barbers", "title": "Handmade in Britain", "text": "UK-sourced ingredients only. Our ever-expanding range of handmade grooming products is THE choice of barbers across the UK and beyond.", "cta": "Book your chair"},
    "gallery": ["g/02.jpg", "g/03.jpg", "g/00.jpg", "g/06.jpg", "g/07.jpg", "g/04.jpg", "g/05.jpg", "g/01.jpg"],
    "reviews": r, "stats": [["5.0", "Google rating"], ["631", "Google reviews"], ["3", "East Midlands shops"], ["Handmade", "in Britain"]],
    "hours": hours(p), "address": "5 Heathcoat Street, Hockley, Nottingham NG1 3AF", "phone": "0115 958 3999",
    "book_url": "https://thedandygent.co.uk/book-services-33-w.asp", "book_label": "Book online",
    "loc": [p["location"]["latitude"], p["location"]["longitude"]], "instagram": "thedandygentuk"})
