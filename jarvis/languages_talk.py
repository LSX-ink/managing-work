"""Telling the time and short role-play dialogues for the language studio.

clock() writes a time out in words in each language (12-hour, on the five minutes). DIALOGUES are two little
scenes per language: the other person speaks, and for each of your turns you pick the right reply from three.
In the data the right reply comes first; languages_practice shuffles them.
"""

HOURS = {
    "es": "una dos tres cuatro cinco seis siete ocho nueve diez once doce".split(),
    "de": "eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf".split(),
    "it": "una due tre quattro cinque sei sette otto nove dieci undici dodici".split(),
    "fr": "une deux trois quatre cinq six sept huit neuf dix onze douze".split(),
    "pt": "uma duas três quatro cinco seis sete oito nove dez onze doze".split(),
}
JA_HOURS = [("一", "ichi"), ("二", "ni"), ("三", "san"), ("四", "yo"), ("五", "go"), ("六", "roku"),
            ("七", "shichi"), ("八", "hachi"), ("九", "ku"), ("十", "jū"), ("十一", "jūichi"), ("十二", "jūni")]
JA_MINUTES = {5: ("五分", "gofun"), 10: ("十分", "juppun"), 15: ("十五分", "jūgofun"), 20: ("二十分", "nijuppun"),
              25: ("二十五分", "nijūgofun"), 35: ("三十五分", "sanjūgofun"), 40: ("四十分", "yonjuppun"),
              45: ("四十五分", "yonjūgofun"), 50: ("五十分", "gojuppun"), 55: ("五十五分", "gojūgofun")}
ES_MINUTES = {5: "cinco", 10: "diez", 15: "cuarto", 20: "veinte", 25: "veinticinco", 30: "media"}
IT_MINUTES = {5: "cinque", 10: "dieci", 15: "un quarto", 20: "venti", 25: "venticinque", 30: "mezza"}
FR_MINUTES = {5: "cinq", 10: "dix", 15: "quart", 20: "vingt", 25: "vingt-cinq", 30: "demie"}
PT_MINUTES = {5: "cinco", 10: "dez", 15: "um quarto", 20: "vinte", 25: "vinte e cinco", 30: "meia"}


def _next(h: int) -> int:
    return h % 12 + 1


def _spanish(h: int, m: int) -> str:
    def lead(n):
        return "Es la una" if n == 1 else f"Son las {HOURS['es'][n - 1]}"
    if m == 0:
        return lead(h) + " en punto"
    if m <= 30:
        return f"{lead(h)} y {ES_MINUTES[m]}"
    return f"{lead(_next(h))} menos {ES_MINUTES[60 - m]}"


def _french(h: int, m: int) -> str:
    def hour(n):
        return f"{HOURS['fr'][n - 1]} heure" + ("" if n == 1 else "s")
    if m == 0:
        return f"Il est {hour(h)}"
    if m == 15:
        return f"Il est {hour(h)} et quart"
    if m == 30:
        return f"Il est {hour(h)} et demie"
    if m < 30:
        return f"Il est {hour(h)} {FR_MINUTES[m]}"
    later = 60 - m
    return f"Il est {hour(_next(h))} moins " + ("le quart" if later == 15 else FR_MINUTES[later])


def _german(h: int, m: int) -> str:
    def word(n):
        return HOURS["de"][n - 1]
    nh = _next(h)
    if m == 0:
        return "Es ist " + ("ein" if h == 1 else word(h)) + " Uhr"
    forms = {5: f"fünf nach {word(h)}", 10: f"zehn nach {word(h)}", 15: f"Viertel nach {word(h)}",
             20: f"zwanzig nach {word(h)}", 25: f"fünf vor halb {word(nh)}", 30: f"halb {word(nh)}",
             35: f"fünf nach halb {word(nh)}", 40: f"zwanzig vor {word(nh)}", 45: f"Viertel vor {word(nh)}",
             50: f"zehn vor {word(nh)}", 55: f"fünf vor {word(nh)}"}
    return "Es ist " + forms[m]


def _italian(h: int, m: int) -> str:
    def lead(n):
        return "È l'una" if n == 1 else f"Sono le {HOURS['it'][n - 1]}"
    if m == 0:
        return lead(h)
    if m <= 30:
        return f"{lead(h)} e {IT_MINUTES[m]}"
    return f"{lead(_next(h))} meno {IT_MINUTES[60 - m]}"


def _portuguese(h: int, m: int) -> str:
    def hour(n):
        return f"{HOURS['pt'][n - 1]} hora" + ("" if n == 1 else "s")
    if m == 0:
        return ("É " if h == 1 else "São ") + hour(h)
    if m <= 30:
        return ("É " if h == 1 else "São ") + f"{hour(h)} e {PT_MINUTES[m]}"
    nh = _next(h)
    minutes = 60 - m
    lead = "É" if minutes == 15 else "São"
    return f"{lead} {PT_MINUTES[minutes]} para {'a uma' if nh == 1 else 'as ' + HOURS['pt'][nh - 1]}"


def _japanese(h: int, m: int) -> tuple[str, str]:
    kanji, roman = JA_HOURS[h - 1]
    kanji, roman = kanji + "時", roman + "ji"
    if m == 0:
        return kanji, roman
    if m == 30:
        return kanji + "半", roman + " han"
    minutes = JA_MINUTES[m]
    return kanji + minutes[0], f"{roman} {minutes[1]}"


def clock(lang: str, hour: int, minute: int) -> tuple[str, str]:
    """The time (hour 1 to 12, minute a multiple of five) as [words, romaji]; romaji is only for Japanese."""
    if not 1 <= hour <= 12 or minute % 5 or not 0 <= minute < 60:
        raise ValueError("Give the time as an hour from 1 to 12 and minutes in fives.")
    if lang == "ja":
        return _japanese(hour, minute)
    words = {"es": _spanish, "fr": _french, "de": _german, "it": _italian, "pt": _portuguese}[lang](hour, minute)
    return words, ""


CAFE = "cafe"
STATION = "directions"
SCENES = {CAFE: "Ordering in a café", STATION: "Asking the way to the station"}

# (text, english, romaji) for the other person; a list of such options for you, the right one first.
DIALOGUES = {
    "es": {
        CAFE: [
            ("them", "Buenos días. ¿Qué desea?", "Good morning. What would you like?", ""),
            ("you", [("Un café con leche, por favor.", "A coffee with milk, please.", ""),
                     ("Me llamo Ana.", "My name is Ana.", ""),
                     ("El tren sale a las tres.", "The train leaves at three.", "")]),
            ("them", "Muy bien. ¿Algo más?", "Very good. Anything else?", ""),
            ("you", [("No, nada más, gracias.", "No, nothing else, thanks.", ""),
                     ("Sí, tengo dos hermanos.", "Yes, I have two brothers.", ""),
                     ("Adiós, hasta mañana.", "Goodbye, see you tomorrow.", "")]),
            ("them", "Son tres euros.", "That's three euros.", ""),
            ("you", [("Aquí tiene. Gracias.", "Here you are. Thank you.", ""),
                     ("Hace mucho calor.", "It's very hot.", ""),
                     ("Buenas noches.", "Good night.", "")]),
        ],
        STATION: [
            ("you", [("Perdone, ¿dónde está la estación?", "Excuse me, where is the station?", ""),
                     ("Me gusta el pan.", "I like bread.", ""),
                     ("Tengo una maleta.", "I have a suitcase.", "")]),
            ("them", "Todo recto y luego a la izquierda.", "Straight on and then left.", ""),
            ("you", [("¿Está lejos?", "Is it far?", ""), ("Tengo veinte años.", "I'm twenty years old.", ""),
                     ("Hasta luego.", "See you later.", "")]),
            ("them", "No, está a cinco minutos.", "No, it's five minutes away.", ""),
            ("you", [("Muchas gracias.", "Thank you very much.", ""),
                     ("Lo siento, no tengo hambre.", "Sorry, I'm not hungry.", ""),
                     ("Es mi hermano.", "It's my brother.", "")]),
        ],
    },
    "fr": {
        CAFE: [
            ("them", "Bonjour. Vous désirez ?", "Hello. What would you like?", ""),
            ("you", [("Un café au lait, s'il vous plaît.", "A coffee with milk, please.", ""),
                     ("Je m'appelle Marie.", "My name is Marie.", ""),
                     ("Le train part à trois heures.", "The train leaves at three.", "")]),
            ("them", "Très bien. Et avec ça ?", "Very good. Anything with that?", ""),
            ("you", [("Non, ce sera tout, merci.", "No, that will be all, thanks.", ""),
                     ("Oui, j'ai deux frères.", "Yes, I have two brothers.", ""),
                     ("Au revoir, à demain.", "Goodbye, see you tomorrow.", "")]),
            ("them", "Ça fait trois euros.", "That's three euros.", ""),
            ("you", [("Voilà. Merci.", "Here you are. Thank you.", ""),
                     ("Il fait très chaud.", "It's very hot.", ""),
                     ("Bonne nuit.", "Good night.", "")]),
        ],
        STATION: [
            ("you", [("Excusez-moi, où est la gare ?", "Excuse me, where is the station?", ""),
                     ("J'aime le pain.", "I like bread.", ""),
                     ("J'ai une valise.", "I have a suitcase.", "")]),
            ("them", "Tout droit, puis à gauche.", "Straight on, then left.", ""),
            ("you", [("C'est loin ?", "Is it far?", ""), ("J'ai vingt ans.", "I'm twenty years old.", ""),
                     ("À tout à l'heure.", "See you later.", "")]),
            ("them", "Non, c'est à cinq minutes.", "No, it's five minutes away.", ""),
            ("you", [("Merci beaucoup.", "Thank you very much.", ""),
                     ("Désolé, je n'ai pas faim.", "Sorry, I'm not hungry.", ""),
                     ("C'est mon frère.", "It's my brother.", "")]),
        ],
    },
    "de": {
        CAFE: [
            ("them", "Guten Morgen. Was möchten Sie?", "Good morning. What would you like?", ""),
            ("you", [("Einen Kaffee mit Milch, bitte.", "A coffee with milk, please.", ""),
                     ("Ich heiße Anna.", "My name is Anna.", ""),
                     ("Der Zug fährt um drei Uhr ab.", "The train leaves at three.", "")]),
            ("them", "Gerne. Sonst noch etwas?", "Gladly. Anything else?", ""),
            ("you", [("Nein, danke, das ist alles.", "No, thanks, that's all.", ""),
                     ("Ja, ich habe zwei Brüder.", "Yes, I have two brothers.", ""),
                     ("Auf Wiedersehen, bis morgen.", "Goodbye, see you tomorrow.", "")]),
            ("them", "Das macht drei Euro.", "That's three euros.", ""),
            ("you", [("Hier, bitte. Danke.", "Here you are. Thank you.", ""),
                     ("Es ist sehr heiß.", "It's very hot.", ""),
                     ("Gute Nacht.", "Good night.", "")]),
        ],
        STATION: [
            ("you", [("Entschuldigung, wo ist der Bahnhof?", "Excuse me, where is the station?", ""),
                     ("Ich mag Brot.", "I like bread.", ""),
                     ("Ich habe einen Koffer.", "I have a suitcase.", "")]),
            ("them", "Geradeaus und dann links.", "Straight on and then left.", ""),
            ("you", [("Ist es weit?", "Is it far?", ""), ("Ich bin zwanzig Jahre alt.", "I'm twenty years old.", ""),
                     ("Bis später.", "See you later.", "")]),
            ("them", "Nein, fünf Minuten zu Fuß.", "No, five minutes on foot.", ""),
            ("you", [("Vielen Dank.", "Thank you very much.", ""),
                     ("Tut mir leid, ich habe keinen Hunger.", "Sorry, I'm not hungry.", ""),
                     ("Das ist mein Bruder.", "That's my brother.", "")]),
        ],
    },
    "it": {
        CAFE: [
            ("them", "Buongiorno. Cosa desidera?", "Good morning. What would you like?", ""),
            ("you", [("Un caffè con latte, per favore.", "A coffee with milk, please.", ""),
                     ("Mi chiamo Anna.", "My name is Anna.", ""),
                     ("Il treno parte alle tre.", "The train leaves at three.", "")]),
            ("them", "Benissimo. Altro?", "Very good. Anything else?", ""),
            ("you", [("No, basta così, grazie.", "No, that's enough, thanks.", ""),
                     ("Sì, ho due fratelli.", "Yes, I have two brothers.", ""),
                     ("Arrivederci, a domani.", "Goodbye, see you tomorrow.", "")]),
            ("them", "Sono tre euro.", "That's three euros.", ""),
            ("you", [("Ecco a lei. Grazie.", "Here you are. Thank you.", ""),
                     ("Fa molto caldo.", "It's very hot.", ""),
                     ("Buonanotte.", "Good night.", "")]),
        ],
        STATION: [
            ("you", [("Scusi, dov'è la stazione?", "Excuse me, where is the station?", ""),
                     ("Mi piace il pane.", "I like bread.", ""),
                     ("Ho una valigia.", "I have a suitcase.", "")]),
            ("them", "Sempre dritto, poi a sinistra.", "Straight on, then left.", ""),
            ("you", [("È lontano?", "Is it far?", ""), ("Ho vent'anni.", "I'm twenty years old.", ""),
                     ("A più tardi.", "See you later.", "")]),
            ("them", "No, è a cinque minuti.", "No, it's five minutes away.", ""),
            ("you", [("Grazie mille.", "Thank you very much.", ""),
                     ("Mi dispiace, non ho fame.", "Sorry, I'm not hungry.", ""),
                     ("È mio fratello.", "It's my brother.", "")]),
        ],
    },
    "pt": {
        CAFE: [
            ("them", "Bom dia. O que deseja?", "Good morning. What would you like?", ""),
            ("you", [("Um café com leite, por favor.", "A coffee with milk, please.", ""),
                     ("Chamo-me Ana.", "My name is Ana.", ""),
                     ("O comboio parte às três horas.", "The train leaves at three.", "")]),
            ("them", "Muito bem. Mais alguma coisa?", "Very good. Anything else?", ""),
            ("you", [("Não, é tudo, obrigado.", "No, that's all, thanks.", ""),
                     ("Sim, tenho dois irmãos.", "Yes, I have two brothers.", ""),
                     ("Adeus, até amanhã.", "Goodbye, see you tomorrow.", "")]),
            ("them", "São três euros.", "That's three euros.", ""),
            ("you", [("Aqui tem. Obrigado.", "Here you are. Thank you.", ""),
                     ("Está muito calor.", "It's very hot.", ""),
                     ("Boa noite.", "Good night.", "")]),
        ],
        STATION: [
            ("you", [("Desculpe, onde fica a estação?", "Excuse me, where is the station?", ""),
                     ("Gosto de pão.", "I like bread.", ""),
                     ("Tenho uma mala.", "I have a suitcase.", "")]),
            ("them", "Sempre em frente e depois à esquerda.", "Straight on and then left.", ""),
            ("you", [("É longe?", "Is it far?", ""), ("Tenho vinte anos.", "I'm twenty years old.", ""),
                     ("Até logo.", "See you later.", "")]),
            ("them", "Não, fica a cinco minutos.", "No, it's five minutes away.", ""),
            ("you", [("Muito obrigado.", "Thank you very much.", ""),
                     ("Desculpe, não tenho fome.", "Sorry, I'm not hungry.", ""),
                     ("É o meu irmão.", "It's my brother.", "")]),
        ],
    },
    "ja": {
        CAFE: [
            ("them", "いらっしゃいませ。ご注文は？", "Welcome. What would you like to order?", "irasshaimase. go-chūmon wa?"),
            ("you", [("コーヒーをお願いします。", "Coffee, please.", "kōhī o onegai shimasu"),
                     ("わたしの名前はアナです。", "My name is Ana.", "watashi no namae wa Ana desu"),
                     ("電車は三時に出ます。", "The train leaves at three.", "densha wa sanji ni demasu")]),
            ("them", "はい。他にございますか？", "Certainly. Anything else?", "hai. hoka ni gozaimasu ka?"),
            ("you", [("いいえ、以上です。", "No, that's all.", "iie, ijō desu"),
                     ("はい、兄が二人います。", "Yes, I have two older brothers.", "hai, ani ga futari imasu"),
                     ("さようなら、また明日。", "Goodbye, see you tomorrow.", "sayōnara, mata ashita")]),
            ("them", "三百円です。", "That's 300 yen.", "sanbyaku en desu"),
            ("you", [("はい、どうぞ。ありがとう。", "Here you are. Thank you.", "hai, dōzo. arigatō"),
                     ("とても暑いです。", "It's very hot.", "totemo atsui desu"),
                     ("おやすみなさい。", "Good night.", "oyasumi nasai")]),
        ],
        STATION: [
            ("you", [("すみません、駅はどこですか。", "Excuse me, where is the station?", "sumimasen, eki wa doko desu ka"),
                     ("パンが好きです。", "I like bread.", "pan ga suki desu"),
                     ("スーツケースがあります。", "I have a suitcase.", "sūtsukēsu ga arimasu")]),
            ("them", "まっすぐ行って、左に曲がってください。", "Go straight, then turn left.",
             "massugu itte, hidari ni magatte kudasai"),
            ("you", [("遠いですか。", "Is it far?", "tōi desu ka"),
                     ("二十歳です。", "I'm twenty years old.", "hatachi desu"),
                     ("また後で。", "See you later.", "mata ato de")]),
            ("them", "いいえ、五分です。", "No, it's five minutes.", "iie, gofun desu"),
            ("you", [("どうもありがとうございます。", "Thank you very much.", "dōmo arigatō gozaimasu"),
                     ("お腹が空いていません。", "I'm not hungry.", "onaka ga suite imasen"),
                     ("私の兄です。", "It's my older brother.", "watashi no ani desu")]),
        ],
    },
}
