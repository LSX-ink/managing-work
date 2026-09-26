import zipfile
from pathlib import Path

import pytest

import pc


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setattr(pc.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "Documents" / "work").mkdir(parents=True)
    (tmp_path / "Downloads").mkdir()
    return tmp_path


def test_find_files_matches_all_words_and_hides_secrets(fake_home):
    (fake_home / "Documents" / "work" / "Thato CV 2026.docx").write_text("x")
    (fake_home / "Downloads" / "cv-old.pdf").write_text("x")
    (fake_home / "Documents" / "passwords cv.txt").write_text("x")
    hits = pc.find_files("cv 2026")
    assert [Path(h).name for h in hits] == ["Thato CV 2026.docx"]
    assert all("password" not in h for h in pc.find_files("cv"))


def test_read_file_text_and_docx(fake_home):
    note = fake_home / "Documents" / "note.txt"
    note.write_text("buy milk")
    assert "buy milk" in pc.read_file(str(note))
    doc = fake_home / "Documents" / "letter.docx"
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>Dear sir</w:t></w:p><w:p><w:t>Regards</w:t></w:p>")
    assert "Dear sir\nRegards" in pc.read_file(str(doc))


def test_read_file_refuses_secrets_and_outside_home(fake_home, tmp_path_factory):
    (fake_home / ".env").write_text("KEY=1")
    with pytest.raises(PermissionError):
        pc.read_file(str(fake_home / ".env"))
    outside = tmp_path_factory.mktemp("elsewhere") / "x.txt"
    outside.write_text("x")
    with pytest.raises(PermissionError):
        pc.read_file(str(outside))


def test_open_file_refuses_programs(fake_home):
    exe = fake_home / "Downloads" / "setup.exe"
    exe.write_text("x")
    assert "only open" in pc.open_file(str(exe))


def test_resolve_folder(fake_home):
    assert pc.resolve_folder("Downloads") == (fake_home / "Downloads").resolve()
    assert pc.resolve_folder("Documents/work") == (fake_home / "Documents" / "work").resolve()
    assert pc.resolve_folder("/etc") is None


def test_match_app_prefers_exact_then_prefix():
    apps = [("Spotify", "a"), ("Spotify Helper", "b"), ("Notepad++", "c"), ("Notepad", "d")]
    assert pc.match_app("spotify", apps) == ("Spotify", "a")
    assert pc.match_app("note", apps) == ("Notepad", "d")
    assert pc.match_app("zzz", apps) is None
