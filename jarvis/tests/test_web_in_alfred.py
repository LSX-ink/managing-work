import asyncio

import httpx
import pytest

import homekitchen
import memory
import screen
import shopping
import tools
import webview_common as web
import webview_food
import webview_listen
import webview_look
import webview_places
from config import Settings

RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<title>Test Cast</title><itunes:image href="https://img.test/cast.jpg"/>
<item><title>Big story</title><link>https://www.bbc.co.uk/news/1</link><description>First</description>
<pubDate>Mon, 28 Sep 2026 07:00:00 GMT</pubDate><enclosure url="https://audio.test/ep1.mp3" type="audio/mpeg"/></item>
<item><title>Old http one</title><link>http://www.bbc.co.uk/news/2</link>
<enclosure url="http://audio.test/ep0.mp3" type="audio/mpeg"/></item>
</channel></rss>"""

RECIPE_PAGE = """<html><head><title>Pancakes</title><script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [{"@type": "WebPage"}, {"@type": ["Recipe"], "name": "Easy pancakes",
 "image": [{"url": "https://img.test/p.jpg"}], "recipeYield": ["4"], "totalTime": "PT1H20M",
 "recipeIngredient": ["100g plain flour", "2 eggs", "300ml milk"],
 "recipeInstructions": [{"@type": "HowToSection", "itemListElement": [{"@type": "HowToStep", "text": "Whisk it all."},
   {"@type": "HowToStep", "text": "Fry in a hot pan."}]}]}]}
</script></head><body>hi</body></html>"""

MEAL = {"idMeal": "52772", "strMeal": "Teriyaki Chicken", "strMealThumb": "https://img.test/t.jpg",
        "strCategory": "Chicken", "strArea": "Japanese", "strInstructions": "STEP 1\r\nMix the sauce.\r\nSTEP 2\r\nCook it.",
        "strIngredient1": "soy sauce", "strMeasure1": "3/4 cup", "strIngredient2": "chicken", "strMeasure2": "2 lbs",
        "strIngredient3": "", "strMeasure3": " "}
DRINKS = [{"idDrink": "1", "strDrink": "Mojito", "strDrinkThumb": "https://img.test/m.jpg", "strAlcoholic": "Alcoholic",
           "strInstructions": "Muddle mint. Add rum and soda.", "strIngredient1": "Mint"},
          {"idDrink": "2", "strDrink": "Virgin Mojito", "strDrinkThumb": "https://img.test/v.jpg",
           "strAlcoholic": "Non alcoholic", "strInstructions": "Muddle mint.", "strIngredient1": "Mint"}]


def handler(request: httpx.Request) -> httpx.Response:
    host, path, q = request.url.host, request.url.path, request.url.params
    if host == "feeds.bbci.co.uk" or host == "feeds.test":
        return httpx.Response(200, text=RSS)
    if host == "en.wikipedia.org":
        return httpx.Response(200, json={"title": "Ada Lovelace", "extract": "Ada was a mathematician.",
                                         "originalimage": {"source": "https://upload.test/ada.jpg"},
                                         "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}}})
    if host == "openlibrary.org":
        assert q["q"] == "dune"
        return httpx.Response(200, json={"docs": [{"title": "Dune", "author_name": ["Frank Herbert"],
                                                   "first_publish_year": 1965, "cover_i": 123}, {"title": "Dune Messiah"}]})
    if host == "news.test":
        return httpx.Response(200, text='<html><head><title>Plain</title><meta property="og:title" content="Rich &amp; Big">'
                                        '<meta content="What it is about." name="description">'
                                        '<meta property="og:image" content="/pic.jpg"><meta property="og:site_name" '
                                        'content="News Site"></head><body><article><p>' + "Words of the story. " * 5
                                        + "</p></article></body></html>", headers={"content-type": "text/html"})
    if host == "redirect.test":
        return httpx.Response(302, headers={"location": "https://news.test/story"})
    if host == "dog.ceo":
        assert path in ("/api/breeds/image/random", "/api/breed/spaniel/cocker/images/random")
        return httpx.Response(200, json={"message": "https://images.dog.ceo/a.jpg", "status": "success"})
    if host == "api.thecatapi.com":
        return httpx.Response(200, json=[{"url": "https://cdn2.thecatapi.com/c.jpg"}])
    if host == "geocoding-api.open-meteo.com":
        places = {"London": (51.5085, -0.1257, "PPLC", "England"), "Paris": (48.8534, 2.3488, "PPLC", "Île-de-France")}
        if q["name"] not in places:
            return httpx.Response(200, json={})
        lat, lon, code, admin = places[q["name"]]
        return httpx.Response(200, json={"results": [{"name": q["name"], "latitude": lat, "longitude": lon,
                                                      "feature_code": code, "admin1": admin, "country": "X"}]})
    if host == "restcountries.com":
        assert q["fields"].count(",") == 9
        return httpx.Response(200, json=[
            {"name": {"common": "Guinea-Bissau", "official": "Republic of Guinea-Bissau"}, "population": 1},
            {"name": {"common": "Japan", "official": "Japan"}, "capital": ["Tokyo"], "population": 125836021,
             "area": 377930, "region": "Asia", "subregion": "Eastern Asia", "languages": {"jpn": "Japanese"},
             "currencies": {"JPY": {"name": "Japanese yen", "symbol": "¥"}},
             "flags": {"png": "https://flagcdn.com/w320/jp.png", "alt": "A red circle on white."}}])
    if host == "api.rainviewer.com":
        return httpx.Response(200, json={"host": "https://tilecache.rainviewer.com",
                                         "radar": {"past": [{"time": 1790000000, "path": "/v2/radar/abc"}]}})
    if host == "de1.api.radio-browser.info":
        assert request.headers["user-agent"] == "Alfred-assistant/1.0" and q["name"] == "jazz"
        return httpx.Response(200, json=[
            {"name": "Jazz FM", "url_resolved": "https://stream.test/jazz", "country": "UK", "tags": "jazz,smooth",
             "bitrate": 128, "favicon": "https://img.test/j.png"},
            {"name": "Plain Jazz", "url_resolved": "http://stream.test/plain"}])
    if host == "itunes.apple.com":
        assert q["media"] == "podcast"
        return httpx.Response(200, json={"results": [
            {"collectionName": "Test Cast", "artistName": "Me", "feedUrl": "https://feeds.test/cast.xml",
             "artworkUrl600": "https://img.test/cast.jpg"}, {"collectionName": "No feed"}]})
    if host == "www.themealdb.com":
        if path.endswith("search.php"):
            return httpx.Response(200, json={"meals": [MEAL] if q["s"] == "teriyaki" else None})
        assert q["i"] == "52772"
        return httpx.Response(200, json={"meals": [MEAL]})
    if host == "www.thecocktaildb.com":
        if path.endswith("filter.php"):
            return httpx.Response(200, json={"drinks": [{"idDrink": "2", "strDrink": "Virgin Mojito",
                                                         "strDrinkThumb": "https://img.test/v.jpg"}]})
        if path.endswith("lookup.php"):
            return httpx.Response(200, json={"drinks": [d for d in DRINKS if d["idDrink"] == q["i"]]})
        return httpx.Response(200, json={"drinks": DRINKS})
    if host == "recipes.test":
        return httpx.Response(200, text=RECIPE_PAGE, headers={"content-type": "text/html"})
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def public_links(monkeypatch):
    async def ok(url):
        if "192.168." in url:
            raise ValueError("home network")
    monkeypatch.setattr(memory, "check_public", ok)


def call(name, args, settings=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await tools._run_tool(name, args, settings or Settings(), http)
    return asyncio.run(go())


def test_registered_with_few_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"web_on_screen", "maps_and_places", "radio_and_podcasts", "recipes_and_cocktails"} <= names
    for module in (webview_look, webview_places, webview_listen, webview_food):
        assert module in tools.ABILITIES and module not in tools.ALWAYS_LOADED
        for t in module.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
    assert {"webcard", "gallery", "map", "radio", "recipe"} <= screen.EXTRA_KINDS


def test_news_list_reads_pages_on_screen():
    out = call("web_on_screen", {"action": "news", "section": "technology"})
    assert out.card["kind"] == "list" and out.card["title"] == "BBC technology headlines"
    assert out.card["items"] == [{"label": "Big story", "done": False,
                                  "say": "Read me the page https://www.bbc.co.uk/news/1 on screen."}]
    assert "Big story" in out


def test_feed_parser_refuses_entities():
    with pytest.raises(ValueError):
        web.parse_feed('<!DOCTYPE x [<!ENTITY a "b">]><rss><channel><item><title>&a;</title></item></channel></rss>')


def test_wikipedia_article_with_button():
    out = call("web_on_screen", {"action": "wikipedia", "query": "Ada Lovelace"})
    c = out.card
    assert c["kind"] == "reader" and c["image"] == "https://upload.test/ada.jpg" and c["site"] == "Wikipedia"
    assert c["buttons"] == [{"label": "Read full article",
                             "say": "Read me the page https://en.wikipedia.org/wiki/Ada_Lovelace on screen."}]


def test_books_gallery_adds_to_reading_list():
    out = call("web_on_screen", {"action": "books", "query": "dune"})
    tiles = out.card["data"]["tiles"]
    assert out.card["kind"] == "gallery"
    assert tiles[0] == {"title": "Dune", "subtitle": "Frank Herbert · 1965",
                        "image": "https://covers.openlibrary.org/b/id/123-M.jpg",
                        "say": "Add the book Dune by Frank Herbert to my reading list."}
    assert tiles[1]["image"] == "" and tiles[1]["say"] == "Add the book Dune Messiah to my reading list."


def test_link_preview_follows_redirects_and_reads_og_tags():
    out = call("web_on_screen", {"action": "link_preview", "url": "redirect.test/x"})
    d = out.card["data"]
    assert out.card["kind"] == "webcard"
    assert d == {"heading": "Rich & Big", "site": "News Site", "text": "What it is about.",
                 "image": "https://news.test/pic.jpg", "link": "https://news.test/story"}
    with pytest.raises(ValueError):
        call("web_on_screen", {"action": "link_preview", "url": "http://192.168.1.1/"})


def test_web_image_with_save_button(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = call("web_on_screen", {"action": "image", "url": "https://img.test/a.png", "folder": "Personal"}, s)
    assert out.card["kind"] == "image" and out.card["src"] == "https://img.test/a.png"
    assert out.card["buttons"][0]["say"] == "Download https://img.test/a.png into my Personal folder."
    with pytest.raises(ValueError):
        call("web_on_screen", {"action": "image", "url": "http://img.test/a.png"}, s)


def test_page_saved_as_markdown_note(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = call("web_on_screen", {"action": "page_to_note", "url": "https://news.test/story"}, s)
    note = tmp_path / "Ideas" / "Plain.md"
    assert note.read_text(encoding="utf-8").startswith("# Plain\n\nFrom https://news.test/story\n\nWords of the story.")
    assert out.card["kind"] == "file" and out.card["mime"] == "text/markdown"


def test_dog_and_cat_pictures_with_another_one():
    dog = call("web_on_screen", {"action": "dog", "breed": "spaniel cocker"})
    assert dog.card["src"] == "https://images.dog.ceo/a.jpg" and dog.card["id"] == "webview-dog"
    assert dog.card["buttons"] == [{"label": "Another one", "say": "Show me another spaniel cocker dog picture."}]
    cat = call("web_on_screen", {"action": "cat"})
    assert cat.card["kind"] == "image" and cat.card["src"] == "https://cdn2.thecatapi.com/c.jpg"


def test_map_embeds_openstreetmap():
    out = call("maps_and_places", {"action": "map", "place": "London"})
    d = out.card["data"]
    assert out.card["kind"] == "map"
    assert d["embed"].startswith("https://www.openstreetmap.org/export/embed.html?bbox=")
    assert d["embed"].endswith("&marker=51.50850%2C-0.12570")
    assert d["places"] == [{"label": "London, England, X", "lat": 51.5085, "lon": -0.1257}]
    with pytest.raises(ValueError):
        call("maps_and_places", {"action": "map", "place": "Nowhereville"})


def test_distance_as_the_crow_flies():
    out = call("maps_and_places", {"action": "distance", "place": "London", "other_place": "Paris"})
    assert out == "London to Paris is 214 miles (344 km) as the crow flies."
    assert len(out.card["data"]["places"]) == 2 and "B: Paris" in out.card["text"]
    assert round(web.haversine_km({"lat": 0, "lon": 0}, {"lat": 0, "lon": 1})) == 111


def test_country_facts_with_flag():
    out = call("maps_and_places", {"action": "country", "place": "japan"})
    d = out.card["data"]
    assert out.card["kind"] == "webcard" and d["image"] == "https://flagcdn.com/w320/jp.png"
    assert ["Capital", "Tokyo"] in d["facts"] and ["Currency", "Japanese yen (¥)"] in d["facts"]
    assert out.startswith("Japan: capital Tokyo; population 125,836,021")


def test_rain_radar_tiles():
    out = call("maps_and_places", {"action": "radar", "place": "London"})
    d = out.card["data"]
    assert out.card["kind"] == "map" and d["mode"] == "radar" and len(d["tiles"]) == 9
    assert d["tiles"][4] == {"base": "https://tile.openstreetmap.org/6/31/21.png",
                             "overlay": "https://tilecache.rainviewer.com/v2/radar/abc/256/6/31/21/2/1_1.png"}
    assert 0.33 < d["marker"]["x"] < 0.67 and 0.33 < d["marker"]["y"] < 0.67


def test_radio_search_and_play_only_https():
    found = call("radio_and_podcasts", {"action": "radio_search", "query": "jazz"})
    d = found.card["data"]
    assert found.card["kind"] == "radio" and d["autoplay"] == -1 and d["live"] is True
    assert d["tracks"] == [{"title": "Jazz FM", "subtitle": "UK · jazz, smooth · 128 kbps",
                            "src": "https://stream.test/jazz", "image": "https://img.test/j.png"}]
    playing = call("radio_and_podcasts", {"action": "radio_play", "query": "jazz"})
    assert playing == "Playing Jazz FM on the screen." and playing.card["data"]["autoplay"] == 0


def test_podcast_search_and_episodes():
    found = call("radio_and_podcasts", {"action": "podcast_search", "query": "test"})
    assert found.card["kind"] == "gallery" and len(found.card["data"]["tiles"]) == 1
    assert found.card["data"]["tiles"][0]["say"] == "Show the latest episodes of the podcast feed https://feeds.test/cast.xml"
    for args in ({"feed_url": "https://feeds.test/cast.xml"}, {"query": "test"}):
        eps = call("radio_and_podcasts", {"action": "podcast_episodes", **args})
        assert eps.card["kind"] == "radio" and eps.card["title"] == "Test Cast"
        assert eps.card["data"]["tracks"] == [{"title": "Big story", "subtitle": "Mon, 28 Sep 2026",
                                               "src": "https://audio.test/ep1.mp3", "image": "https://img.test/cast.jpg"}]


def test_meal_search_and_full_recipe():
    found = call("recipes_and_cocktails", {"action": "meal_search", "query": "teriyaki"})
    assert found.card["kind"] == "gallery"
    assert found.card["data"]["tiles"][0]["say"] == "Show me the recipe mealdb:52772 on screen."
    with pytest.raises(ValueError):
        call("recipes_and_cocktails", {"action": "meal_search", "query": "nothing"})
    out = call("recipes_and_cocktails", {"action": "recipe_show", "source": "mealdb:52772"})
    d = out.card["data"]
    assert out.card["kind"] == "recipe"
    assert d["ingredients"] == ["3/4 cup soy sauce", "2 lbs chicken"] and d["steps"] == ["Mix the sauce.", "Cook it."]
    assert out.card["buttons"][1]["say"] == "Add the ingredients of the web recipe mealdb:52772 to my shopping list."


def test_cocktails_and_mocktails():
    found = call("recipes_and_cocktails", {"action": "cocktail_search", "query": "mojito"})
    assert [t["title"] for t in found.card["data"]["tiles"]] == ["Mojito", "Virgin Mojito"]
    mock = call("recipes_and_cocktails", {"action": "cocktail_search", "query": "mojito", "alcohol_free": True})
    assert [t["title"] for t in mock.card["data"]["tiles"]] == ["Virgin Mojito"]
    every = call("recipes_and_cocktails", {"action": "cocktail_search", "alcohol_free": True})
    assert every.card["title"] == "Mocktails"
    drink = call("recipes_and_cocktails", {"action": "recipe_show", "source": "cocktaildb:1"})
    assert drink.card["data"]["steps"] == ["Muddle mint.", "Add rum and soda."]


def test_recipe_from_web_page_saved_and_shopped(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = call("recipes_and_cocktails", {"action": "recipe_show", "source": "https://recipes.test/pancakes"}, s)
    d = out.card["data"]
    assert d["title"] == "Easy pancakes" and d["image"] == "https://img.test/p.jpg" and d["about"] == "4 · 1 h 20 min"
    assert d["ingredients"] == ["100g plain flour", "2 eggs", "300ml milk"]
    assert d["steps"] == ["Whisk it all.", "Fry in a hot pan."]
    src = {"source": "https://recipes.test/pancakes"}
    assert call("recipes_and_cocktails", {"action": "recipe_save", **src}, s) == \
        "Saved the Easy pancakes recipe with 3 ingredients."
    assert "1. Whisk it all." in homekitchen.recipe_read(s, "Easy pancakes")
    assert "Ask the user" in call("recipes_and_cocktails", {"action": "recipe_save", **src}, s)
    call("recipes_and_cocktails", {"action": "recipe_to_shopping", **src}, s)
    assert shopping.items(s) == ["100g plain flour", "2 eggs", "300ml milk"]


def test_recipe_page_without_recipe():
    with pytest.raises(ValueError):
        webview_food.parse_recipe_page('<script type="application/ld+json">{"@type": "Article"}</script>'
                                       '<script type="application/ld+json">{bad json</script>', "https://x.test/a")
