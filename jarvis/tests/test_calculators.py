import asyncio
import string

import httpx
import pytest

import calcmaths
import calcmoney
import calcrandom
import calcunits
import tools
from config import Settings

S = Settings(currency="GBP")


def money(args):
    return calcmoney.run_tool("money_maths", args, S)


def test_calculator_sums():
    assert calcmaths.calculate("(12.5 + 3) * 4 / 7") == "(12.5 + 3) * 4 / 7 = 8.857142857"
    assert calcmaths.calculate("2^10") == "2^10 = 1,024"
    assert calcmaths.calculate("sqrt(144) + round(2.345, 1)") == "sqrt(144) + round(2.345, 1) = 14.3"
    assert calcmaths.calculate("10 % 3").endswith("= 1")
    assert calcmaths.calculate("200 * 15%").endswith("= 30")
    assert calcmaths.calculate("1,000,000 / 4").endswith("= 250,000")
    assert calcmaths.calculate("sin(30) + factorial(4) + abs(-2)").endswith("= 26.5")
    assert calcmaths.calculate("pi").endswith("= 3.141592654")


@pytest.mark.parametrize("bad", ["1/0", "__import__('os')", "open('x')", "9**9**9", "10**101", "sqrt(-1)",
                                 "'a' * 3", "x + 1", "(-8) ** 0.5", "factorial(500)", "1" * 400, "2 +", ""])
def test_calculator_refuses(bad):
    with pytest.raises(ValueError):
        calcmaths.calculate(bad)


def test_bmi():
    assert calcmaths.bmi({"height_cm": 175, "weight_kg": 70}).startswith("BMI 22.9, which the NHS calls healthy weight")
    assert "overweight" in calcmaths.run_tool("calculate", {"action": "bmi", "feet": 5, "inches": 9, "stone": 14}, S)
    assert "underweight" in calcmaths.bmi({"height_cm": 180, "weight_kg": 55})
    assert "severely obese" in calcmaths.bmi({"height_cm": 160, "weight_kg": 110})
    with pytest.raises(ValueError):
        calcmaths.bmi({"height_cm": 175})


def test_roman():
    assert calcmaths.run_tool("calculate", {"action": "roman", "value": "1987"}, S) == \
        "1987 in Roman numerals is MCMLXXXVII."
    assert calcmaths.roman("mmxxvi") == "MMXXVI is 2026."
    for bad in ("IIII", "VX", "ABC", "0", "4000"):
        with pytest.raises(ValueError):
            calcmaths.roman(bad)


def test_unit_conversions():
    assert calcunits.convert(5, "miles", "km") == "5 miles is 8.04672 km."
    assert calcunits.convert(1, "kg", "lbs") == "1 kg is 2.20462 lb."
    assert calcunits.convert(1, "pint", "ml") == "1 pint is 568.261 ml."
    assert calcunits.convert(1, "acre", "square metres") == "1 acre is 4,046.86 sq m."
    assert calcunits.convert(70, "mph", "km/h") == "70 mph is 112.654 km/h."
    assert calcunits.convert(1, "GB", "MiB") == "1 GB is 953.674 MiB."
    assert calcunits.convert(100, "megabits", "MB") == "100 megabits is 12.5 MB."
    assert calcunits.convert(3, "weeks", "hours") == "3 weeks is 504 hours."
    assert calcunits.convert(2, "ms", "seconds") == "2 ms is 0.002 seconds."
    assert calcunits.convert(12, "stone", "kg") == "12 stone is 76.2035 kg."
    with pytest.raises(ValueError):
        calcunits.convert(1, "miles", "kg")
    with pytest.raises(ValueError):
        calcunits.convert(1, "smoots", "m")


def test_temperature():
    assert calcunits.convert(98.6, "F", "C") == "98.6°F is 37°C."
    assert calcunits.convert(0, "degrees celsius", "kelvin") == "0°C is 273.15K."
    assert calcunits.run_tool("convert_units", {"value": 180, "from": "c", "to": "fahrenheit"}, S) == "180°C is 356°F."
    with pytest.raises(ValueError):
        calcunits.convert(-300, "C", "F")


def test_cooking():
    assert calcunits.convert(1, "cup", "g", "flour") == "1 cup of flour is about 125 g."
    assert calcunits.convert(100, "g", "cups", "sugar") == "100 g of sugar is about 0.5 cups."
    assert calcunits.convert(3, "tbsp", "tsp") == "3 tbsp is 9 tsp."
    assert calcunits.convert(4, "gas mark", "C") == "Gas mark 4 is about 180°C (160°C fan), or 356°F."
    assert calcunits.convert(200, "C", "gas mark") == "200°C is about gas mark 6."
    with pytest.raises(ValueError):
        calcunits.convert(1, "cup", "g")


def test_percentages():
    assert money({"action": "percent_of", "percent": 15, "amount": 80}) == "15% of 80 is 12."
    assert money({"action": "what_percent", "amount": 30, "total": 120}) == "30 is 25% of 120."
    assert money({"action": "percent_change", "amount": 80, "total": 100}) == "From 80 to 100 is up 25%."
    assert money({"action": "percent_change", "amount": 100, "total": 80}) == "From 100 to 80 is down 20%."


def test_tip_and_split():
    assert money({"action": "tip", "amount": 86.4, "percent": 12.5, "people": 3}) == \
        "Tip £10.80, total £97.20. Split 3 ways that's £32.40 each."
    assert money({"action": "tip", "amount": 100, "people": 3}) == \
        "Total £100.00. Split 3 ways that's £33.34 each (rounded up to the penny)."


def test_loan():
    out = money({"action": "loan", "amount": 200000, "rate": 4.5, "years": 25})
    assert "£1,111.66 a month" in out and "£133,499.49 is interest" in out
    assert "£100.00 a month" in money({"action": "loan", "amount": 1200, "rate": 0, "years": 1})


def test_savings():
    out = money({"action": "savings_growth", "amount": 1000, "monthly": 100, "rate": 4, "years": 5})
    assert "£7,850.89" in out and "£850.89 interest" in out
    out = money({"action": "savings_goal", "total": 5000, "monthly": 200, "rate": 3})
    assert "in 2 years and 1 month (25 months)" in out
    with pytest.raises(ValueError):
        money({"action": "savings_goal", "total": 5000})


def test_take_home():
    out = money({"action": "take_home", "amount": 35000})
    assert out.startswith("Estimate for England, 2026/27")
    assert "£28,719.60 a year" in out and "income tax £4,486.00" in out and "National Insurance £1,794.40" in out
    assert calcmoney.income_tax(110_000) == pytest.approx(33_432)
    assert calcmoney.income_tax(150_000) == pytest.approx(53_703)
    assert calcmoney.national_insurance(60_000) == pytest.approx(3_210.60)
    out = money({"action": "take_home", "amount": 60000, "percent": 5, "student_loan": True})
    assert "pension £3,000.00" in out and "Plan 2 student loan £2,755.35" in out and "£40,802.05 a year" in out


def test_vat():
    assert money({"action": "vat_add", "amount": 100}) == "£100.00 plus 20% VAT is £120.00 (VAT £20.00)."
    assert money({"action": "vat_remove", "amount": 120}) == "£120.00 including 20% VAT is £100.00 before VAT (VAT £20.00)."
    assert "£105.00" in money({"action": "vat_add", "amount": 100, "rate": 5})


def test_unit_price():
    out = money({"action": "unit_price", "items": [{"price": 2.10, "size": 500, "unit": "g", "label": "small"},
                                                   {"price": 2.90, "size": 0.75, "unit": "kg", "label": "big"}]})
    assert out == "small: £0.42 per 100 g; big: £0.39 per 100 g. Big is better value, about 8% cheaper per 100 g."
    with pytest.raises(ValueError):
        money({"action": "unit_price", "items": [{"price": 1, "size": 1, "unit": "kg"}, {"price": 1, "size": 1, "unit": "l"}]})


def test_fuel_cost():
    assert money({"action": "fuel_cost", "miles": 120, "mpg": 45, "price": 145.9}) == \
        "120 miles at 45 mpg uses about 12.1 litres; at £1.46 a litre that's about £17.69."


def test_chance():
    assert calcrandom.coin() in ("It's heads.", "It's tails.")
    assert calcrandom.run_tool("chance", {"action": "dice", "dice": "d6"}, S) in {f"You rolled {n}." for n in range(1, 7)}
    out = calcrandom.dice("3d6+2")
    total = int(out.rsplit(" ", 1)[1].rstrip("."))
    assert out.startswith("You rolled") and 5 <= total <= 20
    with pytest.raises(ValueError):
        calcrandom.dice("roll some")
    for _ in range(20):
        assert 3 <= int(calcrandom.number(3, 5).split()[0]) <= 5
    assert calcrandom.run_tool("chance", {"action": "pick", "options": ["pizza", "curry"]}, S) in \
        ("I pick pizza.", "I pick curry.")
    with pytest.raises(ValueError):
        calcrandom.pick(["only one"])


def test_password():
    made = calcrandom.run_tool("chance", {"action": "password", "length": 20}, S).rsplit(" ", 1)[1]
    assert len(made) == 20 and any(c in calcrandom.SYMBOLS for c in made) and any(c.isdigit() for c in made)
    plain = calcrandom.password(12, False).rsplit(" ", 1)[1]
    assert len(plain) == 12 and set(plain) <= set(string.ascii_letters + string.digits)
    with pytest.raises(ValueError):
        calcrandom.password(4)


def test_calculators_registered_and_dispatched():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"calculate", "convert_units", "money_maths", "chance"} <= names
    for module in (calcmaths, calcunits, calcmoney, calcrandom):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools.run_tool("calculate", {"action": "sum", "expression": "6 * 7"}, Settings(), http)

    assert asyncio.run(go()) == "6 * 7 = 42"
