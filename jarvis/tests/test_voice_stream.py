"""Alfred starts speaking while his answer is still being written."""

from types import SimpleNamespace

from brain import Brain, SentenceSplitter
from config import Settings

SETTINGS = Settings(model="claude-opus-5", tasks_file="", enable_screen=False)


def test_first_sentence_goes_alone_then_bigger_pieces():
    s = SentenceSplitter()
    out = []
    for token in ["Right", ". Good ", "evening, sir. ", "It is 18 degrees", " and dry. Rain comes ", "later tonight. ",
                  "Bring a coat if you head out, and the trains are running normally this evening. Anything else?"]:
        out += s.feed(token)
    out += s.flush()
    assert out[0] == "Right. Good evening, sir."  # "Right." alone is too short to start with
    assert "".join(out).replace(" ", "") == ("Right. Good evening, sir. It is 18 degrees and dry. Rain comes later tonight. "
                                            "Bring a coat if you head out, and the trains are running normally this "
                                            "evening. Anything else?").replace(" ", "")
    assert all(len(p) >= 12 for p in out)
    assert len(out) <= 3  # not one voice call per phrase


def test_numbers_and_quotes_do_not_split_mid_sentence():
    s = SentenceSplitter()
    assert s.feed("It costs 3.50 pounds today") == []
    assert s.feed(" and he said \"Fine.\" Then") == ['It costs 3.50 pounds today and he said "Fine."']


class StreamingClient:
    """Streams scripted text in small pieces, like the real API, then returns the whole message."""

    def __init__(self, pieces):
        self.pieces = pieces
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream, create=None))

    def _stream(self, **kwargs):
        pieces = self.pieces

        class Stream:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def __aiter__(self):
                async def gen():
                    for p in pieces:
                        yield SimpleNamespace(type="text", text=p)
                    yield SimpleNamespace(type="content_block_stop")
                return gen()

            async def get_final_message(self):
                return SimpleNamespace(stop_reason="end_turn",
                                       content=[SimpleNamespace(type="text", text="".join(pieces))])

        return Stream()


async def test_streamed_answer_is_spoken_in_pieces_on_one_transcript_line():
    client = StreamingClient(["Good evening, sir. ", "The weather is mild ", "and dry all evening, with a light breeze ",
                              "from the west and clear skies after dark. ", "Enjoy it."])
    said = []

    async def speak(text, quiet=False, join=False):
        said.append((text, join))

    await Brain(SETTINGS, client, http=None).handle("How is the weather?", speak)
    assert said[0] == ("Good evening, sir.", False)
    assert len(said) >= 2 and all(join for _, join in said[1:])
    assert " ".join(t for t, _ in said).startswith("Good evening, sir. The weather is mild")


def test_live_replies_use_the_fastest_voice_model():
    import tts
    assert tts.live_model(Settings(speech_lang="en-GB", elevenlabs_model="")) == "eleven_flash_v2_5"
    assert tts.live_model(Settings(speech_lang="af-ZA", elevenlabs_model="")) == "eleven_v3"
    assert tts.live_model(Settings(speech_lang="en-GB", elevenlabs_model="mine")) == "mine"
    assert tts.elevenlabs_model(Settings(speech_lang="en-GB", elevenlabs_model="")) == "eleven_turbo_v2_5"  # videos unchanged


async def test_a_cancelled_turn_leaves_no_half_finished_history():
    import asyncio

    class SlowClient:
        def __init__(self):
            self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

        async def _create(self, **kwargs):
            await asyncio.sleep(30)

    b = Brain(SETTINGS, SlowClient(), http=None)
    before = len(b.messages)

    async def speak(text, quiet=False, join=False):
        pass

    task = asyncio.create_task(b.handle("Research everything", speak))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert len(b.messages) == before


def test_saying_cancel_stops_a_long_turn(monkeypatch):
    import asyncio

    from fastapi.testclient import TestClient
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    import server

    async def slow(self, text, speak):
        await asyncio.sleep(30)

    monkeypatch.setattr(server.Brain, "handle", slow)
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
            ws.receive_json()  # alerts
            ws.send_json({"text": "research everything"})
            ws.send_json({"type": "cancel"})
            assert ws.receive_json() == {"type": "note", "text": "Cancelled."}
            assert ws.receive_json() == {"type": "done"}


async def test_short_lines_are_voiced_once_then_replayed_from_memory():
    import httpx

    import tts
    tts._cache.clear()
    calls = []

    def answer(request):
        calls.append(request)
        return httpx.Response(200, content=b"MP3")

    settings = Settings(elevenlabs_api_key="key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(answer)) as http:
        for _ in range(3):
            assert [p async for p in tts.stream(http, settings, "One moment, sir.")] == [("One moment, sir.", b"MP3")]
    assert len(calls) == 1


def test_the_page_is_told_what_alfred_is_doing():
    from brain import doing_line
    assert doing_line(["get_weather"]) == "Checking the weather…"
    assert doing_line(["check_inbox"]) == "Checking inbox…"
    assert doing_line(["add_reminder", "get_tasks"]) == "Saving reminder and checking tasks…"
    assert doing_line(["get_a", "get_b", "get_c"]) == "Checking a and 2 more…"
    assert doing_line(["listen_for_name"]) == "Working on listen for name…"


class ToolThenTextClient:
    """First asks for a tool, then answers."""

    def __init__(self):
        self.calls = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[
                SimpleNamespace(type="tool_use", id="t1", name="get_tasks", input={})])
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="All done, sir.")])


async def test_a_running_tool_shows_on_the_status_line(monkeypatch):
    import tools
    sent = []

    async def page(msg):
        sent.append(msg)

    async def fake_tool(name, args, *rest):
        return "no tasks"

    monkeypatch.setattr(tools, "run_tool", fake_tool)

    async def speak(text, quiet=False, join=False):
        pass

    await Brain(SETTINGS, ToolThenTextClient(), http=None, page=page).handle("Any tasks?", speak)
    assert {"type": "status", "text": "Checking tasks…"} in sent


def test_the_time_and_date_are_answered_on_the_spot():
    import time

    from brain import instant_answer
    now = time.strptime("2026-10-05 21:07", "%Y-%m-%d %H:%M")
    en = Settings(speech_lang="en-GB")
    assert instant_answer("Alfred, what time is it?", en, now) == "It's 9:07 pm."
    assert instant_answer("What's the date?", en, now) == "It's Monday the 5th of October."
    assert instant_answer("what time is it in Narnia", en, now) is None  # Claude handles anything more
    assert instant_answer("what time does the shop close", en, now) is None
    assert instant_answer("what time is it", Settings(speech_lang="af-ZA"), now) is None


async def test_an_instant_answer_skips_claude_but_stays_in_the_conversation():
    class NoCalls:
        beta = SimpleNamespace(messages=SimpleNamespace(create=None, stream=None))

    said = []

    async def speak(text, quiet=False, join=False):
        said.append(text)

    b = Brain(Settings(model="claude-opus-5", tasks_file="", enable_screen=False, speech_lang="en-GB"),
              NoCalls(), http=None)
    await b.handle("What time is it?", speak)
    assert said and said[0].startswith("It's ")
    assert b.messages[-2:] == [{"role": "user", "content": "What time is it?"},
                               {"role": "assistant", "content": said[0]}]


async def test_plain_timers_are_set_checked_and_cancelled_on_the_spot():
    import timers
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    timers.timers.clear()
    try:
        assert instant_answer("Alfred, set a timer for ten minutes please", en) == "Timer set for 10 minutes."
        assert instant_answer("a five minute timer", en) == "Timer set for 5 minutes."  # replaces the first
        assert instant_answer("How long left on my timer?", en).endswith("left on the timer.")
        assert instant_answer("set a timer for half an hour", en) == "Timer set for 30 minutes."
        assert instant_answer("set a timer for 48 hours", en) == "Timers can run from 1 second to 24 hours."
        assert instant_answer("set a timer for pasta for 10 minutes", en) is None  # named timers go to Claude
        assert instant_answer("stop the timer and play music", en) is None
        assert instant_answer("cancel the timer", en) == "Cancelled the timer."
        assert not timers.timers
    finally:
        for t in timers.timers.values():
            t.task.cancel()
        timers.timers.clear()


def test_remind_me_in_a_few_minutes_is_set_on_the_spot(tmp_path):
    import reminders
    from brain import instant_answer
    en = Settings(speech_lang="en-GB", memory_dir=str(tmp_path))
    said = instant_answer("Alfred, remind me in 20 minutes to check the oven please", en)
    assert said.startswith("I'll remind you today at ") or said.startswith("I'll remind you tomorrow at ")
    assert said.endswith(": check the oven.")
    assert instant_answer("in 5 minutes remind me to stretch", en).endswith(": stretch.")
    assert sorted(r["text"] for r in reminders.load(en)) == ["check the oven", "stretch"]
    assert instant_answer("remind me tomorrow at 9 to call the bank", en) is None  # Claude works out the time
    assert instant_answer("remind me in 20 minutes", en) is None  # no "what": Claude asks


def test_clock_reminders_and_listing_and_cancelling_are_instant(tmp_path):
    import datetime as dt
    import reminders
    from brain import instant_answer
    en = Settings(speech_lang="en-GB", memory_dir=str(tmp_path))
    said = instant_answer("Alfred, remind me at 7 p.m. to call Mum", en)
    assert said.startswith("I'll remind you ") and said.endswith(" at 19:00: call Mum.")
    said = instant_answer("remind me tomorrow at 8:30am about the bins", en)
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    assert said == "I'll remind you tomorrow at 08:30: the bins."
    assert instant_answer("remind me at 21:15 tomorrow to take my tablets", en).endswith("tomorrow at 21:15: take my tablets.")
    assert {r["at"] for r in reminders.load(en) if r["text"] != "call Mum"} == {f"{tomorrow} 08:30", f"{tomorrow} 21:15"}
    assert instant_answer("remind me at 13 pm to eat", en) == "That isn't a time I recognise."
    assert instant_answer("remind me at 9 to call the bank", en) is None  # am or pm? Claude asks
    listed = instant_answer("What reminders do I have, Alfred?", en)
    assert listed.startswith("Reminders: ") and "call Mum" in listed and "the bins" in listed
    assert instant_answer("cancel the reminder about the bins", en) == "Cancelled: the bins."
    assert "the bins" not in instant_answer("any reminders?", en)
    assert instant_answer("cancel the reminder about the dentist", en).startswith("No reminder matches that.")


def test_the_shopping_list_is_handled_instantly(tmp_path):
    import shopping
    from brain import instant_answer
    en = Settings(speech_lang="en-GB", memory_dir=str(tmp_path))
    assert instant_answer("what's on the shopping list?", en) == "The shopping list is empty."
    assert instant_answer("Alfred, add milk, eggs and some bread to the shopping list please", en) == \
        "Added milk, eggs, some bread. 3 items on the list."
    assert instant_answer("put milk on my shopping list", en) == "Those are already on the list. 3 items on the list."
    assert instant_answer("take eggs off the shopping list", en) == "Ticked off eggs. 2 left."
    assert instant_answer("remove the cheese from my shopping list", en) == "None of those were on the list. 2 left."
    assert instant_answer("What's on my shopping list, Alfred?", en) == "On the list: milk and some bread."
    assert shopping.items(en) == ["milk", "some bread"]
    assert instant_answer("add a meeting to my calendar", en) is None
    assert instant_answer("clear the shopping list", en) is None  # emptying it stays with Claude


def test_simple_sums_are_worked_out_instantly():
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    assert instant_answer("Alfred, what's 12 times 7?", en) == "That's 84."
    assert instant_answer("what is 15% of 80", en) == "That's 12."
    assert instant_answer("work out 100 divided by 3", en) == "That's 33.3333."
    assert instant_answer("what is the square root of 144", en) == "That's 12."
    assert instant_answer("how much is 1,200 plus 350 please", en) == "That's 1,550."
    assert instant_answer("what's 7 squared", en) == "That's 49."
    assert instant_answer("what's 5 divided by 0", en) == "You can't divide by zero."
    assert instant_answer("what is 5", en) is None
    assert instant_answer("what's 2 plus the weather", en) is None
    assert instant_answer("what is 2 plus 2 in French", en) is None


def test_sums_said_in_words_are_worked_out_instantly():
    from brain import instant_answer, spoken_numbers
    en = Settings(speech_lang="en-GB")
    assert spoken_numbers("two hundred and fifty") == "250"
    assert spoken_numbers("a thousand and one nights") == "1001 nights"
    assert instant_answer("what is twenty five times four", en) == "That's 100."
    assert instant_answer("what's two hundred and fifty divided by ten", en) == "That's 25."
    assert instant_answer("work out three point five plus one point two five", en) == "That's 4.75."
    assert instant_answer("what is twelve thousand three hundred and forty five plus five", en) == "That's 12,350."
    assert instant_answer("what's a hundred plus 7", en) == "That's 107."
    assert instant_answer("how many grams in three ounces", en) == "3 oz is 85.0486 g."
    assert instant_answer("what's seven and five", en) is None  # "and" only joins after hundred/thousand
    assert instant_answer("what is one", en) is None


def test_time_until_and_time_in_are_worked_out_instantly():
    import time
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    now = time.strptime("2026-10-06 14:45", "%Y-%m-%d %H:%M")
    assert instant_answer("how long until 5 pm", en, now) == "2 hours and 15 minutes until 5 pm."
    assert instant_answer("Alfred, how many minutes until 3pm?", en, now) == "15 minutes until 3 pm."
    assert instant_answer("how long till 17:30", en, now) == "2 hours and 45 minutes until 5:30 pm."
    assert instant_answer("how long until 2:30 pm", en, now) == "23 hours and 45 minutes until 2:30 pm."
    assert instant_answer("what time will it be in 3 hours", en, now) == "It'll be 5:45 pm."
    assert instant_answer("what time will it be in an hour and a half", en, now) == "It'll be 4:15 pm."
    assert instant_answer("what's the time in 10 hours", en, now) == "It'll be 12:45 am tomorrow."
    assert instant_answer("how long until 13 pm", en, now) is None


def test_unit_conversions_are_instant():
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    assert instant_answer("What's 10 miles in km?", en) == "10 miles is 16.0934 km."
    assert instant_answer("how many grams in 3 ounces", en) == "3 oz is 85.0486 g."
    assert instant_answer("Alfred, what is 20 degrees in Fahrenheit", en) == "20 degrees Celsius is 68 degrees Fahrenheit."
    assert instant_answer("how many feet in a mile", en) == "1 mile is 5,280 feet."
    assert instant_answer("what is 75 kilos in stone", en) == "75 kg is 11.8105 stone."
    assert instant_answer("what is 3 cups in grams", en) is None  # needs the ingredient: Claude asks
    assert instant_answer("what is 10 pounds in euros", en) is None  # money goes to Claude
    assert instant_answer("how many people in London", en) is None


def test_world_times_days_until_and_tomorrow_are_instant():
    import re
    import time
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    now = time.strptime("2026-10-06 21:07", "%Y-%m-%d %H:%M")
    assert re.fullmatch(r"It's \d{1,2}:\d\d [ap]m(?: tomorrow| yesterday)? in Tokyo\.",
                        instant_answer("What's the time in Tokyo?", en, now))
    assert instant_answer("what time is it in Narnia", en, now) is None  # Claude looks it up
    assert instant_answer("how many days until Christmas?", en, now) == \
        "80 days until Christmas, on Friday the 25th of December."
    assert instant_answer("how long till new year's eve", en, now) == \
        "86 days until New Year's Eve, on Thursday the 31st of December."
    assert instant_answer("how many days until Valentine's Day", en, now).startswith("131 days until Valentine's Day, on Sunday")
    assert instant_answer("how many days until my birthday", en, now) is None
    assert instant_answer("what's the date tomorrow", en, now) == "Tomorrow is Wednesday the 7th of October."
    christmas = time.strptime("2026-12-25 09:00", "%Y-%m-%d %H:%M")
    assert instant_answer("how many days until Christmas", en, christmas) == "Christmas is today!"


def test_coins_dice_numbers_and_jokes_are_instant():
    import re
    import fun
    from brain import instant_answer
    en = Settings(speech_lang="en-GB")
    assert instant_answer("Alfred, flip a coin", en) in ("Heads.", "Tails.")
    assert re.fullmatch(r"You rolled a [1-6]\.", instant_answer("roll a dice", en))
    two = instant_answer("roll two dice please", en)
    a, b, total = map(int, re.fullmatch(r"You rolled ([1-6]) and ([1-6]), (\d+) in total\.", two).groups())
    assert a + b == total
    for _ in range(20):
        assert 1 <= int(re.fullmatch(r"I pick (\d+)\.", instant_answer("pick a number between 10 and 1", en))[1]) <= 10
    assert instant_answer("tell me a joke", en) in fun.JOKES
    assert instant_answer("tell me a joke about cats", en) is None  # Claude writes a cat joke
    assert instant_answer("another one", en) is None  # could mean anything: Claude decides


def test_fillers_and_polite_wording_still_get_instant_answers():
    import time
    from brain import instant_answer, tidy_request
    en = Settings(speech_lang="en-GB")
    now = time.strptime("2026-10-07 04:19", "%Y-%m-%d %H:%M")
    assert tidy_request("Um, Alfred, could you please tell me what time it is, mate?") == "what time is it?"
    assert instant_answer("um what time is it", en, now) == "It's 4:19 am."
    assert instant_answer("Alfred, can you tell me what time it is", en, now) == "It's 4:19 am."
    assert instant_answer("do you know what the date is", en, now) == "It's Wednesday the 7th of October."
    assert instant_answer("tell me the date please", en, now) == "It's Wednesday the 7th of October."
    assert instant_answer("could you tell me the date", en, now) == "It's Wednesday the 7th of October."
    assert instant_answer("okay so what's 12 times 7, thanks", en, now) == "That's 84."
    assert instant_answer("so how many days until Christmas", en, now).startswith("79 days until Christmas")
    assert instant_answer("uh, flip a coin", en, now) in ("Heads.", "Tails.")
    assert instant_answer("can you tell me a joke", en, now)
    assert instant_answer("well I want to know about the weather", en, now) is None


def test_spoken_durations_become_plain_numbers():
    from brain import spoken_durations, tidy_request
    assert spoken_durations("set a timer for twenty five minutes") == "set a timer for 25 minutes"
    assert spoken_durations("set a timer for an hour and a half") == "set a timer for 90 minutes"
    assert spoken_durations("set a timer for two and a half hours") == "set a timer for 2.5 hours"
    assert spoken_durations("set a timer for 1 hour 30 minutes") == "set a timer for 90 minutes"
    assert spoken_durations("2 hours and 15 minutes") == "135 minutes"
    assert spoken_durations("a quarter of an hour") == "15 minutes"
    assert tidy_request("Alfred, remind me in half an hour to stretch") == "remind me in 30 minutes to stretch"


async def test_natural_durations_set_timers_and_reminders(tmp_path):
    import timers
    import reminders
    from brain import instant_answer
    en = Settings(speech_lang="en-GB", memory_dir=str(tmp_path))
    try:
        assert instant_answer("set a timer for twenty five minutes", en) == "Timer set for 25 minutes."
        assert instant_answer("set a timer for an hour and a half", en).startswith("Timer set for 1 hour")
        assert instant_answer("remind me in forty five minutes to check the oven", en).endswith(": check the oven.")
        assert [r["text"] for r in reminders.load(en)] == ["check the oven"]
    finally:
        for t in list(timers.timers.values()):
            t.task.cancel()
        timers.timers.clear()
