from datetime import datetime

import pytest

import cooking
import cooking_guide as guide
import cooking_leftovers as leftovers
import cooking_store as cs
import homekitchen
import homestore
import screen
import tools
from config import Settings

CLOCK = {"now": datetime(2026, 9, 28, 17, 0)}  # a Monday


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 28, 17, 0)
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    settings = Settings(memory_dir=str(tmp_path))
    homekitchen.recipe_save(settings, "Chilli", ["500g beef mince", "1 onion, chopped", "400 ml passata",
                                                 "1 tin kidney beans", "Salt and pepper"],
                            ["Fry the onion for 5 minutes.", "Add the mince and brown it.",
                             "Add passata and beans, simmer 30-40 minutes."], False)
    homekitchen.recipe_save(settings, "Pancakes", ["100g plain flour", "2 eggs", "300 ml milk", "½ tsp salt"],
                            ["Whisk everything.", "Rest 10 minutes.", "Fry thin pancakes."], False)
    return settings


def recipes(s, **args):
    return cooking.run_tool("cooking_recipes", args, s)


def ask(s, **args):
    return guide.run_tool("cooking_guide", args, s)


def left(s, **args):
    return leftovers.run_tool("cooking_leftovers", args, s)


def test_registered_and_kinds():
    for module in (cooking, guide, leftovers):
        assert module in tools.ABILITIES and module not in tools.ALWAYS_LOADED
    assert {"cooking-steps", "cooking-timers", "cooking-batch"} <= screen.EXTRA_KINDS
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"cooking_recipes", "cooking_timers", "cooking_guide", "cooking_leftovers"} <= names


def test_quantities():
    assert cs.parse("1 1/2 cups milk") == (1.5, None, "cup", "milk")
    assert cs.parse("½ tsp salt")[0] == 0.5
    assert cs.parse("1½ tbsp oil")[0] == 1.5
    assert cs.parse("2-3 cloves garlic")[:2] == (2, 3)
    assert cs.parse("Salt and pepper") is None
    assert cs.scale_line("200g plain flour", 1.5) == "300 g plain flour"
    assert cs.scale_line("1.5 kg beef", 0.5) == "750 g beef"
    assert cs.scale_line("800 g potatoes", 2) == "1.6 kg potatoes"
    assert cs.scale_line("1 cup milk", 2) == "2 cups milk"
    assert cs.scale_line("2-3 cloves garlic", 1.5) == "3–4½ cloves garlic"
    assert cs.scale_line("3 eggs", 0.5) == "1½ eggs"
    assert cs.minutes("simmer 30-40 minutes") == 30 and cs.minutes("roast 1.5 hours") == 90
    assert cs.have("2 large onions, chopped", ["onion"]) and not cs.have("3 eggs", ["milk"])


def test_cook_mode(s):
    out = recipes(s, action="cook_mode", name="chilli")
    assert out.startswith("Cook mode for Chilli, 3 steps. Step 1: Fry the onion")
    data = out.card["data"]
    assert out.card["kind"] == "cooking-steps" and data["recipe"] == "Chilli"
    assert [st["minutes"] for st in data["steps"]] == [5, None, 30]
    assert recipes(s, action="cook_mode", name="chilli", step=3).card["data"]["start"] == 2
    with pytest.raises(ValueError):
        recipes(s, action="cook_mode", name="lasagne")


def test_scale(s):
    with pytest.raises(ValueError, match="How many"):
        recipes(s, action="scale", name="Pancakes", servings_to=6)
    out = recipes(s, action="scale", name="Pancakes", servings_from=2, servings_to=6)
    assert out.card["kind"] == "table" and out.card["columns"] == ["For 2", "For 6"]
    assert out.card["rows"][0] == ["100g plain flour", "300 g plain flour"]
    assert out.card["rows"][3] == ["½ tsp salt", "1½ tsp salt"]
    # Remembers the servings for next time.
    assert recipes(s, action="scale", name="Pancakes", servings_to=1).card["rows"][1] == ["2 eggs", "1 eggs"]


def test_what_can_i_make(s):
    with pytest.raises(ValueError, match="pantry"):
        recipes(s, action="what_can_i_make")
    homekitchen.pantry_add(s, ["plain flour", "eggs", "milk", "onions"])
    out = recipes(s, action="what_can_i_make")
    assert out == "You can make Pancakes with what you've got."
    labels = [i["label"] for i in out.card["items"]]
    assert labels[0] == "Pancakes: 100%, you've got everything"
    assert labels[1].startswith("Chilli: 40%, missing beef mince, passata, kidney beans")


def test_batch_plan(s):
    homekitchen.recipe_save(s, "Bolognese", ["250 g beef mince", "1 onion", "Herbs to taste"],
                            ["Cook for 1 hour."], False)
    out = recipes(s, action="batch_plan", names=["chilli", "bolognese"])
    data = out.card["data"]
    assert out.card["kind"] == "cooking-batch"
    assert ["beef mince", "750 g"] in data["shopping"]["rows"]
    assert ["onion", "2"] in data["shopping"]["rows"]
    assert data["order"]["rows"][0][1] == "Bolognese" and data["order"]["rows"][0][2] == "about 60 min"
    assert "Bolognese" in out and "shopping list" in out.card["buttons"][0]["say"]
    with pytest.raises(ValueError):
        recipes(s, action="batch_plan", names=["chilli"])


def test_tonight(s):
    assert recipes(s, action="tonight") == "Nothing's on the meal plan for tonight."
    homekitchen.meal_set(s, "today", "Chilli")
    homekitchen.pantry_add(s, ["onion", "passata"])
    left(s, action="add", what="rice", cooked_on="yesterday")
    out = recipes(s, action="tonight")
    assert out == "Tonight it's Chilli. You're missing 2 ingredients."
    labels = [i["label"] for i in out.card["items"]]
    assert "Dinner: Chilli" in labels and "Missing: beef mince, kidney beans" in labels
    assert "Leftovers to eat today: rice" in labels
    assert [b["label"] for b in out.card["buttons"]] == ["Recipe steps", "Kitchen timers", "Add missing to shopping"]


def test_tags(s):
    assert recipes(s, action="tag", name="pancakes", tags=["vegetarian", "nut-free"]) == \
        "Pancakes is tagged vegetarian, nut-free."
    assert recipes(s, action="tag", name="pancakes", tags=["nut-free"], remove=True) == "Pancakes is tagged vegetarian."
    out = recipes(s, action="filter_tags", tags=["vegetarian"])
    assert out == "1 recipe vegetarian: Pancakes." and out.card["items"][0]["say"] == "Start cook mode for Pancakes."
    assert recipes(s, action="filter_tags", tags=["vegan"]) == "No vegan recipes saved."
    with pytest.raises(ValueError):
        recipes(s, action="tag", name="pancakes", tags=[])


def test_ratings_and_not_lately(s):
    assert recipes(s, action="rate", name="chilli", stars=5, note="Add more cumin", made_on="2026-09-20") == \
        "Noted: made Chilli on Sunday 20 September, 5 stars."
    recipes(s, action="rate", name="chilli", stars=3)
    out = recipes(s, action="reviews")
    assert out.card["rows"][0][:4] == ["Chilli", "★★★★ 4.0", "2", "2026-09-28"]
    assert out.card["rows"][1][1] == "not rated"
    one = recipes(s, action="reviews", name="chilli")
    assert one.card["rows"][1] == ["Chilli", "★★★★★", "", "2026-09-20", "Add more cumin"]
    lately = recipes(s, action="not_cooked_lately", days=7)
    assert lately == "Not cooked in 7 days: Pancakes."
    assert lately.card["items"][0]["label"] == "Pancakes: never made"
    with pytest.raises(ValueError):
        recipes(s, action="rate", name="chilli", stars=9)


def test_kitchen_timers(s):
    out = cooking.run_tool("cooking_timers", {"timers": [{"name": "Pasta", "minutes": 10}, {"minutes": 2.5}]}, s)
    assert out == "Started Pasta for 10 minutes, Timer 2 for 2 minutes 30 seconds."
    timers = out.card["data"]["timers"]
    assert out.card["kind"] == "cooking-timers" and [t["seconds"] for t in timers] == [600, 150]
    assert timers[0]["key"] != timers[1]["key"]
    assert cooking.run_tool("cooking_timers", {}, s).card["data"]["timers"] == []


def test_roast_time(s):
    out = ask(s, action="roast_time", meat="chicken", weight_kg=1.5)
    assert out.startswith("Roast chicken at 190°C, fan 170, gas 5, for about 1 h 20 min, then rest 15 min.")
    assert ["Core temperature", "75°C in the thickest part"] in out.card["rows"]
    assert "80 minutes" in out.card["buttons"][0]["say"]
    beef = ask(s, action="roast_time", meat="beef", weight_kg=2, doneness="rare")
    assert "for about 1 h 40 min" in beef and "52°C" in beef
    turkey = ask(s, action="roast_time", meat="turkey", weight_lb=11)
    assert "about 3 h 10 min" in turkey
    with pytest.raises(ValueError):
        ask(s, action="roast_time", meat="chicken")


def test_safe_temps(s):
    out = ask(s, action="safe_temps")
    assert out.card["kind"] == "table" and ["Fish", "63°C", "flesh flakes and turns opaque"] in out.card["rows"]


def test_substitute(s):
    assert ask(s, action="substitute", ingredient="Buttermilk").startswith("Instead of buttermilk: 250 ml milk")
    assert ask(s, action="substitute", ingredient="eggs").startswith("Instead of egg:")
    out = ask(s, action="substitute", ingredient="unicorn dust")
    assert out.startswith("I haven't got a swap for unicorn dust") and len(out.card["rows"]) >= 60


def test_seasonal(s):
    out = ask(s, action="seasonal")
    assert out.card["title"] == "In season in September (UK)"
    assert {"label": "Fruit: blackberries", "done": False, "say": "Find me a recipe with blackberries."} in out.card["items"]
    assert ask(s, action="seasonal", month="dec").card["buttons"][0]["label"] == "January"
    with pytest.raises(ValueError):
        ask(s, action="seasonal", month="smarch")


def test_cups_to_grams(s):
    assert ask(s, action="cups_to_grams", ingredient="walnuts", cups=2) == "2 cups of walnuts is about 200 g."
    assert ask(s, action="cups_to_grams", ingredient="flour") == "1 cup of flour is about 125 g."
    table = ask(s, action="cups_to_grams")
    assert len(table.card["rows"]) >= 30 and table.card["columns"][1] == "1 cup"
    with pytest.raises(ValueError):
        ask(s, action="cups_to_grams", ingredient="moon rock")


def test_baking_ratio(s):
    out = ask(s, action="baking_ratio", flour_g=500, hydration=70)
    assert out == "For 500 g flour at 70% hydration: 350 g water, 10 g salt, 5.0 g yeast."
    assert ["Total dough", "865 g", "173.0%"] in out.card["rows"]
    wet = ask(s, action="baking_ratio", flour_g=1000, water_g=800, extras=[{"name": "Olive oil", "grams": 50}])
    assert "80% hydration" in wet and ["Olive oil", "50 g", "5.0%"] in wet.card["rows"]
    assert "focaccia" in wet.card["text"]


def test_drink_pairing(s):
    out = ask(s, action="drink_pairing", dish="Chicken tikka curry")
    assert out.startswith("With Chicken tikka curry, try Off-dry Riesling") and out.card["rows"][0][0] == "Curry"
    assert ask(s, action="drink_pairing", dish="creamy pasta").card["rows"][0][0] == "Creamy pasta and risotto"
    everything = ask(s, action="drink_pairing", dish="toast")
    assert everything.startswith("I haven't a match") and len(everything.card["rows"]) > 15


def test_leftovers(s):
    assert left(s, action="add", what="Beef stew", cooked_on="yesterday") == "Logged Beef stew; eat by Wednesday 30 September."
    assert left(s, action="add", what="Egg fried rice").endswith("Rice is best eaten within a day; cool it quickly.")
    left(s, action="add", what="Roast chicken", cooked_on="2026-09-24")
    out = left(s, action="list")
    assert out == "3 leftovers in the fridge; throw away Roast chicken."
    assert out.card["checks"] and out.card["items"][0]["label"] == "Roast chicken: past its date, bin it (cooked 2026-09-24)"
    assert left(s, action="clear_old").startswith("Ask the user to confirm")
    assert left(s, action="clear_old", confirmed=True) == "Cleared Roast chicken."
    assert left(s, action="eaten", what="stew") == "Crossed off the Beef stew. 1 leftover left."
    assert left(s, action="eaten", what="pizza") == "There are no leftovers called pizza."
