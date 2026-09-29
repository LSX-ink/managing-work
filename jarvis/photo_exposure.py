"""Exposure maths for photo_calc: equivalent exposures, EV, sunny 16, handheld limits, star trails, ND filters, flash.

Every function takes `a` (a getter for the tool arguments) and returns a Shown table. Nothing is saved or fetched.
"""

import math

import photo_store as ps

EV_SCENES = [(16, "Bright sun on sand or snow"), (15, "Bright sun, clear sky"), (14, "Hazy sun, soft shadows"),
             (13, "Bright cloud, no shadows"), (12, "Overcast sky"), (11, "Open shade or heavy overcast"),
             (9, "Sunset or a bright street at dusk"), (7, "Bright indoor room or street lights"),
             (5, "Home interior at night"), (2, "Moonlit landscape"), (-2, "Milky Way and starry sky")]
SUNNY = [("Sunny, hard shadows", 16), ("Slight overcast, soft shadows", 11), ("Overcast, faint shadows", 8),
         ("Heavy overcast, no shadows", 5.6), ("Open shade or sunset", 4)]
ND_FILTERS = [("ND2", 1), ("ND4", 2), ("ND8", 3), ("ND16", 4), ("ND64", 6), ("ND1000", 10), ("ND32000", 15)]


def _exposure_args(a) -> tuple[float, float, float]:
    return ps.aperture(a("aperture")), ps.shutter(a("shutter")), ps.num(a("iso") or 100, "ISO", 3, 5_000_000)


def _ev(n: float, t: float, iso: float) -> float:
    return math.log2(n * n / t) - math.log2(iso / 100)


def exposure(a) -> ps.Shown:
    n, t, iso = _exposure_args(a)
    new = {"aperture": a("new_aperture"), "shutter": a("new_shutter"), "iso": a("new_iso")}
    given = {k: v for k, v in new.items() if v is not None}
    light = t * iso / (n * n)
    if len(given) != 2:
        return _ladder(n, t, iso, light)
    n2 = ps.aperture(given["aperture"]) if "aperture" in given else None
    t2 = ps.shutter(given["shutter"]) if "shutter" in given else None
    iso2 = ps.num(given["iso"], "ISO", 3, 5_000_000) if "iso" in given else None
    if n2 is None:
        n2 = math.sqrt(t2 * iso2 / light)
    elif t2 is None:
        t2 = light * n2 * n2 / iso2
    else:
        iso2 = light * n2 * n2 / t2
    rows = [["Now", f"{ps.fmt_ap(n)}, {ps.fmt_shutter(t)}, ISO {iso:g}", f"EV100 {_ev(n, t, iso):.1f}"],
            ["Same exposure", f"{ps.fmt_ap(ps.nearest(n2, ps.APERTURES))}, {ps.fmt_shutter(ps.nearest(t2, ps.SHUTTERS) if t2 < 30 else t2)}, "
                              f"ISO {ps.nearest(iso2, ps.ISOS):g}", "Nearest standard settings"],
            ["Exact", f"f/{n2:.2f}, {t2:.4g} s, ISO {iso2:.0f}", ""],
            ["Aperture change", ps.stops(n * n / (n2 * n2)), "Positive means more light"],
            ["Shutter change", ps.stops(t2 / t), ""], ["ISO change", ps.stops(iso2 / iso), ""]]
    spoken = (f"To match {ps.fmt_ap(n)}, {ps.fmt_shutter(t)} at ISO {iso:g}, use {ps.fmt_ap(ps.nearest(n2, ps.APERTURES))}, "
              f"{ps.fmt_shutter(ps.nearest(t2, ps.SHUTTERS) if t2 < 30 else t2)} at ISO {ps.nearest(iso2, ps.ISOS):g}.")
    return ps.facts("Equivalent exposure", rows, "photo-exposure", spoken)


def _ladder(n: float, t: float, iso: float, light: float) -> ps.Shown:
    rows = []
    for ap in (1.4, 2, 2.8, 4, 5.6, 8, 11, 16):
        rows.append([ps.fmt_ap(ap), ps.fmt_shutter(ps.nearest(light * ap * ap / iso, ps.SHUTTERS)), f"ISO {iso:g}"])
    table = ps.table("Same exposure, different look", ["Aperture", "Shutter", "ISO"], rows, "photo-exposure")
    return ps.Shown(f"Equivalent exposures for {ps.fmt_ap(n)}, {ps.fmt_shutter(t)} at ISO {iso:g}: "
                           "each stop wider needs half the shutter time.", table)


def ev(a) -> ps.Shown:
    iso = ps.num(a("iso") or 100, "ISO", 3, 5_000_000)
    if a("ev") is not None:
        target = ps.num(a("ev"), "EV", -10, 25)
        n = ps.aperture(a("aperture"))
        t = n * n / 2 ** (target + math.log2(iso / 100))
        return ps.facts("Shutter for an EV", [["EV100", f"{target:g}"], ["Aperture", ps.fmt_ap(n)], ["ISO", f"{iso:g}"],
                                              ["Shutter", ps.fmt_shutter(ps.nearest(t, ps.SHUTTERS) if t < 30 else t)]],
                        "photo-ev", f"At EV {target:g}, {ps.fmt_ap(n)} and ISO {iso:g} need about {ps.fmt_shutter(t)}.")
    n, t, iso = _exposure_args(a)
    value = _ev(n, t, iso)
    scene = min(EV_SCENES, key=lambda s: abs(s[0] - value))[1]
    rows = [["EV at ISO 100", f"{value:.1f}", "Brightness the settings suit"],
            ["EV at your ISO", f"{math.log2(n * n / t):.1f}", f"ISO {iso:g}"], ["Typical scene", scene, ""]]
    return ps.facts("Exposure value", rows, "photo-ev", f"Those settings are EV {value:.1f} at ISO 100, like: {scene.lower()}.")


def sunny16(a) -> ps.Shown:
    iso = ps.num(a("iso") or 100, "ISO", 3, 5_000_000)
    t = ps.fmt_shutter(ps.nearest(1 / iso, ps.SHUTTERS))
    rows = [[label, ps.fmt_ap(ap), t] for label, ap in SUNNY]
    table = ps.table("Sunny 16 rule", ["Light", "Aperture", "Shutter"], rows, "photo-sunny16")
    return ps.Shown(f"Sunny 16: in bright sun use f/16 and {t} at ISO {iso:g}; open up one stop for each step "
                           "of cloud.", table)


def handheld(a) -> ps.Shown:
    focal = ps.num(a("focal_mm"), "focal length", 4, 2000)
    _, _, _, crop = ps.sensor(a)
    base = 1 / (focal * crop)
    rows = [["None" if s == 0 else f"{s} stops", ps.fmt_shutter(ps.nearest(base * 2 ** s, ps.SHUTTERS))]
            for s in (0, 2, 3, 4, 5)]
    table = ps.table("Slowest handheld shutter", ["Stabilisation", "Slowest shutter"], rows, "photo-handheld")
    return ps.Shown(f"Handheld at {focal:g} mm, stay at {ps.fmt_shutter(ps.nearest(base, ps.SHUTTERS))} or faster, "
                           "or slower with stabilisation.", table)


def star(a) -> ps.Shown:
    focal = ps.num(a("focal_mm"), "focal length", 4, 2000)
    name, w, h, crop = ps.sensor(a)
    n = ps.aperture(a("aperture") or 2.8)
    rule500 = 500 / (focal * crop)
    pitch = a("pixel_pitch_um")
    if pitch is None and a("megapixels") is not None:
        px_wide = math.sqrt(ps.num(a("megapixels"), "megapixels", 1, 500) * 1e6 * w / h)
        pitch = w * 1000 / px_wide
    guessed = pitch is None
    pitch = ps.num(pitch if pitch is not None else 4.3, "pixel pitch", 0.5, 20)
    npf = (35 * n + 30 * pitch) / focal
    rows = [["500 rule", f"{rule500:.1f} s", f"500 / ({focal:g} mm x crop {crop:g})"],
            ["NPF rule", f"{npf:.1f} s", "Sharper stars; uses aperture and pixel size"],
            ["Pixel pitch", f"{pitch:.1f} µm", "Guessed; give megapixels for a better answer" if guessed else name],
            ["Start with", f"{ps.fmt_ap(n)}, ISO 1600 to 3200", "Focus on a bright star, manual focus"]]
    return ps.facts("Star photo shutter", rows, "photo-star",
                    f"For sharp stars at {focal:g} mm, keep it under {npf:.0f} seconds (500 rule says {rule500:.0f}).")


def _stops_from(a) -> float:
    if a("nd_stops") is not None:
        return ps.num(a("nd_stops"), "ND stops", 0.1, 30)
    if a("nd_factor") is not None:
        return math.log2(ps.num(a("nd_factor"), "ND factor", 1.1, 1_000_000))
    if a("nd_density") is not None:
        return ps.num(a("nd_density"), "ND density", 0.1, 9) / 0.301
    raise ValueError("Give the filter as nd_stops (like 10), nd_factor (like 1000) or nd_density (like 3.0).")


def nd(a) -> ps.Shown:
    t = ps.shutter(a("shutter"))
    if a("target_shutter") is not None:
        target = ps.shutter(a("target_shutter"), "target time")
        need = math.log2(target / t)
        if need <= 0:
            raise ValueError("The target is faster than your shutter; you don't need a filter.")
        pick = next((name for name, s in ND_FILTERS if s >= need - 0.05), ND_FILTERS[-1][0])
        return ps.facts("ND filter needed", [["Metered shutter", ps.fmt_shutter(t)], ["Target", ps.fmt_shutter(target)],
                                             ["Stops of ND", f"{need:.1f}"], ["Closest filter", pick]],
                        "photo-nd", f"You need about {need:.1f} stops of ND, so {pick}, to reach {ps.fmt_shutter(target)}.")
    stops = _stops_from(a)
    rows = [["Your filter", f"{stops:.1f} stops", ps.fmt_shutter(t * 2 ** stops)]]
    rows += [[name, f"{s} stop" + ("" if s == 1 else "s"), ps.fmt_shutter(t * 2 ** s)] for name, s in ND_FILTERS]
    table = ps.table("Exposure time with ND", ["Filter", "Light cut", "New shutter"], rows, "photo-nd")
    return ps.Shown(f"With {stops:.1f} stops of ND, {ps.fmt_shutter(t)} becomes {ps.fmt_shutter(t * 2 ** stops)}.", table)


def _power(value) -> float:
    text = str(value if value is not None else "1").strip().lower()
    if text in ("full", "1/1", ""):
        return 1.0
    try:
        top, _, bottom = text.partition("/")
        power = float(top) / float(bottom) if bottom else float(top)
    except (ValueError, ZeroDivisionError):
        raise ValueError("Give the flash power like 1/2, 1/16 or full.") from None
    if not 0 < power <= 1:
        raise ValueError("Flash power is between 1/128 and full.")
    return power


def flash(a) -> ps.Shown:
    iso = ps.num(a("iso") or 100, "ISO", 3, 25_600)
    power = _power(a("flash_power"))
    scale = math.sqrt(iso / 100) * math.sqrt(power)
    gn, n = a("guide_number"), a("aperture")
    d = ps.metres(a) if a("distance_m") is not None or a("distance_ft") is not None else None
    if gn is None:
        raise ValueError("What is the flash's guide number (in metres at ISO 100, full power)?")
    gn = ps.num(gn, "guide number", 1, 500)
    if d is None and n is None:
        raise ValueError("Give either the distance to the subject or the aperture to solve for.")
    if d is None:
        n = ps.aperture(n)
        d = gn * scale / n
        spoken = f"With guide number {gn:g} at {ps.fmt_ap(n)}, the flash reaches {d:.1f} metres."
    else:
        d = ps.num(d, "distance", 0.1, 500)
        if n is None:
            n = gn * scale / d
            spoken = f"At {d:.1f} metres, use about {ps.fmt_ap(ps.nearest(n, ps.APERTURES))} on the flash."
        else:
            n = ps.aperture(n)
            spoken = (f"At {d:.1f} metres and {ps.fmt_ap(n)} you need guide number {d * n / scale:.0f} "
                      f"(yours gives {gn * scale / d:.1f} at that distance).")
    rows = [["Guide number", f"{gn:g}", "Metres at ISO 100, full power"], ["Power", f"{power:g}", f"ISO {iso:g}"],
            ["Distance", f"{d:.1f} m ({d / 0.3048:.0f} ft)", ""], ["Aperture", ps.fmt_ap(n), "Exact value"],
            ["Effective GN", f"{gn * scale:.1f}", "After power and ISO"]]
    return ps.facts("Flash guide number", rows, "photo-flash", spoken)


ACTIONS = {"exposure": exposure, "ev": ev, "sunny16": sunny16, "handheld": handheld, "star": star, "nd": nd, "flash": flash}
