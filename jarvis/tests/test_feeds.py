import asyncio
from datetime import date

import httpx
import pytest

import feeds
import feeds_outdoors
import tools
from config import Settings

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>BBC News</title>
<item><title>Storm hits coast</title><description>Strong winds &amp; rain across the south.</description></item>
<item><title>Markets rally</title><description><![CDATA[Shares <b>rise</b> again.]]></description></item>
<item><title>Third story</title></item>
</channel></rss>"""

LEEDS = {"results": [{"name": "Leeds", "country": "United Kingdom", "latitude": 53.8, "longitude": -1.55}]}


def call(name, args, routes, settings=None, seen=None):
    """Run a tool against fake feeds: routes maps a URL fragment to a Response or JSON body."""
    def handler(request):
        url = str(request.url)
        if seen is not None:
            seen.append(request)
        for fragment, answer in routes.items():
            if fragment in url:
                return answer if isinstance(answer, httpx.Response) else httpx.Response(200, json=answer)
        return httpx.Response(404)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await tools.run_tool(name, args, settings or Settings(city="Leeds"), http)

    return asyncio.run(go())


def test_registered():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"news_headlines", "world_info", "outdoors"} <= names
    for t in feeds.tool_definitions() + feeds_outdoors.tool_definitions():
        assert t["input_schema"]["additionalProperties"] is False


def test_bbc_headlines_by_section():
    seen = []
    out = call("news_headlines", {"kind": "bbc", "section": "technology", "count": 2},
               {"/news/technology/rss.xml": httpx.Response(200, text=RSS)}, seen=seen)
    assert out.startswith("BBC technology headlines:")
    assert "- Storm hits coast: Strong winds & rain across the south." in out
    assert "Shares rise again." in out and "Third story" not in out
    assert seen[0].headers["user-agent"] == "Alfred-assistant/1.0"


def test_rss_rejects_entities():
    evil = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
    with pytest.raises(ValueError, match="unsafe"):
        feeds.parse_rss(evil)
    with pytest.raises(ValueError, match="garbled"):
        feeds.parse_rss("<rss><channel>")


def test_http_errors_are_friendly():
    with pytest.raises(ValueError, match="BBC News service isn't answering"):
        call("news_headlines", {"kind": "bbc"}, {"feeds.bbci": httpx.Response(503)})


def test_hacker_news():
    routes = {
        "topstories.json": [11, 12, 13],
        "item/11.json": {"title": "Show HN: A thing", "url": "https://www.example.com/x", "score": 120, "descendants": 40},
        "item/12.json": {"title": "Ask HN: Why?", "score": 50, "descendants": 9},
    }
    out = call("news_headlines", {"kind": "hacker_news", "count": 2}, routes)
    assert out == ("Top Hacker News stories:\n- Show HN: A thing (example.com), 120 points, 40 comments\n"
                   "- Ask HN: Why?, 50 points, 9 comments")


def test_air_quality():
    routes = {"geocoding": LEEDS, "air-quality": {"current": {"european_aqi": 45, "pm2_5": 8.1, "pm10": 14.0}}}
    out = call("outdoors", {"kind": "air_quality"}, routes)
    assert out.startswith("Air quality in Leeds is moderate (European index 45).")


def test_pollen_and_missing_region():
    routes = {"geocoding": LEEDS, "air-quality": {"current": {"grass_pollen": 60, "birch_pollen": 3, "alder_pollen": None}}}
    out = call("outdoors", {"kind": "pollen"}, routes)
    assert "grass high (60 grains" in out and "birch low" in out and "alder" not in out
    routes["air-quality"] = {"current": {"grass_pollen": None}}
    assert "only available in Europe" in call("outdoors", {"kind": "pollen", "city": "Leeds"}, routes)


def test_uv():
    out = call("outdoors", {"kind": "uv"}, {"geocoding": LEEDS, "api.open-meteo.com/v1/forecast": {"daily": {"uv_index_max": [6.4]}}})
    assert out.startswith("Today's highest UV index in Leeds is 6.4, which is high")


def test_rain():
    hourly = {"time": ["2026-09-28T10:00", "2026-09-28T11:00", "2026-09-28T12:00"],
              "precipitation_probability": [10, 70, 40], "precipitation": [0, 1.2, 0.3]}
    seen = []
    out = call("outdoors", {"kind": "rain", "hours": 3}, {"geocoding": LEEDS, "v1/forecast": {"hourly": hourly}}, seen=seen)
    assert out.startswith("Yes, take an umbrella.") and "70% around 11:00" in out and "1.5 mm" in out
    assert seen[-1].url.params["forecast_hours"] == "3"


def test_drying():
    hourly = {"relative_humidity_2m": [60, 62], "wind_speed_10m": [15, 18],
              "precipitation_probability": [5, 10], "temperature_2m": [17, 19]}
    out = call("outdoors", {"kind": "drying"}, {"geocoding": LEEDS, "v1/forecast": {"hourly": hourly}})
    assert out.startswith("Good drying weather") and "wind about 16 km/h (up to 18)" in out
    hourly["precipitation_probability"] = [50, 80]
    assert call("outdoors", {"kind": "drying"}, {"geocoding": LEEDS, "v1/forecast": {"hourly": hourly}}).startswith("Not a good day")


def test_no_city():
    with pytest.raises(ValueError, match="no home city"):
        call("outdoors", {"kind": "uv"}, {}, settings=Settings(city=""))
    with pytest.raises(ValueError, match="Could not find"):
        call("outdoors", {"kind": "uv", "city": "Nowhere"}, {"geocoding": {"results": []}})


def test_aurora_both_formats():
    rows = [{"time_tag": "2026-09-28T09:00:00", "Kp": 5.33}]
    out = call("outdoors", {"kind": "aurora"}, {"noaa-planetary-k-index": rows})
    assert out.startswith("The planetary K-index is 5.33 (reading from 2026-09-28 09:00 UTC).")
    assert "Scotland" in out
    old = [["time_tag", "Kp", "a_running", "station_count"], ["2026-09-28 06:00:00.000", "2.00", "7", "8"]]
    assert "unlikely" in call("outdoors", {"kind": "aurora"}, {"noaa-planetary-k-index": old})


def test_carbon():
    body = {"data": [{"from": "x", "to": "y", "intensity": {"forecast": 90, "actual": 85, "index": "low"}}]}
    out = call("outdoors", {"kind": "carbon"}, {"carbonintensity": body})
    assert out == ("UK grid carbon intensity is low right now (85 grams of CO2 per kWh). "
                   "Yes, it's a good time to run the washing machine.")


def test_crypto():
    body = {"bitcoin": {"gbp": 48123.5, "gbp_24h_change": -2.345}, "ethereum": {"gbp": 1900, "gbp_24h_change": 1.2}}
    seen = []
    out = call("world_info", {"kind": "crypto"}, {"coingecko": body}, seen=seen)
    assert "- Bitcoin: 48,123.50 GBP, down 2.3% in 24 hours" in out and "Ethereum: 1,900.00 GBP, up 1.2%" in out
    assert seen[0].url.params["ids"] == "bitcoin,ethereum"
    assert "doesn't know" in call("world_info", {"kind": "crypto", "coins": ["notacoin"]}, {"coingecko": {}})


def quake(mag, place, tsunami=0):
    return {"properties": {"mag": mag, "place": place, "time": 1790000000000, "tsunami": tsunami}}


def test_earthquakes():
    out = call("world_info", {"kind": "earthquakes", "period": "week"},
               {"significant_week": {"features": [quake(6.1, "Chile"), quake(7.2, "Japan", 1)]}})
    assert out.splitlines()[0] == "Significant earthquakes in the past week:"
    assert out.splitlines()[1].startswith("- Magnitude 7.2, Japan") and "tsunami" in out
    out = call("world_info", {"kind": "earthquakes"},
               {"significant_day": {"features": []}, "4.5_day": {"features": [quake(4.8, "Fiji")]}})
    assert out.startswith("No significant earthquakes in the past day. The strongest") and "Fiji" in out


def test_iss_and_astronauts():
    out = call("world_info", {"kind": "iss"}, {"iss-now": {"iss_position": {"latitude": "-20.5", "longitude": "-30.0"}}})
    assert out == "The International Space Station is roughly over the Atlantic Ocean, at 20.5 degrees south, 30.0 degrees west."
    assert feeds.region(51.5, 0) == "Europe" and feeds.region(0, -150) == "the Pacific Ocean"
    assert feeds.region(-10, 80) == "the Indian Ocean" and feeds.region(-25, 135) == "Australia and New Zealand"
    people = {"number": 3, "people": [{"name": "A", "craft": "ISS"}, {"name": "B", "craft": "ISS"}, {"name": "C", "craft": "Tiangong"}]}
    assert call("world_info", {"kind": "astronauts"}, {"astros": people}) == \
        "3 people are in space right now. On the ISS: A, B. On the Tiangong: C."


def test_wikipedia_summary():
    seen = []
    body = {"title": "Isaac Newton", "type": "standard", "extract": "English polymath."}
    assert call("world_info", {"kind": "wikipedia", "topic": "Isaac Newton"}, {"summary/Isaac_Newton": body},
                seen=seen) == "Isaac Newton: English polymath."
    assert seen[0].headers["user-agent"] == "Alfred-assistant/1.0"
    with pytest.raises(ValueError, match="no page called Zzzq"):
        call("world_info", {"kind": "wikipedia", "topic": "Zzzq"}, {})
    amb = {"title": "Mercury", "type": "disambiguation", "extract": "Mercury may refer to"}
    assert "more specific" in call("world_info", {"kind": "wikipedia", "topic": "Mercury"}, {"summary/Mercury": amb})


def test_random_article():
    body = {"title": "Lake Bled", "type": "standard", "extract": "A lake in Slovenia."}
    out = call("world_info", {"kind": "random_article"}, {"page/random/summary": body})
    assert out == "A random Wikipedia article. Lake Bled: A lake in Slovenia."


def test_on_this_day():
    events = [{"year": y, "text": f"Event {y}"} for y in (2001, 1066, 1800, 1969, 1900, 1500, 1945)]

    def go():
        def handler(request):
            assert request.url.path.endswith("/events/09/28")
            return httpx.Response(200, json={"events": events})

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
                return await feeds.on_this_day(http, 4, date(2026, 9, 28))
        return asyncio.run(run())

    out = go()
    lines = out.splitlines()
    assert lines[0] == "On this day, 28 September:" and len(lines) == 5
    assert lines[1] == "- 1066: Event 1066" and lines[-1] == "- 2001: Event 2001"
    assert call("world_info", {"kind": "on_this_day", "count": 9}, {"onthisday": {"events": events}}).count("\n- ") == 5
