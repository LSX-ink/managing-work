"""Local facts for the discover abilities: elements, planets, moons, stars, quizzes, spelling words, dated events.

Everything here is plain data, so the discover abilities work offline.
"""

# number symbol name mass group category; group 0 = the f-block rows. Masses in [..] are the most stable isotope.
_ELEMENTS = """
1 H Hydrogen 1.008 1 n|2 He Helium 4.0026 18 g|3 Li Lithium 6.94 1 a|4 Be Beryllium 9.0122 2 e|5 B Boron 10.81 13 m
6 C Carbon 12.011 14 n|7 N Nitrogen 14.007 15 n|8 O Oxygen 15.999 16 n|9 F Fluorine 18.998 17 h|10 Ne Neon 20.180 18 g
11 Na Sodium 22.990 1 a|12 Mg Magnesium 24.305 2 e|13 Al Aluminium 26.982 13 p|14 Si Silicon 28.085 14 m
15 P Phosphorus 30.974 15 n|16 S Sulfur 32.06 16 n|17 Cl Chlorine 35.45 17 h|18 Ar Argon 39.948 18 g
19 K Potassium 39.098 1 a|20 Ca Calcium 40.078 2 e|21 Sc Scandium 44.956 3 t|22 Ti Titanium 47.867 4 t
23 V Vanadium 50.942 5 t|24 Cr Chromium 51.996 6 t|25 Mn Manganese 54.938 7 t|26 Fe Iron 55.845 8 t
27 Co Cobalt 58.933 9 t|28 Ni Nickel 58.693 10 t|29 Cu Copper 63.546 11 t|30 Zn Zinc 65.38 12 t
31 Ga Gallium 69.723 13 p|32 Ge Germanium 72.630 14 m|33 As Arsenic 74.922 15 m|34 Se Selenium 78.971 16 n
35 Br Bromine 79.904 17 h|36 Kr Krypton 83.798 18 g|37 Rb Rubidium 85.468 1 a|38 Sr Strontium 87.62 2 e
39 Y Yttrium 88.906 3 t|40 Zr Zirconium 91.224 4 t|41 Nb Niobium 92.906 5 t|42 Mo Molybdenum 95.95 6 t
43 Tc Technetium [98] 7 t|44 Ru Ruthenium 101.07 8 t|45 Rh Rhodium 102.91 9 t|46 Pd Palladium 106.42 10 t
47 Ag Silver 107.87 11 t|48 Cd Cadmium 112.41 12 t|49 In Indium 114.82 13 p|50 Sn Tin 118.71 14 p
51 Sb Antimony 121.76 15 m|52 Te Tellurium 127.60 16 m|53 I Iodine 126.90 17 h|54 Xe Xenon 131.29 18 g
55 Cs Caesium 132.91 1 a|56 Ba Barium 137.33 2 e|57 La Lanthanum 138.91 0 l|58 Ce Cerium 140.12 0 l
59 Pr Praseodymium 140.91 0 l|60 Nd Neodymium 144.24 0 l|61 Pm Promethium [145] 0 l|62 Sm Samarium 150.36 0 l
63 Eu Europium 151.96 0 l|64 Gd Gadolinium 157.25 0 l|65 Tb Terbium 158.93 0 l|66 Dy Dysprosium 162.50 0 l
67 Ho Holmium 164.93 0 l|68 Er Erbium 167.26 0 l|69 Tm Thulium 168.93 0 l|70 Yb Ytterbium 173.05 0 l
71 Lu Lutetium 174.97 0 l|72 Hf Hafnium 178.49 4 t|73 Ta Tantalum 180.95 5 t|74 W Tungsten 183.84 6 t
75 Re Rhenium 186.21 7 t|76 Os Osmium 190.23 8 t|77 Ir Iridium 192.22 9 t|78 Pt Platinum 195.08 10 t
79 Au Gold 196.97 11 t|80 Hg Mercury 200.59 12 t|81 Tl Thallium 204.38 13 p|82 Pb Lead 207.2 14 p
83 Bi Bismuth 208.98 15 p|84 Po Polonium [209] 16 p|85 At Astatine [210] 17 h|86 Rn Radon [222] 18 g
87 Fr Francium [223] 1 a|88 Ra Radium [226] 2 e|89 Ac Actinium [227] 0 c|90 Th Thorium 232.04 0 c
91 Pa Protactinium 231.04 0 c|92 U Uranium 238.03 0 c|93 Np Neptunium [237] 0 c|94 Pu Plutonium [244] 0 c
95 Am Americium [243] 0 c|96 Cm Curium [247] 0 c|97 Bk Berkelium [247] 0 c|98 Cf Californium [251] 0 c
99 Es Einsteinium [252] 0 c|100 Fm Fermium [257] 0 c|101 Md Mendelevium [258] 0 c|102 No Nobelium [259] 0 c
103 Lr Lawrencium [266] 0 c|104 Rf Rutherfordium [267] 4 t|105 Db Dubnium [268] 5 t|106 Sg Seaborgium [269] 6 t
107 Bh Bohrium [270] 7 t|108 Hs Hassium [269] 8 t|109 Mt Meitnerium [278] 9 t|110 Ds Darmstadtium [281] 10 t
111 Rg Roentgenium [282] 11 t|112 Cn Copernicium [285] 12 t|113 Nh Nihonium [286] 13 p|114 Fl Flerovium [289] 14 p
115 Mc Moscovium [290] 15 p|116 Lv Livermorium [293] 16 p|117 Ts Tennessine [294] 17 h|118 Og Oganesson [294] 18 g
"""
CATEGORIES = {"n": "reactive nonmetal", "g": "noble gas", "a": "alkali metal", "e": "alkaline earth metal",
              "t": "transition metal", "p": "post-transition metal", "m": "metalloid", "h": "halogen",
              "l": "lanthanide", "c": "actinide"}
PERIOD_ENDS = [2, 10, 18, 36, 54, 86, 118]


def _elements() -> list[dict]:
    out = []
    for chunk in _ELEMENTS.replace("\n", "|").split("|"):
        if chunk.strip():
            num, sym, name, mass, group, cat = chunk.split()
            number = int(num)
            out.append({"number": number, "symbol": sym, "name": name, "mass": mass, "group": int(group),
                        "period": next(i + 1 for i, end in enumerate(PERIOD_ENDS) if number <= end),
                        "category": CATEGORIES[cat]})
    return out


ELEMENTS = _elements()

# name: (type, diameter km, million km from the Sun, day length in hours, year in Earth days, known moons,
#        gravity m/s², average temperature °C, a fact)
PLANETS = {
    "Mercury": ("rocky", 4879, 57.9, 4222.6, 88, 0, 3.7, 167,
                "It is the smallest planet, and one day there lasts longer than its year."),
    "Venus": ("rocky", 12104, 108.2, 2802.0, 224.7, 0, 8.9, 464,
              "It is the hottest planet, and it spins backwards, so the Sun rises in the west."),
    "Earth": ("rocky", 12756, 149.6, 24.0, 365.25, 1, 9.8, 15,
              "It is the only planet known to have life and liquid water on its surface."),
    "Mars": ("rocky", 6792, 228.0, 24.7, 687, 2, 3.7, -65,
             "It has Olympus Mons, the tallest volcano in the solar system, about 22 km high."),
    "Jupiter": ("gas giant", 142984, 778.5, 9.9, 4331, 95, 23.1, -110,
                "It is so big that all the other planets would fit inside it, and its Great Red Spot is a storm "
                "wider than Earth."),
    "Saturn": ("gas giant", 120536, 1432.0, 10.7, 10747, 274, 9.0, -140,
               "It is less dense than water, and its rings are mostly ice, some pieces as big as a house."),
    "Uranus": ("ice giant", 51118, 2867.0, 17.2, 30589, 28, 8.7, -195,
               "It is tipped on its side, so each pole gets about 42 years of sunlight then 42 years of darkness."),
    "Neptune": ("ice giant", 49528, 4515.0, 16.1, 59800, 16, 11.0, -200,
                "It has the fastest winds in the solar system, over 2,000 km an hour."),
}
PLANET_COLUMNS = ["Planet", "Type", "Diameter km", "From Sun (m km)", "Day (hours)", "Year (days)", "Moons",
                  "Gravity m/s²", "Temp °C"]

# moon: (planet, diameter km, a fact)
MOONS = {
    "Moon": ("Earth", 3475, "It is slowly moving away from Earth, about 3.8 cm a year, and always shows us the "
                            "same face."),
    "Phobos": ("Mars", 22, "It is spiralling inwards and will break up or crash into Mars in about 50 million years."),
    "Deimos": ("Mars", 12, "It is one of the smallest moons known, and from Mars it looks like a bright star."),
    "Io": ("Jupiter", 3643, "It is the most volcanic place in the solar system, with hundreds of active volcanoes."),
    "Europa": ("Jupiter", 3122, "Under its icy crust is a salty ocean with more water than all of Earth's oceans."),
    "Ganymede": ("Jupiter", 5268, "It is the biggest moon in the solar system, larger than the planet Mercury."),
    "Callisto": ("Jupiter", 4821, "It has one of the most heavily cratered surfaces in the solar system."),
    "Titan": ("Saturn", 5150, "It has a thick orange atmosphere and lakes of liquid methane and ethane."),
    "Enceladus": ("Saturn", 504, "It shoots jets of water ice into space from an ocean under its south pole."),
    "Mimas": ("Saturn", 396, "A giant crater called Herschel makes it look like the Death Star."),
    "Rhea": ("Saturn", 1527, "It is Saturn's second-largest moon, a cold ball of ice and rock."),
    "Titania": ("Uranus", 1578, "It is the largest moon of Uranus, with canyons hundreds of kilometres long."),
    "Miranda": ("Uranus", 472, "It has Verona Rupes, a cliff about 20 km high, perhaps the tallest in the solar system."),
    "Triton": ("Neptune", 2707, "It orbits backwards and has geysers of nitrogen; it may be a captured dwarf planet."),
    "Charon": ("Pluto", 1212, "It is half the size of Pluto, so the two orbit a point in the space between them."),
}

# What to look for in each constellation from the UK.
CONSTELLATIONS = {
    "Ursa Major": "The Plough's seven bright stars; the two end stars point to Polaris, the North Star.",
    "Ursa Minor": "The Little Bear; Polaris, at the end of its tail, barely moves all night.",
    "Cassiopeia": "A bright W or M shape opposite the Plough across Polaris.",
    "Cepheus": "A faint house shape next to Cassiopeia.",
    "Draco": "A long dragon winding between the two bears; its head is a small lozenge of four stars.",
    "Orion": "The hunter: three belt stars in a row, red Betelgeuse above and blue-white Rigel below.",
    "Taurus": "The bull: orange Aldebaran and the Pleiades star cluster, the Seven Sisters.",
    "Gemini": "The twins: the bright pair of stars Castor and Pollux.",
    "Auriga": "A pentagon of stars led by very bright yellow Capella, high overhead in winter.",
    "Canis Major": "The great dog, with Sirius, the brightest star in the night sky, low in the south.",
    "Canis Minor": "A small pair of stars with bright Procyon; part of the Winter Triangle.",
    "Perseus": "The hero, with Algol, the demon star that dims every few days; home of August's meteors.",
    "Cancer": "Faint crab between Gemini and Leo; look for the Beehive cluster with binoculars.",
    "Leo": "The lion: a backwards question mark (the Sickle) ending in bright Regulus.",
    "Virgo": "A large Y shape with bright blue-white Spica.",
    "Hydra": "The longest constellation, a faint snake stretching low across the southern sky.",
    "Bootes": "A kite shape with orange Arcturus; follow the Plough's handle to 'arc to Arcturus'.",
    "Corona Borealis": "A small, pretty semicircle of stars, the Northern Crown.",
    "Hercules": "A faint Keystone of four stars, holding the great globular cluster M13.",
    "Lyra": "Small but with brilliant blue-white Vega, almost overhead in summer.",
    "Cygnus": "The swan, or Northern Cross, flying along the Milky Way with bright Deneb at its tail.",
    "Aquila": "The eagle, with bright Altair between two fainter stars; Vega, Deneb and Altair make the Summer Triangle.",
    "Scorpius": "Only the top of the scorpion rises from the UK, with red Antares very low in the south.",
    "Sagittarius": "A teapot shape very low in the south, pointing to the centre of our galaxy.",
    "Ophiuchus": "A big faint coffin shape, the serpent bearer, above Scorpius.",
    "Delphinus": "A tiny, neat dolphin shape near Altair.",
    "Capricornus": "A faint wide triangle low in the south in late summer.",
    "Aquarius": "A faint water-carrier; look for the small Y-shaped 'water jar'.",
    "Pegasus": "The Great Square of Pegasus, four stars making a big square high in the south.",
    "Andromeda": "A chain of stars from Pegasus; with dark skies you can see the Andromeda Galaxy, 2.5 million light years away.",
    "Pisces": "A faint loop of stars, the Circlet, below the Square of Pegasus.",
    "Aries": "A short bent line of three stars between Taurus and Pisces.",
}
CIRCUMPOLAR = ["Ursa Major", "Ursa Minor", "Cassiopeia", "Cepheus", "Draco"]
# Well placed in the evening sky (about 10pm) from the UK, month by month.
BY_MONTH = {
    1: ["Orion", "Taurus", "Gemini", "Auriga", "Perseus", "Canis Major"],
    2: ["Orion", "Canis Major", "Canis Minor", "Gemini", "Auriga", "Cancer"],
    3: ["Leo", "Cancer", "Gemini", "Auriga", "Canis Minor", "Orion"],
    4: ["Leo", "Virgo", "Cancer", "Hydra", "Bootes", "Gemini"],
    5: ["Bootes", "Virgo", "Leo", "Corona Borealis", "Hercules", "Hydra"],
    6: ["Bootes", "Hercules", "Corona Borealis", "Lyra", "Virgo", "Scorpius"],
    7: ["Lyra", "Cygnus", "Aquila", "Hercules", "Ophiuchus", "Sagittarius", "Scorpius"],
    8: ["Cygnus", "Lyra", "Aquila", "Delphinus", "Sagittarius", "Capricornus", "Perseus"],
    9: ["Pegasus", "Andromeda", "Cygnus", "Lyra", "Aquila", "Capricornus", "Aquarius"],
    10: ["Pegasus", "Andromeda", "Perseus", "Pisces", "Aquarius", "Cygnus"],
    11: ["Andromeda", "Perseus", "Pegasus", "Taurus", "Aries", "Auriga", "Pisces"],
    12: ["Taurus", "Orion", "Perseus", "Auriga", "Gemini", "Aries"],
}

SCIENCE_FACTS = [
    "A teaspoon of a neutron star would weigh about as much as a mountain.",
    "Light from the Sun takes about 8 minutes 20 seconds to reach Earth.",
    "Water expands by about 9% when it freezes, which is why ice floats.",
    "Your body has about 37 trillion cells.",
    "Bananas are slightly radioactive because they contain potassium-40.",
    "Sound travels about four times faster in water than in air.",
    "A day on Venus is longer than a year on Venus.",
    "Octopuses have three hearts and blue blood.",
    "Diamonds and pencil graphite are both pure carbon, just arranged differently.",
    "There are more possible games of chess than atoms in the observable universe.",
    "Honey never goes off; edible honey has been found in ancient Egyptian tombs.",
    "Lightning is about five times hotter than the surface of the Sun.",
    "The Eiffel Tower grows about 15 cm taller in summer as the iron expands.",
    "A single bolt of lightning carries about a billion joules of energy.",
    "Helium is the only element that won't freeze at normal pressure, even at absolute zero.",
    "Tardigrades, tiny water bears, can survive in the vacuum of space.",
    "Glass is made mostly from sand melted at about 1,700 °C.",
    "Earth's core is about as hot as the surface of the Sun, around 5,200 °C.",
    "Humans share about 60% of their genes with bananas.",
    "The speed of light is about 300,000 kilometres every second.",
    "Hot water can sometimes freeze faster than cold water; it's called the Mpemba effect.",
    "Sharks existed before trees; sharks are about 450 million years old, trees about 385 million.",
    "The Moon has moonquakes, some lasting over ten minutes.",
    "Gold is so easy to shape that one gram can be beaten into a sheet of one square metre.",
    "A cloud can weigh more than a million kilograms.",
    "Oxygen is pale blue when it's a liquid.",
    "Your stomach gets a new lining every few days so it doesn't digest itself.",
    "Venus is the brightest planet in our sky, bright enough to cast shadows on a dark night.",
    "Some metals, like sodium and potassium, explode when dropped in water.",
    "Plants make the oxygen we breathe from water, splitting it apart with sunlight.",
    "An astronaut can be up to 5 cm taller in space because the spine stretches.",
]

# (unit, what it measures, what it is)
UNITS = [
    ("newton", "force", "the force that speeds up 1 kg by 1 metre per second every second; an apple weighs about 1 newton"),
    ("joule", "energy", "the energy used lifting an apple 1 metre; a slice of toast has about 300,000 joules"),
    ("watt", "power", "one joule every second; a phone charger uses about 5 to 20 watts"),
    ("pascal", "pressure", "one newton pressing on a square metre; the air presses at about 101,000 pascals"),
    ("hertz", "frequency", "one cycle a second; UK mains electricity is 50 hertz"),
    ("volt", "electrical push", "a UK plug socket gives 230 volts, an AA battery 1.5"),
    ("ampere", "electric current", "the flow of electric charge; a kettle draws about 13 amps"),
    ("ohm", "electrical resistance", "one volt pushing one amp through something"),
    ("kelvin", "temperature", "starts at absolute zero, minus 273.15 °C, with the same step size as Celsius"),
    ("mole", "amount of substance", "about 602 thousand billion billion particles; 18 grams of water is one mole"),
    ("candela", "brightness of light", "roughly the light of one candle"),
    ("light year", "distance", "how far light travels in a year, about 9.46 trillion kilometres"),
    ("astronomical unit", "distance", "the average distance from Earth to the Sun, about 150 million kilometres"),
    ("parsec", "distance", "about 3.26 light years, used by astronomers"),
    ("decibel", "loudness", "a log scale; every 10 decibels up is ten times the sound power, and a whisper is about 30"),
    ("calorie", "food energy", "a food Calorie is a kilocalorie, about 4,184 joules"),
    ("knot", "speed at sea and in the air", "one nautical mile an hour, about 1.15 miles an hour"),
    ("hectare", "area", "10,000 square metres, about two and a half acres or one and a half football pitches"),
    ("carat", "mass of gems", "one fifth of a gram, 200 milligrams"),
    ("tesla", "magnetic field", "a fridge magnet is about 0.005 tesla, an MRI scanner 1.5 to 3"),
    ("coulomb", "electric charge", "the charge carried by one amp flowing for one second"),
    ("lumen", "light output", "a 10-watt LED bulb gives about 800 lumens"),
    ("becquerel", "radioactivity", "one atom decaying each second"),
    ("sievert", "radiation dose", "the average UK person gets about 2.7 millisieverts a year from natural sources"),
    ("nanometre", "tiny lengths", "a billionth of a metre; a fingernail grows about one nanometre a second"),
    ("furlong", "distance in horse racing", "220 yards, about 201 metres; eight make a mile"),
    ("fathom", "depth of water", "six feet, about 1.83 metres"),
    ("stone", "body weight in the UK", "14 pounds, about 6.35 kilograms"),
    ("bar", "pressure", "100,000 pascals, close to the air pressure at sea level"),
    ("byte", "digital information", "8 bits; a page of plain text is about 2,000 bytes"),
]

# (question, right answer, three wrong answers)
BODY_QUESTIONS = [
    ("How many bones are in the adult human body?", "206", ["186", "256", "300"]),
    ("What is the largest organ of the human body?", "The skin", ["The liver", "The brain", "The lungs"]),
    ("Which organ pumps blood around the body?", "The heart", ["The lungs", "The kidneys", "The liver"]),
    ("What is the smallest bone in the body?", "The stapes, in the ear", ["The little toe bone", "The hyoid", "The coccyx"]),
    ("What is the longest bone in the body?", "The femur (thigh bone)", ["The tibia", "The humerus", "The spine"]),
    ("How many chambers does the human heart have?", "Four", ["Two", "Three", "Six"]),
    ("Which blood cells fight infection?", "White blood cells", ["Red blood cells", "Platelets", "Plasma"]),
    ("Which blood cells carry oxygen?", "Red blood cells", ["White blood cells", "Platelets", "Nerve cells"]),
    ("What helps your blood clot when you cut yourself?", "Platelets", ["Red blood cells", "Bile", "Insulin"]),
    ("Which organ filters your blood to make urine?", "The kidneys", ["The liver", "The spleen", "The bladder"]),
    ("Where in the body is the cornea?", "The eye", ["The ear", "The knee", "The heart"]),
    ("What is the strongest muscle for its size?", "The masseter (jaw muscle)", ["The biceps", "The heart", "The calf"]),
    ("How many teeth does an adult usually have?", "32", ["28", "24", "36"]),
    ("How many milk teeth does a child usually have?", "20", ["16", "24", "32"]),
    ("Which gas do we breathe out as waste?", "Carbon dioxide", ["Oxygen", "Nitrogen", "Helium"]),
    ("What is the main job of the lungs?", "Getting oxygen into the blood", ["Digesting food", "Filtering blood", "Making hormones"]),
    ("Which organ produces insulin?", "The pancreas", ["The liver", "The stomach", "The thyroid"]),
    ("What is the biggest internal organ?", "The liver", ["The heart", "The stomach", "The brain"]),
    ("What is the name of the body's biggest artery?", "The aorta", ["The vena cava", "The carotid", "The femoral"]),
    ("Roughly how much of your body weight is water?", "About 60%", ["About 20%", "About 40%", "About 90%"]),
    ("What connects muscles to bones?", "Tendons", ["Ligaments", "Cartilage", "Nerves"]),
    ("What connects bones to other bones?", "Ligaments", ["Tendons", "Veins", "Muscles"]),
    ("Which part of the brain controls balance?", "The cerebellum", ["The frontal lobe", "The brain stem", "The hippocampus"]),
    ("What is the coloured part of the eye called?", "The iris", ["The pupil", "The retina", "The lens"]),
    ("Where would you find the smallest muscle in the body?", "The ear", ["The eyelid", "The finger", "The tongue"]),
    ("What does the small intestine mainly do?", "Absorbs nutrients from food", ["Stores urine", "Pumps blood", "Makes bile"]),
    ("Which organ makes bile?", "The liver", ["The gallbladder", "The pancreas", "The spleen"]),
    ("Roughly how long is the small intestine?", "About 6 metres", ["About 1 metre", "About 20 metres", "About 50 cm"]),
    ("What is the hardest substance in the body?", "Tooth enamel", ["Bone", "Fingernails", "Cartilage"]),
    ("How often does the stomach lining renew itself?", "Every few days", ["Every year", "Every month", "Never"]),
    ("Which vitamin does skin make in sunlight?", "Vitamin D", ["Vitamin C", "Vitamin A", "Vitamin B12"]),
    ("What is the normal body temperature?", "About 37 °C", ["About 33 °C", "About 40 °C", "About 35 °C"]),
    ("Which body system includes the brain and nerves?", "The nervous system", ["The digestive system", "The immune system", "The skeletal system"]),
    ("Where are the alveoli?", "The lungs", ["The kidneys", "The brain", "The stomach"]),
    ("What is the kneecap's proper name?", "The patella", ["The tibia", "The scapula", "The clavicle"]),
    ("What is the collarbone's proper name?", "The clavicle", ["The sternum", "The patella", "The radius"]),
    ("Roughly how many times does a resting adult heart beat each minute?", "60 to 100", ["20 to 40", "120 to 160", "200"]),
    ("What carries messages from the brain around the body?", "Nerves", ["Veins", "Tendons", "Hormones only"]),
    ("Which sense is closely linked to taste?", "Smell", ["Hearing", "Touch", "Sight"]),
    ("Which part of the body has the most sweat glands?", "The soles of the feet", ["The back", "The scalp", "The knees"]),
]

KIDS_QUESTIONS = [
    ("How many legs does a spider have?", "8", ["6", "4", "10"]),
    ("What colour do you get mixing blue and yellow?", "Green", ["Purple", "Orange", "Pink"]),
    ("Which animal says moo?", "A cow", ["A sheep", "A dog", "A duck"]),
    ("How many days are in a week?", "7", ["5", "6", "10"]),
    ("What is the biggest planet?", "Jupiter", ["Earth", "Mars", "Saturn"]),
    ("Which is the fastest land animal?", "Cheetah", ["Horse", "Lion", "Elephant"]),
    ("What do bees make?", "Honey", ["Milk", "Jam", "Butter"]),
    ("How many sides does a triangle have?", "3", ["4", "5", "6"]),
    ("What is frozen water called?", "Ice", ["Steam", "Rain", "Sand"]),
    ("Which season comes after winter?", "Spring", ["Summer", "Autumn", "Winter again"]),
    ("What is the capital of the United Kingdom?", "London", ["Paris", "Cardiff", "Dublin"]),
    ("How many wheels does a bicycle have?", "2", ["3", "4", "1"]),
    ("Which animal is known as the king of the jungle?", "Lion", ["Tiger", "Monkey", "Bear"]),
    ("What colour is a ripe banana?", "Yellow", ["Blue", "Red", "Purple"]),
    ("What do caterpillars turn into?", "Butterflies", ["Spiders", "Bees", "Frogs"]),
    ("How many months are in a year?", "12", ["10", "11", "14"]),
    ("What is 5 plus 5?", "10", ["8", "12", "15"]),
    ("Which is the largest ocean?", "Pacific", ["Atlantic", "Indian", "Arctic"]),
    ("What do we call a baby dog?", "A puppy", ["A kitten", "A calf", "A cub"]),
    ("What do we call a baby cat?", "A kitten", ["A puppy", "A foal", "A lamb"]),
    ("Which shape has four equal sides?", "A square", ["A circle", "A triangle", "An oval"]),
    ("What is the opposite of hot?", "Cold", ["Warm", "Wet", "Big"]),
    ("Which body part do we use to smell?", "Nose", ["Ears", "Elbow", "Knee"]),
    ("Where do penguins mostly live?", "Antarctica", ["The desert", "The jungle", "The Arctic"]),
    ("How many colours are in a rainbow?", "7", ["5", "6", "10"]),
    ("What gives us light in the daytime?", "The Sun", ["The Moon", "The stars", "Lamps"]),
    ("Which animal has a very long neck?", "Giraffe", ["Zebra", "Hippo", "Pig"]),
    ("What is 3 times 3?", "9", ["6", "12", "33"]),
    ("Which fruit keeps the doctor away, as the saying goes?", "An apple", ["A lemon", "A grape", "A melon"]),
    ("What is the tallest animal?", "Giraffe", ["Elephant", "Horse", "Camel"]),
    ("How many legs does an insect have?", "6", ["8", "4", "10"]),
    ("Which planet do we live on?", "Earth", ["Mars", "Venus", "The Moon"]),
    ("What do plants need to grow?", "Water and sunlight", ["Chocolate", "Sand only", "Nothing"]),
    ("Which animal is black and white and eats bamboo?", "Giant panda", ["Zebra", "Penguin", "Skunk"]),
    ("How many minutes are in an hour?", "60", ["30", "100", "24"]),
    ("What is the colour of grass?", "Green", ["Blue", "Orange", "Grey"]),
    ("Which instrument has black and white keys?", "Piano", ["Drum", "Guitar", "Trumpet"]),
    ("What do we call the home of a bird?", "A nest", ["A den", "A hive", "A burrow"]),
    ("Which is the biggest animal in the world?", "Blue whale", ["Elephant", "Shark", "Giraffe"]),
    ("How many hours are in a day?", "24", ["12", "60", "10"]),
]

# (year, event); negative years are BC.
EVENTS = [
    (-2560, "The Great Pyramid of Giza is finished"), (-776, "The first recorded Olympic Games in Greece"),
    (-44, "Julius Caesar is assassinated"), (43, "The Romans invade Britain"),
    (122, "Work starts on Hadrian's Wall"), (1066, "The Battle of Hastings"),
    (1215, "Magna Carta is sealed"), (1347, "The Black Death reaches Europe"),
    (1440, "Gutenberg's printing press"), (1492, "Columbus sails to the Americas"),
    (1564, "William Shakespeare is born"), (1588, "The Spanish Armada is defeated"),
    (1605, "The Gunpowder Plot"), (1666, "The Great Fire of London"),
    (1687, "Newton publishes his laws of motion"), (1707, "England and Scotland unite as Great Britain"),
    (1776, "The US Declaration of Independence"), (1789, "The French Revolution begins"),
    (1805, "The Battle of Trafalgar"), (1815, "The Battle of Waterloo"),
    (1825, "The first public steam railway, Stockton to Darlington"), (1837, "Queen Victoria comes to the throne"),
    (1859, "Darwin publishes On the Origin of Species"), (1863, "The London Underground opens"),
    (1876, "Bell patents the telephone"), (1903, "The Wright brothers' first powered flight"),
    (1912, "The Titanic sinks"), (1914, "The First World War begins"),
    (1918, "Women over 30 get the vote in the UK"), (1928, "Fleming discovers penicillin"),
    (1936, "The BBC starts regular TV broadcasts"), (1939, "The Second World War begins"),
    (1945, "The Second World War ends"), (1948, "The NHS is founded"),
    (1953, "The structure of DNA is described"), (1953, "Everest is first climbed"),
    (1957, "Sputnik, the first satellite, is launched"), (1961, "Yuri Gagarin is the first person in space"),
    (1963, "The Beatles release their first album"), (1966, "England win the football World Cup"),
    (1969, "Apollo 11 lands on the Moon"), (1971, "UK money goes decimal"),
    (1973, "The UK joins the European Economic Community"), (1979, "Margaret Thatcher becomes Prime Minister"),
    (1981, "The first Space Shuttle launch"), (1985, "Live Aid concerts"),
    (1989, "The Berlin Wall falls"), (1991, "The World Wide Web goes public"),
    (1994, "The Channel Tunnel opens"), (1994, "Nelson Mandela becomes President of South Africa"),
    (1997, "Dolly the sheep, the first cloned mammal, is announced"), (2000, "The Millennium Dome opens"),
    (2001, "Wikipedia is launched"), (2004, "Facebook is launched"),
    (2007, "The first iPhone goes on sale"), (2008, "The Large Hadron Collider is switched on"),
    (2012, "London hosts the Olympic Games"), (2016, "The UK votes to leave the EU"),
    (2020, "The COVID-19 pandemic and first UK lockdown"), (2022, "Queen Elizabeth II dies"),
    (2021, "The James Webb Space Telescope is launched"),
]

SPELLING = {
    "easy": ["because", "friend", "people", "school", "house", "water", "little", "should", "would", "thought",
             "animal", "family", "garden", "yellow", "window", "birthday", "brother", "sister", "orange", "purple"],
    "medium": ["necessary", "separate", "definitely", "believe", "receive", "tomorrow", "beautiful", "February",
               "Wednesday", "library", "government", "environment", "restaurant", "interesting", "different",
               "knowledge", "neighbour", "favourite", "calendar", "surprise"],
    "hard": ["accommodation", "conscientious", "embarrass", "millennium", "occasionally", "questionnaire",
             "rhythm", "entrepreneur", "bureaucracy", "pharaoh", "onomatopoeia", "mischievous", "liaison",
             "hierarchy", "phenomenon", "manoeuvre", "Mediterranean", "silhouette", "handkerchief", "idiosyncrasy"],
}
