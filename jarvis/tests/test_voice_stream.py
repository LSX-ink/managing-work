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
    assert instant_answer("what time is it in Tokyo", en, now) is None  # Claude handles anything more
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
