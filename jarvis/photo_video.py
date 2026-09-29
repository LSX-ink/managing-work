"""Video and storage maths for photo_calc: bitrate and recording time, photos per card, timelapse planning.

Bitrates are typical figures (the camera's own menu is the last word); card sizes count about 7% lost to formatting.
"""

import photo_store as ps

USABLE = 0.93
# Typical recording bitrates in megabits per second.
PRESETS = {"iphone 1080p30": 8, "iphone 4k24": 18, "iphone 4k30": 23, "iphone 4k60": 53, "1080p30": 25,
           "1080p60": 50, "4k24": 100, "4k30": 100, "4k60": 200, "8k24": 400}
CARDS = [16, 32, 64, 128, 256, 512, 1024, 2048]
# Megabytes per megapixel for a photo file.
FILE_MB_PER_MP = {"raw": 1.6, "jpeg": 0.4, "heif": 0.2}


def _hours_min(minutes: float) -> str:
    whole = int(minutes)
    return f"{whole // 60} h" + (f" {whole % 60} min" if whole % 60 else "") if whole >= 60 else f"{minutes:.0f} min" if minutes >= 1 else f"{minutes * 60:.0f} s"


def _bitrate(a) -> tuple[float, str]:
    if a("bitrate_mbps") is not None:
        return ps.num(a("bitrate_mbps"), "bitrate", 0.1, 5000), "your bitrate"
    key = str(a("preset") or "").lower().replace(" ", "")
    for name, mbps in PRESETS.items():
        if name.replace(" ", "") == key:
            return float(mbps), name
    raise ValueError(f"Give the bitrate_mbps, or a preset: {', '.join(PRESETS)}.")


def video(a) -> ps.Shown:
    if a("card_gb") is None and a("minutes") is None:
        rows = [[name, f"{mbps} Mbps", f"{mbps * 60 / 8:.0f} MB", f"{mbps * 3600 / 8000:.1f} GB"]
                for name, mbps in PRESETS.items()]
        table = ps.table("Video bitrates", ["Format", "Bitrate", "Per minute", "Per hour"], rows, "photo-video")
        return ps.Shown("Typical video sizes; give a card size or a length for a full answer.", table)
    mbps, label = _bitrate(a)
    per_min_mb = mbps * 60 / 8
    if a("card_gb") is not None:
        gb = ps.num(a("card_gb"), "card size", 0.1, 100_000)
        minutes = gb * 1000 * USABLE / per_min_mb
        rows = [["Format", f"{label} ({mbps:g} Mbps)"], ["Card", f"{gb:g} GB"], ["Recording time", _hours_min(minutes)],
                ["Per minute", f"{per_min_mb:.0f} MB"]]
        return ps.facts("Card recording time", rows, "photo-video",
                        f"A {gb:g} gigabyte card holds about {_hours_min(minutes)} of {label} video.")
    minutes = ps.num(a("minutes"), "minutes", 0.1, 100_000)
    gb = per_min_mb * minutes / 1000
    rows = [["Format", f"{label} ({mbps:g} Mbps)"], ["Length", _hours_min(minutes)], ["Storage needed", f"{gb:.1f} GB"],
            ["Card to buy", f"{next((c for c in CARDS if c >= gb / USABLE), CARDS[-1])} GB or more"]]
    return ps.facts("Storage for video", rows, "photo-video", f"{_hours_min(minutes)} of {label} needs about {gb:.1f} gigabytes.")


def card(a) -> ps.Shown:
    gb = ps.num(a("card_gb"), "card size", 0.1, 100_000)
    usable_mb = gb * 1000 * USABLE
    fmt = str(a("format") or "raw").lower()
    if fmt not in FILE_MB_PER_MP and fmt != "raw+jpeg":
        raise ValueError("The format is raw, jpeg, heif or raw+jpeg.")
    if a("file_mb") is not None:
        each = ps.num(a("file_mb"), "file size", 0.01, 5000)
        how = f"{each:g} MB each"
    else:
        mp = ps.num(a("megapixels") or 24, "megapixels", 0.1, 500)
        each = mp * (FILE_MB_PER_MP["raw"] + FILE_MB_PER_MP["jpeg"] if fmt == "raw+jpeg" else FILE_MB_PER_MP[fmt])
        how = f"about {each:.0f} MB each ({mp:g} MP {fmt})"
    photos = int(usable_mb // each)
    rows = [["Photos", f"{photos:,}", how]]
    rows += [[name, _hours_min(usable_mb / (mbps * 60 / 8)), f"{mbps} Mbps"]
             for name, mbps in PRESETS.items() if name in ("iphone 4k30", "1080p30", "4k30", "4k60")]
    table = ps.table(f"What fits on {gb:g} GB", ["Type", "Fits", "Detail"], rows, "photo-card")
    return ps.Shown(f"A {gb:g} gigabyte card holds about {photos:,} photos, {how}.", table)


def timelapse(a) -> ps.Shown:
    fps = ps.num(a("fps") or 25, "frame rate", 1, 120)
    given = {k: a(k) for k in ("interval_s", "duration_min", "clip_s") if a(k) is not None}
    if len(given) != 2:
        raise ValueError("Give any two of interval_s (seconds between shots), duration_min (how long you'll shoot) "
                         "and clip_s (finished clip length).")
    interval = ps.num(given["interval_s"], "interval", 0.1, 3600) if "interval_s" in given else None
    duration = ps.num(given["duration_min"], "duration", 0.1, 100_000) * 60 if "duration_min" in given else None
    clip = ps.num(given["clip_s"], "clip length", 0.5, 3600) if "clip_s" in given else None
    if interval is None:
        interval = duration / (clip * fps)
    elif duration is None:
        duration = clip * fps * interval
    else:
        clip = duration / interval / fps
    frames = round(duration / interval)
    rows = [["Shoot for", _hours_min(duration / 60), ""], ["Interval", f"{interval:.1f} s", f"Exposure up to about {interval * 0.6:.1f} s"],
            ["Frames", f"{frames:,}", ""], ["Clip length", f"{clip:.1f} s", f"At {fps:g} fps"],
            ["Speed-up", f"{interval * fps:.0f}x", "Real time compared with the clip"]]
    if a("file_mb") is not None:
        rows.append(["Storage", f"{frames * ps.num(a('file_mb'), 'file size', 0.01, 5000) / 1000:.1f} GB", "All frames"])
    return ps.facts("Timelapse plan", rows, "photo-timelapse",
                    f"Shoot {frames:,} frames, one every {interval:.0f} seconds over {_hours_min(duration / 60)}, "
                    f"for a {clip:.0f} second clip.")


ACTIONS = {"video": video, "card": card, "timelapse": timelapse}
