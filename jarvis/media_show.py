"""Photos, music and videos from the memory folders in pop-ups: a photo gallery, a slideshow, a music player, a video.

The gallery, slideshow and playlist kinds are drawn by frontend/popup-files-and-media.js.
"""

import media_common as mc
import screen
from config import Settings

screen.EXTRA_KINDS.update({"gallery", "slideshow", "playlist"})


def gallery(settings: Settings, folder: str) -> screen.Shown:
    pictures = mc.files_in(settings, folder, mc.PICTURES | {".svg"})
    if not pictures:
        raise ValueError(f"There are no pictures in {folder}.")
    name = mc.folder(settings, folder).name
    c = screen.card("gallery", f"{name} photos", f"gallery-{mc.rel(settings, mc.folder(settings, folder))}",
                    data={"items": [mc.item(settings, p) for p in pictures]},
                    buttons=[{"label": "Slideshow", "say": f"Play a slideshow of the pictures in {folder}."}])
    return screen.Shown(f"Showing {len(pictures)} pictures from {name}.", c)


def slideshow(settings: Settings, folder: str, seconds) -> screen.Shown:
    pictures = mc.files_in(settings, folder, mc.PICTURES)
    if not pictures:
        raise ValueError(f"There are no pictures in {folder}.")
    seconds = min(max(float(seconds or 5), 1), 60)
    name = mc.folder(settings, folder).name
    c = screen.card("slideshow", f"{name} slideshow", f"slideshow-{mc.rel(settings, mc.folder(settings, folder))}",
                    data={"items": [mc.item(settings, p) for p in pictures], "seconds": seconds})
    return screen.Shown(f"Starting a slideshow of {len(pictures)} pictures from {name}.", c)


def playlist(settings: Settings, folder: str, shuffle: bool) -> screen.Shown:
    songs = mc.files_in(settings, folder, mc.AUDIO)
    if not songs:
        raise ValueError(f"There's no music in {folder}.")
    name = mc.folder(settings, folder).name
    c = screen.card("playlist", f"{name} music", f"playlist-{mc.rel(settings, mc.folder(settings, folder))}",
                    data={"items": [mc.item(settings, p) for p in songs], "shuffle": bool(shuffle)})
    return screen.Shown(f"Playing {len(songs)} songs from {name}.", c)


def video(settings: Settings, folder: str, filename: str) -> screen.Shown:
    if filename:
        path = mc.user_file(settings, folder, filename)
        if path.suffix.lower() not in mc.VIDEO:
            raise ValueError(f"{path.name} isn't a video I can play.")
    else:
        top = mc.folder(settings, folder) if folder else None
        videos = [p for p in mc.all_files(settings, top) if p.suffix.lower() in mc.VIDEO]
        if not videos:
            raise ValueError("There are no videos there.")
        path = max(videos, key=lambda p: p.stat().st_mtime)
    return screen.Shown(f"Playing {path.name}.", screen.file_card(settings, path))


def tool_definitions() -> list[dict]:
    return [{
        "name": "show_photos_music_videos",
        "description": "Show photos, pictures, music and videos from a memory folder in a pop-up on the Alfred "
                       "screen. action 'gallery' a photo gallery (thumbnails; click to see one big); 'slideshow' "
                       "pictures one after another; 'music' a music player for the songs in a folder (play, pause, "
                       "next, shuffle, volume); 'video' plays a video (the named one, else the newest).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["gallery", "slideshow", "music", "video"]},
                "folder": {"type": "string", "description": "Memory folder, e.g. 'Personal' or 'Personal/Holiday'."},
                "filename": {"type": "string", "description": "video: the file's name or part of it."},
                "seconds": {"type": "number", "description": "slideshow: seconds per picture (default 5)."},
                "shuffle": {"type": "boolean", "description": "music: start shuffled."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"show_photos_music_videos"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    action, folder = args.get("action"), args.get("folder") or ""
    if action == "gallery":
        return gallery(settings, folder)
    if action == "slideshow":
        return slideshow(settings, folder, args.get("seconds"))
    if action == "music":
        return playlist(settings, folder, bool(args.get("shuffle")))
    if action == "video":
        return video(settings, folder, args.get("filename") or "")
    raise ValueError("Pick gallery, slideshow, music or video.")
