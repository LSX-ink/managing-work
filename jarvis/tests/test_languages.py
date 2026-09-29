from datetime import date, datetime

import pytest

import homestore
import languages_data as data
import languages_practice as practice
import languages_progress as progress
import languages_store as ls
import languages_study as study
import languages_talk as talk
import languages_verbs as verbs
import screen
import tools
from config import Settings

NOW = datetime(2026, 9, 29, 9, 0)


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: NOW)
    return Settings(memory_dir=str(tmp_path))


def st(s, **args):
    return study.run_tool("language_study", args, s)


def pr(s, **args):
    return practice.run_tool("language_practice", args, s)


def pg(s, **args):
    return progress.run_tool("language_progress", args, s)


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in (study, practice, progress):
        assert module in tools.ABILITIES
        (tool,) = module.tool_definitions()
        assert tool["name"] in names and tool["input_schema"]["additionalProperties"] is False
        assert set(tool["input_schema"]["properties"]["action"]["enum"]) == set(
            {"language_study": study.ACTIONS, "language_practice": practice.ACTIONS,
             "language_progress": progress.ACTIONS}[tool["name"]])
    for kind in ("languages-cards", "languages-say", "languages-quiz", "languages-conjugate", "languages-dialogue",
                 "languages-dash"):
        assert kind in screen.EXTRA_KINDS


def test_data_lines_up():
    for lang in data.LANGS:
        for topic, english in data.ENGLISH.items():
            assert len(data.VOCAB[lang][topic]) == len(english)
        assert len(data.number_words(lang)) == len(data.NUMBER_VALUES)
        assert len(data.TIPS[lang]) == 5
    assert data.number_words("ja")[12] == "十二|jūni" and data.number_words("ja")[22] == "四十|yonjū"
    assert ls.entry("es", "la mañana:f", "morning", "time")["word"] == "mañana"
    assert ls.entry("fr", "l'œuf:m", "egg", "food")["article"] == "l'"


# ---- study ---------------------------------------------------------------------------------------------

def test_languages_and_set_language(s):
    shown = st(s, action="languages")
    assert shown.card["kind"] == "list" and len(shown.card["items"]) == 6
    assert "Spanish" in st(s, action="set_language", language="spanish")
    assert ls.load(s)["language"] == "es"
    with pytest.raises(ValueError, match="Klingon|teach"):
        st(s, action="set_language", language="Klingon")
    with pytest.raises(ValueError, match="Which language"):
        st(Settings(memory_dir=s.memory_dir + "/other"), action="decks")


def test_decks_and_flashcards(s):
    st(s, action="set_language", language="French")
    decks = st(s, action="decks")
    assert decks.card["kind"] == "list" and len(decks.card["items"]) == 7
    shown = st(s, action="flashcards", topic="food", count=5)
    card = shown.card
    assert card["kind"] == "languages-cards" and len(card["data"]["cards"]) == 5
    assert card["data"]["speech"] == "fr-FR" and card["data"]["track"] is True
    reverse = st(s, action="flashcards", topic="numbers", direction="from_english", count=3).card["data"]["cards"][0]
    assert reverse["front"].isdigit() and reverse["say"]
    with pytest.raises(ValueError, match="nothing due"):
        st(s, action="review_due")
    with pytest.raises(ValueError, match="deck called"):
        st(s, action="flashcards", topic="spaceships")


def test_save_review_schedules_due_dates(s):
    st(s, action="set_language", language="es")
    msg = st(s, action="save_review", results="el pan=good; la leche=again; el queso=easy; el té=hard")
    assert "Saved 4" in msg and "1 will come back" in msg
    cards = ls.load(s)["cards"]["es"]
    assert cards["el pan"]["due"] == "2026-09-30" and cards["el pan"]["box"] == 1
    assert cards["la leche"]["due"] == "2026-09-29" and cards["la leche"]["lapses"] == 1
    assert cards["el queso"]["box"] == 2 and cards["el queso"]["due"] == "2026-10-02"
    assert cards["el té"]["box"] == 0 and cards["el té"]["due"] == "2026-09-30"
    due = st(s, action="review_due")
    assert [c["id"] for c in due.card["data"]["cards"]] == ["la leche"]
    assert ls.load(s)["log"]["2026-09-29"]["reviews"] == 4
    with pytest.raises(ValueError, match="grades"):
        st(s, action="save_review", results="nonsense")


def test_srs_intervals_grow():
    found = {"cards": {}}
    day = date(2026, 9, 29)
    for expected in (1, 3, 7, 14):
        ls.grade(found, "es", "hola", "good", day)
        assert found["cards"]["es"]["hola"]["due"] == (day.fromordinal(day.toordinal() + expected)).isoformat()


def test_own_words(s):
    st(s, action="set_language", language="de")
    assert "Added" in st(s, action="add_word", word="der Hund", meaning="dog", note="masculine")
    with pytest.raises(ValueError, match="already"):
        st(s, action="add_word", word="Der Hund", meaning="dog")
    shown = st(s, action="my_words")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][:2] == ["der Hund", "dog"]
    own = st(s, action="flashcards", topic="mine").card["data"]["cards"]
    assert [c["id"] for c in own] == ["der hund"]
    assert "Shall I remove" in st(s, action="remove_word", word="der Hund")
    assert ls.load(s)["words"]["de"]
    assert "Removed" in st(s, action="remove_word", word="der Hund", confirmed=True)
    assert not ls.load(s)["words"]["de"]
    with pytest.raises(ValueError, match="haven't added"):
        st(s, action="my_words")


def test_find_word_and_word_of_the_day(s):
    found = st(s, action="find_word", language="Spanish", query="milk")
    assert found.card["kind"] == "table" and found.card["rows"][0][:2] == ["milk", "la leche"]
    assert st(s, action="find_word", language="ja", query="kōhī").card["rows"][0][0] == "coffee"
    with pytest.raises(ValueError, match="haven't got"):
        st(s, action="find_word", language="es", query="zzzz")
    day = st(s, action="word_of_the_day", language="it")
    assert day.card["kind"] == "languages-cards" and day.card["data"]["track"] is False
    assert len(day.card["data"]["cards"]) == 1 and "Italian word" in str(day)
    assert st(s, action="word_of_the_day", language="it") == day


def test_speak_and_tips(s):
    said = st(s, action="speak", language="pt", text="Bom dia. Como estás?")
    assert said.card["kind"] == "languages-say" and len(said.card["data"]["items"]) == 2
    assert said.card["data"]["speech"] == "pt-PT"
    deck = st(s, action="speak", language="ja", topic="greetings").card["data"]["items"]
    assert deck[0]["text"] == "こんにちは" and "konnichiwa" in deck[0]["note"]
    tips = st(s, action="pronunciation_tips", language="fr")
    assert tips.card["kind"] == "list" and len(tips.card["items"]) == 5


def test_unknown_action(s):
    with pytest.raises(ValueError):
        st(s, action="nope")


# ---- practice ------------------------------------------------------------------------------------------

def test_vocab_quiz_choice_and_typing(s):
    shown = pr(s, action="vocab_quiz", language="es", topic="food", count=5)
    q = shown.card["data"]["questions"]
    assert shown.card["kind"] == "languages-quiz" and len(q) == 5
    assert all(x["answer"] in x["options"] and len(x["options"]) == 4 for x in q)
    typed = pr(s, action="vocab_quiz", language="es", topic="food", kind="typing", direction="from_english",
               count=3).card["data"]["questions"]
    assert all(x["kind"] == "type" and x["accept"] for x in typed)
    assert any(x["answer"].startswith(("el ", "la ")) for x in typed) and all(x["key"] for x in typed)
    ja = pr(s, action="vocab_quiz", language="ja", topic="food", kind="typing", direction="from_english",
            count=2).card["data"]["questions"]
    assert all(len(x["accept"]) == 2 for x in ja)
    with pytest.raises(ValueError, match="nothing to quiz"):
        pr(s, action="vocab_quiz", language="es", topic="due")


def test_article_and_gender_drill(s):
    article = pr(s, action="article_drill", language="de", mode="article", count=6).card["data"]["questions"]
    assert all(q["options"] == ["der", "die", "das"] and q["answer"] in q["options"] for q in article)
    gender = pr(s, action="article_drill", language="fr", mode="gender", count=6).card["data"]["questions"]
    assert all(q["options"] == ["masculine", "feminine"] for q in gender)
    german = pr(s, action="article_drill", language="de", mode="gender", count=3).card["data"]["questions"]
    assert "neuter" in german[0]["options"]
    for q in pr(s, action="article_drill", language="it", mode="article", count=20).card["data"]["questions"]:
        assert q["answer"] in ("il", "la")
    with pytest.raises(ValueError, match="no articles"):
        pr(s, action="article_drill", language="ja")


def test_number_practice(s):
    to_word = pr(s, action="number_practice", language="de", up_to=10, count=5).card["data"]["questions"]
    assert all(q["prompt"].isdigit() and int(q["prompt"]) <= 10 for q in to_word)
    to_number = pr(s, action="number_practice", language="ja", direction="to_english", kind="typing",
                   count=4).card["data"]["questions"]
    assert all(q["accept"] == [q["answer"]] and "(" in q["prompt"] for q in to_number)
    hundred = pr(s, action="number_practice", language="fr", up_to=100, count=20).card["data"]["questions"]
    assert max(int(q["prompt"]) for q in hundred) > 20


def test_clock_words():
    assert talk.clock("es", 3, 15)[0] == "Son las tres y cuarto"
    assert talk.clock("es", 1, 40)[0] == "Son las dos menos veinte"
    assert talk.clock("fr", 6, 45)[0] == "Il est sept heures moins le quart"
    assert talk.clock("fr", 1, 30)[0] == "Il est une heure et demie"
    assert talk.clock("de", 3, 30)[0] == "Es ist halb vier"
    assert talk.clock("de", 3, 45)[0] == "Es ist Viertel vor vier"
    assert talk.clock("it", 1, 0)[0] == "È l'una"
    assert talk.clock("it", 12, 35)[0] == "È l'una meno venticinque"
    assert talk.clock("pt", 1, 0)[0] == "É uma hora"
    assert talk.clock("pt", 4, 45)[0] == "É um quarto para as cinco"
    assert talk.clock("pt", 12, 50)[0] == "São dez para a uma"
    assert talk.clock("ja", 4, 30) == ("四時半", "yoji han")
    assert talk.clock("ja", 7, 10) == ("七時十分", "shichiji juppun")
    with pytest.raises(ValueError):
        talk.clock("es", 13, 0)
    for lang in data.LANGS:
        for h in range(1, 13):
            for m in range(0, 60, 5):
                assert talk.clock(lang, h, m)[0]


def test_time_practice(s):
    say = pr(s, action="time_practice", language="es", count=4).card["data"]["questions"]
    assert all(q["clock"] and q["answer"] in q["options"] for q in say)
    read = pr(s, action="time_practice", language="de", direction="to_english", count=3).card["data"]["questions"]
    assert all(":" in q["answer"] and q["clock"] for q in read)
    typed = pr(s, action="time_practice", language="ja", kind="typing", count=2).card["data"]["questions"]
    assert all(q["kind"] == "type" and len(q["accept"]) == 2 for q in typed)


def test_verb_tables():
    assert verbs.table("es", "ir")["tenses"][1]["rows"][1] == ["tú", "fuiste"]
    assert verbs.table("es", "hablar")["tenses"][2]["rows"][3] == ["nosotros", "hablaremos"]
    assert verbs.table("es", "vivir")["tenses"][0]["rows"][4] == ["vosotros", "vivís"]
    assert verbs.table("fr", "avoir")["tenses"][1]["rows"][0] == ["j'", "ai eu"]
    assert verbs.table("fr", "finir")["tenses"][0]["rows"][3] == ["nous", "finissons"]
    assert verbs.table("de", "sprechen")["tenses"][0]["rows"][2] == ["er/sie/es", "spricht"]
    assert verbs.table("de", "gehen")["tenses"][1]["rows"][0] == ["ich", "bin gegangen"]
    assert verbs.table("it", "essere")["tenses"][1]["rows"][0] == ["io", "sono stato/a"]
    assert verbs.table("pt", "falar")["tenses"][1]["rows"][3] == ["nós", "falámos"]
    assert verbs.table("pt", "ser")["tenses"][0]["rows"][4] == ["eles/elas", "são"]
    assert verbs.table("ja", "taberu")["tenses"][1]["rows"][0] == ["polite", "食べました (tabemashita)"]
    for lang, table in verbs.VERBS.items():
        for verb, info in table.items():
            if lang != "ja":
                for key in ("present", "past", "future"):
                    assert len(info[key]) == len(verbs.PERSONS[lang]), (lang, verb, key)


def test_conjugation_and_verb_list(s):
    shown = pr(s, action="conjugation", language="es", verb="to go")
    assert shown.card["kind"] == "languages-conjugate" and shown.card["data"]["verb"] == "ir"
    assert len(shown.card["data"]["tenses"]) == 3 and "voy, vas, va" in str(shown)
    past = pr(s, action="conjugation", language="fr", verb="être", tense="past").card["data"]["tenses"]
    assert len(past) == 1 and past[0]["rows"][0] == ["j'", "ai été"]
    assert pr(s, action="conjugation", language="de").card["kind"] == "list"
    lst = pr(s, action="verb_list", language="ja")
    assert lst.card["kind"] == "list" and lst.card["items"][0]["say"].startswith("Conjugate")
    with pytest.raises(ValueError, match="don't have"):
        pr(s, action="conjugation", language="es", verb="fly")


def test_conjugation_drill(s):
    typed = pr(s, action="conjugation_drill", language="it", verb="andare", tense="past", kind="typing",
               count=6).card["data"]["questions"]
    assert all(q["kind"] == "type" for q in typed)
    row = next(q for q in typed if q["answer"] == "sono andato/a")
    assert "sono andato" in row["accept"] and "sono andata" in row["accept"]
    choice = pr(s, action="conjugation_drill", language="es", verb="ser", count=5).card["data"]["questions"]
    assert all(q["answer"] in q["options"] for q in choice)
    with pytest.raises(ValueError, match="Japanese"):
        pr(s, action="conjugation_drill", language="ja")


def test_dialogue(s):
    lst = pr(s, action="dialogue_list", language="fr")
    assert lst.card["kind"] == "list" and len(lst.card["items"]) == 2
    assert pr(s, action="dialogue", language="fr").card["kind"] == "list"
    shown = pr(s, action="dialogue", language="es", scene="cafe")
    turns = shown.card["data"]["turns"]
    assert shown.card["kind"] == "languages-dialogue" and len(turns) == 6
    mine = [t for t in turns if t["who"] == "you"]
    assert len(mine) == 3 and all(len(t["options"]) == 3 for t in mine)
    assert mine[0]["options"][mine[0]["correct"]]["text"] == "Un café con leche, por favor."
    ja = pr(s, action="dialogue", language="ja", scene="directions").card["data"]["turns"]
    assert ja[0]["options"][ja[0]["correct"]]["roman"].startswith("sumimasen")
    for lang in data.LANGS:
        for scene in talk.SCENES:
            assert len(talk.DIALOGUES[lang][scene]) in (5, 6)


def test_save_result_puts_misses_back(s):
    msg = pr(s, action="save_result", language="es", label="food vocabulary", score=7, total=10,
             wrong="el pan; la leche; nonsense")
    assert "7 out of 10" in msg and "2 missed words" in msg
    found = ls.load(s)
    assert found["quizzes"][0]["score"] == 7 and found["log"]["2026-09-29"]["quizzes"] == 1
    assert found["cards"]["es"]["el pan"]["lapses"] == 1 and "nonsense" not in found["cards"]["es"]
    with pytest.raises(ValueError):
        pr(s, action="save_result", language="es", score=11, total=10)


def test_practice_unknown_action(s):
    with pytest.raises(ValueError):
        pr(s, action="nope")


# ---- progress ------------------------------------------------------------------------------------------

def test_log_minutes_streak_and_goal(s):
    assert "No study logged" in pg(s, action="streak")
    assert "Logged 15 minutes" in pg(s, action="log_minutes", minutes=15)
    assert "Daily goal reached" in pg(s, action="log_minutes", minutes=1)
    pg(s, action="log_minutes", minutes=5, date="yesterday")
    pg(s, action="log_minutes", minutes=5, date="2026-09-25")
    assert "streak is 2 days" in pg(s, action="streak")
    assert "best is 2 days" in pg(s, action="streak")
    with pytest.raises(ValueError, match="already happened"):
        pg(s, action="log_minutes", minutes=5, date="2026-10-01")
    assert "20 minutes" in pg(s, action="set_goal", goal=20)
    assert "to your goal of 20" in pg(s, action="log_minutes", minutes=2)


def test_streak_counts_reviews_and_survives_today_empty(s):
    found = {"log": {"2026-09-27": {"reviews": 3}, "2026-09-28": {"quizzes": 1}}}
    assert ls.streaks(found, date(2026, 9, 29)) == (2, 2)
    assert ls.streaks(found, date(2026, 9, 30)) == (0, 2)


def test_dashboard_and_charts(s):
    st(s, action="set_language", language="es")
    st(s, action="save_review", results="el pan=easy; el té=easy; la leche=easy")
    pg(s, action="log_minutes", minutes=12)
    dash = pg(s, action="dashboard")
    d = dash.card["data"]
    assert dash.card["kind"] == "languages-dash" and d["streak"] == 1 and d["today"] == 12
    assert d["seen"] == 3 and len(d["decks"]) == 7 and len(d["week"]["values"]) == 14 and d["week"]["values"][-1] == 12
    chart = pg(s, action="minutes_chart", days=7)
    assert chart.card["kind"] == "chart" and chart.card["chart"]["values"][-1] == 12
    assert len(chart.card["chart"]["values"]) == 7
    forecast = pg(s, action="due_forecast")
    assert forecast.card["chart"]["values"][3] == 3 and len(forecast.card["chart"]["labels"]) == 7
    progress_table = pg(s, action="deck_progress")
    assert progress_table.card["kind"] == "table" and progress_table.card["rows"][1][:3] == ["Food and drink", "10", "3"]


def test_quiz_history_and_weak_words(s):
    st(s, action="set_language", language="es")
    with pytest.raises(ValueError, match="No Spanish quizzes"):
        pg(s, action="quiz_history")
    with pytest.raises(ValueError, match="No missed"):
        pg(s, action="weak_words")
    pr(s, action="save_result", label="food", score=8, total=10, wrong="el pan")
    hist = pg(s, action="quiz_history")
    assert hist.card["rows"][0][2:] == ["8/10", "80%"]
    weak = pg(s, action="weak_words")
    assert weak.card["kind"] == "list" and "el pan: bread" in weak.card["items"][0]["label"]


def test_reset_progress_needs_confirmation(s):
    st(s, action="set_language", language="es")
    st(s, action="save_review", results="el pan=good")
    assert "Shall I go ahead" in pg(s, action="reset_progress")
    assert ls.load(s)["cards"]["es"]
    assert "Cleared" in pg(s, action="reset_progress", confirmed=True)
    assert "es" not in ls.load(s)["cards"]


def test_progress_unknown_action(s):
    with pytest.raises(ValueError):
        pg(s, action="nope")
