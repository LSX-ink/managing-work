"""Lens and picture-size maths for photo_calc: depth of field, hyperfocal distance, field of view, print size, crops.

Depth of field, field of view and crops pop up a drawn diagram (kinds "photo-dof", "photo-fov", "photo-crop",
drawn by frontend/popup-photo.js); print size is a table. Nothing is saved or fetched.
"""

import math

import photo_store as ps

for _kind in ("photo-dof", "photo-fov", "photo-crop"):
    ps.screen.EXTRA_KINDS.add(_kind)

PRINTS = [("6 x 4 in", 6, 4), ("7 x 5 in", 7, 5), ("10 x 8 in", 10, 8), ("12 x 8 in", 12, 8), ("A4", 8.27, 11.69),
          ("16 x 12 in", 16, 12), ("A3", 11.69, 16.54), ("20 x 16 in", 20, 16), ("A2", 16.54, 23.39),
          ("30 x 20 in", 30, 20)]
RATIOS = {"1:1": 1.0, "5:4": 1.25, "4:5": 0.8, "4:3": 4 / 3, "3:4": 0.75, "3:2": 1.5, "2:3": 2 / 3, "16:9": 16 / 9,
          "9:16": 9 / 16, "2:1": 2.0, "3:1": 3.0}


def _optics(a) -> tuple[float, float, float, float, float, str]:
    """(focal mm, f-number, distance m, circle of confusion mm, crop, sensor name)."""
    focal = ps.num(a("focal_mm"), "focal length", 4, 2000)
    n = ps.aperture(a("aperture"))
    name, _, _, crop = ps.sensor(a)
    return focal, n, ps.metres(a), 0.03 / crop, crop, name


def _limits(focal: float, n: float, s: float, coc: float) -> tuple[float, float, float]:
    """(hyperfocal m, near m, far m) with the far limit infinite past the hyperfocal distance."""
    h = (focal * focal / (n * coc) + focal) / 1000
    f = focal / 1000
    near = s * (h - f) / (h + s - 2 * f)
    far = s * (h - f) / (h - s) if s < h else math.inf
    return h, near, far


def dof(a) -> ps.Shown:
    focal, n, s, coc, crop, name = _optics(a)
    h, near, far = _limits(focal, n, s, coc)
    total = far - near
    data = {"focus": round(s, 3), "near": round(near, 3), "far": None if math.isinf(far) else round(far, 3),
            "hyperfocal": round(h, 2),
            "facts": [["Lens", f"{focal:g} mm at {ps.fmt_ap(n)} on {name}"], ["Focused at", ps.fmt_m(s)],
                      ["Sharp from", ps.fmt_m(near)], ["Sharp to", ps.fmt_m(far)],
                      ["Depth of field", "all the way back" if math.isinf(far) else ps.fmt_m(total)],
                      ["Hyperfocal", ps.fmt_m(h)]]}
    card = ps.screen.card("photo-dof", "Depth of field", "photo-dof", data=data)
    reach = "to infinity" if math.isinf(far) else f"to {ps.fmt_m(far)}"
    return ps.Shown(f"At {focal:g} mm, {ps.fmt_ap(n)}, focused at {ps.fmt_m(s)}, it's sharp from {ps.fmt_m(near)} {reach}.", card)


def hyperfocal(a) -> ps.Shown:
    focal = ps.num(a("focal_mm"), "focal length", 4, 2000)
    n = ps.aperture(a("aperture"))
    name, _, _, crop = ps.sensor(a)
    coc = 0.03 / crop
    h = (focal * focal / (n * coc) + focal) / 1000
    _, near_h, _ = _limits(focal, n, h, coc)
    rows = [["Hyperfocal distance", ps.fmt_m(h), f"{focal:g} mm at {ps.fmt_ap(n)} on {name}"],
            ["Sharp from", ps.fmt_m(near_h), "When focused at the hyperfocal distance"], ["Sharp to", "infinity", ""],
            ["Circle of confusion", f"{coc * 1000:.0f} µm", "Standard for the sensor size"]]
    spoken = f"Focus at {ps.fmt_m(h)} and everything from {ps.fmt_m(near_h)} to infinity is sharp."
    return ps.facts("Hyperfocal distance", rows, "photo-hyperfocal", spoken)


def _angle(size: float, focal: float) -> float:
    return math.degrees(2 * math.atan(size / (2 * focal)))


def fov(a) -> ps.Shown:
    focal = ps.num(a("focal_mm"), "focal length", 2, 3000)
    name, w, h, crop = ps.sensor(a)
    diag = math.hypot(w, h)
    dist = ps.metres(a) if a("distance_m") is not None or a("distance_ft") is not None else 10.0
    across = 2 * dist * math.tan(math.radians(_angle(w, focal) / 2))
    high = 2 * dist * math.tan(math.radians(_angle(h, focal) / 2))
    data = {"angle": round(_angle(w, focal), 1), "distance": round(dist, 2), "width": round(across, 2),
            "facts": [["Sensor", f"{name}, crop {crop:g}"], ["Angle of view", f"{_angle(w, focal):.1f}° wide, {_angle(h, focal):.1f}° tall"],
                      ["Diagonal", f"{_angle(diag, focal):.1f}°"], ["Full-frame equivalent", f"{focal * crop:.0f} mm"],
                      [f"Covers at {ps.fmt_m(dist)}", f"{across:.1f} m wide, {high:.1f} m tall"]]}
    card = ps.screen.card("photo-fov", "Field of view", "photo-fov", data=data)
    return ps.Shown(f"{focal:g} mm on {name} sees {_angle(w, focal):.0f} degrees across, like {focal * crop:.0f} mm on full frame; "
                    f"at {ps.fmt_m(dist)} that's {across:.1f} metres wide.", card)


def _print_table(w: float, h: float, dpi: float) -> ps.Shown:
    rows = []
    for label, pw, ph in PRINTS:
        long_side, short_side = max(w, h), min(w, h)
        got = min(long_side / max(pw, ph), short_side / min(pw, ph))
        verdict = "Excellent" if got >= 300 else "Good" if got >= 200 else "Fine at arm's length" if got >= 150 else "Too soft"
        rows.append([label, f"{got:.0f} dpi", verdict])
    table = ps.table(f"Print sizes for {w:g} x {h:g} px", ["Print", "Sharpness", "Verdict"], rows, "photo-print")
    return ps.Shown(f"{w:g} by {h:g} pixels prints {w / dpi * 2.54:.0f} by {h / dpi * 2.54:.0f} centimetres at {dpi:g} dpi; the table shows common sizes.",
                    table)


def print_size(a) -> ps.Shown:
    dpi = ps.num(a("dpi") or 300, "dpi", 20, 1200)
    if a("width_px") is not None:
        return _print_table(ps.num(a("width_px"), "width", 1, 200_000), ps.num(a("height_px"), "height", 1, 200_000), dpi)
    if a("print_width") is None or a("print_height") is None:
        raise ValueError("Give the picture size in pixels (width_px and height_px) or a print size to work back from.")
    unit = str(a("print_unit") or "cm").lower()
    inch = 1 / 2.54 if unit == "cm" else 1.0
    pw, ph = ps.num(a("print_width"), "print width", 1, 5000) * inch, ps.num(a("print_height"), "print height", 1, 5000) * inch
    px_w, px_h = math.ceil(pw * dpi), math.ceil(ph * dpi)
    rows = [["Print", f"{pw * 2.54:.1f} x {ph * 2.54:.1f} cm ({pw:.1f} x {ph:.1f} in)"], ["Pixels needed", f"{px_w} x {px_h}"],
            ["Megapixels", f"{px_w * px_h / 1e6:.1f} MP"], ["At", f"{dpi:g} dpi"]]
    return ps.facts("Pixels for a print", rows, "photo-print", f"For that print at {dpi:g} dpi you need {px_w} by {px_h} pixels.")


def _ratio(value) -> float:
    text = str(value if value is not None else "").strip().lower().replace("x", ":").replace("/", ":")
    try:
        if ":" in text:
            top, bottom = text.split(":", 1)
            r = float(top) / float(bottom)
        else:
            r = float(text)
    except (ValueError, ZeroDivisionError):
        raise ValueError("Give the ratio like 16:9, 4:5 or 1:1.") from None
    if not 0.1 <= r <= 10:
        raise ValueError("That ratio doesn't look right.")
    return r


def _crop_box(w: float, h: float, ratio: float, anchor: str) -> tuple[int, int, int, int]:
    cw, ch = w, w / ratio
    if ch > h:
        cw, ch = h * ratio, h
    cw, ch = int(cw), int(ch)
    x = {"left": 0, "right": int(w) - cw}.get(anchor, (int(w) - cw) // 2)
    y = {"top": 0, "bottom": int(h) - ch}.get(anchor, (int(h) - ch) // 2)
    return cw, ch, x, y


def crop(a) -> ps.Shown:
    w = ps.num(a("width_px"), "width", 1, 200_000)
    h = ps.num(a("height_px"), "height", 1, 200_000)
    if a("ratio") is None:
        rows = []
        for label, r in RATIOS.items():
            cw, ch, _, _ = _crop_box(w, h, r, "centre")
            rows.append([label, f"{cw} x {ch}", f"{100 - cw * ch * 100 / (w * h):.0f}% trimmed"])
        table = ps.table(f"Crops of {w:g} x {h:g}", ["Ratio", "Crop size", "Lost"], rows, "photo-crop")
        return ps.Shown("Here is what each aspect ratio keeps from your picture.", table)
    label = str(a("ratio")).strip()
    anchor = str(a("anchor") or "centre").lower()
    cw, ch, x, y = _crop_box(w, h, _ratio(label), anchor)
    lost = 100 - cw * ch * 100 / (w * h)
    data = {"width": int(w), "height": int(h), "cw": cw, "ch": ch, "x": x, "y": y,
            "facts": [["Ratio", label], ["Crop size", f"{cw} x {ch} px"], ["Starts at", f"{x} across, {y} down"],
                      ["Trimmed", f"{lost:.0f}% of the picture"]]}
    card = ps.screen.card("photo-crop", f"Crop to {label}", "photo-crop", data=data)
    return ps.Shown(f"Crop to {label} keeps {cw} by {ch} pixels, trimming {lost:.0f} percent.", card)


ACTIONS = {"dof": dof, "hyperfocal": hyperfocal, "fov": fov, "print": print_size, "crop": crop}
