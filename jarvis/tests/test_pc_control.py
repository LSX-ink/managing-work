import asyncio
import ctypes
import subprocess
import time
from types import SimpleNamespace

import psutil
import pytest

import pctools
import tools
from config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(memory_dir=str(tmp_path / "memory"), enable_pc=True)


@pytest.fixture
def win(monkeypatch):
    """Pretend to be Windows and record every subprocess call instead of running it."""
    calls = []
    replies = {}

    def fake_run(argv, **kw):
        calls.append({"argv": argv, "input": kw.get("input")})
        script = " ".join(argv)
        for key, (code, out) in replies.items():
            if key in script:
                return subprocess.CompletedProcess(argv, code, out, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(pctools, "WINDOWS", True)
    monkeypatch.setattr(pctools.subprocess, "run", fake_run)
    return SimpleNamespace(calls=calls, replies=replies)


def run(tool, action, settings, **args):
    return pctools.run_tool(tool, {"action": action, **args}, settings)


def test_four_tools_offered_only_with_pc_control():
    assert len(pctools.tool_definitions()) == 4
    for t in pctools.tool_definitions():
        assert t["input_schema"]["additionalProperties"] is False
    names = lambda s: {t["name"] for t in tools.client_tool_definitions(s)}
    assert pctools.NAMES <= names(Settings(enable_pc=True))
    assert not pctools.NAMES & names(Settings(enable_pc=False))


def test_routed_through_tools_only_when_enabled(settings):
    with pytest.raises(ValueError):
        asyncio.run(tools.run_tool("pc_system", {"action": "uptime"}, Settings(enable_pc=False), None))
    assert "on for" in asyncio.run(tools.run_tool("pc_system", {"action": "uptime"}, settings, None))


def test_windows_only_actions_say_so_elsewhere(settings, monkeypatch):
    monkeypatch.setattr(pctools, "WINDOWS", False)
    assert run("pc_system", "clipboard_read", settings) == pctools.ONLY_WINDOWS
    assert run("pc_network", "wifi", settings) == pctools.ONLY_WINDOWS
    assert run("pc_power", "shutdown", settings, confirmed=True) == pctools.ONLY_WINDOWS


def test_unknown_action_is_refused(settings):
    with pytest.raises(ValueError):
        run("pc_windows", "shutdown", settings)


def test_clipboard_read(settings, win):
    win.replies["Get-Clipboard"] = (0, "hello there\n")
    assert run("pc_system", "clipboard_read", settings) == "On the clipboard: hello there"
    win.replies["Get-Clipboard"] = (0, "")
    assert "empty" in run("pc_system", "clipboard_read", settings)


def test_clipboard_copy_sends_text_on_stdin(settings, win):
    evil = "'; Remove-Item C:\\ -Recurse; '"
    assert run("pc_system", "clipboard_copy", settings, text=evil) == "Copied to the clipboard."
    call = win.calls[-1]
    assert call["input"] == evil
    assert all(evil not in part for part in call["argv"])


def test_brightness_get_and_unsupported(settings, win):
    win.replies["WmiMonitorBrightness "] = (0, "70\n")
    assert run("pc_system", "brightness_get", settings) == "The screen brightness is 70%."
    win.replies["WmiMonitorBrightness "] = (1, "")
    assert "desktop monitors" in run("pc_system", "brightness_get", settings)


def test_brightness_set(settings, win):
    assert run("pc_system", "brightness_set", settings, level=150) == "Set the screen brightness to 100%."
    assert win.calls[-1]["input"] == "100"
    win.replies["WmiSetBrightness"] = (1, "")
    assert "desktop monitors" in run("pc_system", "brightness_set", settings, level=40)


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_dark_and_light_mode(settings, win, monkeypatch):
    written = {}
    fake = SimpleNamespace(HKEY_CURRENT_USER=1, KEY_SET_VALUE=2, REG_DWORD=4,
                           OpenKey=lambda *a: FakeKey(),
                           SetValueEx=lambda key, name, _, kind, value: written.__setitem__(name, value))
    monkeypatch.setattr(pctools, "winreg_module", lambda: fake)
    assert run("pc_system", "dark_mode", settings) == "Switched Windows and apps to dark mode."
    assert written == {"AppsUseLightTheme": 0, "SystemUsesLightTheme": 0}
    written.clear()
    assert run("pc_system", "light_mode", settings, target="apps") == "Switched apps to light mode."
    assert written == {"AppsUseLightTheme": 1}


def test_sound_device(settings, win):
    win.replies["Win32_SoundDevice"] = (0, "Realtek(R) Audio\nNVIDIA High Definition Audio\n")
    assert run("pc_system", "sound_device", settings) == \
        "Sound devices: Realtek(R) Audio, NVIDIA High Definition Audio."


def test_uptime(settings, monkeypatch):
    monkeypatch.setattr(pctools.psutil, "boot_time", lambda: time.time() - (2 * 86400 + 3 * 3600 + 60))
    assert run("pc_system", "uptime", settings).startswith("The PC has been on for 2 days and 3 hours, since ")


class FakeProc:
    def __init__(self, pid, name, rss=0, cpu=0.0):
        self.pid = pid
        self.info = {"name": name, "memory_info": SimpleNamespace(rss=rss)}
        self.cpu = cpu
        self.terminated = False

    def cpu_percent(self, _):
        return self.cpu

    def terminate(self):
        self.terminated = True


def test_top_processes(settings, monkeypatch):
    procs = [FakeProc(1, "chrome.exe", 900 * 2**20, 10), FakeProc(2, "game.exe", 100 * 2**20, 80)]
    monkeypatch.setattr(pctools.psutil, "process_iter", lambda attrs=None: procs)
    monkeypatch.setattr(pctools.psutil, "cpu_count", lambda: 2)
    monkeypatch.setattr(pctools.time, "sleep", lambda s: None)
    out = run("pc_system", "top_processes", settings)
    assert out == "Most memory: chrome.exe (900 MB), game.exe (100 MB). Most CPU: game.exe (40%), chrome.exe (5%)."


def test_downloads_usage(settings, tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "Downloads" / "sub").mkdir(parents=True)
    (home / "Downloads" / "big.iso").write_bytes(b"x" * 3000)
    (home / "Downloads" / "sub" / "small.txt").write_bytes(b"x" * 10)
    monkeypatch.setattr(pctools.pc.Path, "home", classmethod(lambda cls: home))
    out = run("pc_system", "downloads_usage", settings)
    assert out.splitlines()[0] == "Downloads holds 2 files using 2.9 KB."
    assert out.splitlines()[1] == "- big.iso: 2.9 KB"


def test_open_settings(settings, win, monkeypatch):
    opened = []
    monkeypatch.setattr(pctools.os, "startfile", opened.append, raising=False)
    assert run("pc_system", "open_settings", settings, page="wifi") == "Opened the wifi settings."
    assert opened == ["ms-settings:network-wifi"]
    assert "I can open" in run("pc_system", "open_settings", settings, page="regedit")
    assert opened == ["ms-settings:network-wifi"]


class FakeUser32:
    def __init__(self):
        self.titles = {1: "Inbox - Google Chrome", 2: "", 3: "Spotify Premium", 4: "Hidden"}
        self.foreground = None
        self.restored = []

    def EnumWindows(self, callback, _):
        for hwnd in self.titles:
            callback(hwnd, 0)

    def IsWindowVisible(self, hwnd):
        return hwnd != 4

    def GetWindowTextLengthW(self, hwnd):
        return len(self.titles[hwnd])

    def GetWindowTextW(self, hwnd, buf, n):
        ctypes.memmove(buf, ctypes.create_unicode_buffer(self.titles[hwnd]), n * ctypes.sizeof(ctypes.c_wchar))

    def IsIconic(self, hwnd):
        return True

    def ShowWindow(self, hwnd, cmd):
        self.restored.append(hwnd)

    def keybd_event(self, *a):
        pass

    def SetForegroundWindow(self, hwnd):
        self.foreground = hwnd


def test_list_and_switch_windows(settings, win, monkeypatch):
    u = FakeUser32()
    monkeypatch.setattr(pctools, "user32", lambda: u)
    assert run("pc_windows", "list", settings) == "Open windows:\n- Inbox - Google Chrome\n- Spotify Premium"
    assert run("pc_windows", "switch", settings, name="spotify") == "Switched to Spotify Premium."
    assert u.foreground == 3 and u.restored == [3]
    assert run("pc_windows", "switch", settings, name="word").startswith("No open window matches")


def test_minimise_all(settings, win):
    assert run("pc_windows", "minimise_all", settings) == "Minimised all windows."
    assert "MinimizeAll" in win.calls[-1]["argv"][-1]


def test_screenshot_saves_into_memory(settings, monkeypatch):
    from PIL import Image, ImageGrab

    monkeypatch.setattr(ImageGrab, "grab", lambda **kw: Image.new("RGB", (4, 4)))
    out = run("pc_windows", "screenshot", settings)
    shots = list((pctools.memory.root(settings) / "Screenshots").glob("*.png"))
    assert len(shots) == 1 and shots[0].name in out
    out = run("pc_windows", "screenshot", settings, folder="work")
    assert "Work folder" in out and list((pctools.memory.root(settings) / "Work").glob("*.png"))


@pytest.mark.parametrize("action", ["sleep", "restart", "shutdown", "empty_recycle_bin", "close_app"])
def test_risky_actions_need_confirmation(settings, win, action):
    assert run("pc_power", action, settings, name="chrome") == pctools.CONFIRM
    assert win.calls == []


def test_shutdown_restart_and_cancel(settings, win):
    assert run("pc_power", "shutdown", settings, confirmed=True).startswith("Shutting down in 60 seconds")
    assert win.calls[-1]["argv"] == ["shutdown", "/s", "/t", "60"]
    assert run("pc_power", "restart", settings, confirmed=True).startswith("Restarting in 60 seconds")
    assert win.calls[-1]["argv"] == ["shutdown", "/r", "/t", "60"]
    assert run("pc_power", "cancel_shutdown", settings) == "Cancelled the shutdown."
    assert win.calls[-1]["argv"] == ["shutdown", "/a"]


def test_sleep(settings, win):
    assert run("pc_power", "sleep", settings, confirmed=True) == "Putting the PC to sleep."
    assert "SetSuspendState" in win.calls[-1]["argv"][-1]


def test_empty_recycle_bin(settings, win, monkeypatch):
    results = iter([0, -2147418113])
    monkeypatch.setattr(pctools, "shell32", lambda: SimpleNamespace(SHEmptyRecycleBinW=lambda *a: next(results)))
    assert run("pc_power", "empty_recycle_bin", settings, confirmed=True) == "Emptied the Recycle Bin."
    assert run("pc_power", "empty_recycle_bin", settings, confirmed=True) == "The Recycle Bin is already empty."


def test_close_app(settings, monkeypatch):
    procs = [FakeProc(101, "Spotify.exe"), FakeProc(102, "spotify.exe"), FakeProc(103, "chrome.exe")]
    monkeypatch.setattr(pctools.psutil, "process_iter", lambda attrs=None: procs)
    monkeypatch.setattr(pctools.psutil, "wait_procs", lambda procs, timeout: ([], []))
    monkeypatch.setattr(pctools, "own_pids", lambda: {1})
    assert run("pc_power", "close_app", settings, name="spotify", confirmed=True) == \
        "Closed spotify (2 windows or processes)."
    assert [p.terminated for p in procs] == [True, True, False]
    assert run("pc_power", "close_app", settings, name="notepad", confirmed=True) == "notepad isn't running."


@pytest.mark.parametrize("name", ["explorer.exe", "svchost", "LSASS.exe", "python.exe", "winlogon"])
def test_close_app_refuses_system_and_jarvis(settings, name, monkeypatch):
    monkeypatch.setattr(pctools.psutil, "process_iter", lambda attrs=None: pytest.fail("must not look"))
    assert run("pc_power", "close_app", settings, name=name, confirmed=True).startswith("I won't close")


def test_close_app_refuses_own_process(settings, monkeypatch):
    procs = [FakeProc(55, "jarvis.exe")]
    monkeypatch.setattr(pctools.psutil, "process_iter", lambda attrs=None: procs)
    monkeypatch.setattr(pctools, "own_pids", lambda: {55})
    assert "Jarvis itself" in run("pc_power", "close_app", settings, name="jarvis", confirmed=True)
    assert not procs[0].terminated


def test_wifi(settings, win):
    win.replies["netsh"] = (0, "    Name                   : Wi-Fi\n    State                  : connected\n"
                               "    SSID                   : Lesufi Home 5G\n    BSSID                  : aa:bb:cc:dd:ee:ff\n"
                               "    Signal                 : 87%\n")
    assert run("pc_network", "wifi", settings) == "Connected to Lesufi Home 5G with 87% signal."
    assert win.calls[-1]["argv"] == ["netsh", "wlan", "show", "interfaces"]
    win.replies["netsh"] = (0, "    State : disconnected\n")
    assert "isn't connected" in run("pc_network", "wifi", settings)


def test_ip_and_internet(settings, monkeypatch):
    monkeypatch.setattr(pctools, "local_ip", lambda: "192.168.1.20")
    monkeypatch.setattr(pctools, "internet_up", lambda: True)
    assert run("pc_network", "ip_and_internet", settings) == \
        "The PC's local IP address is 192.168.1.20. The internet is reachable."
    monkeypatch.setattr(pctools, "internet_up", lambda: False)
    assert "isn't reachable" in run("pc_network", "ip_and_internet", settings)


def test_internet_check_uses_cloudflare_443(monkeypatch):
    seen = []

    def fake_connect(addr, timeout):
        seen.append(addr)
        raise OSError("offline")

    monkeypatch.setattr(pctools.socket, "create_connection", fake_connect)
    assert pctools.internet_up() is False
    assert seen == [("1.1.1.1", 443)]


def test_powershell_timeout_is_reported(settings, monkeypatch):
    monkeypatch.setattr(pctools, "WINDOWS", True)

    def slow(argv, **kw):
        assert kw["timeout"] == pctools.PS_TIMEOUT
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    monkeypatch.setattr(pctools.subprocess, "run", slow)
    assert "too long" in run("pc_system", "clipboard_read", settings)
