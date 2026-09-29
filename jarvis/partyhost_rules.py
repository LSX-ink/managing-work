"""Party host: rules for classic party games, ideas for what to play, and a running order for the evening.

Everything is built in; nothing goes online.
"""

import random

import homestore as hs
import screen
from config import Settings

RNG = random.Random()
ACTIONS = ("rules", "list_games", "ideas", "plan_night")

RULES: dict[str, str] = {
    "charades": "Split into two teams. One player picks a card and acts it out without speaking or pointing at "
                "objects, while their team guesses before the timer ends. Agreed signs: hold up fingers for the number "
                "of words, tap your arm for 'sounds like'. Score a point for a correct guess; take turns.",
    "pictionary": "Teams take turns. The artist sees a word and draws it for their team, with no letters, numbers "
                  "or speaking. Guess it before the timer runs out to score a point. If the other team can guess it "
                  "in the last few seconds they can steal.",
    "articulate": "Teams take turns. The describer explains as many words as they can on a card in the time, "
                  "using any words except the ones on the card. Skip a word if you're stuck. Score a point per word "
                  "guessed. Some versions use categories per row.",
    "taboo": "Describe the word at the top of the card without saying it or any of the forbidden words. Your team "
             "guesses. A watcher from the other team buzzes you if you say a forbidden word, and you lose a point.",
    "heads_up": "One player holds a word to their forehead, without looking. Everyone else gives clues (no saying "
                "the word). Tilt down for correct, up to pass. Get as many as you can before the timer ends.",
    "two_truths": "Each player tells three statements about themselves: two true and one a lie. The group "
                  "discusses and votes on the lie. Fooling more people scores more points.",
    "musical_chairs": "Put out one fewer chair than players, in a line or circle. While the music plays, everyone "
                      "walks around. When it stops, everyone sits. The one left standing is out, a chair is taken "
                      "away, and play goes on until one player wins.",
    "musical_statues": "Everyone dances while the music plays. When it stops, everyone freezes. Anyone seen moving "
                       "is out. The last dancer still in wins. It's the same idea as musical chairs but with no "
                       "chairs to squabble over.",
    "pass_the_parcel": "Wrap a prize in many layers of paper. Players sit in a circle and pass the parcel while music "
                       "plays. When it stops, the player holding it unwraps one layer. The one who unwraps the last "
                       "layer wins the prize. Tuck a small sweet in each layer so everyone gets something.",
    "sardines": "Hide and seek in reverse. One person hides. Whoever finds them squeezes in beside them, silently. "
                "Play on until only one seeker is left, who loses and hides next.",
    "murder_in_the_dark": "Everyone draws a slip; one says 'murderer' and one 'detective'. In the dark, the murderer "
                          "taps a victim, who counts to five and screams. Lights on: the detective has three guesses "
                          "to spot the murderer. Family-friendly version: use 'the thief' who steals a sweet.",
    "wink_murder": "Everyone sits in a circle with eyes down while slips are passed; the murderer gets a marked "
                   "one. The murderer winks at people to 'kill' them, who then play dead after a few seconds. "
                   "The rest try to guess who the winker is before too many are gone.",
    "chinese_whispers": "Players sit in a line. The first whispers a phrase to the next, and so on, only once and "
                        "with no repeats. The last person says what they heard out loud, and the group compares it "
                        "to the original. Often called telephone.",
    "i_spy": "One player says 'I spy with my little eye something beginning with' and a letter. Others guess objects "
             "they can see. The one who guesses right spies next.",
    "twenty_questions": "One player thinks of an object, person or place. The others can ask up to twenty yes-or-no "
                        "questions to work it out. If they haven't guessed by the end, the thinker wins.",
    "simon_says": "The leader gives commands like 'Simon says touch your nose'. Players only obey commands that "
                  "start with 'Simon says'. Anyone who obeys a command without it is out. The last player wins.",
    "consequences": "Each player has a sheet and writes a girl's name, folds it over, and passes it on; then a boy's "
                    "name, where they met, what she said, what he said, what they did and what the consequence was. "
                    "Unfold and read the silly stories aloud.",
    "hot_potato": "Sit in a circle and pass an object round as fast as you can while music plays. When it stops, "
                  "whoever holds it is out. Keep going until one player is left.",
    "fizz_buzz": "Count round the circle from one. Say 'fizz' for multiples of three and 'buzz' for multiples of "
                 "five, and 'fizz buzz' for both. A slip or hesitation puts you out, or gives you a forfeit.",
    "werewolf": "A narrator secretly gives out roles: a few werewolves and the rest villagers. Each night the wolves "
                "quietly choose a villager to remove. Each day everyone discusses and votes out a suspect. "
                "Villagers win if they remove all the wolves; wolves win if they outnumber villagers.",
    "bingo": "Each player has a ticket of 15 numbers (UK 90-ball). The caller draws numbers 1 to 90 and reads them "
             "out. Mark off any you have. A line is one row complete, then two lines, then a full house (all 15). "
             "Shout 'house!' or 'bingo!' when you win.",
    "snap": "Deal the cards evenly, face down. Take turns to flip the top card onto a pile in the middle. When two "
            "matching cards appear in a row, the first to shout 'snap!' takes the pile. Win by holding all cards.",
    "old_maid": "Remove one queen so one is left without a pair. Deal all the cards. Players pair up and discard "
                "matches, then take turns drawing one card unseen from the neighbour. Whoever ends up holding the "
                "unpaired queen is the Old Maid and loses.",
    "go_fish": "Each player gets seven cards. On your turn, ask another player for a rank you hold ('Any sevens?'). "
               "If they have one, they give it to you and you go again; if not, 'Go fish' and draw from the pile. "
               "Collect sets of four. Most sets wins.",
    "cheat": "Deal all the cards. Players take turns putting cards face down on a central pile, saying what "
             "they are (starting with aces, then twos, and so on). Anyone can call 'Cheat!' if they think you're "
             "lying. If you were lying, you take the pile; if not, the caller does. First to get rid of all cards wins.",
    "dominoes": "Each player takes seven tiles. The highest double starts. On your turn, place a tile with a matching "
                "end against one on the table; if you can't, draw or pass. First to play all their tiles wins.",
    "scattergories": "Roll or pick a letter and a list of categories. Everyone writes a word for each category that "
                     "starts with that letter before the timer runs out. Unique answers score a point; answers two "
                     "players share score nothing.",
    "quiz_night": "Teams write answers to each question and hand the sheet in at the end of the round, or the "
                  "host lets the first buzzer press answer. One point per correct answer. Add up the rounds and "
                  "break a tie with a closest-number question.",
}
ALIASES = {"musical chairs": "musical_chairs", "musical statues": "musical_statues", "pass the parcel": "pass_the_parcel",
           "murder in the dark": "murder_in_the_dark", "wink murder": "wink_murder", "chinese whispers": "chinese_whispers",
           "telephone": "chinese_whispers", "i spy": "i_spy", "20 questions": "twenty_questions",
           "twenty questions": "twenty_questions", "hot potato": "hot_potato", "fizz buzz": "fizz_buzz",
           "mafia": "werewolf", "heads up": "heads_up", "two truths and a lie": "two_truths", "go fish": "go_fish",
           "quiz": "quiz_night", "pub quiz": "quiz_night", "articulate": "articulate", "cheat": "cheat",
           "i doubt it": "cheat", "bluff": "cheat", "snap": "snap", "simon says": "simon_says"}

# (name, min players, max players, minutes, kids ok, lively, what you need)
GAMES: list[tuple[str, int, int, int, bool, bool, str]] = [
    ("Charades", 4, 20, 30, True, True, "Nothing (or Alfred's cards)"),
    ("Pictionary", 4, 16, 30, True, False, "Paper and pens"),
    ("Articulate or Taboo", 4, 16, 30, True, False, "Alfred's cards"),
    ("Heads Up", 3, 12, 15, True, True, "Alfred's deck"),
    ("Quiz night", 4, 30, 60, True, False, "Paper and pens, Alfred as quizmaster"),
    ("Two truths and a lie", 4, 15, 20, False, False, "Nothing"),
    ("Truth or dare", 3, 12, 20, True, True, "Nothing"),
    ("Scattergories", 3, 12, 25, True, False, "Paper and pens"),
    ("Musical chairs", 5, 20, 15, True, True, "Chairs and music"),
    ("Musical statues", 4, 25, 10, True, True, "Music"),
    ("Pass the parcel", 5, 20, 20, True, False, "A wrapped prize and music"),
    ("Sardines", 5, 20, 30, True, True, "A house with hiding places"),
    ("Murder in the dark", 6, 20, 30, False, False, "Cards and a dark room"),
    ("Chinese whispers", 5, 20, 10, True, False, "Nothing"),
    ("I spy", 2, 8, 10, True, False, "Nothing"),
    ("Twenty questions", 2, 10, 15, True, False, "Nothing"),
    ("Simon says", 3, 20, 10, True, True, "Nothing"),
    ("Consequences", 4, 15, 20, True, False, "Paper and pens"),
    ("Bingo", 3, 40, 30, True, False, "Alfred's bingo caller and tickets"),
    ("Werewolf", 6, 20, 30, False, False, "Cards or slips"),
    ("Snap", 2, 6, 10, True, True, "A pack of cards"),
    ("Go Fish", 2, 6, 15, True, False, "A pack of cards"),
    ("Cheat", 3, 8, 20, True, True, "A pack of cards"),
    ("Dominoes", 2, 4, 20, True, False, "A set of dominoes"),
    ("Secret Santa", 3, 40, 10, False, False, "Alfred's draw"),
    ("Fizz Buzz", 3, 12, 10, True, False, "Nothing"),
]


def _game_key(name) -> str:
    text = hs.clean(name, 60).lower().replace("-", " ").replace("'", "")
    if text in ALIASES:
        return ALIASES[text]
    key = text.replace(" ", "_")
    if key in RULES:
        return key
    for k in RULES:
        if key and (key in k or k in key):
            return k
    raise ValueError(f"I don't have rules for {text or 'that'}. Ask me to list the games.")


def rules(a: dict) -> screen.Shown:
    key = _game_key(a.get("game"))
    title = key.replace("_", " ").capitalize()
    return screen.Shown(f"{title}. {RULES[key]}", screen.card("text", f"How to play: {title}", text=RULES[key]))


def list_games() -> screen.Shown:
    items = [{"label": k.replace("_", " ").capitalize(), "say": f"What are the rules for {k.replace('_', ' ')}?"}
             for k in RULES]
    return screen.Shown(f"I know the rules to {len(RULES)} party games. Tap one to hear how to play.",
                        screen.card("list", "Party game rules", items=items))


def ideas(a: dict) -> screen.Shown:
    players = int(a.get("players") or 0)
    minutes = int(a.get("minutes") or 0)
    found = [g for g in GAMES
             if (not players or g[1] <= players <= g[2]) and (not minutes or g[3] <= minutes)
             and (not a.get("kids") or g[4]) and (a.get("energy") not in ("lively", "calm") or g[5] == (a["energy"] == "lively"))]
    if not found:
        raise ValueError("Nothing fits all that. Try fewer conditions.")
    RNG.shuffle(found)
    rows = [[g[0], f"{g[1]}-{g[2]}", f"{g[3]} min", "lively" if g[5] else "calm", g[6]] for g in found[:8]]
    said = f"How about {found[0][0]}" + (f" or {found[1][0]}?" if len(found) > 1 else "?")
    return screen.Shown(said, screen.card("table", "Game ideas", columns=["Game", "Players", "Time", "Energy", "You need"],
                                          rows=rows, buttons=[{"label": "More ideas", "say": "Give me more party game ideas."}]))


def plan_night(a: dict) -> screen.Shown:
    hours = min(6.0, max(1.0, float(a.get("hours") or 3)))
    players = int(a.get("players") or 6)
    kids = bool(a.get("kids"))
    pool = [g for g in GAMES if g[1] <= players <= g[2] and (not kids or g[4])]
    calm = [g for g in pool if not g[5] and g[0] != "Secret Santa"] or pool
    lively = [g for g in pool if g[5]] or pool
    RNG.shuffle(calm)
    RNG.shuffle(lively)
    slots = max(3, int(hours * 60 // 30))
    plan = ["Welcome and icebreaker questions"]
    for i in range(slots - 2):
        source = lively if i % 2 else calm
        plan.append(source[(i // 2) % len(source)][0])
    plan.append("Winners, prizes and a final chat")
    step = hours * 60 / len(plan)
    items = [{"label": f"{int(i * step)} min: {p}"} for i, p in enumerate(plan)]
    return screen.Shown(f"A {hours:g}-hour night for {players}: {len(plan)} stops, from {plan[1]} to {plan[-2]}.",
                        screen.card("list", "Game night running order", "partyhost-plan", items=items,
                                    buttons=[{"label": "Plan again", "say": "Plan the game night again."}]))


# ---- Tool ------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "party_rules",
        "description": "Party-game help. action: 'rules' (how to play a classic: charades, pictionary, articulate, "
                       "taboo, musical chairs, pass the parcel, sardines, murder in the dark, Chinese whispers, "
                       "twenty questions, Simon says, consequences, bingo, snap, old maid, go fish, cheat, dominoes, "
                       "werewolf and more), 'list_games', 'ideas' (what to play: players, minutes, kids, energy "
                       "lively or calm) or 'plan_night' (a running order for the evening: hours, players, kids).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "game": {"type": "string"},
                "players": {"type": "integer"}, "minutes": {"type": "integer"}, "hours": {"type": "number"},
                "kids": {"type": "boolean", "description": "Only games children can play."},
                "energy": {"type": "string", "enum": ["lively", "calm", "any"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"party_rules"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "rules":
        return rules(args)
    if action == "list_games":
        return list_games()
    if action == "ideas":
        return ideas(args)
    if action == "plan_night":
        return plan_night(args)
    raise ValueError(f"I don't know the party action {action}.")
