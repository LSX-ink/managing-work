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
