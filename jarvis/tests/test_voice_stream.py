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
