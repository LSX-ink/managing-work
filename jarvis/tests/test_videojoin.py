import subprocess

import pytest

import memory
import tools
import videojoin
from config import Settings
from tiktokstudio_video import ffmpeg

pytest.importorskip("imageio_ffmpeg")


def make_clip(path, seconds, size="320x240", rate=24, colour="red", sound=True):
    sources = ["-f", "lavfi", "-i", f"color=c={colour}:s={size}:r={rate}:d={seconds}"]
    if sound:
        sources += ["-f", "lavfi", "-i", f"sine=f=440:d={seconds}"]
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", *sources, "-shortest", "-pix_fmt", "yuv420p", str(path)],
                   check=True)
    return path


@pytest.fixture
def films():
    settings = Settings()
    folder = memory.folder(settings, "Work/Films", create=True)
    return settings, folder


def run(settings, **args):
    return videojoin.run_tool("join_video_clips", args, settings)


def test_registered_and_deferred():
    defs = [t for t in tools.client_tool_definitions(Settings()) if t["name"] == "join_video_clips"]
    assert len(defs) == 1 and defs[0].get("defer_loading")


def test_joins_mixed_clips_with_cuts(films):
    settings, folder = films
    make_clip(folder / "a.mp4", 1.0)
    make_clip(folder / "b.mp4", 1.5, size="640x360", rate=30, colour="blue", sound=False)  # other size, no sound
    said = run(settings, action="join", clips=["Work/Films/a.mp4", "b.mp4"], name="Duel")
    assert "Joined 2 clips into Duel.mp4" in said and "320x240" in said
    assert said.card["src"].endswith("Duel.mp4")
    facts = videojoin.probe(folder / "Duel.mp4")
    assert (facts["w"], facts["h"]) == (320, 240) and facts["sound"]
    assert 2.4 <= facts["seconds"] <= 2.65


def test_crossfade_and_music_over_the_film(films):
    settings, folder = films
    for name in ("one", "two", "three"):
        make_clip(folder / f"{name}.mp4", 1.0)
    make_clip(folder / "music.mp4", 0.5)  # a short track, looped to fill the film
    said = run(settings, action="join", clips=["one.mp4", "two.mp4", "three.mp4"], transition="crossfade",
               fade_seconds=0.4, size="360x640", audio=[{"source": "music.mp4", "volume": 0.3, "loop": True}],
               keep_clip_sound=False, name="Film")
    assert "crossfaded" in said
    facts = videojoin.probe(folder / "Film.mp4")
    assert (facts["w"], facts["h"]) == (360, 640)
    assert 2.0 <= facts["seconds"] <= 2.4  # 3 seconds less two 0.4 s overlaps
    again = run(settings, action="join", clips=["one.mp4"], name="Film")
    assert "Film 2.mp4" in again


def test_last_frame_for_the_next_shot(films):
    settings, folder = films
    make_clip(folder / "shot1.mp4", 1.0, colour="green")
    said = videojoin.run_tool("join_video_clips", {"action": "last_frame", "clip": "shot1.mp4"}, settings)
    assert "shot1 last frame.png" in said and (folder / "shot1 last frame.png").stat().st_size > 0


def test_clear_errors(films):
    settings, folder = films
    with pytest.raises(ValueError, match="Which clips"):
        run(settings, action="join", clips=[])
    with pytest.raises(ValueError, match="can't find"):
        run(settings, action="join", clips=["nowhere.mp4"])
    with pytest.raises(ValueError, match="isn't in the memory folders"):
        run(settings, action="join", clips=["../../secret.mp4"])
    (folder / "notes.mp4").write_text("not a video")
    with pytest.raises(ValueError, match="isn't a video"):
        run(settings, action="join", clips=["notes.mp4"])


def test_downloads_linked_clips(films, tmp_path):
    import threading
    from functools import partial
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    settings, folder = films
    make_clip(tmp_path / "gen1.mp4", 1.0)
    make_clip(tmp_path / "gen2.mp4", 1.0, colour="blue")
    server = HTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        said = run(settings, action="join", clips=[f"{base}/gen1.mp4", f"{base}/gen2.mp4"], name="Anime")
    finally:
        server.shutdown()
    assert "Joined 2 clips into Anime.mp4" in said
    assert not list((folder / ".parts").iterdir())  # the downloads are cleared once the film is made
