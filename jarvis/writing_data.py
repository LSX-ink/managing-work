"""Local word lists for the writing studio: 100 prompts by genre, name parts by style, poem forms and song shapes."""

PROMPTS = {
    "fantasy": [
        "A blacksmith forges a sword that refuses to be used for anything but defence.",
        "The last dragon applies for a job at the village library.",
        "Every lie told in the kingdom turns into a moth; the palace is full of them.",
        "A map redraws itself each night, and one road now leads to your front door.",
        "An apprentice wizard accidentally swaps voices with the family cat.",
        "The river spirit wants its stolen stone back before the spring flood.",
        "A girl inherits a key that opens any door but only once.",
        "The king's shadow walks off and starts ruling a neighbouring country.",
        "Seeds from a witch's garden grow into whatever you were thinking when you planted them.",
        "A knight is sent to rescue a princess who has built a very comfortable life in the tower.",
    ],
    "sci-fi": [
        "The colony ship's AI starts writing poems in the maintenance logs.",
        "A time traveller can only go back ten minutes, but as often as they like.",
        "Earth receives a message from space: an apology.",
        "Memories can be sold; someone buys your worst day at a very high price.",
        "The last human on a space station trains the robots to tell jokes.",
        "A delivery drone falls in love with the one house it always gets wrong.",
        "Gravity on the moon base switches off every Tuesday at noon.",
        "A clone meets the original and neither can prove which is which.",
        "Your phone starts predicting the news a day early.",
        "Terraformers find someone has already planted a garden on Mars.",
    ],
    "mystery": [
        "A locked room, a missing violin and a parrot that won't stop humming.",
        "Every item in the lost property office belongs to the same person.",
        "The village's best baker is found asleep in the church bell tower, with no memory of climbing it.",
        "A detective receives a postcard from herself, dated next week.",
        "Someone has been returning stolen library books, forty years late.",
        "A crossword in the local paper contains a confession.",
        "The lighthouse keeper insists the light was on the night the ship ran aground.",
        "A house sale falls through because the attic has a room that isn't on the plans.",
        "Two strangers turn up at a funeral, each claiming to be the only child.",
        "A cold case reopens when the victim's dog finds its way home.",
    ],
    "horror": [
        "The new baby monitor picks up a second voice.",
        "Every photograph taken in the house shows one more chair at the table.",
        "A village holds its annual festival, and this year you're the guest of honour.",
        "The motorway services are open all night, but the staff never blink.",
        "A lift in an old hotel has a button for a floor that doesn't exist.",
        "Your reflection is half a second slow, and getting slower.",
        "The fog comes in off the sea and the church bells ring by themselves.",
        "A doll left on the doorstep comes with a note: 'She missed you.'",
        "The last train home stops at a station that closed in 1962.",
        "Someone has been leaving footprints in the snow, leading into your house, not out.",
    ],
    "romance": [
        "Two rival bakers are forced to share a stall at the Christmas market.",
        "A wrong-number text turns into a year of messages between strangers.",
        "Wedding planners who fell out years ago must plan the same wedding.",
        "A love letter is found inside a second-hand book, and the reader goes looking for its writer.",
        "Two people keep meeting at the same bus stop, in the rain, for a year.",
        "A tour guide falls for the one tourist who hates everything about the city.",
        "Old friends make a pact to marry at forty if they're both single; the birthday is next week.",
        "A florist keeps receiving orders for flowers for the same person, from different senders.",
        "Neighbours communicate only through notes on the shared bins.",
        "A translator falls in love with the voice of the author whose book they're translating.",
    ],
    "literary": [
        "A family clears out their late grandmother's house and finds she had a second life.",
        "Write a day in the life of a lollipop lady on her last day before retiring.",
        "Two brothers who haven't spoken in ten years share a long car journey.",
        "A woman returns to the seaside town she left at eighteen.",
        "A man writes letters to the house he grew up in.",
        "The story of a single coat passed through five owners.",
        "A night-shift nurse and a patient who can't sleep trade stories until dawn.",
        "A teenager works out that their parents are just people.",
        "Write about a kitchen table and everything that has happened around it.",
        "An allotment, three neighbours, and a disagreement about a fence.",
    ],
    "children": [
        "A small cloud is scared of raining.",
        "The school hamster runs for class president.",
        "A sock goes looking for its missing partner inside the washing machine.",
        "A child finds a door at the bottom of the garden, just big enough for a fox.",
        "The moon takes a night off and the stars have to cover for it.",
        "A dinosaur moves in next door and wants to join the football team.",
        "A lost teddy bear has an adventure getting home from the seaside.",
        "A little dragon can only breathe bubbles instead of fire.",
        "A robot learns to make its first friend.",
        "The alphabet letters go on strike and the letter E is in charge.",
    ],
    "poetry": [
        "Write a poem about the first cup of tea of the morning.",
        "A poem from the point of view of an umbrella left on a train.",
        "Write about a smell that takes you straight back to childhood.",
        "A poem that begins with 'I never told you'.",
        "Write about the sea in exactly fourteen lines.",
        "A poem addressed to a street light.",
        "Write about a hand you have held.",
        "A haiku sequence following one day of the seasons.",
        "A poem about a word in another language that English doesn't have.",
        "Write about the moment just before sleep.",
    ],
    "songs": [
        "A song about driving home at 2am with the windows down.",
        "A break-up song from the point of view of the house they shared.",
        "A chorus that repeats a phone number you'll never ring again.",
        "A song about a small town everybody leaves.",
        "An anthem for people who work night shifts.",
        "A love song that never uses the word love.",
        "A song about your grandparents' first dance.",
        "A song for the last day of summer.",
        "A song about starting again after everything went wrong.",
        "A song told as a series of voicemails.",
    ],
    "blog": [
        "Five things you learned the hard way this year.",
        "A beginner's guide to a hobby you love.",
        "What your job looks like on an ordinary Tuesday.",
        "The best cheap day out near you.",
        "A recipe with the story behind it.",
        "Something you changed your mind about, and why.",
        "The tools and apps you use every day.",
        "A review of the last book that kept you up at night.",
        "Lessons from a failure.",
        "Letter to yourself ten years ago.",
    ],
}

NAME_PARTS = {
    "fantasy": {
        "start": ["Ae", "Bra", "Cal", "Dra", "El", "Fen", "Gal", "Is", "Kael", "Lor", "Mor", "Nym", "Or", "Syl",
                  "Thal", "Vey", "Zar", "Ery", "Il", "Rho", "Ara", "Bel", "Cor", "Eo", "Fae"],
        "middle": ["a", "e", "i", "o", "ae", "ia", "an", "el", "", "", ""],
        "end": ["dor", "wen", "ric", "lith", "mir", "ra", "th", "nor", "iel", "wyn", "ros", "dan", "eth", "ys",
                "ion", "is", "ara", "orn"],
    },
    "sci-fi": {
        "start": ["Zy", "Kor", "Vex", "Ax", "Tal", "Nex", "Qua", "Ry", "Orb", "Xan", "Cy", "Dex", "Jax", "Ion", "Sol",
                  "Vor", "Kai", "Tyr", "Ze", "Lux"],
        "middle": ["a", "o", "i", "y", "", "", "-"],
        "end": ["on", "ar", "is", "ex", "ix", "ara", "oth", "us", "ion", "yx", "tron", "ris", "ek", "7", "9", "ax"],
    },
    "english": {
        "first": ["Alice", "Arthur", "Beatrice", "Charlie", "Daisy", "Edward", "Eleanor", "Florence", "George",
                  "Harriet", "Henry", "Isla", "Jack", "Lily", "Margaret", "Oliver", "Poppy", "Rosie", "Thomas",
                  "William", "Amelia", "Freddie", "Grace", "Harry", "Ivy", "Mabel", "Noah", "Ruby", "Stanley", "Wilf"],
        "last": ["Ashworth", "Barnes", "Cartwright", "Davies", "Fletcher", "Hartley", "Hughes", "Kendall",
                 "Marsh", "Oakley", "Pemberton", "Radcliffe", "Shaw", "Thornton", "Whitmore", "Brooks", "Clarke",
                 "Holloway", "Lambert", "Wilde"],
    },
    "places": {
        "start": ["Ash", "Brook", "Stan", "Wick", "Mar", "Hol", "Ald", "Bex", "Carl", "Dun", "Elm", "Fair", "Gold",
                  "Har", "Kings", "Lang", "Mill", "Nor", "Oak", "Red", "Salt", "Thorn", "Wes", "Whit", "Crow"],
        "end": ["ford", "ton", "by", "ham", "wick", "bury", "field", "stead", "mouth", "thorpe", "ley", "cester",
                "dale", "well", "combe", "bridge", "minster", "hurst", "wold", "moor"],
    },
}

# rules, lines, syllables per line (None = free), tolerance in syllables, rhyme scheme
POEM_FORMS = {
    "haiku": {"rules": "Three lines of 5, 7 and 5 syllables. Traditionally about nature or a season, with a turn "
                       "or contrast between two images. No rhyme needed.", "syllables": [5, 7, 5], "tolerance": 0,
              "rhyme": "none"},
    "senryu": {"rules": "Shaped like a haiku (5, 7, 5 syllables) but about people and their foibles, often wry or "
                        "funny.", "syllables": [5, 7, 5], "tolerance": 0, "rhyme": "none"},
    "tanka": {"rules": "Five lines of 5, 7, 5, 7 and 7 syllables: a haiku with two longer lines that turn "
                       "towards feeling.", "syllables": [5, 7, 5, 7, 7], "tolerance": 0, "rhyme": "none"},
    "cinquain": {"rules": "Five lines of 2, 4, 6, 8 and 2 syllables (Adelaide Crapsey's form), building up then "
                          "snapping shut on the last line.", "syllables": [2, 4, 6, 8, 2], "tolerance": 0,
                 "rhyme": "none"},
    "limerick": {"rules": "Five lines rhyming AABBA with a bouncy rhythm. Lines 1, 2 and 5 are long (about 8 or 9 "
                          "syllables, three beats); lines 3 and 4 are short (about 5 or 6, two beats). Usually "
                          "comic, with a punchline at the end.", "syllables": [8, 8, 5, 5, 8], "tolerance": 1,
                 "rhyme": "AABBA"},
    "sonnet": {"rules": "Fourteen lines of iambic pentameter (about 10 syllables, da-DUM five times). The "
                        "Shakespearean sonnet rhymes ABAB CDCD EFEF GG with a twist in the final couplet; the "
                        "Petrarchan sonnet is an octave ABBAABBA and a sestet CDECDE, with a turn at line 9.",
               "syllables": [10] * 14, "tolerance": 1, "rhyme": "ABAB CDCD EFEF GG"},
    "villanelle": {"rules": "Nineteen lines: five tercets and a closing quatrain, on only two rhymes (ABA). Line 1 "
                            "repeats as lines 6, 12 and 18; line 3 repeats as lines 9, 15 and 19. Think 'Do not "
                            "go gentle into that good night'.", "syllables": None, "tolerance": 0,
                   "rhyme": "ABA ABA ABA ABA ABA ABAA"},
    "ballad": {"rules": "A story told in quatrains, usually alternating lines of four and three beats, rhyming "
                        "ABCB or ABAB, often with a refrain.", "syllables": [8, 6, 8, 6], "tolerance": 1,
               "rhyme": "ABCB"},
    "couplet": {"rules": "Two lines that rhyme and usually share a metre, making one complete thought.",
                "syllables": None, "tolerance": 0, "rhyme": "AA"},
    "acrostic": {"rules": "The first letters of the lines spell a word or name read downwards.",
                 "syllables": None, "tolerance": 0, "rhyme": "none"},
    "free verse": {"rules": "No fixed metre or rhyme; the shape comes from line breaks, rhythm and images.",
                   "syllables": None, "tolerance": 0, "rhyme": "none"},
    "ode": {"rules": "A poem of praise addressed to a person, thing or idea, in formal stanzas, often "
                     "celebratory and full of feeling.", "syllables": None, "tolerance": 0, "rhyme": "varies"},
    "sestina": {"rules": "Six stanzas of six lines plus a three-line envoi. The same six end-words rotate in a "
                         "fixed order (ABCDEF, FAEBDC, CFDABE...), all appearing in the envoi.",
                "syllables": None, "tolerance": 0, "rhyme": "repeated end-words"},
    "ghazal": {"rules": "Five or more couplets, each complete in itself. Both lines of the first couplet end "
                        "with the same refrain word, which then ends every second line; the poet often names "
                        "themselves in the last couplet.", "syllables": None, "tolerance": 0,
               "rhyme": "AA BA CA DA..."},
}

SONG_SHAPES = {
    "verse-chorus": ["Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Chorus"],
    "pop": ["Verse 1", "Pre-chorus", "Chorus", "Verse 2", "Pre-chorus", "Chorus", "Bridge", "Chorus", "Outro"],
    "ballad": ["Verse 1", "Verse 2", "Chorus", "Verse 3", "Chorus"],
    "aaba": ["Verse 1", "Verse 2", "Bridge", "Verse 3"],
    "rap": ["Intro", "Verse 1", "Hook", "Verse 2", "Hook", "Verse 3", "Hook", "Outro"],
}

SECTION_HINTS = {
    "Intro": "A few lines or a spoken hook to set the mood.",
    "Verse": "Tell the story: 4 to 8 lines of detail, a new scene each verse.",
    "Pre-chorus": "2 to 4 lines that build the tension into the chorus.",
    "Chorus": "The big idea and the title, simple and repeatable.",
    "Hook": "The catchiest line or two; it comes back again and again.",
    "Bridge": "Something new: a different angle, melody or twist before the last chorus.",
    "Outro": "Wind down; echo the chorus or leave one last image.",
}

STOPWORDS = set("""a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on
once only or other our ours ourselves out over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very was we were what when where which while
who whom why will with would you your yours yourself yourselves said says i'm it's don't didn't can't won't i'd i'll
one like""".split())

# Words ending in -ly that aren't adverbs.
NOT_ADVERBS = set("""only family reply apply supply fly july ally belly bully holly jelly lily rally silly ugly
early friendly lovely lonely lively likely daily weekly monthly yearly holy wobbly curly chilly smelly sly italy
emily molly polly sally kelly billy woolly elderly costly deadly jolly melancholy anomaly assembly homily butterfly
dragonfly gadfly firefly monopoly rely comply multiply imply""".split())
