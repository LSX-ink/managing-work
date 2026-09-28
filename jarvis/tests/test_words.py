import asyncio
from datetime import date

import httpx
import pytest

import tools
import words
from config import Settings


def call(args, handler=None):
    def refuse(request):
        raise AssertionError(f"Unexpected request to {request.url}")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or refuse)) as http:
            return await tools.run_tool("word_lookup", args, Settings(), http)

    return asyncio.run(go())


def test_define():
    def handler(request):
        assert str(request.url) == "https://api.dictionaryapi.dev/api/v2/entries/en/serendipity"
        return httpx.Response(200, json=[{"word": "serendipity", "phonetic": "/ˌsɛɹ.ənˈdɪp.ɪ.ti/", "meanings": [
            {"partOfSpeech": "noun", "definitions": [
                {"definition": "A combination of events which have come together by chance to make a surprisingly "
                               "good or wonderful outcome.", "example": "Pure serendipity."}]}]}])

    out = call({"action": "define", "word": "Serendipity"}, handler)
    assert out.startswith("serendipity /ˌsɛɹ.ənˈdɪp.ɪ.ti/:\n- (noun) A combination of events")
    assert out.endswith('Example: "Pure serendipity."')


def test_define_unknown_word():
    out = call({"action": "define", "word": "blorptastic"}, lambda r: httpx.Response(404, json={"title": "No Definitions Found"}))
    assert out == "I couldn't find blorptastic in the dictionary."
    with pytest.raises(ValueError):
        call({"action": "define", "word": "https://evil.example/x"})


@pytest.mark.parametrize("action,param,expected", [
    ("synonyms", "rel_syn", "Synonyms for happy: glad, cheerful."),
    ("antonyms", "rel_ant", "Opposites of happy: glad, cheerful."),
    ("rhymes", "rel_rhy", "Words that rhyme with happy: glad, cheerful."),
    ("sounds_like", "sl", "Words that sound like happy: glad, cheerful."),
])
def test_datamuse(action, param, expected):
    def handler(request):
        assert request.url.host == "api.datamuse.com" and request.url.params[param] == "happy"
        return httpx.Response(200, json=[{"word": "glad", "score": 9}, {"word": "happy"}, {"word": "cheerful"}])

    assert call({"action": action, "word": "happy"}, handler) == expected


def test_datamuse_nothing_found():
    assert call({"action": "antonyms", "word": "the"}, lambda r: httpx.Response(200, json=[])) == \
        "I couldn't find any antonyms for the."


def test_spell_and_count():
    assert call({"action": "spell", "word": "Cat"}) == "Cat is spelled C, A, T."
    assert call({"action": "spell", "word": "ice cream"}) == "ice cream is spelled I, C, E, space, C, R, E, A, M."
    assert call({"action": "count", "text": "Hello there,  General Kenobi"}) == \
        "4 words, 28 characters including spaces, 24 without."
    assert words.count("one") == "1 word, 3 characters including spaces, 3 without."


def test_word_of_the_day_is_stable_for_a_day():
    day = date(2026, 9, 28)
    assert words.word_of_the_day(day) == words.word_of_the_day(day)
    assert words.word_of_the_day(day) != words.word_of_the_day(date(2026, 9, 29))
    assert call({"action": "word_of_the_day"}).startswith("Today's word is ")
    assert len(words.WORDS_OF_THE_DAY) >= 60


def test_tool_registered():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert "word_lookup" in names
