"""Copy each business's real site findings and current-homepage screenshot (from their first mock-up) into its premium config."""
import json, shutil
from pathlib import Path
L = Path(__file__).parent; M = Path(r"C:\Users\Thato\kinetic-repo\kinetic-live\m")
A = json.load(open(L / "_audits.json", encoding="utf-8"))
for slug, au in A.items():
    f = L / slug / "config.json"; c = json.load(open(f, encoding="utf-8")); c["audit"] = au
    json.dump(c, open(f, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    shutil.copy(M / slug / "before.jpg", L / slug / "before.jpg")
    print(slug, len(au["fixes"]), "fixes")
