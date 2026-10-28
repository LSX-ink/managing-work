import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import kinetic_premium as kp
import tools
from config import ROOT, Settings

sys.path.insert(0, str(ROOT / "hq" / "premium"))
import auto  # noqa: E402


def test_the_tool_is_one_of_alfreds_abilities():
    names = [t["name"] for t in tools.client_tool_definitions(Settings())]
    assert "kinetic_premium_mockup" in names


def test_build_needs_a_business_and_the_places_key():
    with pytest.raises(ValueError, match="which business"):
        kp.build(Settings(), {"business": " "})
    with pytest.raises(ValueError, match="Google Places key"):
        kp.build(replace(Settings(), google_places_key=""), {"business": "A Cut Above, Sheffield"})


def test_the_phone_message_has_the_link_checks_instagram_and_dm():
    r = {"name": "A Cut Above", "layout": "atelier", "link": "https://k.test/m/a-cut-above/", "issues": [],
         "instagram": "acutabove", "instagram_ok": True, "dm": "Hi A Cut Above team"}
    text = kp.ready_text(r)
    assert "https://k.test/m/a-cut-above/" in text and "every check passed" in text
    assert "@acutabove is a real, live profile" in text and text.endswith("Hi A Cut Above team")
    assert "check these first: no map" in kp.ready_text({**r, "issues": ["no map"], "instagram": ""})


def test_a_link_already_made_is_never_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(auto, "LEADS", tmp_path / "leads")
    (tmp_path / "m" / "vox").mkdir(parents=True)
    (tmp_path / "m" / "vox-v2").mkdir()
    assert auto.free_slug("vox", tmp_path) == "vox-v3"
    assert auto.free_slug("new-shop", tmp_path) == "new-shop"
    assert auto.slugify("A Cut Above, Sheffield") == "a-cut-above-sheffield"


def test_each_new_mock_up_takes_the_least_used_layout(tmp_path):
    for i, lay in enumerate(["editorial", "split", "bold", "cinema", "atelier", "editorial", "split", "bold"]):
        f = tmp_path / str(i) / "config.json"
        f.parent.mkdir()
        f.write_text(json.dumps({} if lay == "atelier" else {"layout": lay}))
        os.utime(f, (i, i))
    assert auto.next_layout(tmp_path) == "cinema"  # used once, like atelier, but longer ago


def test_google_facts_are_kept_word_for_word():
    place = {"displayName": {"text": "A Cut Above"}, "nationalPhoneNumber": "0114 000", "formattedAddress": "81 Road",
             "rating": 4.7, "userRatingCount": 138, "location": {"latitude": 53.3, "longitude": -1.4},
             "regularOpeningHours": {"weekdayDescriptions": ["Monday: 9:00 AM – 6:00 PM"]},
             "reviews": [{"rating": 5, "text": {"text": "Great\ncut"}, "authorAttribution": {"displayName": "Sam"}},
                         {"rating": 2, "text": {"text": "Meh"}, "authorAttribution": {"displayName": "Lee"}}]}
    f = auto.listing_facts(place, "@acut", "")
    assert f["hours"] == [["Monday", "9:00 AM – 6:00 PM"]]
    assert f["reviews"] == [["Great cut", "Sam"]]  # low ratings left out
    assert f["stats"] == [["4.7", "Google rating"], ["138", "Google reviews"]]
    assert (f["instagram"], f["book_label"], f["loc"]) == ("acut", "Call us", [53.3, -1.4])


def test_mock_up_words_follow_the_copywriting_skill():
    assert "copywriting guide" in auto.copy_guide() and len(auto.copy_guide()) > 1000


class _Reviewer:
    def __init__(self, answer):
        self.answer = answer
        self.messages = self
        self.system = ""

    async def create(self, **kw):
        self.system = kw["system"]
        return type("R", (), {"content": [type("B", (), {"text": self.answer})()]})()


async def test_design_review_uses_every_website_skill_and_never_touches_facts(tmp_path, monkeypatch):
    import design
    (tmp_path / "g").mkdir()
    for n in range(4):
        (tmp_path / "g" / f"0{n}.jpg").write_bytes(b"x")

    async def no_shots(page):
        return [b"img"]
    monkeypatch.setattr(auto, "page_shots", no_shots)
    c = {"name": "Shop", "h1": ["a", "b", "c"], "services": [{"group": "All", "items": [["Cut", "£10"], ["Fade", "£12"]]}],
         "hero": ["g/00.jpg"], "gallery": ["g/01.jpg"], "experience": {"photos": []}, "phone": "0114"}
    answer = json.dumps({"changes": {
        "h1": ["Sharp.", "Clean.", "Yours."], "phone": "999",  # phone isn't allowed: it's a fact
        "special": {"title": "50% off!"},  # may not add an offer
        "services": [{"group": "Cuts", "items": [["Cut", "£10"]]}, {"group": "Fades", "items": [["Skin fade", "£12"]]}],
        "hero": ["g/02.jpg", "g/02.jpg", "nope.jpg"]}, "notes": ["tighter headline (copywriting)"]})
    reviewer = _Reviewer(answer)
    new, notes = await auto.review(reviewer, "m", tmp_path, tmp_path / "index.html", c, "atelier", {"name": "Shop", "phone": "0114"})
    assert "OUR DESIGN SKILLS" in reviewer.system
    for name, _, _, size in design.WEBSITE_SKILLS:
        assert (f"=== {name}/" in reviewer.system) == bool(size)  # every review skill; the 3D ones are for hand builds
    assert new["h1"] == ["Sharp.", "Clean.", "Yours."] and new["phone"] == "0114" and "special" not in new
    assert [g["group"] for g in new["services"]] == ["Cuts", "Fades"]  # regrouped, prices kept
    assert new["hero"] == ["g/02.jpg"] and notes == ["tighter headline (copywriting)"]
    moved = json.dumps({"changes": {"services": [{"group": "All", "items": [["Cut", "£8"], ["Fade", "£12"]]}]}})
    new2, _ = await auto.review(_Reviewer(moved), "m", tmp_path, tmp_path / "x", c, "atelier", {"name": "Shop"})
    assert new2["services"] == c["services"]  # a changed price is refused


async def test_the_review_cannot_break_the_page_shape(tmp_path, monkeypatch):
    (tmp_path / "g").mkdir()
    for n in range(4):
        (tmp_path / "g" / f"0{n}.jpg").write_bytes(b"x")

    async def no_shots(page):
        return [b"img"]
    monkeypatch.setattr(auto, "page_shots", no_shots)
    c = {"name": "Shop", "h1": ["a", "b", "c"], "kicker": "High St", "lead": "Cuts.",
         "colours": {"bg": "#000000", "panel": "#111111", "ink": "#ffffff", "muted": "#999999", "gold": "#ffcc00"},
         "experience": {"title": "T", "text": "X", "photos": ["g/01.jpg"]}, "hero": ["g/00.jpg"], "gallery": ["g/02.jpg"]}
    answer = json.dumps({"changes": {"h1": ["Sharp fades.", "No nonsense."],  # two lines: the layouts need three
                                     "colours": {"muted": "#a0a0a0"}, "experience": {"title": "Reciprocity"}}})
    new, _ = await auto.review(_Reviewer(answer), "m", tmp_path, tmp_path / "x", c, "split", {"name": "Shop"})
    assert new["h1"] == ["a", "b", "c"]
    assert new["colours"]["muted"] == "#a0a0a0" and new["colours"]["gold"] == "#ffcc00"  # partial change merged
    assert new["experience"]["title"] == "Reciprocity" and new["experience"]["text"] == "X"


def test_a_logo_the_builder_cannot_read_is_left_out(tmp_path):
    from PIL import Image
    Image.new("RGB", (8, 8)).save(tmp_path / "logo0.png")
    (tmp_path / "logo1.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    assert auto.usable_image(tmp_path / "logo0.png") and not auto.usable_image(tmp_path / "logo1.svg")
    c = auto.tidy({"logo": "logo1.svg"}, tmp_path, [], "atelier", None, {"name": "Shop"})
    assert c["logo"] == ""


async def test_a_garbled_review_is_asked_for_again(tmp_path, monkeypatch):
    async def no_shots(page):
        return [b"img"]
    monkeypatch.setattr(auto, "page_shots", no_shots)

    class Twice(_Reviewer):
        def __init__(self):
            super().__init__("")
            self.calls = 0

        async def create(self, **kw):
            self.calls += 1
            self.answer = '{"changes": {"kicker": "x" "y"}}' if self.calls == 1 else '{"changes": {"kicker": "High St"}, "notes": ["ok"]}'
            return await super().create(**kw)
    r = Twice()
    new, notes = await auto.review(r, "m", tmp_path, tmp_path / "x", {"name": "S", "kicker": "a"}, "atelier", {"name": "S"})
    assert r.calls == 2 and new["kicker"] == "High St" and notes == ["ok"]


def test_3d_only_on_pages_that_ask_for_it(tmp_path):
    import depth3d
    c = {"name": "Kamo Barbers", "short": "Kamo", "layout": "split",
         "colours": {"gold": "#e3262f", "second": "#ffffff", "panel": "#141414"}}
    page = "<html><body><h1>Hi</h1></body></html>"
    assert depth3d.add(page, c, tmp_path) == page  # sent mock-ups never change
    (tmp_path / "logo.png").write_bytes(b"x")
    out = depth3d.add(page, {**c, "depth3d": True}, tmp_path)
    assert '<canvas id="d3"' in out and "three@0.160.0" in out and '"piece": "pole"' in out  # a barber's first piece
    assert '"layout": "split"' in out and out.endswith("</body></html>")


def test_each_mock_up_gets_its_own_3d_piece_for_its_trade(tmp_path):
    import depth3d
    assert depth3d.pieces_for("Kamo Barbers")[0] == "pole" and depth3d.pieces_for("Treat Hair & Beauty")[0] == "dryer"
    assert auto.next_piece("Kamo Barbers", leads=tmp_path) == "pole"
    for i, pc in enumerate(["pole", "scissors"]):
        (tmp_path / str(i)).mkdir()
        (tmp_path / str(i) / "config.json").write_text(json.dumps({"piece": pc}))
    assert auto.next_piece("Kamo Barbers", leads=tmp_path) == "razor"  # the least used barber piece next
    page = depth3d.add("<body></body>", {"name": "Kamo", "depth3d": True, "piece": "razor", "colours": {"gold": "#e3262f"}}, tmp_path)
    assert '"piece": "razor"' in page and "logo.png" not in page  # their tool, not a logo coin
