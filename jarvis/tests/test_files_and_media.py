import os
import time
import zipfile

import pytest
from PIL import Image

import media_files
import media_find
import media_pictures
import media_show
import screen
from config import Settings


@pytest.fixture
def s(tmp_path):
    settings = Settings(memory_dir=str(tmp_path))
    hol = tmp_path / "Personal" / "Holiday"
    hol.mkdir(parents=True)
    for n, colour in enumerate(["red", "green", "blue"]):
        Image.new("RGB", (40 + n * 10, 30), colour).save(hol / f"beach {n}.jpg")
    (tmp_path / "Music").mkdir()
    (tmp_path / "Music" / "song a.mp3").write_bytes(b"ID3 a")
    (tmp_path / "Music" / "song b.mp3").write_bytes(b"ID3 b")
    (tmp_path / "Work").mkdir()
    (tmp_path / "Work" / "old.mp4").write_bytes(b"old video")
    (tmp_path / "Work" / "new.mp4").write_bytes(b"new video")
    os.utime(tmp_path / "Work" / "old.mp4", (time.time() - 1000, time.time() - 1000))
    return settings


def run(module, settings, **args):
    return module.run_tool(next(iter(module.NAMES)), args, settings)


def test_gallery_slideshow_and_music(s):
    g = run(media_show, s, action="gallery", folder="Personal/Holiday")
    assert g.card["kind"] == "gallery" and len(g.card["data"]["items"]) == 3
    assert g.card["data"]["items"][0]["src"] == "/screen/file?path=Personal/Holiday/beach%200.jpg"
    sl = run(media_show, s, action="slideshow", folder="personal/holiday", seconds=2)
    assert sl.card["kind"] == "slideshow" and sl.card["data"]["seconds"] == 2
    pl = run(media_show, s, action="music", folder="Music", shuffle=True)
    assert pl.card["kind"] == "playlist" and pl.card["data"]["shuffle"] is True
    assert [i["mime"] for i in pl.card["data"]["items"]] == ["audio/mpeg", "audio/mpeg"]
    with pytest.raises(ValueError):
        run(media_show, s, action="gallery", folder="Work")
    with pytest.raises(ValueError):
        run(media_show, s, action="gallery", folder="../..")


def test_video_newest_or_named(s):
    assert run(media_show, s, action="video").card["name"] == "new.mp4"
    shown = run(media_show, s, action="video", folder="Work", filename="old")
    assert shown.card["kind"] == "file" and shown.card["mime"] == "video/mp4"


def test_recent_and_search(s, tmp_path):
    (tmp_path / "folders.json").write_text("[]")  # Alfred's own file is never listed
    r = run(media_find, s, action="recent")
    assert r.card["kind"] == "list" and len(r.card["items"]) == 7
    assert all("folders.json" not in i["label"] for i in r.card["items"])
    found = run(media_find, s, action="search", query="BEACH 1")
    assert [i["say"] for i in found.card["items"]] == ["Show me the file beach 1.jpg from folder Personal/Holiday"]
    assert run(media_find, s, action="search", query="zebra").startswith("No file names")


def test_duplicates_and_folder_sizes(s, tmp_path):
    (tmp_path / "Work" / "copy.mp4").write_bytes(b"new video")
    d = run(media_find, s, action="duplicates")
    assert d.startswith("Found 1 set") and len(d.card["items"]) == 2
    sizes = run(media_find, s, action="folder_sizes")
    assert sizes.card["kind"] == "chart" and "Personal" in sizes.card["chart"]["labels"]


def test_info_and_exif(s, tmp_path):
    info = run(media_find, s, action="info", folder="Personal", filename="beach 2")
    assert "60 by 30 pixels" in info and info.card["kind"] == "table"
    (tmp_path / "Work" / "doc.pdf").write_bytes(b"%PDF /Type /Pages /Type /Page x /Type/Page y")
    assert "2 pages" in run(media_find, s, action="info", folder="Work", filename="doc.pdf")
    exif = Image.Exif()
    exif[0x010F], exif[0x0110], exif[0x0132] = "Apple", "iPhone 15", "2026:08:01 10:30:00"
    Image.new("RGB", (8, 8)).save(tmp_path / "Personal" / "phone.jpg", exif=exif)
    shown = run(media_find, s, action="exif", folder="Personal", filename="phone")
    assert str(shown) == "phone.jpg was taken 2026-08-01 10:30:00 with Apple iPhone 15."
    assert "no date" in run(media_find, s, action="exif", folder="Personal", filename="beach 0")


def test_rename_move_copy_delete(s, tmp_path):
    shown = run(media_files, s, action="rename", folder="Personal", filename="beach 0", new_name="sunset")
    assert shown.card["name"] == "sunset.jpg" and (tmp_path / "Personal" / "Holiday" / "sunset.jpg").exists()
    moved = run(media_files, s, action="move", folder="Personal", filename="sunset", to_folder="Work")
    assert moved.card["kind"] == "file" and (tmp_path / "Work" / "sunset.jpg").exists()
    run(media_files, s, action="copy", folder="Work", filename="sunset")
    assert (tmp_path / "Work" / "sunset (2).jpg").exists()
    assert run(media_files, s, action="delete", folder="Work", filename="sunset (2)").startswith("Not deleted")
    assert run(media_files, s, action="delete", folder="Work", filename="sunset (2)", confirmed=True).startswith("Deleted")
    assert not (tmp_path / "Work" / "sunset (2).jpg").exists()
    (tmp_path / "email-rules.json").write_text("[]")
    with pytest.raises(ValueError):
        run(media_files, s, action="delete", filename="email-rules.json", confirmed=True)
    run(media_files, s, action="rename", folder="Work", filename="new.mp4", new_name="../x")
    assert (tmp_path / "Work" / "x.mp4").exists()  # slashes are dropped, so it stays in its folder


def test_zip_list_and_unzip(s, tmp_path):
    z = run(media_files, s, action="zip", folder="Personal/Holiday")
    assert z.card["kind"] == "table" and len(z.card["rows"]) == 3
    listed = run(media_files, s, action="zip_contents", folder="Personal", filename="Holiday.zip")
    assert listed == "Holiday.zip holds 3 files."
    out = run(media_files, s, action="unzip", folder="Personal", filename="Holiday.zip")
    assert out.card["kind"] == "list" and (tmp_path / "Personal" / "Holiday" / "Holiday" / "beach 1.jpg").exists()


def _zip(path, entries):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries:
            z.writestr(name, data)


def test_unzip_blocks_zip_slip_and_bombs(s, tmp_path, monkeypatch):
    _zip(tmp_path / "Work" / "evil.zip", [("../../escape.txt", "x")])
    with pytest.raises(ValueError):
        run(media_files, s, action="unzip", folder="Work", filename="evil.zip")
    assert not (tmp_path.parent / "escape.txt").exists() and not (tmp_path / "Work" / "evil").exists()
    _zip(tmp_path / "Work" / "abs.zip", [("C:/Windows/x.txt", "x")])
    with pytest.raises(ValueError):
        run(media_files, s, action="unzip", folder="Work", filename="abs.zip")
    _zip(tmp_path / "Work" / "many.zip", [(f"f{n}.txt", "x") for n in range(5)])
    monkeypatch.setattr(media_files, "MAX_UNZIP_FILES", 3)
    with pytest.raises(ValueError, match="limit"):
        run(media_files, s, action="unzip", folder="Work", filename="many.zip")
    _zip(tmp_path / "Work" / "big.zip", [("zeros.bin", b"\0" * 5000)])
    monkeypatch.setattr(media_files, "MAX_UNZIP_BYTES", 1000)
    with pytest.raises(ValueError):
        run(media_files, s, action="unzip", folder="Work", filename="big.zip")
    assert not (tmp_path / "Work" / "big").exists()


def test_picture_edits(s, tmp_path):
    hol = tmp_path / "Personal" / "Holiday"
    r = run(media_pictures, s, action="resize", folder="Personal", filename="beach 0", width=20)
    assert r.card["kind"] == "file" and Image.open(hol / "beach 0 20x15.jpg").size == (20, 15)
    r = run(media_pictures, s, action="resize", folder="Personal", filename="beach 0.jpg", percent=50)
    assert Image.open(hol / "beach 0 20x15 (2).jpg").size == (20, 15)
    run(media_pictures, s, action="rotate", folder="Personal", filename="beach 1")
    assert Image.open(hol / "beach 1 rotated 90.jpg").size == (30, 50)
    c = run(media_pictures, s, action="convert", folder="Personal", filename="beach 2", format="webp")
    assert c.card["mime"] == "image/webp" and Image.open(hol / "beach 2.webp").format == "WEBP"
    run(media_pictures, s, action="greyscale", folder="Personal", filename="beach 2.jpg")
    assert Image.open(hol / "beach 2 greyscale.jpg").mode == "L"
    with pytest.raises(ValueError):
        run(media_pictures, s, action="resize", folder="Work", filename="new.mp4", width=10)


def test_pdf_gif_and_contact_sheet(s, tmp_path):
    hol = tmp_path / "Personal" / "Holiday"
    pdf = run(media_pictures, s, action="pdf", folder="Personal/Holiday")
    assert pdf.card["mime"] == "application/pdf" and "3-page" in pdf
    assert media_find.pdf_pages(hol / "Holiday pictures.pdf") == 3
    gif = run(media_pictures, s, action="gif", folder="Personal/Holiday", seconds=0.5)
    with Image.open(hol / "Holiday animation.gif") as im:
        assert im.n_frames == 3 and gif.card["mime"] == "image/gif"
    sheet = run(media_pictures, s, action="contact_sheet", folder="Personal/Holiday")
    assert sheet.card["kind"] == "file" and (hol / "Holiday contact sheet.jpg").exists()


def test_tools_have_strict_schemas():
    for module in (media_show, media_find, media_files, media_pictures):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert {"gallery", "slideshow", "playlist"} <= screen.EXTRA_KINDS
