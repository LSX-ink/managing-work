"""Photography and video calculators: exposure, EV, sunny 16, handheld, depth of field, hyperfocal, field of view,
star shots, ND filters, flash, print size, crops, video bitrate, card capacity and timelapse planning.

Every answer pops up a table, or a drawn diagram for depth of field, field of view and crops. Nothing is saved
and nothing goes online.
"""

import photo_exposure
import photo_lens
import photo_video
from config import Settings

ALL = {**photo_exposure.ACTIONS, **photo_lens.ACTIONS, **photo_video.ACTIONS}
NAMES = {"photo_calc"}


def tool_definitions() -> list[dict]:
    num = {"type": "number"}
    return [{
        "name": "photo_calc",
        "description": "Camera and video calculator. action: exposure (equivalent settings after changing two of "
                       "new_aperture/new_shutter/new_iso), ev, sunny16, handheld (slowest handheld shutter), dof "
                       "(depth of field diagram), hyperfocal, fov (angle of view diagram, crop equivalent), star (500/NPF "
                       "rule), nd (filter exposure time), flash (guide number), print (pixels vs print size and dpi), "
                       "crop (aspect ratio crop diagram), video (bitrate, card time), card (photos per card), "
                       "timelapse (interval, frames, clip length). Shutter like 1/125 or seconds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ALL)},
                "aperture": {"type": ["number", "string"]}, "shutter": {"type": ["number", "string"]},
                "iso": num, "new_aperture": {"type": ["number", "string"]}, "new_shutter": {"type": ["number", "string"]},
                "new_iso": num, "ev": {**num, "description": "EV100 to solve a shutter for."},
                "focal_mm": num, "sensor": {"type": "string", "description": "full frame, aps-c, micro four thirds, "
                                            "1 inch, medium format or phone."},
                "crop_factor": num, "distance_m": num, "distance_ft": num, "pixel_pitch_um": num, "megapixels": num,
                "nd_stops": num, "nd_factor": num, "nd_density": num, "target_shutter": {"type": ["number", "string"]},
                "guide_number": num, "flash_power": {"type": "string", "description": "1/2, 1/16 or full."},
                "width_px": num, "height_px": num, "dpi": num, "print_width": num, "print_height": num,
                "print_unit": {"type": "string", "enum": ["cm", "in"]},
                "ratio": {"type": "string", "description": "Crop ratio like 16:9, 4:5, 1:1."},
                "anchor": {"type": "string", "enum": ["centre", "left", "right", "top", "bottom"]},
                "preset": {"type": "string"}, "bitrate_mbps": num, "card_gb": num, "minutes": num,
                "format": {"type": "string", "enum": ["raw", "jpeg", "heif", "raw+jpeg"]}, "file_mb": num,
                "interval_s": num, "duration_min": num, "clip_s": num, "fps": num,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = ALL.get(args.get("action"))
    if action is None:
        raise ValueError(f"I can't do {args.get('action')}. Try: {', '.join(ALL)}.")
    return action(args.get)
