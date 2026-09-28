"""Games and fun: trivia, guess the number, rock paper scissors, riddles, word scramble,
magic 8-ball, would you rather, jokes, quotes, fun facts and a this-or-that decider.

Games and scores live in this process only (they reset when Alfred restarts). Trivia questions come
from the free Open Trivia Database (opentdb.com, no key); everything else is local.
"""

import html
import random
import re

import httpx

from config import Settings

TRIVIA_URL = "https://opentdb.com/api.php"
TRIVIA_CATEGORIES = {
    "general": 9, "books": 10, "film": 11, "music": 12, "tv": 14, "video games": 15, "science": 17,
    "computers": 18, "maths": 19, "mythology": 20, "sport": 21, "geography": 22, "history": 23,
    "politics": 24, "art": 25, "celebrities": 26, "animals": 27, "vehicles": 28,
}
LETTERS = "ABCD"
MOVES = ("rock", "paper", "scissors")
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

rng = random.Random()
# Current game per kind and running scores, for this session only.
state: dict = {"trivia": None, "number": None, "riddle": None, "scramble": None, "jokes_told": set(),
               "scores": {}}

EIGHT_BALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.", "You may rely on it.",
    "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.",
    "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]

WOULD_YOU_RATHER = [
    "be able to fly or be invisible", "live without music or without films", "always be ten minutes late or "
    "always be twenty minutes early", "have a rewind button or a pause button for your life",
    "speak every language or play every instrument", "live by the sea or in the mountains",
    "never have to sleep or never have to eat", "be the funniest person in the room or the cleverest",
    "have summer all year or winter all year", "explore space or the deep ocean",
    "give up your phone for a month or chocolate for a year", "meet your ancestors or your great-grandchildren",
    "have a personal chef or a personal driver", "be able to talk to animals or read minds",
    "always know the time or always know which way is north", "travel to the past or to the future",
    "live in a treehouse or a houseboat", "only eat pizza or only eat curry for a year",
    "be a famous actor or a famous musician", "have unlimited free flights or unlimited free food",
    "never get stuck in traffic again or never catch a cold again", "win the lottery or live twice as long",
    "have a pet dragon or a pet unicorn", "be able to teleport or breathe underwater",
    "have perfect memory or perfect eyesight", "lose your keys every day or your phone once a month",
    "watch the sunrise every day or the sunset every day", "have a garden full of flowers or full of vegetables",
    "be a brilliant cook or a brilliant dancer", "give a speech to a thousand people or sing on your own "
    "to ten", "live without the internet or without hot water", "only whisper or only shout",
    "be stuck in a lift with your boss or with your ex", "go camping for a week or stay in a city for a week",
    "have a rewind for conversations or a skip button for queues", "know how you'll die or when you'll die",
    "be the best player on a losing team or the worst on a winning team", "have fingers as long as your legs "
    "or legs as long as your fingers", "always have to sing instead of speak or dance everywhere you walk",
    "find true love or a suitcase with a million pounds",
]

RIDDLES = [
    ("What has keys but can't open locks?", "a piano", ["piano", "keyboard"]),
    ("What gets wetter the more it dries?", "a towel", ["towel"]),
    ("What has a head and a tail but no body?", "a coin", ["coin"]),
    ("What can you catch but not throw?", "a cold", ["cold"]),
    ("What has hands but can't clap?", "a clock", ["clock", "watch"]),
    ("What has to be broken before you can use it?", "an egg", ["egg"]),
    ("I'm tall when I'm young and short when I'm old. What am I?", "a candle", ["candle"]),
    ("What month of the year has 28 days?", "all of them", ["all"]),
    ("What goes up but never comes down?", "your age", ["age"]),
    ("What has lots of teeth but can't bite?", "a comb", ["comb", "zip"]),
    ("What has one eye but can't see?", "a needle", ["needle"]),
    ("What can travel around the world while staying in a corner?", "a stamp", ["stamp"]),
    ("What has a neck but no head?", "a bottle", ["bottle"]),
    ("The more you take, the more you leave behind. What are they?", "footsteps", ["footstep", "step"]),
    ("What belongs to you, but other people use it more than you do?", "your name", ["name"]),
    ("What runs but never walks, and has a mouth but never talks?", "a river", ["river"]),
    ("What has cities but no houses, forests but no trees, and water but no fish?", "a map", ["map"]),
    ("What can fill a room but takes up no space?", "light", ["light"]),
    ("What is full of holes but still holds water?", "a sponge", ["sponge"]),
    ("What goes through towns and over hills but never moves?", "a road", ["road"]),
    ("If you have me, you want to share me. If you share me, you haven't got me. What am I?", "a secret",
     ["secret"]),
    ("What word is spelled incorrectly in every dictionary?", "incorrectly", ["incorrectly"]),
    ("What has four legs but can't walk?", "a table", ["table", "chair"]),
    ("Which building has the most stories?", "a library", ["library"]),
    ("What can you break without ever touching it?", "a promise", ["promise"]),
    ("Forward I'm heavy, but backward I'm not. What am I?", "a ton", ["ton"]),
    ("What lets you look right through a wall?", "a window", ["window"]),
    ("What kind of band never plays music?", "a rubber band", ["rubber"]),
    ("What is always in front of you but can't be seen?", "the future", ["future"]),
    ("What comes once in a minute, twice in a moment, but never in a thousand years?", "the letter M",
     ["m", "letter m"]),
    ("I have branches, but no fruit, trunk or leaves. What am I?", "a bank", ["bank"]),
]

SCRAMBLE_WORDS = [
    ("planet", "found in space"), ("garden", "somewhere outside with plants"), ("pencil", "you write with it"),
    ("castle", "a king might live there"), ("rabbit", "an animal with long ears"), ("orange", "a fruit and a "
    "colour"), ("guitar", "a musical instrument"), ("window", "part of a house"), ("dragon", "a mythical "
    "creature"), ("pirate", "sails the seas looking for treasure"), ("bridge", "crosses a river"),
    ("candle", "gives light"), ("winter", "a season"), ("jungle", "a thick tropical forest"),
    ("rocket", "goes into space"), ("banana", "a yellow fruit"), ("coffee", "a morning drink"),
    ("button", "on a shirt"), ("monkey", "an animal that climbs trees"), ("island", "land surrounded by "
    "water"), ("puzzle", "something to solve"), ("silver", "a precious metal"), ("tomato", "red and goes in "
    "salads"), ("violin", "a stringed instrument"), ("penguin", "a bird that can't fly"), ("blanket", "keeps "
    "you warm in bed"), ("kitchen", "a room for cooking"), ("thunder", "comes with lightning"),
    ("library", "full of books"), ("dolphin", "a clever sea mammal"), ("volcano", "a mountain that erupts"),
    ("pyramid", "found in Egypt"), ("biscuit", "goes with a cup of tea"), ("rainbow", "colours in the sky"),
    ("octopus", "has eight arms"), ("chimney", "smoke comes out of it"), ("compass", "shows north"),
    ("pancake", "flipped in a pan"), ("giraffe", "the tallest animal"), ("lantern", "a light you carry"),
    ("teacher", "works at a school"), ("holiday", "time off"), ("mountain", "very high land"),
    ("elephant", "a big grey animal"), ("umbrella", "keeps the rain off"), ("sandwich", "lunch between bread"),
    ("football", "a popular sport"), ("dinosaur", "extinct giant reptile"), ("treasure", "pirates hunt it"),
    ("keyboard", "you type on it"), ("chocolate", "a sweet treat"), ("butterfly", "an insect with bright "
    "wings"), ("astronaut", "travels to space"), ("crocodile", "a reptile with big jaws"),
    ("telescope", "for looking at stars"), ("snowflake", "falls in winter"), ("adventure", "an exciting trip"),
    ("waterfall", "a river dropping off a cliff"), ("cucumber", "a long green vegetable"),
    ("hedgehog", "a small spiky animal"),
]

JOKES = [
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "What do you call a fake noodle? An impasta.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a bear with no teeth? A gummy bear.",
    "Why can't a bicycle stand up by itself? It's two tired.",
    "I only know twenty-five letters of the alphabet. I don't know y.",
    "What do you call a fish with no eyes? A fsh.",
    "Why did the maths book look sad? It had too many problems.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "How do you organise a space party? You planet.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "I would tell you a joke about construction, but I'm still working on it.",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "Why did the golfer bring two pairs of trousers? In case he got a hole in one.",
    "What do you call a dinosaur with an extensive vocabulary? A thesaurus.",
    "I'm on a seafood diet. I see food and I eat it.",
    "What do you call a sleeping bull? A bulldozer.",
    "Why did the coffee file a police report? It got mugged.",
    "How does a penguin build its house? Igloos it together.",
    "What's brown and sticky? A stick.",
    "Why do cows wear bells? Because their horns don't work.",
    "I used to be a banker, but I lost interest.",
    "What did one wall say to the other? I'll meet you at the corner.",
    "Why was the broom late? It over swept.",
    "What do you call a man with a rubber toe? Roberto.",
    "Did you hear about the claustrophobic astronaut? He just needed a little space.",
    "Why don't scientists trust atoms? Because they make up everything.",
    "What's orange and sounds like a parrot? A carrot.",
    "Why did the tomato turn red? Because it saw the salad dressing.",
    "What do you call a boomerang that won't come back? A stick.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why are elevator jokes so good? They work on so many levels.",
    "What do you call a pig that does karate? A pork chop.",
    "How do you make a tissue dance? Put a little boogie in it.",
    "Why did the picture go to jail? Because it was framed.",
    "What do you call a deer with no eyes? No idea.",
    "Why did the cookie go to the doctor? Because it felt crummy.",
    "What did the grape do when it got stepped on? It let out a little wine.",
    "I don't trust stairs. They're always up to something.",
    "What do you call an alligator in a vest? An investigator.",
    "Why couldn't the leopard play hide and seek? Because he was always spotted.",
    "What kind of shoes do ninjas wear? Sneakers.",
    "How do you find Will Smith in the snow? You look for the fresh prints.",
    "What do you call a factory that makes okay products? A satisfactory.",
    "Why did the invisible man turn down the job offer? He couldn't see himself doing it.",
    "I asked the librarian if they had books about paranoia. She whispered, they're right behind you.",
    "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
    "Why do bees have sticky hair? Because they use honeycombs.",
    "What do you call a snowman with a six-pack? An abdominal snowman.",
    "How do you make a Swiss roll? Push him down a hill.",
]

QUOTES = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Never give in, never give in, never, never, never.", "Winston Churchill"),
    ("I learned that courage was not the absence of fear, but the triumph over it.", "Nelson Mandela"),
    ("Education is the most powerful weapon which you can use to change the world.", "Nelson Mandela"),
    ("It is not the critic who counts.", "Theodore Roosevelt"),
    ("The only thing we have to fear is fear itself.", "Franklin D. Roosevelt"),
    ("You may encounter many defeats, but you must not be defeated.", "Maya Angelou"),
    ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison"),
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "Will Durant"),
    ("Life is like riding a bicycle. To keep your balance you must keep moving.", "Albert Einstein"),
    ("Imagination is more important than knowledge.", "Albert Einstein"),
    ("You must do the thing you think you cannot do.", "Eleanor Roosevelt"),
    ("If you can't fly then run, if you can't run then walk, if you can't walk then crawl, but whatever you "
     "do you have to keep moving forward.", "Martin Luther King Jr."),
    ("You miss one hundred percent of the shots you don't take.", "Wayne Gretzky"),
    ("Start where you are. Use what you have. Do what you can.", "Arthur Ashe"),
    ("Ever tried. Ever failed. No matter. Try again. Fail again. Fail better.", "Samuel Beckett"),
    ("Alone we can do so little; together we can do so much.", "Helen Keller"),
    ("Optimism is the faith that leads to achievement.", "Helen Keller"),
    ("All we have to decide is what to do with the time that is given us.", "J. R. R. Tolkien"),
    ("While we are postponing, life speeds by.", "Seneca"),
    ("Waste no more time arguing about what a good man should be. Be one.", "Marcus Aurelius"),
    ("The most difficult thing is the decision to act, the rest is merely tenacity.", "Amelia Earhart"),
    ("It's not whether you get knocked down, it's whether you get up.", "Vince Lombardi"),
    ("Nothing great was ever achieved without enthusiasm.", "Ralph Waldo Emerson"),
    ("If one advances confidently in the direction of his dreams, he will meet with a success unexpected "
     "in common hours.", "Henry David Thoreau"),
    ("I've failed over and over and over again in my life. And that is why I succeed.", "Michael Jordan"),
    ("Well done is better than well said.", "Benjamin Franklin"),
    ("Nothing in life is to be feared, it is only to be understood.", "Marie Curie"),
    ("If I have seen further it is by standing on the shoulders of giants.", "Isaac Newton"),
    ("If you want the rainbow, you gotta put up with the rain.", "Dolly Parton"),
    ("Those who don't believe in magic will never find it.", "Roald Dahl"),
    ("Remember to look up at the stars and not down at your feet.", "Stephen Hawking"),
    ("One child, one teacher, one book, one pen can change the world.", "Malala Yousafzai"),
    ("Knowing is not enough; we must apply. Willing is not enough; we must do.", "Johann Wolfgang von Goethe"),
    ("I attribute my success to this: I never gave or took any excuse.", "Florence Nightingale"),
    ("You must never be fearful about what you are doing when it is right.", "Rosa Parks"),
    ("You have brains in your head. You have feet in your shoes. You can steer yourself any direction you "
     "choose.", "Dr. Seuss"),
    ("Courage doesn't always roar. Sometimes courage is the quiet voice at the end of the day saying, "
     "I will try again tomorrow.", "Mary Anne Radmacher"),
    ("How wonderful it is that nobody need wait a single moment before starting to improve the world.",
     "Anne Frank"),
    ("Suffer now and live the rest of your life as a champion.", "Muhammad Ali"),
]

FACTS = [
    "Octopuses have three hearts and blue blood.",
    "Botanically, bananas are berries, but strawberries aren't.",
    "A day on Venus is longer than its year: it takes 243 Earth days to spin once and 225 to orbit the Sun.",
    "Wombats produce cube-shaped poo.",
    "The Eiffel Tower grows around 15 centimetres taller in summer, because the iron expands in the heat.",
    "Sharks have been around longer than trees.",
    "Scotland's national animal is the unicorn.",
    "The shortest war in history, between Britain and Zanzibar in 1896, lasted under an hour.",
    "A group of flamingos is called a flamboyance.",
    "Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid.",
    "Teaching at Oxford University began before the Aztec capital, Tenochtitlan, was founded.",
    "Sea otters sometimes hold hands while they sleep so they don't drift apart.",
    "There are more possible games of chess than there are atoms in the observable universe.",
    "The blue whale is the largest animal known to have ever lived.",
    "Venus is the hottest planet, even though Mercury is closer to the Sun.",
    "Koalas have fingerprints that are almost impossible to tell apart from human ones.",
    "A bolt of lightning is about five times hotter than the surface of the Sun.",
    "Butterflies taste with their feet.",
    "Nintendo was founded in 1889 as a playing card company.",
    "The man who designed the Pringles tube, Fredric Baur, had some of his ashes buried in one.",
    "Neptune has only completed one orbit of the Sun since it was discovered in 1846.",
    "The Pacific Ocean is bigger than all of the Earth's land put together.",
    "Honeybees tell each other where to find flowers with a waggle dance.",
    "The word robot comes from the Czech word robota, meaning forced labour.",
    "The London Underground, opened in 1863, is the world's oldest underground railway.",
    "Big Ben is the name of the great bell, not the tower. The tower is the Elizabeth Tower.",
    "Tardigrades, tiny water bears, have survived being exposed to the vacuum of space.",
    "The dot over a lower-case i or j is called a tittle.",
    "Sunlight takes about 8 minutes and 20 seconds to reach Earth.",
    "Mount Everest grows by a few millimetres each year.",
    "Researchers at the University of Glasgow counted over 400 Scots words for snow.",
    "The first ever text message, sent in 1992, said Merry Christmas.",
    "Carrots used to be mostly purple or yellow. Orange carrots became popular in the Netherlands in the "
    "1600s.",
    "Babies are born with around 300 bones, but adults have 206, because some fuse together.",
    "A teaspoon of neutron star would weigh around a billion tonnes.",
    "Almost all penguins live in the Southern Hemisphere.",
    "The Welsh village Llanfairpwllgwyngyll has one of the longest place names in the world, 58 letters in "
    "full.",
    "Cats can't taste sweet things.",
    "The Moon drifts about 3.8 centimetres further from Earth every year.",
    "Ordinary matter, everything we can see, makes up only about 5 percent of the universe.",
    "A honeybee makes only about a twelfth of a teaspoon of honey in its whole life.",
    "Pots of honey thousands of years old have been found in Egyptian tombs, and honey barely spoils.",
]

THIS_OR_THAT = [
    ("tea", "coffee"), ("a film", "a series"), ("pizza", "curry"), ("a walk", "a nap"), ("beach", "city"),
    ("cats", "dogs"), ("sweet", "savoury"), ("sunrise", "sunset"), ("a book", "a podcast"),
    ("stay in", "go out"), ("chips", "mash"), ("summer", "winter"),
]
REASONS = [
    "it just feels right today", "you'll thank yourself later", "it's the bolder choice",
    "the other one can wait", "it'll make a better story", "you deserve a treat", "it's the easy win",
    "fortune favours it today", "it's what a sensible butler would advise", "the coin in my head landed that way",
]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(text or "").lower()).strip()


def _score(game: str, won: bool | None) -> dict:
    tally = state["scores"].setdefault(game, {"won": 0, "lost": 0, "drawn": 0})
    tally["won" if won else "drawn" if won is None else "lost"] += 1
    return tally


def score_text() -> str:
    if not state["scores"]:
        return "No games played yet this session."
    parts = []
    for game, t in state["scores"].items():
        drawn = f", {t['drawn']} drawn" if t["drawn"] else ""
        parts.append(f"{game}: {t['won']} won, {t['lost']} lost{drawn}")
    return "Scores this session. " + ". ".join(parts) + "."


# Trivia

async def trivia_question(http: httpx.AsyncClient, category: str = "", difficulty: str = "") -> str:
    params = {"amount": 1, "type": "multiple"}
    if category:
        if category not in TRIVIA_CATEGORIES:
            raise ValueError("I don't have that trivia category.")
        params["category"] = TRIVIA_CATEGORIES[category]
    if difficulty in ("easy", "medium", "hard"):
        params["difficulty"] = difficulty
    r = await http.get(TRIVIA_URL, params=params, timeout=10)
    r.raise_for_status()
    body = r.json()
    if body.get("response_code") != 0 or not body.get("results"):
        raise ValueError("The trivia service didn't send a question. Try again in a few seconds.")
    q = body["results"][0]
    correct = html.unescape(q["correct_answer"])
    options = [correct, *(html.unescape(a) for a in q["incorrect_answers"][:3])]
    rng.shuffle(options)
    state["trivia"] = {"question": html.unescape(q["question"]), "options": options, "correct": correct}
    choices = ". ".join(f"{LETTERS[i]}: {o}" for i, o in enumerate(options))
    return f"{html.unescape(q.get('category', 'Trivia'))}. {state['trivia']['question']} {choices}."


def _pick(options: list[str], answer: str) -> str | None:
    said = _norm(answer)
    if len(said) == 1 and said.upper() in LETTERS[:len(options)]:
        return options[LETTERS.index(said.upper())]
    exact = [o for o in options if _norm(o) == said]
    if exact:
        return exact[0]
    near = [o for o in options if said and (said in _norm(o) or _norm(o) in said)]
    return near[0] if len(near) == 1 else None


def trivia_answer(answer: str) -> str:
    q = state["trivia"]
    if not q:
        return "There's no trivia question waiting. Ask for one first."
    chosen = _pick(q["options"], answer)
    if chosen is None:
        return "I couldn't match that to one of the options. Say A, B, C or D."
    state["trivia"] = None
    right = chosen == q["correct"]
    t = _score("trivia", right)
    verdict = "Correct!" if right else f"Not quite. The answer was {q['correct']}."
    return f"{verdict} Trivia score: {t['won']} out of {t['won'] + t['lost']}."


def trivia_reveal() -> str:
    q = state["trivia"]
    if not q:
        return "There's no trivia question waiting."
    state["trivia"] = None
    _score("trivia", False)
    return f"The answer was {q['correct']}."


# Guess the number

def number_start() -> str:
    state["number"] = {"secret": rng.randint(1, 100), "guesses": 0}
    return "I'm thinking of a number between 1 and 100. What's your guess?"


def number_guess(answer: str) -> str:
    game = state["number"]
    if not game:
        return "We're not playing guess the number. Say start to begin."
    found = re.search(r"-?\d+", str(answer or ""))
    if not found:
        return "Say a number between 1 and 100."
    n = int(found.group())
    game["guesses"] += 1
    if n < game["secret"]:
        return f"Higher than {n}. That's {game['guesses']} guesses."
    if n > game["secret"]:
        return f"Lower than {n}. That's {game['guesses']} guesses."
    state["number"] = None
    _score("guess the number", True)
    tries = "first try!" if game["guesses"] == 1 else f"{game['guesses']} guesses."
    return f"Yes! It was {n}. You got it in {tries}"


def number_reveal() -> str:
    game = state["number"]
    if not game:
        return "We're not playing guess the number."
    state["number"] = None
    _score("guess the number", False)
    return f"The number was {game['secret']}."


# Rock, paper, scissors

def rps(answer: str) -> str:
    said = _norm(answer)
    move = next((m for m in MOVES if m in said or (said and m.startswith(said))), None)
    if not move:
        return "Say rock, paper or scissors."
    mine = rng.choice(MOVES)
    if mine == move:
        outcome, won = "It's a draw.", None
    elif BEATS[move] == mine:
        outcome, won = "You win!", True
    else:
        outcome, won = "I win!", False
    t = _score("rock paper scissors", won)
    return f"I chose {mine}. {outcome} Score: you {t['won']}, me {t['lost']}."


# Riddles

def riddle_start() -> str:
    current = state["riddle"]
    choices = [r for r in RIDDLES if r is not current] or RIDDLES
    state["riddle"] = rng.choice(choices)
    return state["riddle"][0]


def riddle_answer(answer: str) -> str:
    riddle = state["riddle"]
    if not riddle:
        return "There's no riddle waiting. Ask me for one."
    said = f" {_norm(answer)} "
    if any(f" {k}" in said for k in riddle[2]):
        state["riddle"] = None
        _score("riddles", True)
        return f"Correct, it's {riddle[1]}!"
    return "Not quite. Have another go, or ask me to reveal it."


def riddle_reveal() -> str:
    riddle = state["riddle"]
    if not riddle:
        return "There's no riddle waiting."
    state["riddle"] = None
    _score("riddles", False)
    return f"The answer is {riddle[1]}."


# Word scramble

def _shuffle(word: str) -> str:
    letters = list(word)
    for _ in range(10):
        rng.shuffle(letters)
        if "".join(letters) != word:
            break
    return "".join(letters)


def scramble_start() -> str:
    word, clue = rng.choice(SCRAMBLE_WORDS)
    mixed = _shuffle(word)
    state["scramble"] = {"word": word, "clue": clue, "hints": 0, "mixed": mixed}
    return f"Unscramble this {len(word)}-letter word: {', '.join(mixed.upper())}."


def scramble_answer(answer: str) -> str:
    game = state["scramble"]
    if not game:
        return "There's no scrambled word waiting. Ask for one."
    if _norm(answer).replace(" ", "") == game["word"]:
        state["scramble"] = None
        _score("word scramble", True)
        return f"Well done, it's {game['word']}!"
    return "Not that one. Try again, or ask for a hint."


def scramble_hint() -> str:
    game = state["scramble"]
    if not game:
        return "There's no scrambled word waiting."
    game["hints"] += 1
    if game["hints"] == 1:
        return f"Hint: {game['clue']}."
    shown = min(game["hints"] - 1, len(game["word"]) - 1)
    return f"Hint: it starts with {', '.join(game['word'][:shown].upper())}."


def scramble_reveal() -> str:
    game = state["scramble"]
    if not game:
        return "There's no scrambled word waiting."
    state["scramble"] = None
    _score("word scramble", False)
    return f"The word was {game['word']}."


GAMES = {
    "number": {"start": number_start, "answer": number_guess, "reveal": number_reveal},
    "riddle": {"start": riddle_start, "answer": riddle_answer, "reveal": riddle_reveal},
    "scramble": {"start": scramble_start, "answer": scramble_answer, "reveal": scramble_reveal,
                 "hint": scramble_hint},
}


async def play(args: dict, http: httpx.AsyncClient) -> str:
    game, action = args.get("game") or "", args.get("action") or "start"
    answer = str(args.get("answer") or "")
    if action == "score":
        return score_text()
    if game == "rps":
        return rps(answer)
    if game == "trivia":
        if action == "answer":
            return trivia_answer(answer)
        if action == "reveal":
            return trivia_reveal()
        return await trivia_question(http, args.get("category") or "", args.get("difficulty") or "")
    handlers = GAMES.get(game)
    if not handlers:
        return "Which game? Trivia, guess the number, rock paper scissors, riddles or word scramble."
    handler = handlers.get(action)
    if not handler:
        return "There are no hints for that game." if action == "hint" else "I can't do that in this game."
    return handler(answer) if action == "answer" else handler()


# Fun one-offs

def next_joke() -> str:
    left = [j for j in JOKES if j not in state["jokes_told"]]
    if not left:
        state["jokes_told"].clear()
        left = JOKES
    joke = rng.choice(left)
    state["jokes_told"].add(joke)
    return joke


def this_or_that(options: list[str]) -> str:
    options = [re.sub(r"\s+", " ", str(o)).strip()[:80] for o in options or [] if str(o).strip()]
    if len(options) < 2:
        options = list(rng.choice(THIS_OR_THAT))
    return f"Go with {rng.choice(options)}, because {rng.choice(REASONS)}."


def fun(args: dict) -> str:
    kind = args.get("kind")
    if kind == "eight_ball":
        return f"The magic 8-ball says: {rng.choice(EIGHT_BALL)}"
    if kind == "would_you_rather":
        return f"Would you rather {rng.choice(WOULD_YOU_RATHER)}?"
    if kind == "quote":
        text, who = rng.choice(QUOTES)
        return f"{text} That's {who}."
    if kind == "fact":
        return rng.choice(FACTS)
    if kind == "this_or_that":
        return this_or_that(args.get("options") or [])
    return next_joke()


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [
        {
            "name": "play_game",
            "description": "Games with a running score this session. game: 'trivia' (multiple choice from the "
                           "internet; optional category and difficulty), 'number' (guess 1 to 100, higher or "
                           "lower), 'rps' (rock paper scissors: pass the user's move as answer), 'riddle', "
                           "'scramble' (unscramble a word; hints). action: 'start' a new round, 'answer' with "
                           "the user's answer, 'hint', 'reveal' (give up), 'score' (all scores).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "game": {"type": "string", "enum": ["trivia", "number", "rps", "riddle", "scramble"]},
                    "action": {"type": "string", "enum": ["start", "answer", "hint", "reveal", "score"]},
                    "answer": text,
                    "category": {"type": "string", "enum": list(TRIVIA_CATEGORIES)},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "fun",
            "description": "Something fun to say. kind: 'joke' (clean dad joke, no repeats), 'eight_ball' "
                           "(magic 8-ball answer to a yes/no question), 'would_you_rather', 'quote' "
                           "(motivational), 'fact' (fun fact), 'this_or_that' (pick one of options, with a "
                           "reason; random pair if none given).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["joke", "eight_ball", "would_you_rather", "quote",
                                                         "fact", "this_or_that"]},
                    "options": {"type": "array", "items": text, "description": "Choices for this_or_that."},
                },
                "required": ["kind"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"play_game", "fun"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> str:
    if name == "play_game":
        return await play(args, http)
    return fun(args)
