"""Built-in content for the creator-ideas abilities: hook templates, script outlines, CTAs, word lists and safe zones.

Templates use {topic}, {number}, {thing} and {year}; the fill-in helper swaps them for the user's own words.
"""

HOOKS = {
    "question": [
        "Have you ever wondered why {topic}?",
        "What if everything you knew about {topic} was wrong?",
        "Why does nobody explain {topic} like this?",
        "Did you know {topic} works the opposite way?",
        "Ever noticed how {topic} always happens at the worst time?",
        "What would you do if {topic} happened tomorrow?",
        "Is {topic} really what it looks like?",
        "Why do people who {thing} never talk about {topic}?",
        "Can you spot the {thing} hiding in {topic}?",
        "What does {topic} say about you?",
    ],
    "shock stat": [
        "{number} out of 10 people get {topic} wrong.",
        "Only {number}% of people know this about {topic}.",
        "{number} years ago, {topic} looked completely different.",
        "In {number} seconds you will never see {topic} the same way.",
        "{number} people a day fall for {topic}.",
        "The average person spends {number} hours on {topic}, and hardly notices.",
        "{topic} is {number} times more common than you think.",
        "One tiny {thing} changes {number}% of {topic}.",
        "Researchers found {number} strange facts about {topic}.",
        "It takes just {number} minutes to change {topic}.",
    ],
    "story": [
        "I never expected {topic} to end like this.",
        "It started with one {thing}, and then {topic} happened.",
        "Nobody believed her when she said {topic}.",
        "He kept {topic} a secret for {number} years.",
        "The night {topic} happened, everything changed.",
        "This is the story of {topic} that they tried to hide.",
        "She found a {thing} that explained {topic}.",
        "One small choice about {topic} ruined everything.",
        "I thought {topic} was a joke, until this.",
        "Here is what really happened with {topic}.",
    ],
    "POV": [
        "POV: you finally understand {topic}.",
        "POV: you are the {thing} in {topic}.",
        "POV: {topic} just got personal.",
        "POV: it is {year} and {topic} is everywhere.",
        "POV: you are the only one who noticed {topic}.",
        "POV: your {thing} explains {topic} to you.",
        "POV: you wake up and {topic} has changed.",
        "POV: someone tells you the truth about {topic}.",
        "POV: you are about to learn {topic} the hard way.",
        "POV: you found out why {topic} happens.",
    ],
    "list": [
        "{number} signs of {topic} you should not ignore.",
        "{number} things about {topic} that will surprise you.",
        "{number} {thing}s that explain {topic}.",
        "Top {number} mistakes people make with {topic}.",
        "{number} secrets about {topic} in under a minute.",
        "{number} habits that show {topic}.",
        "{number} facts about {topic}, ranked from strange to strangest.",
        "{number} reasons {topic} is not what you think.",
        "{number} quick tests for {topic}.",
        "{number} {thing}s people forget about {topic}.",
    ],
    "nobody talks about": [
        "Nobody talks about this side of {topic}.",
        "The part of {topic} nobody warns you about.",
        "What they don't tell you about {topic}.",
        "Nobody talks about how {topic} changes your {thing}.",
        "The truth about {topic} that most people skip.",
        "Nobody is telling you this about {topic}.",
        "Here is the dark side of {topic} that nobody mentions.",
        "The {thing} about {topic} that everyone ignores.",
        "Things about {topic} you only learn too late.",
        "Nobody talks about what happens after {topic}.",
    ],
}

# Outlines: (beat, share of the total time, what to do). Shares add up to 1.
OUTLINES = {
    "story_arc": ("Story arc, one minute", [
        ("Hook", 0.05, "One line that makes them stay. Start mid-action or with the strangest fact."),
        ("Setup", 0.15, "Who, where, and what was normal."),
        ("Rising", 0.30, "Things get worse or stranger. One new detail every few seconds."),
        ("Twist", 0.25, "The turn nobody saw coming."),
        ("Payoff", 0.17, "What it meant, what happened next."),
        ("Call to action", 0.08, "Ask for a follow, comment or part 2."),
    ]),
    "listicle": ("Listicle", [
        ("Hook", 0.08, "Promise the list and the number: 'Five signs of...'"),
        ("Item 1", 0.16, "Short and clear. Save a good one for last."),
        ("Item 2", 0.16, "Keep the same rhythm as item 1."),
        ("Item 3", 0.16, "Add a small twist or example."),
        ("Item 4", 0.16, "Change the pace a little."),
        ("Item 5", 0.20, "The best one, with a reason to comment."),
        ("Call to action", 0.08, "Ask which one they relate to."),
    ]),
    "myth_vs_fact": ("Myth vs fact", [
        ("Hook", 0.08, "Say the myth out loud as if it is true."),
        ("The myth", 0.17, "Why everyone believes it."),
        ("The turn", 0.10, "'But actually...'"),
        ("The fact", 0.30, "The real answer with one clear proof or example."),
        ("Why it matters", 0.20, "What changes for the viewer."),
        ("Call to action", 0.15, "Ask for the next myth they want busted."),
    ]),
    "part_series": ("Part 1 of 5", [
        ("Hook", 0.06, "Name the series and the part: 'Part 1 of 5.'"),
        ("Recap", 0.10, "One line for people who missed earlier parts (skip in part 1)."),
        ("This part's story", 0.60, "One clear chunk with a small twist."),
        ("Cliffhanger", 0.14, "End on the question the next part answers."),
        ("Call to action", 0.10, "Follow for part 2."),
    ]),
    "did_you_know": ("Did you know", [
        ("Hook", 0.10, "The surprising fact in one line."),
        ("Explain", 0.45, "Why it is true, in plain words."),
        ("Second fact", 0.25, "A related fact that builds on the first."),
        ("Call to action", 0.20, "Ask if they knew it."),
    ]),
}

CTAS = {
    "follow": ["Follow for part 2.", "Follow for more like this.", "Follow, you will want the next one.",
               "Follow so you do not miss the ending."],
    "comment": ["Comment your answer below.", "Which one are you? Tell me in the comments.",
                "Comment the number you got.", "Tell me what to cover next."],
    "share": ["Send this to someone who needs it.", "Share this with a friend who would get it.",
              "Tag someone this reminds you of."],
    "save": ["Save this for later.", "Save this so you remember it.", "Bookmark this one."],
    "series": ["This is part {number}. Follow for the rest.", "Part {number} is coming tomorrow.",
               "Want part {number}? Say so in the comments."],
}

CURIOSITY = {"secret", "hidden", "nobody", "never", "truth", "why", "actually", "really", "weird", "strange", "wrong",
             "mistake", "warning", "shocking", "surprising", "reason", "revealed", "changed", "real", "dark",
             "creepy", "unexpected", "stop", "before", "only", "except", "finally", "quietly", "secretly"}
WEAK_OPENERS = {"so", "hey", "hi", "hello", "um", "today", "okay", "ok", "welcome", "in", "this", "i", "guys"}

RISKY = {
    "violence and gore": (["kill", "murder", "blood", "gore", "shoot", "stab", "dead body"],
                          "Describe what happened without graphic detail, e.g. 'attacked' or 'lost his life'."),
    "self-harm and suicide": (["suicide", "self harm", "self-harm", "cutting"],
                              "Avoid these topics or handle them with care and support links; do not use evasive spellings."),
    "drugs and alcohol": (["cocaine", "heroin", "weed", "drugs", "high on"],
                          "Talk about it as history or a warning rather than showing use or how to get it."),
    "weapons": (["gun", "bomb", "weapon", "firearm"], "Keep it educational or historical, never how to make or use one."),
    "hate and harassment": (["hate", "slur", "stupid people"], "Criticise ideas or actions, never groups of people."),
    "adult content": (["nude", "sexual", "porn", "explicit"], "Keep it family-friendly to stay eligible for monetising."),
    "dangerous acts": (["challenge", "don't try this", "stunt"], "Add a clear safety warning or leave it out."),
    "medical and health claims": (["cure", "cures", "miracle", "detox", "heals"],
                                  "Say 'may help' and point to a doctor; never promise a cure."),
    "money promises": (["guaranteed", "get rich", "passive income", "easy money", "risk-free", "risk free"],
                       "Never promise income. Be honest that results vary and can be zero."),
    "misleading or scary": (["conspiracy", "hoax", "they don't want you to know", "fake news"],
                            "Label speculation as a theory or story, and do not present made-up events as real news."),
    "swearing": (["fuck", "shit", "damn", "bitch"], "Heavy swearing in the first seconds can limit reach and ads."),
    "copyright": (["full song", "movie clip", "copyrighted"], "Use royalty-free or in-app licensed sounds and your own visuals."),
}

# Fractions of the phone screen kept clear of TikTok's buttons and captions: top, bottom, left, right.
SAFE_ZONE = {"top": 0.10, "bottom": 0.22, "left": 0.05, "right": 0.16}
