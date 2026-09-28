"""Discover: codes and numbers. Morse code both ways (the pop-up can beep it), the NATO phonetic alphabet,
Unicode braille, and facts about any whole number (prime, factors, binary, hex, square, cube, Fibonacci).

Nothing goes online or is saved.
"""

import math

import screen
from config import Settings

screen.EXTRA_KINDS.add("discover-code")

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
    "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....",
    "7": "--...", "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.",
    "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...", ";": "-.-.-.",
    "=": "-...-", "+": ".-.-.", "-": "-....-", "\"": ".-..-.", "@": ".--.-.",
}
FROM_MORSE = {v: k for k, v in MORSE.items()}
NATO = {
    "A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo", "F": "Foxtrot", "G": "Golf", "H": "Hotel",
    "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November", "O": "Oscar", "P": "Papa",
    "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango", "U": "Uniform", "V": "Victor", "W": "Whiskey",
    "X": "X-ray", "Y": "Yankee", "Z": "Zulu", "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
    "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
}
# Grade 1 (uncontracted) braille: which of the six dots are raised.
BRAILLE_DOTS = {
    "a": "1", "b": "12", "c": "14", "d": "145", "e": "15", "f": "124", "g": "1245", "h": "125", "i": "24",
    "j": "245", "k": "13", "l": "123", "m": "134", "n": "1345", "o": "135", "p": "1234", "q": "12345", "r": "1235",
    "s": "234", "t": "2345", "u": "136", "v": "1236", "w": "2456", "x": "1346", "y": "13456", "z": "1356",
    ",": "2", ";": "23", ":": "25", ".": "256", "!": "235", "?": "236", "'": "3", "-": "36",
}
NUMBER_SIGN, CAPITAL_SIGN = "3456", "6"
MAX_TEXT = 500


def _text(text) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        raise ValueError("What text should I convert?")
    return text[:MAX_TEXT]


def _cell(dots: str) -> str:
    return chr(0x2800 + sum(1 << (int(d) - 1) for d in dots))


def to_morse(text) -> screen.Shown:
    text = _text(text)
    words = [" ".join(MORSE[c] for c in w.upper() if c in MORSE) for w in text.split()]
    code = " / ".join(w for w in words if w)
    if not code:
        raise ValueError("There's nothing in that I can write in Morse.")
    return screen.Shown(f"In Morse code, {text} is: {code}. Press Play on the screen to hear it.",
                        screen.card("discover-code", "Morse code", "discover-morse",
                                    data={"text": text, "code": code, "mode": "morse", "wpm": 15}))


def from_morse(code) -> screen.Shown:
    code = _text(code).replace("_", "-").replace("·", ".").replace("—", "-").replace("|", "/")
    words = []
    for word in code.split("/"):
        letters = [FROM_MORSE.get(sym, "?") for sym in word.split()]
        if letters:
            words.append("".join(letters))
    text = " ".join(words)
    if not text or set(text) <= {"?", " "}:
        raise ValueError("That doesn't look like Morse code. Use dots, dashes, spaces between letters and / between words.")
    return screen.Shown(f"That Morse code says: {text}.", screen.card(
        "discover-code", "Morse decoded", "discover-morse", data={"text": text, "code": code, "mode": "morse",
                                                                  "wpm": 15}))


def nato(text) -> screen.Shown:
    text = _text(text)[:100]
    words = [NATO.get(c.upper(), c) for c in text if not c.isspace()]
    items = [{"label": f"{c.upper()}  {NATO.get(c.upper(), '')}".strip()} for c in text if not c.isspace()]
    return screen.Shown(f"{text} in the phonetic alphabet: {', '.join(words)}.",
                        screen.card("list", f"Phonetic: {text}", "discover-nato", items=items))


def braille(text) -> screen.Shown:
    text = _text(text)
    out, numbers = [], False
    for c in text:
        if c.isdigit():
            if not numbers:
                out.append(_cell(NUMBER_SIGN))
                numbers = True
            out.append(_cell(BRAILLE_DOTS["j" if c == "0" else "abcdefghi"[int(c) - 1]]))
            continue
        numbers = False
        if c.isspace():
            out.append(_cell(""))
        elif c.lower() in BRAILLE_DOTS:
            if c.isupper():
                out.append(_cell(CAPITAL_SIGN))
            out.append(_cell(BRAILLE_DOTS[c.lower()]))
    code = "".join(out)
    return screen.Shown(f"{text} in braille is on the screen.", screen.card(
        "discover-code", "Braille", "discover-braille", data={"text": text, "code": code, "mode": "braille"}))


# ---- Numbers ----------------------------------------------------------------------------------

def _factors(n: int) -> list[int]:
    small = [d for d in range(1, math.isqrt(n) + 1) if n % d == 0]
    return sorted(set(small + [n // d for d in small]))


def _prime_factors(n: int) -> list[int]:
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    return out + ([n] if n > 1 else [])


def _fibonacci(n: int) -> bool:
    return any(math.isqrt(x) ** 2 == x for x in (5 * n * n + 4, 5 * n * n - 4))


def number_facts(value) -> screen.Shown:
    try:
        n = int(float(str(value).replace(",", "").strip()))
    except ValueError:
        raise ValueError("Which whole number?") from None
    if not 0 <= n <= 10 ** 12:
        raise ValueError("Pick a whole number from 0 to a trillion.")
    rows = [["Even or odd", "even" if n % 2 == 0 else "odd"]]
    if n >= 2:
        pf = _prime_factors(n)
        rows.append(["Prime?", "yes" if len(pf) == 1 else "no"])
        if len(pf) > 1:
            rows.append(["Prime factors", " × ".join(map(str, pf))])
        if n <= 10 ** 10:
            fs = _factors(n)
            rows.append(["Factors", ", ".join(map(str, fs[:40])) + (" ..." if len(fs) > 40 else "")])
    rows += [["Binary", bin(n)[2:]], ["Hexadecimal", hex(n)[2:].upper()], ["Octal", oct(n)[2:]],
             ["Squared", f"{n * n:,}"], ["Cubed", f"{n ** 3:,}"], ["Square root", f"{math.sqrt(n):,.4g}"],
             ["Perfect square?", "yes" if math.isqrt(n) ** 2 == n else "no"],
             ["Fibonacci number?", "yes" if _fibonacci(n) else "no"]]
    facts = dict(rows)
    said = f"{n:,} is {facts['Even or odd']}"
    if n >= 2:
        said += ", prime" if facts["Prime?"] == "yes" else f", not prime ({facts['Prime factors']})"
    if facts["Fibonacci number?"] == "yes":
        said += ", a Fibonacci number"
    said += f"; in binary it's {facts['Binary']}."
    return screen.Shown(said, screen.card("table", f"The number {n:,}", "discover-number",
                                          columns=["", f"{n:,}"], rows=rows))


ACTIONS = ["number_facts", "morse", "morse_to_text", "nato", "braille"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "codes_and_numbers",
        "description": "Codes and number facts with pop-ups. number_facts: is a number prime, its factors, "
                       "binary, hex, square, cube, is it a Fibonacci number. morse: text to Morse code (the pop-up "
                       "can play the beeps); morse_to_text: decode Morse (dots, dashes, / between words). nato: "
                       "spell text in the NATO phonetic alphabet (Alfa, Bravo...). braille: text in braille.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "The text, Morse code or number."},
            },
            "required": ["action", "text"],
            "additionalProperties": False,
        },
    }]


NAMES = {"codes_and_numbers"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, text = args.get("action"), args.get("text")
    if action == "number_facts":
        return number_facts(text)
    if action == "morse":
        return to_morse(text)
    if action == "morse_to_text":
        return from_morse(text)
    if action == "nato":
        return nato(text)
    if action == "braille":
        return braille(text)
    raise ValueError(f"Unknown codes action: {action}")
