"""Built-in tables for the sky abilities: UK cities, bright stars and constellation outlines, meteor showers, eclipses.

Star positions are J2000 (right ascension in hours, declination in degrees); the shift since then is far too small
to matter on a chart. Eclipse dates are from published predictions (UTC).
"""

CITIES = {
    "london": (51.507, -0.128), "birmingham": (52.486, -1.890), "manchester": (53.481, -2.243),
    "leeds": (53.801, -1.549), "liverpool": (53.408, -2.992), "sheffield": (53.381, -1.470),
    "bristol": (51.454, -2.588), "newcastle": (54.978, -1.618), "nottingham": (52.954, -1.150),
    "leicester": (52.637, -1.135), "southampton": (50.904, -1.404), "portsmouth": (50.819, -1.088),
    "brighton": (50.823, -0.137), "plymouth": (50.375, -4.143), "exeter": (50.726, -3.527),
    "cardiff": (51.482, -3.179), "swansea": (51.621, -3.944), "newport": (51.588, -2.998),
    "edinburgh": (55.953, -3.189), "glasgow": (55.864, -4.252), "aberdeen": (57.150, -2.094),
    "inverness": (57.478, -4.225), "dundee": (56.462, -2.971), "stirling": (56.116, -3.937),
    "perth": (56.397, -3.437), "belfast": (54.597, -5.930), "derry": (54.997, -7.309),
    "oxford": (51.752, -1.258), "cambridge": (52.205, 0.119), "norwich": (52.630, 1.297),
    "york": (53.959, -1.081), "bath": (51.381, -2.360), "canterbury": (51.280, 1.080),
    "coventry": (52.408, -1.511), "stoke": (53.003, -2.180), "hull": (53.744, -0.332),
    "sunderland": (54.906, -1.383), "carlisle": (54.892, -2.944), "lincoln": (53.234, -0.538),
    "peterborough": (52.573, -0.242), "reading": (51.454, -0.978), "milton keynes": (52.041, -0.759),
    "bournemouth": (50.720, -1.879), "gloucester": (51.864, -2.244), "worcester": (52.192, -2.220),
    "lancaster": (54.048, -2.801), "truro": (50.263, -5.051), "penzance": (50.119, -5.537),
    "wrexham": (53.046, -2.992), "lerwick": (60.155, -1.145), "stornoway": (58.209, -6.385),
}

# name: (right ascension hours, declination degrees, magnitude); mag under 1.6 counts as a named bright star
STARS = {
    "Dubhe": (11.062, 61.751, 1.8), "Merak": (11.031, 56.382, 2.4), "Phecda": (11.897, 53.695, 2.4),
    "Megrez": (12.257, 57.033, 3.3), "Alioth": (12.900, 55.960, 1.8), "Mizar": (13.399, 54.925, 2.2),
    "Alkaid": (13.792, 49.313, 1.9), "Polaris": (2.530, 89.264, 2.0), "Kochab": (14.845, 74.156, 2.1),
    "Pherkad": (15.345, 71.834, 3.0), "Caph": (0.153, 59.150, 2.3), "Schedar": (0.675, 56.537, 2.2),
    "Navi": (0.945, 60.717, 2.5), "Ruchbah": (1.430, 60.235, 2.7), "Segin": (1.907, 63.670, 3.4),
    "Betelgeuse": (5.919, 7.407, 0.5), "Bellatrix": (5.419, 6.350, 1.6), "Mintaka": (5.533, -0.299, 2.2),
    "Alnilam": (5.604, -1.202, 1.7), "Alnitak": (5.679, -1.943, 1.8), "Saiph": (5.796, -9.670, 2.1),
    "Rigel": (5.242, -8.202, 0.1), "Aldebaran": (4.599, 16.509, 0.9), "Elnath": (5.438, 28.608, 1.7),
    "Zeta Tauri": (5.627, 21.143, 3.0), "Pleiades": (3.790, 24.105, 1.6), "Castor": (7.577, 31.888, 1.6),
    "Pollux": (7.755, 28.026, 1.1), "Alhena": (6.629, 16.399, 1.9), "Capella": (5.278, 45.998, 0.1),
    "Menkalinan": (5.992, 44.947, 1.9), "Sirius": (6.752, -16.716, -1.5), "Adhara": (6.977, -28.972, 1.5),
    "Wezen": (7.140, -26.393, 1.8), "Procyon": (7.655, 5.225, 0.4), "Gomeisa": (7.452, 8.289, 2.9),
    "Regulus": (10.140, 11.967, 1.4), "Algieba": (10.333, 19.842, 2.0), "Zosma": (11.235, 20.524, 2.6),
    "Denebola": (11.818, 14.572, 2.1), "Chertan": (11.237, 15.430, 3.3), "Spica": (13.420, -11.161, 1.0),
    "Arcturus": (14.261, 19.182, 0.0), "Izar": (14.750, 27.074, 2.4), "Muphrid": (13.911, 18.398, 2.7),
    "Alphecca": (15.578, 26.715, 2.2), "Vega": (18.616, 38.784, 0.0), "Sheliak": (18.835, 33.363, 3.5),
    "Sulafat": (18.982, 32.690, 3.3), "Deneb": (20.690, 45.280, 1.3), "Sadr": (20.370, 40.257, 2.2),
    "Albireo": (19.512, 27.960, 3.1), "Gienah": (20.770, 33.970, 2.5), "Delta Cygni": (19.750, 45.131, 2.9),
    "Altair": (19.846, 8.868, 0.8), "Tarazed": (19.771, 10.613, 2.7), "Alshain": (19.922, 6.407, 3.7),
    "Antares": (16.490, -26.432, 1.1), "Graffias": (16.090, -19.805, 2.6), "Dschubba": (16.005, -22.622, 2.3),
    "Shaula": (17.560, -37.104, 1.6), "Markab": (23.079, 15.205, 2.5), "Scheat": (23.063, 28.083, 2.4),
    "Algenib": (0.220, 15.184, 2.8), "Alpheratz": (0.140, 29.091, 2.1), "Mirach": (1.162, 35.621, 2.1),
    "Almach": (2.065, 42.330, 2.1), "Mirfak": (3.405, 49.861, 1.8), "Algol": (3.136, 40.956, 2.1),
    "Deneb Kaitos": (0.727, -17.987, 2.0), "Fomalhaut": (22.961, -29.622, 1.2),
}

# constellation: list of stars, and outline pairs of star names
CONSTELLATIONS = {
    "Ursa Major (the Plough)": (
        ["Dubhe", "Merak", "Phecda", "Megrez", "Alioth", "Mizar", "Alkaid"],
        [("Dubhe", "Merak"), ("Merak", "Phecda"), ("Phecda", "Megrez"), ("Megrez", "Dubhe"), ("Megrez", "Alioth"),
         ("Alioth", "Mizar"), ("Mizar", "Alkaid")]),
    "Ursa Minor": (["Polaris", "Kochab", "Pherkad"], [("Polaris", "Kochab"), ("Kochab", "Pherkad")]),
    "Cassiopeia": (["Caph", "Schedar", "Navi", "Ruchbah", "Segin"],
                   [("Caph", "Schedar"), ("Schedar", "Navi"), ("Navi", "Ruchbah"), ("Ruchbah", "Segin")]),
    "Orion": (["Betelgeuse", "Bellatrix", "Mintaka", "Alnilam", "Alnitak", "Saiph", "Rigel"],
              [("Betelgeuse", "Bellatrix"), ("Bellatrix", "Mintaka"), ("Betelgeuse", "Alnitak"),
               ("Mintaka", "Alnilam"), ("Alnilam", "Alnitak"), ("Mintaka", "Rigel"), ("Alnitak", "Saiph")]),
    "Taurus": (["Aldebaran", "Elnath", "Zeta Tauri", "Pleiades"],
               [("Aldebaran", "Elnath"), ("Aldebaran", "Zeta Tauri")]),
    "Gemini": (["Castor", "Pollux", "Alhena"], [("Castor", "Pollux"), ("Pollux", "Alhena")]),
    "Auriga": (["Capella", "Menkalinan"], [("Capella", "Menkalinan")]),
    "Canis Major": (["Sirius", "Adhara", "Wezen"], [("Sirius", "Adhara"), ("Sirius", "Wezen")]),
    "Canis Minor": (["Procyon", "Gomeisa"], [("Procyon", "Gomeisa")]),
    "Leo": (["Regulus", "Algieba", "Zosma", "Denebola", "Chertan"],
            [("Regulus", "Algieba"), ("Algieba", "Zosma"), ("Zosma", "Denebola"), ("Denebola", "Chertan"),
             ("Chertan", "Regulus")]),
    "Virgo": (["Spica"], []),
    "Bootes": (["Arcturus", "Izar", "Muphrid"], [("Arcturus", "Izar"), ("Arcturus", "Muphrid")]),
    "Corona Borealis": (["Alphecca"], []),
    "Lyra": (["Vega", "Sheliak", "Sulafat"], [("Vega", "Sheliak"), ("Sheliak", "Sulafat")]),
    "Cygnus": (["Deneb", "Sadr", "Albireo", "Gienah", "Delta Cygni"],
               [("Deneb", "Sadr"), ("Sadr", "Albireo"), ("Delta Cygni", "Sadr"), ("Sadr", "Gienah")]),
    "Aquila": (["Altair", "Tarazed", "Alshain"], [("Tarazed", "Altair"), ("Altair", "Alshain")]),
    "Scorpius": (["Antares", "Graffias", "Dschubba", "Shaula"],
                 [("Graffias", "Dschubba"), ("Dschubba", "Antares"), ("Antares", "Shaula")]),
    "Pegasus": (["Markab", "Scheat", "Algenib", "Alpheratz"],
                [("Markab", "Scheat"), ("Scheat", "Alpheratz"), ("Alpheratz", "Algenib"), ("Algenib", "Markab")]),
    "Andromeda": (["Alpheratz", "Mirach", "Almach"], [("Alpheratz", "Mirach"), ("Mirach", "Almach")]),
    "Perseus": (["Mirfak", "Algol"], [("Mirfak", "Algol")]),
    "Cetus": (["Deneb Kaitos"], []),
    "Piscis Austrinus": (["Fomalhaut"], []),
}

# name: (constellation, colour, distance in light years, fact)
STAR_FACTS = {
    "Polaris": ("Ursa Minor", "yellow-white", 430, "The North Star: it sits almost exactly over the north pole, so it barely moves all night. "
                "Find it by following the two end stars of the Plough's bowl."),
    "Sirius": ("Canis Major", "blue-white", 8.6, "The brightest star in the night sky, and one of our nearest neighbours. "
               "It twinkles in bright flashes of colour when low in the winter sky."),
    "Betelgeuse": ("Orion", "orange-red", 550, "A red supergiant so big it would swallow Mars's orbit if it sat where the Sun is. "
                   "It will explode as a supernova one day, but probably not for a very long while."),
    "Rigel": ("Orion", "blue-white", 860, "A blue supergiant, tens of thousands of times more luminous than the Sun, at Orion's foot."),
    "Vega": ("Lyra", "white", 25, "One of the Summer Triangle's corners, high overhead on summer evenings. "
             "In about 12,000 years it will be the pole star."),
    "Deneb": ("Cygnus", "white", 2600, "The tail of the Swan and a Summer Triangle corner; among the most distant stars you can see without a telescope."),
    "Altair": ("Aquila", "white", 17, "The third Summer Triangle corner. It spins so fast it is squashed, with a day of about nine hours."),
    "Arcturus": ("Bootes", "orange", 37, "The brightest star of the northern sky in spring; follow the Plough's handle round in a curve to find it."),
    "Capella": ("Auriga", "yellow", 43, "A bright pair of yellow giants that looks like one star, high in the winter sky and always above the UK horizon."),
    "Aldebaran": ("Taurus", "orange", 65, "The bull's fiery eye, a red giant. It only looks part of the Hyades cluster; that cluster is twice as far away."),
    "Antares": ("Scorpius", "red", 550, "The red heart of the scorpion, low in the south on summer evenings; its name means rival of Mars."),
    "Spica": ("Virgo", "blue-white", 250, "Virgo's brightest star; follow the arc of the Plough's handle to Arcturus, then drive a spike to Spica."),
    "Regulus": ("Leo", "blue-white", 79, "The heart of the lion, sitting at the base of the Sickle, the backwards question mark of Leo."),
    "Procyon": ("Canis Minor", "yellow-white", 11.5, "One of the Winter Triangle with Betelgeuse and Sirius, and a close neighbour."),
    "Pollux": ("Gemini", "orange", 34, "The brighter of the Twins; it has a known planet. Castor, next to it, is really six stars."),
    "Castor": ("Gemini", "white", 51, "The other twin, a system of six stars orbiting each other."),
    "Algol": ("Perseus", "blue-white", 90, "The Demon Star: it dims noticeably for a few hours every 2 days 21 hours as a dimmer partner passes in front."),
    "Fomalhaut": ("Piscis Austrinus", "white", 25, "The lonely star low in the south on autumn evenings, sometimes called the Autumn Star."),
    "Mizar": ("Ursa Major", "white", 83, "The middle star of the Plough's handle; with sharp eyes you can see its faint partner Alcor. It is an old eyesight test."),
    "Albireo": ("Cygnus", "gold and blue", 430, "The beak of the Swan: in a small telescope it splits into a gold and a blue star, a lovely sight."),
}

# name, active, peak (month, day), rate per hour in ideal skies, best viewing, comet or asteroid it comes from
SHOWERS = [
    ("Quadrantids", "28 Dec to 12 Jan", (1, 3), 80, "a sharp peak of a few hours, best after midnight in the north-east", "asteroid 2003 EH1"),
    ("Lyrids", "14 to 30 Apr", (4, 22), 18, "after midnight, radiant near bright Vega", "comet Thatcher"),
    ("Eta Aquariids", "19 Apr to 28 May", (5, 6), 30, "the hour before dawn, low in the south-east (better from the south)", "Halley's Comet"),
    ("Perseids", "17 Jul to 24 Aug", (8, 12), 100, "late evening to dawn, warm nights and many bright meteors", "comet Swift-Tuttle"),
    ("Draconids", "6 to 10 Oct", (10, 8), 10, "early evening, radiant high in the north-west", "comet Giacobini-Zinner"),
    ("Orionids", "2 Oct to 7 Nov", (10, 21), 20, "after midnight, fast bright meteors from Orion", "Halley's Comet"),
    ("Southern Taurids", "10 Sep to 20 Nov", (11, 5), 5, "a slow trickle of bright fireballs, all evening", "comet Encke"),
    ("Northern Taurids", "20 Oct to 10 Dec", (11, 12), 5, "a slow trickle of bright fireballs, all evening", "comet Encke"),
    ("Leonids", "6 to 30 Nov", (11, 17), 15, "after midnight, fast meteors from Leo", "comet Tempel-Tuttle"),
    ("Geminids", "4 to 20 Dec", (12, 14), 150, "from about 9pm, high all night: usually the best shower of the year", "asteroid Phaethon"),
    ("Ursids", "17 to 26 Dec", (12, 22), 10, "before dawn, radiant circling near the Little Bear", "comet Tuttle"),
]

# date, kind (solar or lunar), type, where it can be seen, and what the UK sees
ECLIPSES = [
    ("2026-02-17", "solar", "annular", "Antarctica and the southern oceans", "Not visible from the UK."),
    ("2026-03-03", "lunar", "total", "Pacific, Asia, Australia and the Americas", "Not visible: it happens in UK daylight."),
    ("2026-08-12", "solar", "total", "Greenland, Iceland and northern Spain",
     "A deep partial eclipse (roughly 90 percent) at about 6 to 8pm, with the sun low in the west; never look without eclipse glasses."),
    ("2026-08-28", "lunar", "partial", "Americas, Europe and Africa", "A deep partial eclipse visible before dawn, moon low in the south-west."),
    ("2027-02-06", "solar", "annular", "South America, Atlantic and west Africa", "Not visible from the UK."),
    ("2027-02-20", "lunar", "penumbral", "Americas, Europe, Africa", "A very faint shading; hard to notice by eye."),
    ("2027-07-18", "lunar", "penumbral", "Asia, Australia, Pacific", "Not visible from the UK."),
    ("2027-08-02", "solar", "total", "Spain, north Africa and the Middle East (the longest totality for decades)",
     "A partial eclipse in the south of England, roughly 40 percent around midday, less further north."),
    ("2027-08-17", "lunar", "penumbral", "Americas", "Not visible from the UK."),
    ("2028-01-12", "lunar", "partial", "Americas, Europe, Africa", "A shallow partial eclipse before dawn, moon low in the west."),
    ("2028-01-26", "solar", "annular", "Ecuador, Peru, Brazil, Spain and Portugal", "A partial eclipse around noon, roughly 30 to 40 percent."),
    ("2028-07-06", "lunar", "partial", "Asia, Australia, Africa, Europe", "The moon is only just rising in the UK in the evening, so it is barely visible."),
    ("2028-07-22", "solar", "total", "Australia and New Zealand", "Not visible from the UK."),
    ("2028-12-31", "lunar", "total", "Europe, Africa, Asia, Australia", "Visible on New Year's Eve evening from about 4pm, with the moon rising in the east."),
    ("2029-01-14", "solar", "partial", "North America", "Not visible from the UK."),
    ("2029-06-12", "solar", "partial", "Arctic and northern Europe", "A partial eclipse in the evening, small in the south and larger in Scotland."),
    ("2029-06-26", "lunar", "total", "Americas, Europe, Africa", "Total eclipse before dawn with the moon low in the south-west."),
    ("2029-07-11", "solar", "partial", "South Pacific and southern South America", "Not visible from the UK."),
    ("2029-12-05", "solar", "partial", "Antarctica", "Not visible from the UK."),
    ("2029-12-20", "lunar", "total", "Europe, Africa, Asia, Americas", "A total eclipse high in the evening sky: the best UK lunar eclipse of the decade."),
    ("2030-06-01", "solar", "annular", "Algeria, Greece, Turkey and Russia", "A partial eclipse in the early afternoon, roughly 50 to 60 percent."),
    ("2030-06-15", "lunar", "partial", "Europe, Africa, Asia, Australia", "A shallow partial eclipse low in the south-east at moonrise."),
    ("2030-11-25", "solar", "total", "Namibia, Botswana, South Africa and Australia", "Not visible from the UK."),
    ("2030-12-09", "lunar", "penumbral", "Europe, Africa, Asia", "A faint shading; hard to notice by eye."),
]
