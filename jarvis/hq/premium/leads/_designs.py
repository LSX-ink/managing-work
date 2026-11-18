"""A different design for each business (owner, 26 Oct 2026: "don't use the same design for every creation ... so the websites
for all look different"). Run after the _configs_*.py scripts; Moroccan Barber keeps the original atelier design (owner liked it)."""
import json
from pathlib import Path

L = Path(__file__).parent
DESIGNS = {
    # editorial (light magazine) x3, each in its own fonts and paper colour
    "281-hair-hairdressers-glasgow": {"layout": "editorial", "fonts": "editorial", "paper": "#f7f1e6", "text": "#1c1813", "soft": "#6b6153", "rule": "#e0d4bf", "gold": "#a97c22"},
    "hair-in-the-city": {"layout": "editorial", "fonts": "fashion", "paper": "#f6efea", "text": "#1b1717", "soft": "#6e6460", "rule": "#e3d6cf", "gold": "#9a6b55"},
    "the-dandy-gent-barber-shop-nottm": {"layout": "editorial", "fonts": "vintage", "paper": "#efe6d2", "text": "#1f1a14", "soft": "#665a48", "rule": "#d6c8a8", "gold": "#8a2f2a"},
    # split (fixed photo panel) x2
    "vox-hairdressing": {"layout": "split", "fonts": "split"},
    "melissa-timperley-hair-salon": {"layout": "split", "fonts": "fashion"},
    # bold (giant type, colour blocks) x2
    "prestige-hair-beauty-west-croydon": {"layout": "bold", "fonts": "bold"},
    "sans-barber": {"layout": "bold", "fonts": "cinema"},
    # cinema (full-screen scenes) x2
    "fade-barber": {"layout": "cinema", "fonts": "cinema"},
    "scammells-barber-shop": {"layout": "cinema", "fonts": "vintage"},
}
for slug, d in DESIGNS.items():
    f = L / slug / "config.json"
    c = json.load(open(f, encoding="utf-8"))
    c["layout"], c["fonts"] = d["layout"], d["fonts"]
    for k in ("paper", "text", "soft", "rule"):
        if k in d:
            c["colours"][k] = d[k]
    if "gold" in d:  # light pages need a darker accent to read on paper
        c["colours"]["gold"] = d["gold"]
    json.dump(c, open(f, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(slug, d["layout"], d["fonts"])
