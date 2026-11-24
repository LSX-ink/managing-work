import asyncio
import os
import sys

import selfupdate


def test_changed_code_restarts_only_once_settled_and_idle(tmp_path):
    (tmp_path / "brain.py").write_text("a")
    busy = {"now": True}
    restarted = []

    async def scenario():
        task = asyncio.create_task(selfupdate.watch(tmp_path, lambda: busy["now"], lambda: restarted.append(1),
                                                    every=0.05, settle=0.05, idle_for=0.05))
        await asyncio.sleep(0.2)
        assert not restarted  # nothing changed yet
        (tmp_path / "brain.py").write_text("b")
        os.utime(tmp_path / "brain.py", ns=(1, 10 ** 18))
        await asyncio.sleep(0.4)
        assert not restarted  # still answering: it waits
        busy["now"] = False
        await asyncio.wait_for(task, 5)

    asyncio.run(scenario())
    assert restarted == [1]


def test_memory_and_data_files_do_not_count(tmp_path):
    (tmp_path / "brain.py").write_text("a")
    before = selfupdate.fingerprint(tmp_path)
    (tmp_path / "notes.json").write_text("{}")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "x.py").write_text("")
    assert selfupdate.fingerprint(tmp_path) == before
    (tmp_path / ".env").write_text("JARVIS_X=1")
    assert selfupdate.fingerprint(tmp_path) != before


def test_supervise_starts_the_server_again_after_an_update(tmp_path, monkeypatch):
    runs = tmp_path / "runs.txt"
    script = tmp_path / "fake_server.py"
    script.write_text(
        "import sys, pathlib\n"
        f"p = pathlib.Path({str(runs)!r})\n"
        "n = len(p.read_text().splitlines()) if p.exists() else 0\n"
        "p.write_text(p.read_text() + ' '.join(sys.argv[1:]) + '\\n' if p.exists() else ' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.exit({selfupdate.RESTART_CODE} if n < 2 else 0)\n")
    monkeypatch.setattr(sys, "argv", ["server.py"])
    monkeypatch.setattr(selfupdate.time, "sleep", lambda s: None)
    monkeypatch.setattr(selfupdate, "port_taken", lambda h, p: False)
    assert selfupdate.supervise(str(script)) == 0
    assert runs.read_text().splitlines() == [selfupdate.CHILD_FLAG] * 3


def test_a_taken_port_or_a_failed_start_never_loops(tmp_path, monkeypatch, capsys):
    import socket
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert selfupdate.supervise(str(tmp_path / "never_run.py"), "127.0.0.1", port) == 1
        assert "already running" in capsys.readouterr().out
    script = tmp_path / "fails.py"
    runs = tmp_path / "runs.txt"
    script.write_text(f"import pathlib, sys\np = pathlib.Path({str(runs)!r})\np.write_text((p.read_text() if p.exists() else '') + 'x')\nsys.exit(3)\n")
    monkeypatch.setattr(sys, "argv", ["server.py"])
    assert selfupdate.supervise(str(script), "127.0.0.1", port) == 3  # uvicorn's "couldn't start": no restart
    assert runs.read_text() == "x"
