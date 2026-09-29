import pytest

import partyhost_cards as cards
import partyhost_draw as draw
import partyhost_questions as bank
import partyhost_quiz as quiz
import partyhost_rules as rules
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def q(s, **a):
    return quiz.run_tool("party_quiz", a, s)


def c(s, **a):
    return cards.run_tool("party_cards", a, s)


def d(s, **a):
    return draw.run_tool("party_draw", a, s)


def r(s, **a):
    return rules.run_tool("party_rules", a, s)


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in (quiz, cards, draw, rules):
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False
        for kind in ("partyhost-scoreboard", "partyhost-cards", "partyhost-santa"):
            assert kind in screen.EXTRA_KINDS


def test_bank_has_150_questions_in_ten_categories():
    assert bank.total() == 150
    assert len(bank.categories()) == 10
    assert all(len(v) == 15 for v in bank.QUESTIONS.values())


# ---- quiz ---------------------------------------------------------------------------------------

def start(s, **extra):
    return q(s, action="start", teams=["Reds", "Blues", "Greens"], rounds=2, per_round=3, **extra)


def test_start_and_categories(s):
    out = q(s, action="categories")
    assert out.card["kind"] == "table" and len(out.card["rows"]) == 10
    out = start(s, categories=["science", "sport"])
    assert isinstance(out, screen.Shown) and out.card["kind"] == "partyhost-scoreboard"
    assert len(out.card["data"]["rows"]) == 3
    assert "Science, Sport" in out
    with pytest.raises(ValueError, match="2 to 8 teams"):
        q(s, action="start", teams=["Solo"])
    with pytest.raises(ValueError, match="round"):
        q(s, action="start", teams=["A", "B"], categories=["knitting"])
    out = q(s, action="start", team_count=3, confirmed=True)
    assert [t["name"] for t in out.card["data"]["rows"]] == ["Team 1", "Team 2", "Team 3"]


def test_start_needs_confirmation_when_scores_exist(s):
    start(s)
    q(s, action="award", team="Reds")
    with pytest.raises(ValueError, match="confirmed"):
        start(s)
    assert start(s, confirmed=True)


def test_question_reveal_award_flow(s):
    start(s, categories=["Geography"])
    out = q(s, action="question")
    assert out.card["kind"] == "partyhost-question"
    assert out.card["data"]["answer"] == "" and "Round 1" in out
    assert out.card["data"]["question"] in out
    shown = q(s, action="reveal")
    assert shown.card["data"]["answer"] and shown.startswith("The answer is")
    out = q(s, action="award", team="blues", points=2)
    assert out.startswith("2 points to Blues. That makes 2.")
    out = q(s, action="award", team="Blues")
    assert "1 point to Blues. That makes 3." in out
    assert out.card["data"]["rows"][0]["name"] == "Blues" and out.card["data"]["rows"][0]["rank"] == 1
    with pytest.raises(ValueError, match="Which team"):
        q(s, action="award", team="Purples")
    with pytest.raises(ValueError, match="Give between"):
        q(s, action="award", team="Reds", points=0)


def test_questions_run_through_rounds_then_finish(s):
    start(s)
    seen = []
    for _ in range(6):
        out = q(s, action="question")
        seen.append(out.card["data"]["question"])
    assert len(set(seen)) == 6
    assert out.card["data"]["label"] == "Round 2 of 2"
    last = q(s, action="question")
    assert last.card["kind"] == "partyhost-scoreboard" and "last question" in last


def test_reveal_and_others_need_a_quiz(s):
    with pytest.raises(ValueError, match="no quiz"):
        q(s, action="question")
    start(s)
    with pytest.raises(ValueError, match="No question"):
        q(s, action="reveal")


def test_undo_scoreboard_round_results(s):
    start(s)
    with pytest.raises(ValueError, match="no points"):
        q(s, action="undo")
    q(s, action="question")
    q(s, action="award", team="Reds", points=3)
    q(s, action="award", team="Greens", points=1)
    out = q(s, action="round_results", round=1)
    rows = out.card["data"]["rows"]
    assert out.card["data"]["mode"] == "round" and rows[0]["name"] == "Reds" and rows[0]["rounds"] == [3]
    assert "Reds won it with 3" in out
    with pytest.raises(ValueError, match="2 rounds"):
        q(s, action="round_results", round=5)
    out = q(s, action="undo")
    assert "Taken back 1 from Greens" in out
    board = q(s, action="scoreboard")
    assert board.card["data"]["mode"] == "total" and board.card["data"]["rows"][0]["total"] == 3


def test_end_with_winner_and_tie(s):
    start(s)
    q(s, action="award", team="Reds", points=4)
    out = q(s, action="end")
    assert out.card["data"]["mode"] == "final" and "Reds win with 4" in out
    start(s, confirmed=True)
    q(s, action="award", team="Reds")
    q(s, action="award", team="Blues")
    out = q(s, action="end")
    assert "tie between Reds and Blues" in out
    assert out.card["buttons"][0]["label"] == "Tiebreaker"


def test_tiebreaker_add_question_and_sheets(s):
    with pytest.raises(ValueError, match="no quiz"):
        q(s, action="tiebreaker")
    start(s)
    out = q(s, action="tiebreaker")
    assert out.card["data"]["tiebreak"] and "closest number" in out.card["data"]["question"]
    assert "The answer" in q(s, action="reveal")
    assert q(s, action="add_question", category="Family", question="Who snores loudest?", answer="Dad") \
        == "Added your question to Family."
    assert q(s, action="add_question", category="science", question="Q?", answer="A").endswith("Science.")
    with pytest.raises(ValueError, match="answer"):
        q(s, action="add_question", question="No answer")
    cats = dict((row[0], row[1]) for row in q(s, action="categories").card["rows"])
    assert cats["Family"] == "1" and cats["Science"] == "16"
    out = q(s, action="start", teams=["A", "B"], rounds=1, per_round=1, categories=["Family"], confirmed=True)
    assert "Family" in out
    assert q(s, action="host_sheet").card["rows"][0][2] == "Dad"
    sheet = q(s, action="answer_sheet")
    assert sheet.card["kind"] == "table" and sheet.card["rows"][0][:2] == ["Round 1: Family", "1"]


def test_questions_do_not_repeat_between_quizzes(s):
    firsts = set()
    for _ in range(3):
        q(s, action="start", teams=["A", "B"], rounds=1, per_round=5, categories=["History"], confirmed=True)
        firsts |= {row[1] for row in q(s, action="host_sheet").card["rows"]}
    assert len(firsts) == 15


def test_buzzer(s):
    out = q(s, action="buzzer", teams=["Reds", "Blues"])
    assert out.card["kind"] == "partyhost-buzzer"
    assert out.card["data"]["teams"] == [{"name": "Reds", "key": "1"}, {"name": "Blues", "key": "2"}]
    with pytest.raises(ValueError, match="team names"):
        q(s, action="buzzer")
    start(s)
    assert len(q(s, action="buzzer").card["data"]["teams"]) == 3
    with pytest.raises(ValueError, match="quiz action"):
        q(s, action="nope")


# ---- cards --------------------------------------------------------------------------------------

def test_charades_pictionary_taboo_do_not_speak_words(s):
    out = c(s, mode="charades", category="animals")
    word = out.card["data"]["cards"][0]["word"]
    assert word in cards.data.WORDS["animals"] and word not in out
    assert out.card["kind"] == "partyhost-cards" and out.card["data"]["seconds"] == 90
    out = c(s, mode="pictionary", seconds=45)
    assert out.card["data"]["seconds"] == 45 and out.card["data"]["cards"][0]["category"] != "tv and books"
    with pytest.raises(ValueError, match="pictionary"):
        c(s, mode="pictionary", category="tv and books")
    out = c(s, mode="taboo")
    card = out.card["data"]["cards"][0]
    assert len(card["forbidden"]) == 5 and card["word"] not in out


def test_heads_up_deck_and_no_repeats(s):
    out = c(s, mode="heads_up", category="easy", count=20)
    words = [x["word"] for x in out.card["data"]["cards"]]
    assert len(words) == 20 and len(set(words)) == 20
    assert not any(w in out for w in words)
    with pytest.raises(ValueError, match="crockery"):
        c(s, mode="heads_up", category="crockery")


def test_truth_dare_and_icebreakers(s):
    out = c(s, mode="truth")
    assert out.startswith("Truth:") and out.card["data"]["mode"] == "prompt"
    assert c(s, mode="dare").startswith("Dare:")
    assert c(s, mode="truth_or_dare").startswith(("Truth:", "Dare:"))
    assert c(s, mode="icebreaker").startswith("Icebreaker:")
    cards._used.clear()
    seen = {c(s, mode="truth").card["data"]["cards"][0]["word"] for _ in range(len(cards.data.TRUTHS))}
    assert len(seen) == len(cards.data.TRUTHS)


def test_two_truths(s):
    out = c(s, mode="two_truths")
    assert out.card["kind"] == "text" and "two truths" in out.lower()
    out = c(s, mode="two_truths_shuffle", statements=["I swam with sharks", "I have 3 cats", "I can juggle"], lie=2)
    lies = [x for x in out.card["data"]["cards"] if x["lie"]]
    assert len(lies) == 1 and lies[0]["word"] == "I have 3 cats"
    with pytest.raises(ValueError, match="three"):
        c(s, mode="two_truths_shuffle", statements=["a", "b"], lie=1)
    with pytest.raises(ValueError, match="lie"):
        c(s, mode="two_truths_shuffle", statements=["a", "b", "c"], lie=7)


def test_scattergories_and_word_categories(s):
    out = c(s, mode="scattergories", count=6)
    data = out.card["data"]
    assert len(data["cards"]) == 6 and data["letter"] in cards.data.SCATTER_LETTERS and data["seconds"] == 120
    assert f"letter is {data['letter']}" in out
    table = c(s, mode="word_categories")
    assert table.card["kind"] == "table" and len(table.card["rows"]) == 10
    with pytest.raises(ValueError, match="party game"):
        c(s, mode="nope")


# ---- draws --------------------------------------------------------------------------------------

NAMES = ["Mum", "Dad", "Ava", "Leo", "Nan"]


def test_santa_draw_valid_and_private(s):
    out = d(s, action="santa_draw", names=NAMES, exclusions=[["Mum", "Dad"]], budget="£10")
    assert out.card["kind"] == "text" and "5 people" in out
    for _ in range(20):
        d(s, action="santa_draw", names=NAMES, exclusions=[["Mum", "Dad"]], confirmed=True)
        import homestore
        pairs = homestore.load(s, draw.SANTA, {})["pairs"]
        assert sorted(pairs.values()) == sorted(NAMES)
        assert all(g != rcv for g, rcv in pairs.items())
        assert pairs["Mum"] != "Dad" and pairs["Dad"] != "Mum"


def test_santa_draw_rules(s):
    with pytest.raises(ValueError, match="3 to 40"):
        d(s, action="santa_draw", names=["A", "B"])
    with pytest.raises(ValueError, match="two names"):
        d(s, action="santa_draw", names=NAMES, exclusions=[["Mum", "Bob"]])
    with pytest.raises(ValueError, match="no way"):
        d(s, action="santa_draw", names=["A", "B", "C"], exclusions=[["A", "B"], ["B", "C"], ["A", "C"]])
    d(s, action="santa_draw", names=NAMES)
    with pytest.raises(ValueError, match="confirmed"):
        d(s, action="santa_draw", names=NAMES)


def test_santa_next_status_clear(s):
    with pytest.raises(ValueError, match="no Secret Santa"):
        d(s, action="santa_next")
    d(s, action="santa_draw", names=NAMES, budget="£10")
    seen = []
    for i in range(5):
        out = d(s, action="santa_next")
        data = out.card["data"]
        assert out.card["kind"] == "partyhost-santa" and data["step"] == i + 1 and data["budget"] == "£10"
        assert data["recipient"] not in out and data["giver"] in out
        seen.append(data["giver"])
    assert seen == NAMES
    assert "Everybody has seen" in d(s, action="santa_next")
    again = d(s, action="santa_next", name="leo")
    assert again.card["data"]["giver"] == "Leo" and again.card["data"]["step"] == 5
    with pytest.raises(ValueError, match="in the draw"):
        d(s, action="santa_next", name="Zed")
    status = d(s, action="santa_status")
    assert "Everyone has seen" in status and status.card["kind"] == "table"
    with pytest.raises(ValueError, match="confirmed"):
        d(s, action="santa_clear")
    assert d(s, action="santa_clear", confirmed=True) == "The Secret Santa draw is cleared."
    assert d(s, action="santa_clear") == "There's no Secret Santa draw to clear."


def test_team_split(s):
    names = [f"P{i}" for i in range(7)]
    out = d(s, action="team_split", names=names, teams=3, captains=True)
    teams = out.card["data"]["teams"]
    assert out.card["kind"] == "partyhost-teams" and len(teams) == 3
    assert sorted(m for t in teams for m in t["members"]) == sorted(names)
    assert max(len(t["members"]) for t in teams) - min(len(t["members"]) for t in teams) <= 1
    assert all(t["captain"] in t["members"] for t in teams)
    out = d(s, action="team_split", names=names, team_size=3)
    assert len(out.card["data"]["teams"]) == 2
    with pytest.raises(ValueError, match="2 to 3 teams"):
        d(s, action="team_split", names=["A", "B", "C"], teams=5)
    with pytest.raises(ValueError, match="2 to 60"):
        d(s, action="team_split", names=["A"])


def test_musical_stop_and_round_timer(s):
    out = d(s, action="musical_stop", min_seconds=5, max_seconds=15)
    assert out.card["kind"] == "partyhost-stop" and out.card["data"] == {"min": 5, "max": 15}
    assert d(s, action="musical_stop").card["data"] == {"min": 8, "max": 30}
    out = d(s, action="round_timer", seconds=90)
    assert out.card["kind"] == "timer" and out.card["ends_at"] > 0 and "90 seconds" in out


def test_bingo_tickets_are_valid_uk_tickets(s):
    out = d(s, action="bingo_card", count=4)
    assert out.card["kind"] == "partyhost-bingo" and len(out.card["data"]["tickets"]) == 4
    for _ in range(30):
        ticket = draw._ticket()
        assert [sum(n is not None for n in row) for row in ticket] == [5, 5, 5]
        nums = [n for row in ticket for n in row if n]
        assert len(nums) == len(set(nums)) == 15
        for col in range(9):
            column = [row[col] for row in ticket if row[col]]
            assert 1 <= len(column) <= 3 and column == sorted(column)
            low, high = (1, 9) if col == 0 else (80, 90) if col == 8 else (col * 10, col * 10 + 9)
            assert all(low <= n <= high for n in column)


def test_bingo_calls(s):
    assert d(s, action="bingo_calls", number=11) == "11 is 'Legs eleven'."
    assert "no special call" in d(s, action="bingo_calls", number=34)
    with pytest.raises(ValueError, match="1 to 90"):
        d(s, action="bingo_calls", number=91)
    assert d(s, action="bingo_calls").card["kind"] == "table"


def test_who_goes_first(s):
    out = d(s, action="who_goes_first", names=["A", "B", "C"])
    assert out.card["kind"] == "list" and len(out.card["items"]) == 3
    with pytest.raises(ValueError, match="2 to 40"):
        d(s, action="who_goes_first", names=["A"])
    with pytest.raises(ValueError, match="party action"):
        d(s, action="nope")


# ---- rules --------------------------------------------------------------------------------------

def test_rules_and_list(s):
    out = r(s, action="rules", game="Musical chairs")
    assert "one fewer chair" in out and out.card["kind"] == "text"
    assert r(s, action="rules", game="telephone").card["title"] == "How to play: Chinese whispers"
    assert r(s, action="rules", game="pass the parcel").card["title"] == "How to play: Pass the parcel"
    assert "twenty" in r(s, action="rules", game="20 questions").lower()
    with pytest.raises(ValueError, match="rules for"):
        r(s, action="rules", game="quidditch")
    listing = r(s, action="list_games")
    assert len(listing.card["items"]) == len(rules.RULES) >= 25
    assert all(i["say"] for i in listing.card["items"])


def test_every_rule_resolves():
    for key in rules.RULES:
        assert rules._game_key(key.replace("_", " ")) == key


def test_ideas_and_plan_night(s):
    out = r(s, action="ideas", players=4, kids=True, energy="lively")
    assert out.card["kind"] == "table" and out.card["rows"]
    with pytest.raises(ValueError, match="Nothing fits"):
        r(s, action="ideas", players=500)
    out = r(s, action="plan_night", hours=3, players=8)
    labels = [i["label"] for i in out.card["items"]]
    assert labels[0].endswith("Welcome and icebreaker questions") and labels[-1].endswith("a final chat")
    assert len(labels) >= 5
    assert r(s, action="plan_night", kids=True).card["kind"] == "list"
    with pytest.raises(ValueError, match="party action"):
        r(s, action="nope")
