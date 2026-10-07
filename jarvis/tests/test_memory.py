from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import memory
from config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(memory_dir=str(tmp_path / "memory"))


def test_default_folders_are_created(settings):
    assert [f["name"] for f in memory.listing(settings)] == memory.DEFAULT_FOLDERS
    assert (memory.root(settings) / "Ideas").is_dir()


def test_rename_keeps_place_and_files(settings):
    memory.save_note(settings, 1, "Standup", "Ship the HUD")
    assert memory.rename(settings, 1, "Job") == "Job"
    folders = memory.listing(settings)
    assert folders[1]["name"] == "Job"
    assert folders[1]["items"][0]["name"] == "Standup.txt"
    with pytest.raises(ValueError):
        memory.rename(settings, 0, "job")  # already taken, any case


def test_notes_by_name_and_duplicates(settings):
    memory.save_note(settings, "ideas", "Idea", "one")
    memory.save_note(settings, "Ideas", "Idea", "two")
    names = sorted(i["name"] for i in memory.listing(settings)[0]["items"])
    assert names == ["Idea (2).txt", "Idea.txt"]
    text = memory.read(settings, "Ideas")
    assert "one" in text and "two" in text
    assert "Ideas: " in memory.read(settings)


@pytest.mark.parametrize("bad", ["", "  ..  ", "CON", "x" * 61])
def test_unsafe_names_refused(settings, bad):
    with pytest.raises(ValueError):
        memory.rename(settings, 0, bad)


def test_path_characters_are_stripped(settings):
    path = memory.save_file(settings, 0, "../../evil.txt", b"hi")
    assert path.parent == memory.root(settings) / "Ideas"
    assert path.name == "....evil.txt".strip(".") or path.name == "evil.txt"


def test_unknown_folder(settings):
    with pytest.raises(ValueError):
        memory.save_note(settings, "Nope", "t", "x")
    with pytest.raises(ValueError):
        memory.folder(settings, 9)


def test_tools_save_and_read(settings):
    assert "Saved as Milk.txt in the Shopping folder" in memory.run_tool(
        "save_to_memory", {"folder": "shopping", "title": "Milk", "text": "2 litres"}, settings)
    assert "2 litres" in memory.run_tool("read_memory", {"folder": "Shopping"}, settings)


def test_memory_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    monkeypatch.setattr(server, "settings", replace(server.settings, memory_dir=str(tmp_path / "m"), password=""))
    ours = {"origin": "http://testserver"}
    with TestClient(server.app) as client:
        assert len(client.get("/memory").json()["folders"]) == 6
        # other websites can't change the folders
        assert client.post("/memory/0/rename", json={"name": "Hacked"}).status_code == 403
        assert client.post("/memory/0/rename", json={"name": "Hacked"}, headers={"origin": "http://evil.com"}).status_code == 403
        assert client.post("/memory/0/rename", json={"name": "Big ideas"}, headers=ours).json() == {"name": "Big ideas"}
        assert client.post("/memory/0/note", json={"title": "Plan", "text": "hello"}, headers=ours).json() == {"name": "Plan.txt"}
        assert client.put("/memory/0/files/pic.png", content=b"\x89PNG", headers=ours).json() == {"name": "pic.png"}
        opened = client.get("/memory/0/files/Plan.txt")
        assert opened.text == "hello" and opened.headers["content-security-policy"] == "sandbox"
        assert client.post("/memory/0/rename", json={"name": "a/b:c"}, headers=ours).json() == {"name": "abc"}
        assert client.post("/memory/0/rename", json={"name": "?"}, headers=ours).status_code == 400
        assert client.delete("/memory/0/files/pic.png", headers=ours).json() == {"ok": True}
        assert [i["name"] for i in client.get("/memory").json()["folders"][0]["items"]] == ["Plan.txt"]
        assert client.get("/memory/0/files/pic.png").status_code == 400



def test_big_uploads_stream_to_disk(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    monkeypatch.setattr(server, "settings", replace(server.settings, memory_dir=str(tmp_path / "m"), password=""))
    monkeypatch.setattr(server, "UPLOAD_CHUNK", 1024 * 1024)
    ours = {"origin": "http://testserver"}
    big = bytes(range(256)) * (100 * 1024)  # 25 MB: over the old 20 MB limit
    with TestClient(server.app) as client:
        assert client.put("/memory/0/files/clip.mp4", content=big, headers=ours).json() == {"name": "clip.mp4"}
        assert client.put("/memory/0/files/clip.mp4", content=b"x", headers=ours).json() == {"name": "clip (2).mp4"}
        assert client.put("/memory/0/files/clip.mp4", content=b"x").status_code == 403
        monkeypatch.setattr(memory, "MAX_UPLOAD_BYTES", 1000)
        assert client.put("/memory/0/files/huge.mp4", content=b"x" * 5000, headers=ours).status_code == 413

        def chunks():
            yield b"x" * 800
            yield b"x" * 800
        assert client.put("/memory/0/files/sneaky.mp4", content=chunks(), headers=ours).status_code == 413  # no length given
    folder = memory.folder(replace(server.settings, memory_dir=str(tmp_path / "m")), 0)
    assert (folder / "clip.mp4").read_bytes() == big
    assert sorted(p.name for p in folder.iterdir()) == ["clip (2).mp4", "clip.mp4"]  # nothing half-written left behind


# ---- downloads ----------------------------------------------------------------------

def run(coro):
    import asyncio
    return asyncio.run(coro)


def fake_web(pages):
    """An httpx client that answers from a dict of url -> (status, headers, body)."""
    import httpx

    def handler(request):
        status, headers, body = pages[str(request.url)]
        return httpx.Response(status, headers=headers, content=body)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def public(monkeypatch):
    async def ok(url):
        if not url.startswith(("http://", "https://")):
            raise ValueError("I can only download http or https links.")
    monkeypatch.setattr(memory, "check_public", ok)


def test_download_saves_into_folder(settings, public):
    web = fake_web({"https://example.com/files/report%20v2.pdf": (200, {}, b"%PDF-1.7 hello")})
    path = run(memory.download(settings, web, "work", "https://example.com/files/report%20v2.pdf"))
    assert path.name == "report v2.pdf" and path.parent.name == "Work"
    assert path.read_bytes() == b"%PDF-1.7 hello"
    assert not list(path.parent.glob("*.part"))


def test_download_uses_server_name_redirects_and_own_name(settings, public):
    web = fake_web({
        "https://example.com/get?id=1": (302, {"location": "/real"}, b""),
        "https://example.com/real": (200, {"content-disposition": 'attachment; filename="song.mp3"'}, b"ID3"),
    })
    assert run(memory.download(settings, web, "Music", "https://example.com/get?id=1")).name == "song.mp3"
    assert run(memory.download(settings, web, "Music", "https://example.com/get?id=1", "Theme")).name == "Theme.mp3"


def test_download_refuses_errors_and_big_files(settings, public, monkeypatch):
    web = fake_web({
        "https://example.com/missing": (404, {}, b""),
        "https://example.com/big": (200, {}, b"x" * 50),
        "https://example.com/loop": (302, {"location": "/loop"}, b""),
    })
    with pytest.raises(ValueError, match="404"):
        run(memory.download(settings, web, "Work", "https://example.com/missing"))
    with pytest.raises(ValueError, match="redirected"):
        run(memory.download(settings, web, "Work", "https://example.com/loop"))
    with pytest.raises(ValueError, match="http"):
        run(memory.download(settings, web, "Work", "file:///C:/Windows/win.ini"))
    monkeypatch.setattr(memory, "MAX_DOWNLOAD_BYTES", 10)
    with pytest.raises(ValueError, match="too big"):
        run(memory.download(settings, web, "Work", "https://example.com/big"))
    assert memory.listing(settings)[1]["items"] == []


@pytest.mark.parametrize("url", ["http://127.0.0.1:8340/memory", "http://192.168.1.1/", "http://[::1]/", "http://10.0.0.5/x"])
def test_download_refuses_this_pc_and_home_network(url):
    with pytest.raises(ValueError, match="home network"):
        run(memory.check_public(url))


def test_public_address_is_allowed():
    run(memory.check_public("http://93.184.215.14/file.pdf"))


def test_open_memory_folder_on_hud_and_pc(settings, monkeypatch):
    import asyncio
    import pc
    import tools

    sent, launched = [], []

    async def page(message):
        sent.append(message)
    monkeypatch.setattr(pc, "launch", launched.append)
    hud = replace(settings, theme="hud-stars")
    assert "HUD" in asyncio.run(tools.run_tool("open_memory_folder", {"folder": "ideas"}, hud, None, page))
    assert sent == [{"type": "memory", "open": "Ideas"}]
    assert "File Explorer" in asyncio.run(tools.run_tool("open_memory_folder", {"folder": "Work", "on_pc": True}, hud, None, page))
    assert "File Explorer" in asyncio.run(tools.run_tool("open_memory_folder", {"folder": "Music"}, replace(settings, theme="classic"), None, page))
    assert [p.name for p in launched] == ["Work", "Music"] and launched[0].is_absolute()


def test_create_folders_inside_memory_folders(settings):
    path = memory.create_folder(settings, "work", "Invoices")
    assert path == memory.root(settings) / "Work" / "Invoices" and path.is_dir()
    with pytest.raises(ValueError, match="already"):
        memory.create_folder(settings, "Work", "invoices")
    memory.save_note(settings, "Work/invoices", "March", "paid")
    assert (path / "March.txt").read_text() == "paid"
    assert memory.listing(settings)[1]["folders"] == [{"name": "Invoices", "count": 1}]
    assert "Invoices/ (folder)" in memory.read(settings)
    assert "Invoices/ (folder, 1 items)" in memory.read(settings, "Work")
    assert "paid" in memory.read(settings, "Work\\Invoices")
    assert memory.inner_folder(settings, 1, "Invoices") == path
    memory.create_folder(settings, "Work/Invoices", "2026")
    assert (path / "2026").is_dir()
    with pytest.raises(ValueError, match="no folder called Receipts"):
        memory.save_note(settings, "Work/Receipts", "x", "y")
    with pytest.raises(ValueError):
        memory.create_folder(settings, "Work", "..")
    assert "Created the folder Work/Taxes." == memory.run_tool("create_memory_folder", {"parent": "Work", "name": "Taxes"}, settings)


def test_open_inner_folder_goes_to_file_explorer(settings, monkeypatch):
    import asyncio
    import pc
    import tools

    launched = []
    monkeypatch.setattr(pc, "launch", launched.append)
    memory.create_folder(settings, "Work", "Invoices")

    sent = []

    async def page(message):
        sent.append(message)
    msg = asyncio.run(tools.run_tool("open_memory_folder", {"folder": "work/invoices"}, replace(settings, theme="hud-stars"), None, page))
    assert "File Explorer" in msg and launched[0].name == "Invoices"
    assert sent == [{"type": "memory", "star": "Work/Invoices"}]  # its star flares on the HUD


def test_alfreds_own_folders(settings, monkeypatch):
    import asyncio
    import pc
    import tools

    path = memory.create_folder(settings, "", "Fitness")
    assert path == memory.root(settings) / "Fitness"
    assert memory.extras(settings) == [{"name": "Fitness", "count": 0}]
    assert [f["name"] for f in memory.listing(settings)] == memory.DEFAULT_FOLDERS  # the wolf keeps its six
    memory.save_note(settings, "fitness", "Monday", "legs")
    memory.create_folder(settings, "Fitness", "Plans")
    assert "Fitness: Alfred's own folder, 2 items" in memory.read(settings)
    with pytest.raises(ValueError, match="already"):
        memory.create_folder(settings, "", "work")  # one of the six
    with pytest.raises(ValueError, match="already"):
        memory.rename(settings, 0, "Fitness")
    assert memory.run_tool("create_memory_folder", {"name": "Books"}, settings) == "Created the folder Books."

    launched, sent = [], []
    monkeypatch.setattr(pc, "launch", launched.append)

    async def page(message):
        sent.append(message)
    asyncio.run(tools.run_tool("open_memory_folder", {"folder": "fitness"}, replace(settings, theme="hud-stars"), None, page))
    assert launched[0].name == "Fitness" and sent == [{"type": "memory", "star": "Fitness"}]


def test_delete_memory_folder(settings):
    memory.create_folder(settings, "Work", "Payslips")
    memory.create_folder(settings, "", "Fitness")
    memory.save_note(settings, "Fitness", "Monday", "legs")
    assert "Not deleted" in memory.run_tool("delete_memory_folder", {"folder": "Work/Payslips", "confirmed": False}, settings)
    assert (memory.root(settings) / "Work" / "Payslips").is_dir()
    assert memory.run_tool("delete_memory_folder", {"folder": "work/payslips", "confirmed": True}, settings) == "Deleted the empty folder Work/Payslips."
    assert not (memory.root(settings) / "Work" / "Payslips").exists()
    with pytest.raises(ValueError, match="still has 1"):
        memory.delete_folder(settings, "Fitness")
    with pytest.raises(ValueError, match="six folders"):
        memory.delete_folder(settings, "Work")
    with pytest.raises(ValueError, match="no folder"):
        memory.delete_folder(settings, "Nope")


def test_move_chat_panel(settings):
    import asyncio
    import tools

    sent = []

    async def page(message):
        sent.append(message)
    assert asyncio.run(tools.run_tool("move_chat_panel", {"position": "bottom-left"}, settings, None, page)) == "Moved the chat panel to the bottom left."
    assert sent == [{"type": "chat", "corner": "bottom-left"}]
    with pytest.raises(ValueError):
        asyncio.run(tools.run_tool("move_chat_panel", {"position": "middle"}, settings, None, page))
    assert "isn't open" in asyncio.run(tools.run_tool("move_chat_panel", {"position": "centre"}, settings, None, None))


def test_read_document(settings):
    memory.save_file(settings, "Work", "slip.pdf", b"%PDF-1.4 fake")
    memory.save_file(settings, "Work", "photo.jpg", b"\xff\xd8fake")
    memory.save_note(settings, "Work", "plan", "build a shed")
    pdf = memory.run_tool("read_document", {"folder": "work", "filename": "slip.pdf"}, settings)
    assert pdf[0]["type"] == "document" and pdf[0]["source"]["media_type"] == "application/pdf"
    assert pdf[1]["text"] == "slip.pdf, from the Work folder."
    assert memory.document_content(settings, "Work", "photo.jpg")[0]["source"]["media_type"] == "image/jpeg"
    assert "build a shed" in memory.document_content(settings, "Work", "plan.txt")
    memory.save_file(settings, "Work", "song.mp3", b"x")
    with pytest.raises(ValueError, match="not .mp3"):
        memory.document_content(settings, "Work", "song.mp3")


def test_starter_folders_are_made_once(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert memory.starter_extras(s) == ["Kinetic Web Designs", "YouTube"]
    assert (tmp_path / "YouTube" / "Shorts Analytics").is_dir() and (tmp_path / "YouTube" / "TikTok Pages").is_dir()
    assert [e["name"] for e in memory.extras(s)] == ["Kinetic Web Designs", "YouTube"]
    memory.delete_folder(s, "Kinetic Web Designs")
    assert memory.starter_extras(s) == [] and not (tmp_path / "Kinetic Web Designs").exists()
