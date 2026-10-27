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
