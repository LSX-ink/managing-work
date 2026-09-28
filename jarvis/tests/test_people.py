import asyncio
import json
from datetime import datetime

import httpx
import pytest

import homestore
import people_book
import people_lists
import people_occasions
import people_touch
import reminders
import screen
import tools
from config import Settings

CLOCK = {}


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 28, 10, 30)  # a Monday
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def book(s, **args):
    return people_book.run_tool("people_book", args, s)


def touch(s, **args):
    return people_touch.run_tool("people_keep_in_touch", args, s)


def occ(s, **args):
    return people_occasions.run_tool("people_occasions", args, s)


def lists(s, **args):
    return people_lists.run_tool("people_lists", args, s)


def fill(s):
    book(s, action="add", name="Sam", how_known="school friend", phone="07700 900123", address="1 High St, Leeds")
    book(s, action="add", name="Mum", how_known="family", address="2 Park Rd, York")
    book(s, action="add", name="Jo", how_known="work")


def test_registered_deferred_with_four_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    mods = (people_book, people_touch, people_occasions, people_lists)
    assert {"people_book", "people_keep_in_touch", "people_occasions", "people_lists"} <= names
    for m in mods:
        assert m in tools.ABILITIES and m not in tools.ALWAYS_LOADED
        for t in m.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
    assert "people-tree" in screen.EXTRA_KINDS


def test_add_edit_list_remove(s, tmp_path):
    assert book(s, action="list") == "Your people notebook is empty. Tell me someone to add."
    assert book(s, action="add", name="Sam", how_known="school friend", phone="07700 900123") == \
        "Added Sam in your people notebook."
    assert book(s, action="add", name="sam", email="sam@example.com") == "Updated Sam in your people notebook."
    assert book(s, action="edit", name="sam", new_name="Samantha", address="1 High St") == "Updated Samantha."
    saved = json.loads((tmp_path / "people-book.json").read_text())
    assert saved["Samantha"]["phone"] == "07700 900123" and saved["Samantha"]["email"] == "sam@example.com"
    shown = book(s, action="list")
    assert str(shown) == "1 person in your notebook." and shown.card["kind"] == "table"
    assert shown.card["rows"] == [["Samantha", "school friend", "", "never"]]
    assert "confirm" in book(s, action="remove", name="samantha")
    assert book(s, action="remove", name="samantha", confirmed=True) == "Removed Samantha from your people notebook."
    with pytest.raises(ValueError):
        book(s, action="card", name="Samantha")


def test_card_notes_birthday_and_gifts(s, tmp_path):
    fill(s)
    (tmp_path / "birthdays.json").write_text(json.dumps({"Sam": "1991-10-08"}))
    (tmp_path / "gifts.json").write_text(json.dumps({"sam": ["horse book"]}))
    assert book(s, action="note", name="sam", text="Daughter Mia loves horses") == "Saved a note about Sam."
    assert book(s, action="note", name="sam", field="like", text="Jazz") == "Saved a like about Sam."
    book(s, action="note", name="sam", field="dislike", text="Mushrooms")
    book(s, action="note", name="sam", field="family", text="Mia (daughter)")
    shown = book(s, action="card", name="sam")
    assert str(shown) == "Here's Sam's card. Last in touch never."
    assert "07700" not in str(shown)
    text = shown.card["text"]
    for bit in ("Phone: 07700 900123", "Birthday: 8 Oct 2026, in 10 days, turning 35", "Likes: Jazz",
                "Dislikes: Mushrooms", "Family: Mia (daughter)", "Gift ideas: horse book", "Daughter Mia loves horses"):
        assert bit in text
    assert "07700 900123" in book(s, action="card", name="sam", show_contact=True)


def test_search_any_detail(s):
    fill(s)
    book(s, action="note", name="sam", text="Daughter Mia loves horses")
    shown = book(s, action="search", query="horses")
    assert str(shown) == "1 person match: Sam." and shown.card["kind"] == "list"
    assert shown.card["items"][0] == {"label": "Sam - note: Daughter Mia loves horses", "done": False,
                                      "say": "Show Sam's person card."}
    assert str(book(s, action="search", query="york")) == "1 person match: Mum."
    assert book(s, action="search", query="unicorn") == "Nobody in your notebook matches unicorn."


def test_groups(s):
    fill(s)
    assert book(s, action="group_add", people=["Sam", "jo"], group="Uni friends") == "Added Sam, Jo to Uni friends."
    book(s, action="group_add", name="Mum", group="Family")
    shown = book(s, action="groups")
    assert shown.card["rows"] == [["Family", "1", "Mum"], ["Uni friends", "2", "Jo, Sam"]]
    listed = book(s, action="list", group="uni friends")
    assert str(listed) == "2 people in uni friends." and len(listed.card["rows"]) == 2
    assert book(s, action="group_leave", people=["jo"], group="uni friends") == "Took Jo out of uni friends."
    assert len(book(s, action="list", group="Uni friends").card["rows"]) == 1


def test_family_tree(s):
    fill(s)
    assert book(s, action="link", name="Mum", relation="parent", other="Sam") == "Noted: Mum is Sam's parent."
    assert book(s, action="link", name="Mia", relation="child", other="Sam") == \
        "Noted: Mia is Sam's child. I added Mia to the notebook too."
    book(s, action="link", name="Alex", relation="partner", other="Sam")
    shown = book(s, action="tree", name="sam")
    assert shown.card["kind"] == "people-tree"
    data = shown.card["data"]
    assert data["rows"] == [["Mum"], ["Alex", "Sam"], ["Mia"]]
    assert data["edges"] == [["Mum", "Sam"], ["Sam", "Mia"]] and data["partners"] == [["Alex", "Sam"]]
    assert str(shown) == "The family tree has 4 people over 3 generations."
    assert book(s, action="tree").card["data"]["rows"] == data["rows"]
    assert "confirm" in book(s, action="unlink", name="Alex", relation="partner", other="Sam")
    book(s, action="unlink", name="Alex", relation="partner", other="Sam", confirmed=True)
    assert book(s, action="tree", name="sam").card["data"]["partners"] == []
    assert book(s, action="tree", name="jo").startswith("No family links yet.")


def test_call_reminder(s):
    fill(s)
    out = book(s, action="call_reminder", name="mum", when="2026-10-04 18:00", repeat="weekly")
    assert out.startswith("I'll remind them") and "Call Mum" in out
    assert reminders.load(s)[0]["text"] == "Call Mum" and reminders.load(s)[0]["repeat"] == "weekly"


def test_keep_in_touch(s):
    fill(s)
    assert touch(s, action="overdue").startswith("No keep-in-touch goals yet.")
    assert touch(s, action="every", name="mum", days=7) == \
        "I'll aim for you to be in touch with Mum every 7 days. You're due to get in touch now."
    touch(s, action="every", name="sam", days=30)
    assert touch(s, action="contacted", name="sam", date="2026-09-20", how="visit") == \
        "Logged a visit with Sam 8 days ago. Next catch-up due in 30 days."
    shown = touch(s, action="overdue")
    assert str(shown).startswith("1 person to get in touch with: Mum.")
    assert shown.card["checks"] and shown.card["items"][0]["say"] == "I've just been in touch with Mum."
    assert touch(s, action="contacted", name="mum", topics=["holiday", "the garden"]) == \
        "Logged a call with Mum today. Next catch-up due in 7 days."
    assert touch(s, action="overdue") == "You're up to date with everyone."
    with pytest.raises(ValueError):
        touch(s, action="contacted", name="mum", date="2026-10-10")


def test_conversations_and_week(s, tmp_path):
    fill(s)
    touch(s, action="contacted", name="mum", date="2026-09-01", topics=["holiday"])
    touch(s, action="contacted", name="mum", date="2026-09-27", topics=["the garden"], text="Roses doing well")
    shown = touch(s, action="conversations", name="mum")
    assert str(shown) == "2 catch-ups with Mum; the last was yesterday, about the garden."
    assert shown.card["rows"][0] == ["27 Sep 2026", "call", "the garden", "Roses doing well"]
    assert touch(s, action="conversations", name="jo") == "Nothing logged with Jo yet."
    (tmp_path / "birthdays.json").write_text(json.dumps({"Jo": "10-03"}))
    occ(s, action="thanks_add", name="Sam", what="scarf")
    week = touch(s, action="week")
    assert str(week) == "This week you've been in touch 1 time, and Jo's birthday is in 5 days."
    assert "Thank-yous to send: 1 (Sam)" in week.card["text"] and week.card["id"] == "people-week"


def test_special_dates(s):
    fill(s)
    assert occ(s, action="date_add", name="sam", label="Wedding anniversary", date="2015-10-20") == \
        "Saved Sam's wedding anniversary: next on Tuesday 20 October, in 22 days, 11 years."
    occ(s, action="date_add", name="mum", label="Retirement day", date="10-01")
    with pytest.raises(ValueError):
        occ(s, action="date_add", name="mum", label="birthday", date="10-01")
    shown = occ(s, action="dates")
    assert str(shown) == "Next up: Mum's retirement day, in 3 days."
    assert shown.card["rows"][1] == ["Sam", "wedding anniversary", "20 Oct 2026", "in 22 days", "11"]
    assert "Wedding anniversary: 20 Oct 2026" in book(s, action="card", name="sam").card["text"]
    assert "confirm" in occ(s, action="date_remove", name="mum", label="retirement")
    assert occ(s, action="date_remove", name="mum", label="retirement", confirmed=True) == "Removed Mum's retirement day."


def test_thank_yous(s):
    fill(s)
    assert occ(s, action="thanks") == "No gifts or favours on the thank-you list."
    assert occ(s, action="thanks_add", name="sam", what="lift to the airport", kind="favour") == \
        "Noted lift to the airport from Sam. 1 thank-you still to send."
    occ(s, action="thanks_add", name="Gran", what="scarf")
    shown = occ(s, action="thanks")
    assert str(shown) == "2 thank-yous to send, the oldest to Sam." and shown.card["checks"]
    assert shown.card["items"][1]["say"] == "I've sent the thank-you to Gran for scarf."
    assert occ(s, action="thanks_sent", name="gran") == "Thank-you to Gran for scarf sent. 1 thank-you left."
    assert occ(s, action="thanks").card["items"][-1]["done"] is True
    with pytest.raises(ValueError):
        occ(s, action="thanks_sent", name="gran")


def test_promises(s):
    fill(s)
    assert occ(s, action="promise_add", name="jo", what="lend the ladder", date="2026-10-02") == \
        "Noted: you promised Jo lend the ladder by Friday 2 October."
    assert occ(s, action="promise_add", name="sam", what="a coffee", direction="they_owe") == "Noted: Sam owes you a coffee."
    shown = occ(s, action="promises")
    assert str(shown) == "You owe 1, others owe you 1."
    assert shown.card["items"][0]["label"] == "You owe - Jo: lend the ladder, due in 4 days"
    assert occ(s, action="promise_done", name="jo") == "Ticked off lend the ladder for Jo."
    assert len(occ(s, action="promises").card["items"]) == 1


def test_holiday_cards(s):
    fill(s)
    book(s, action="group_add", people=["Mum", "Sam"], group="Family")
    assert lists(s, action="cards_add", groups=["family"], people=["Jo"]) == "3 people on the 2026 card list."
    shown = lists(s, action="cards")
    assert str(shown) == "3 cards to go out of 3." and shown.card["checks"]
    assert shown.card["items"][1]["label"] == "Mum - 2 Park Rd, York"
    assert "York" not in str(shown)
    assert lists(s, action="card_sent", name="mum") == "Mum's card done. 2 cards to go."
    assert lists(s, action="cards").card["items"][1]["done"] is True
    assert "confirm" in lists(s, action="card_remove", name="jo")
    assert lists(s, action="card_remove", name="jo", confirmed=True) == "Took Jo off the 2026 card list."
    with pytest.raises(ValueError):
        lists(s, action="cards_add", groups=["Nobody"])


def test_invite_lists(s):
    fill(s)
    book(s, action="group_add", people=["Sam", "Jo"], group="Uni friends")
    assert lists(s, action="invites").startswith("No invite lists yet.")
    assert lists(s, action="invite_build", list_name="Birthday party", groups=["uni friends"], people=["Mum"]) == \
        "3 people on the Birthday party invite list."
    shown = lists(s, action="invites", list_name="birthday party")
    assert shown.card["kind"] == "table" and [r[0] for r in shown.card["rows"]] == ["Mum", "Sam", "Jo"]
    assert lists(s, action="invite_drop", list_name="birthday party", people=["mum"]) == \
        "2 people left on the Birthday party invite list."
    assert lists(s, action="invites").card["items"][0]["say"] == "Show my Birthday party invite list."
    assert "confirm" in lists(s, action="invite_remove", list_name="birthday party")
    assert lists(s, action="invite_remove", list_name="birthday party", confirmed=True) == \
        "Deleted the Birthday party invite list."


def test_runs_through_tools_without_network(s):
    fill(s)

    def handler(request):
        raise AssertionError("people abilities must not use the network")

    cards = []

    async def page(message):
        cards.append(message["card"])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await tools.run_tool("people_book", {"action": "list"}, s, http, page)

    assert asyncio.run(go()) == "3 people in your notebook." and cards[0]["kind"] == "table"
