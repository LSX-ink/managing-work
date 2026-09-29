import json
from datetime import datetime

import pytest

import homestore
import screen
import techhelp_calc
import techhelp_fix
import techhelp_gadgets
import techhelp_secure
import tools
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 29, 10, 30))
    return Settings(memory_dir=str(tmp_path), city="London", currency="GBP")


def gad(s, action, **args):
    return techhelp_gadgets.run_tool("techhelp_gadgets", {"action": action, **args}, s)


def fix(s, action, **args):
    return techhelp_fix.run_tool("techhelp_fix", {"action": action, **args}, s)


def sec(s, action, **args):
    return techhelp_secure.run_tool("techhelp_secure", {"action": action, **args}, s)


def calc(s, action, **args):
    return techhelp_calc.run_tool("techhelp_calc", {"action": action, **args}, s)


def test_registered_and_deferred():
    for mod in (techhelp_gadgets, techhelp_fix, techhelp_secure, techhelp_calc):
        assert mod in tools.ABILITIES and mod not in tools.ALWAYS_LOADED
        for d in mod.tool_definitions():
            assert d["input_schema"]["additionalProperties"] is False
            assert d["name"] in mod.NAMES
    assert {"techhelp-steps", "techhelp-meter"} <= screen.EXTRA_KINDS


# ---- gadgets ----

def add_kettle(s):
    return gad(s, "gadget_add", name="Laptop", kind="laptop", model="XPS 13", serial="ABC123", bought="2024-10-20",
               price=999, warranty_months=24, shop="Dell")


def test_gadget_add_list_show(s):
    assert "Warranty 21 days left" in add_kettle(s)
    listed = gad(s, "gadget_list")
    assert isinstance(listed, screen.Shown) and listed.card["kind"] == "table"
    assert listed.card["rows"][0][:3] == ["Laptop", "laptop", "XPS 13"]
    shown = gad(s, "gadget_show", name="lap")
    assert ["Serial", "ABC123"] in shown.card["rows"]
    assert gad(s, "gadget_list").card["rows"][0][5] == "999.00 GBP"


def test_gadget_empty_list(s):
    assert gad(s, "gadget_list").card["kind"] == "text"


def test_warranty_soon_and_spend(s):
    add_kettle(s)
    gad(s, "gadget_add", name="Phone", price=700, until="2027-12-01")
    soon = gad(s, "gadget_warranty")
    assert soon.card["kind"] == "table" and [r[0] for r in soon.card["rows"]] == ["Laptop"]
    assert "Laptop" in soon
    assert gad(s, "gadget_warranty", days=1).card["kind"] == "text"
    spend = gad(s, "gadget_spend")
    assert spend.card["kind"] == "chart" and spend.card["chart"]["values"] == [999, 700]
    assert "1,699" in spend


def test_receipt_link_and_show(s):
    add_kettle(s)
    folder = homestore.path(s, "Shopping")
    folder.mkdir()
    (folder / "laptop-receipt.pdf").write_bytes(b"%PDF-1.4")
    assert "Linked laptop-receipt.pdf" in gad(s, "gadget_receipt", name="Laptop", folder="Shopping", filename="laptop-receipt")
    shown = gad(s, "receipt_show", name="Laptop")
    assert shown.card["kind"] == "file" and shown.card["mime"] == "application/pdf"
    assert gad(s, "gadget_show", name="Laptop").card["buttons"]
    with pytest.raises(ValueError):
        gad(s, "gadget_receipt", name="Laptop", folder="Shopping", filename="nothing-here")


def test_receipt_show_without_link(s):
    add_kettle(s)
    with pytest.raises(ValueError):
        gad(s, "receipt_show", name="Laptop")


def test_gadget_remove_needs_confirmation(s):
    add_kettle(s)
    assert "confirm" in gad(s, "gadget_remove", name="Laptop")
    assert gad(s, "gadget_list").card["kind"] == "table"
    assert "Removed" in gad(s, "gadget_remove", name="Laptop", confirmed=True)
    assert gad(s, "gadget_list").card["kind"] == "text"


def test_battery_log_and_show(s):
    assert "low" in gad(s, "battery_log", device="Watch", percent=12)
    gad(s, "battery_log", device="Watch", percent=90, charging=True)
    shown = gad(s, "battery_show", device="watch")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"] == [12, 90]
    with pytest.raises(ValueError):
        gad(s, "battery_log", device="Watch", percent=150)


def test_updates(s):
    gad(s, "update_add", name="Router firmware", every_days=30, last="2026-08-01")
    gad(s, "update_add", name="iPhone", every_days=90, last="2026-09-20")
    due = gad(s, "update_due")
    assert due.card["kind"] == "table" and due.card["rows"][0][0] == "Router firmware"
    assert due.card["rows"][0][3] == "overdue" and "Router firmware" in due
    assert "Next one" in gad(s, "update_done", name="router")
    assert gad(s, "update_due").card["rows"][0][0] == "Router firmware"
    assert "confirm" in gad(s, "update_remove", name="iPhone")
    assert "Removed" in gad(s, "update_remove", name="iPhone", confirmed=True)


def test_update_due_needs_reminders(s):
    with pytest.raises(ValueError):
        gad(s, "update_due")


# ---- guides and reference ----

def test_guide_list_and_start(s):
    listing = fix(s, "guide_list")
    assert listing.card["kind"] == "list" and len(listing.card["items"]) == 7
    assert all(i["say"] for i in listing.card["items"])
    start = fix(s, "guide_start", topic="my wifi is not working")
    assert start.card["kind"] == "techhelp-steps" and start.card["data"]["current"] == 0
    assert "step 1 of 7" in start and "Check other devices" in start
    for topic in ("printer offline", "slow pc", "no sound", "bluetooth won't pair", "phone storage full", "iphone backup"):
        assert fix(s, "guide_start", topic=topic).card["kind"] == "techhelp-steps"
    with pytest.raises(ValueError):
        fix(s, "guide_start", topic="toaster")


def test_guide_tick_walks_through(s):
    fix(s, "guide_start", topic="wifi")
    nxt = fix(s, "guide_tick", topic="wifi")
    assert "step 2 of 7" in nxt and nxt.card["data"]["done"] == 1
    third = fix(s, "guide_tick", topic="wifi", step=5)
    assert third.card["data"]["steps"][4]["done"] and third.card["data"]["current"] == 1
    undone = fix(s, "guide_tick", topic="wifi", step=5, done=False)
    assert not undone.card["data"]["steps"][4]["done"]
    assert fix(s, "guide_start", topic="wifi").card["data"]["done"] == 1  # remembered
    for _ in range(8):
        last = fix(s, "guide_tick", topic="wifi")
    assert "All 7 steps" in last and last.card["data"]["current"] is None
    assert fix(s, "guide_reset", topic="wifi").card["data"]["done"] == 0
    with pytest.raises(ValueError):
        fix(s, "guide_tick", topic="wifi", step=9)


def test_shortcuts(s):
    apps = fix(s, "shortcuts")
    assert apps.card["kind"] == "list" and apps.card["items"][0]["say"]
    excel = fix(s, "shortcuts", app="excel")
    assert excel.card["kind"] == "table" and excel.card["columns"] == ["Keys", "Does"]
    found = fix(s, "shortcuts", search="screenshot")
    assert found.card["rows"][0][0] == "Win + Shift + S"
    with pytest.raises(ValueError):
        fix(s, "shortcuts", search="zzzzzz")


def test_jargon(s):
    one = fix(s, "jargon", term="DNS")
    assert "phone book" in one and one.card["kind"] == "text"
    assert fix(s, "jargon", term="what is an ip address").card["kind"] == "text"
    everything = fix(s, "jargon")
    assert everything.card["kind"] == "table" and len(everything.card["rows"]) > 50
    with pytest.raises(ValueError):
        fix(s, "jargon", term="blorptronic")


def test_cable_guide(s):
    iphone = fix(s, "cable_guide", query="charger for my iPhone 15")
    assert "USB-C" in iphone and iphone.card["kind"] == "table"
    assert "Lightning" in fix(s, "cable_guide", query="iphone 12")
    other = fix(s, "cable_guide", query="quantum flux capacitor")
    assert other.card["columns"][0] == "Plug"


# ---- secure ----

def test_password_check_weak_and_strong(s):
    weak = sec(s, "password_check", password="Password123")
    assert weak.card["kind"] == "techhelp-meter" and weak.card["data"]["label"] in ("very weak", "weak")
    assert "Password123" not in weak and "Password123" not in str(weak.card)
    strong = sec(s, "password_check", password="correct horse battery staple river")
    assert strong.card["data"]["label"] in ("strong", "very strong")
    mid = sec(s, "password_check", password="tRx9!vQp2#Lm")
    assert mid.card["data"]["bits"] > weak.card["data"]["bits"]
    with pytest.raises(ValueError):
        sec(s, "password_check", password="")


def test_password_never_stored(s, tmp_path):
    sec(s, "password_check", password="Sup3rSecretValue!!")
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert "Sup3rSecretValue" not in f.read_text(errors="ignore")


def test_phish_check(s):
    bad = sec(s, "phish_check", text="URGENT: your account is suspended. Verify your password at http://paypa1-secure.xyz/login "
                                     "within 24 hours or lose access.")
    assert bad.card["kind"] == "table" and "scam" in bad
    reasons = " ".join(r[0] for r in bad.card["rows"])
    assert "Pressure" in reasons and "isn't its real site" in reasons
    parcel = sec(s, "phish_check", text="Royal Mail: we missed you. Pay the delivery fee at bit.ly/abc123")
    assert "shortened link" in " ".join(r[0] for r in parcel.card["rows"])
    fine = sec(s, "phish_check", text="See you at 7 for dinner, bring the wine.")
    assert fine.card["rows"][0][0] == "Nothing obvious found"
    real = sec(s, "phish_check", text="Your parcel is on its way https://www.royalmail.com/track")
    assert "isn't its real site" not in " ".join(r[0] for r in real.card["rows"])
    with pytest.raises(ValueError):
        sec(s, "phish_check", text="  ")


def test_checklists(s):
    shown = sec(s, "checklist_show", list="2fa")
    assert shown.card["kind"] == "techhelp-steps" and shown.card["data"]["total"] == 8
    ticked = sec(s, "checklist_tick", list="2fa", step=1)
    assert ticked.card["data"]["done"] == 1 and ticked.card["data"]["steps"][0]["done"]
    assert sec(s, "checklist_show", list="backup").card["data"]["done"] == 0
    assert sec(s, "checklist_reset", list="2fa").card["data"]["done"] == 0
    assert sec(s, "checklist_show", list="two-factor").card["data"]["total"] == 8
    with pytest.raises(ValueError):
        sec(s, "checklist_show", list="gardening")


# ---- calculators and network ----

def test_filesize_and_fit(s):
    size = calc(s, "filesize", size=2.5, unit="GB")
    assert size.card["kind"] == "table" and size.card["rows"][2][1] == "2,500"
    fits = calc(s, "fit", capacity=64, capacity_unit="GB", size=4, unit="MB")
    assert "16,000" in fits and fits.card["kind"] == "table"
    with pytest.raises(ValueError):
        calc(s, "fit", capacity=1, capacity_unit="GB", size=0, unit="MB")
    with pytest.raises(ValueError):
        calc(s, "filesize", size=1, unit="XB")


def test_download_time(s):
    shown = calc(s, "download_time", size=1, unit="GB", speed_mbps=100)
    assert "about 89 seconds" in shown and shown.card["rows"][0][0].startswith("10 Mbps")
    with pytest.raises(ValueError):
        calc(s, "download_time", size=1, unit="GB", speed_mbps=0)


def test_screen_and_resolution(s):
    laptop = calc(s, "screen_size", diagonal_inches=15.6, width_px=1920, height_px=1080)
    assert "141 pixels per inch" in laptop and ["Aspect ratio", "16:9"] in laptop.card["rows"]
    phone = calc(s, "screen_size", diagonal_inches=6.1, width_px=2532, height_px=1170)
    assert "crisp" in phone
    named = calc(s, "resolution", width_px=3840, height_px=2160)
    assert "4K Ultra HD" in named
    table = calc(s, "resolution")
    assert table.card["kind"] == "table" and len(table.card["rows"]) >= 8
    with pytest.raises(ValueError):
        calc(s, "screen_size", diagonal_inches=15, width_px=1920)


def test_network_list(s):
    empty = calc(s, "network_list")
    assert empty.card["kind"] == "text"
    assert "Saved" in calc(s, "network_add", name="Living room TV", ip="192.168.1.20", kind="TV")
    calc(s, "network_add", name="Printer", ip="192.168.1.9", note="Hallway")
    listed = calc(s, "network_list")
    assert [r[0] for r in listed.card["rows"]] == ["Printer", "Living room TV"]
    with pytest.raises(ValueError):
        calc(s, "network_add", name="Laptop", ip="192.168.1.9")
    with pytest.raises(ValueError):
        calc(s, "network_add", name="Laptop", ip="not an ip")
    assert "confirm" in calc(s, "network_remove", name="Printer")
    assert "Removed" in calc(s, "network_remove", name="Printer", confirmed=True)
    assert len(calc(s, "network_list").card["rows"]) == 1
    data = json.loads(homestore.path(s, "techhelp-network.json").read_text())
    assert data["Living room TV"]["ip"] == "192.168.1.20"
