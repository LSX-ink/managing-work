"""Built-in starter vocabulary for the language studio: six languages, six topic decks each, numbers and tips.

A vocabulary entry is a string: "article word:g" for nouns (g is m, f or n), "phrase" for other words, and
"kanji|romaji" for Japanese. The English lists and the language lists line up one to one.
European Portuguese is used. Everything here is small on purpose: a starting point, not a dictionary.
"""

LANGS = {
    "es": {"name": "Spanish", "speech": "es-ES", "hello": "Hola"},
    "fr": {"name": "French", "speech": "fr-FR", "hello": "Bonjour"},
    "de": {"name": "German", "speech": "de-DE", "hello": "Hallo"},
    "it": {"name": "Italian", "speech": "it-IT", "hello": "Ciao"},
    "pt": {"name": "Portuguese", "speech": "pt-PT", "hello": "Olá"},
    "ja": {"name": "Japanese", "speech": "ja-JP", "hello": "こんにちは"},
}

TOPIC_NAMES = {"greetings": "Greetings", "food": "Food and drink", "travel": "Travel", "family": "Family",
               "time": "Time", "home": "Home"}

ENGLISH = {
    "greetings": ["hello", "goodbye", "please", "thank you", "sorry", "yes", "no", "good morning", "good night",
                  "how are you?"],
    "food": ["bread", "tea", "milk", "cheese", "apple", "chicken", "rice", "coffee", "egg", "fish"],
    "travel": ["ticket", "train", "airport", "hotel", "passport", "map", "bus", "station", "street", "suitcase"],
    "family": ["mother", "father", "sister", "brother", "grandmother", "grandfather", "son", "daughter", "friend",
               "baby"],
    "time": ["day", "week", "month", "year", "today", "tomorrow", "yesterday", "morning", "night", "hour"],
    "home": ["house", "room", "kitchen", "table", "chair", "window", "door", "bed", "book", "key"],
}

VOCAB = {
    "es": {
        "greetings": ["hola", "adiós", "por favor", "gracias", "lo siento", "sí", "no", "buenos días",
                      "buenas noches", "¿cómo estás?"],
        "food": ["el pan:m", "el té:m", "la leche:f", "el queso:m", "la manzana:f", "el pollo:m", "el arroz:m",
                 "el café:m", "el huevo:m", "el pescado:m"],
        "travel": ["el billete:m", "el tren:m", "el aeropuerto:m", "el hotel:m", "el pasaporte:m", "el mapa:m",
                   "el autobús:m", "la estación:f", "la calle:f", "la maleta:f"],
        "family": ["la madre:f", "el padre:m", "la hermana:f", "el hermano:m", "la abuela:f", "el abuelo:m",
                   "el hijo:m", "la hija:f", "el amigo:m", "el bebé:m"],
        "time": ["el día:m", "la semana:f", "el mes:m", "el año:m", "hoy", "mañana", "ayer", "la mañana:f",
                 "la noche:f", "la hora:f"],
        "home": ["la casa:f", "la habitación:f", "la cocina:f", "la mesa:f", "la silla:f", "la ventana:f",
                 "la puerta:f", "la cama:f", "el libro:m", "la llave:f"],
    },
    "fr": {
        "greetings": ["salut", "au revoir", "s'il vous plaît", "merci", "désolé", "oui", "non", "bonjour",
                      "bonne nuit", "comment ça va ?"],
        "food": ["le pain:m", "le thé:m", "le lait:m", "le fromage:m", "la pomme:f", "le poulet:m", "le riz:m",
                 "le café:m", "l'œuf:m", "le poisson:m"],
        "travel": ["le billet:m", "le train:m", "l'aéroport:m", "l'hôtel:m", "le passeport:m", "la carte:f",
                   "le bus:m", "la gare:f", "la rue:f", "la valise:f"],
        "family": ["la mère:f", "le père:m", "la sœur:f", "le frère:m", "la grand-mère:f", "le grand-père:m",
                   "le fils:m", "la fille:f", "l'ami:m", "le bébé:m"],
        "time": ["le jour:m", "la semaine:f", "le mois:m", "l'année:f", "aujourd'hui", "demain", "hier",
                 "le matin:m", "la nuit:f", "l'heure:f"],
        "home": ["la maison:f", "la chambre:f", "la cuisine:f", "la table:f", "la chaise:f", "la fenêtre:f",
                 "la porte:f", "le lit:m", "le livre:m", "la clé:f"],
    },
    "de": {
        "greetings": ["hallo", "auf Wiedersehen", "bitte", "danke", "Entschuldigung", "ja", "nein",
                      "guten Morgen", "gute Nacht", "wie geht's?"],
        "food": ["das Brot:n", "der Tee:m", "die Milch:f", "der Käse:m", "der Apfel:m", "das Hähnchen:n",
                 "der Reis:m", "der Kaffee:m", "das Ei:n", "der Fisch:m"],
        "travel": ["die Fahrkarte:f", "der Zug:m", "der Flughafen:m", "das Hotel:n", "der Reisepass:m",
                   "die Karte:f", "der Bus:m", "der Bahnhof:m", "die Straße:f", "der Koffer:m"],
        "family": ["die Mutter:f", "der Vater:m", "die Schwester:f", "der Bruder:m", "die Oma:f", "der Opa:m",
                   "der Sohn:m", "die Tochter:f", "der Freund:m", "das Baby:n"],
        "time": ["der Tag:m", "die Woche:f", "der Monat:m", "das Jahr:n", "heute", "morgen", "gestern",
                 "der Morgen:m", "die Nacht:f", "die Stunde:f"],
        "home": ["das Haus:n", "das Zimmer:n", "die Küche:f", "der Tisch:m", "der Stuhl:m", "das Fenster:n",
                 "die Tür:f", "das Bett:n", "das Buch:n", "der Schlüssel:m"],
    },
    "it": {
        "greetings": ["ciao", "arrivederci", "per favore", "grazie", "scusa", "sì", "no", "buongiorno",
                      "buonanotte", "come stai?"],
        "food": ["il pane:m", "il tè:m", "il latte:m", "il formaggio:m", "la mela:f", "il pollo:m", "il riso:m",
                 "il caffè:m", "l'uovo:m", "il pesce:m"],
        "travel": ["il biglietto:m", "il treno:m", "l'aeroporto:m", "l'albergo:m", "il passaporto:m", "la mappa:f",
                   "l'autobus:m", "la stazione:f", "la strada:f", "la valigia:f"],
        "family": ["la madre:f", "il padre:m", "la sorella:f", "il fratello:m", "la nonna:f", "il nonno:m",
                   "il figlio:m", "la figlia:f", "l'amico:m", "il neonato:m"],
        "time": ["il giorno:m", "la settimana:f", "il mese:m", "l'anno:m", "oggi", "domani", "ieri",
                 "la mattina:f", "la notte:f", "l'ora:f"],
        "home": ["la casa:f", "la stanza:f", "la cucina:f", "il tavolo:m", "la sedia:f", "la finestra:f",
                 "la porta:f", "il letto:m", "il libro:m", "la chiave:f"],
    },
    "pt": {
        "greetings": ["olá", "adeus", "por favor", "obrigado", "desculpa", "sim", "não", "bom dia", "boa noite",
                      "como estás?"],
        "food": ["o pão:m", "o chá:m", "o leite:m", "o queijo:m", "a maçã:f", "o frango:m", "o arroz:m",
                 "o café:m", "o ovo:m", "o peixe:m"],
        "travel": ["o bilhete:m", "o comboio:m", "o aeroporto:m", "o hotel:m", "o passaporte:m", "o mapa:m",
                   "o autocarro:m", "a estação:f", "a rua:f", "a mala:f"],
        "family": ["a mãe:f", "o pai:m", "a irmã:f", "o irmão:m", "a avó:f", "o avô:m", "o filho:m", "a filha:f",
                   "o amigo:m", "o bebé:m"],
        "time": ["o dia:m", "a semana:f", "o mês:m", "o ano:m", "hoje", "amanhã", "ontem", "a manhã:f",
                 "a noite:f", "a hora:f"],
        "home": ["a casa:f", "o quarto:m", "a cozinha:f", "a mesa:f", "a cadeira:f", "a janela:f", "a porta:f",
                 "a cama:f", "o livro:m", "a chave:f"],
    },
    "ja": {
        "greetings": ["こんにちは|konnichiwa", "さようなら|sayōnara", "お願いします|onegai shimasu",
                      "ありがとう|arigatō", "ごめんなさい|gomen nasai", "はい|hai", "いいえ|iie",
                      "おはようございます|ohayō gozaimasu", "おやすみなさい|oyasumi nasai",
                      "お元気ですか|o-genki desu ka"],
        "food": ["パン|pan", "お茶|ocha", "牛乳|gyūnyū", "チーズ|chīzu", "りんご|ringo", "鶏肉|toriniku",
                 "ご飯|gohan", "コーヒー|kōhī", "卵|tamago", "魚|sakana"],
        "travel": ["切符|kippu", "電車|densha", "空港|kūkō", "ホテル|hoteru", "パスポート|pasupōto", "地図|chizu",
                   "バス|basu", "駅|eki", "道|michi", "スーツケース|sūtsukēsu"],
        "family": ["母|haha", "父|chichi", "姉|ane", "兄|ani", "祖母|sobo", "祖父|sofu", "息子|musuko",
                   "娘|musume", "友達|tomodachi", "赤ちゃん|akachan"],
        "time": ["日|hi", "一週間|isshūkan", "一か月|ikkagetsu", "年|nen", "今日|kyō", "明日|ashita",
                 "昨日|kinō", "朝|asa", "夜|yoru", "時間|jikan"],
        "home": ["家|ie", "部屋|heya", "台所|daidokoro", "テーブル|tēburu", "椅子|isu", "窓|mado", "ドア|doa",
                 "ベッド|beddo", "本|hon", "鍵|kagi"],
    },
}

# 0 to 20, then 30, 40, 50, 60, 70, 80, 90 and 100.
NUMBER_VALUES = list(range(0, 21)) + [30, 40, 50, 60, 70, 80, 90, 100]
NUMBER_WORDS = {
    "es": "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis "
          "diecisiete dieciocho diecinueve veinte treinta cuarenta cincuenta sesenta setenta ochenta noventa cien",
    "fr": "zéro un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize dix-sept "
          "dix-huit dix-neuf vingt trente quarante cinquante soixante soixante-dix quatre-vingts quatre-vingt-dix "
          "cent",
    "de": "null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn vierzehn fünfzehn "
          "sechzehn siebzehn achtzehn neunzehn zwanzig dreißig vierzig fünfzig sechzig siebzig achtzig neunzig "
          "hundert",
    "it": "zero uno due tre quattro cinque sei sette otto nove dieci undici dodici tredici quattordici quindici "
          "sedici diciassette diciotto diciannove venti trenta quaranta cinquanta sessanta settanta ottanta "
          "novanta cento",
    "pt": "zero um dois três quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezasseis "
          "dezassete dezoito dezanove vinte trinta quarenta cinquenta sessenta setenta oitenta noventa cem",
}
JA_DIGITS = [("ゼロ", "zero"), ("一", "ichi"), ("二", "ni"), ("三", "san"), ("四", "yon"), ("五", "go"),
             ("六", "roku"), ("七", "nana"), ("八", "hachi"), ("九", "kyū")]


def _japanese_number(n: int) -> str:
    if n < 10:
        return "|".join(JA_DIGITS[n])
    if n == 100:
        return "百|hyaku"
    tens, unit = divmod(n, 10)
    kanji, roman = ("十", "jū") if tens == 1 else (JA_DIGITS[tens][0] + "十", JA_DIGITS[tens][1] + "jū")
    if unit:
        kanji, roman = kanji + JA_DIGITS[unit][0], roman + JA_DIGITS[unit][1]
    return f"{kanji}|{roman}"


def number_words(lang: str) -> list[str]:
    """Written-out numbers for NUMBER_VALUES in that language (Japanese as "kanji|romaji")."""
    if lang == "ja":
        return [_japanese_number(n) for n in NUMBER_VALUES]
    return NUMBER_WORDS[lang].split()


TIPS = {
    "es": ["Every vowel is short and clean: a, e, i, o, u, always the same.",
           "J sounds like a rough h; H is silent; LL sounds like y.",
           "Ñ is like ny in canyon; the rolled rr needs a quick tongue tap.",
           "Words ending in a vowel, n or s stress the second-to-last syllable; an accent mark overrides that.",
           "Questions and exclamations start with an upside-down mark: ¿Cómo estás?"],
    "fr": ["The last consonant of a word is often silent: petit, vous, grand.",
           "R is made at the back of the throat; U is oo said with rounded lips.",
           "Nasal vowels (an, on, in) are said through the nose without a hard n.",
           "Liaison: a silent final consonant links to a vowel next: vous avez sounds like vou-z-avez.",
           "Stress is even; the last syllable is only slightly longer."],
    "de": ["W sounds like v, V often sounds like f, and Z sounds like ts.",
           "CH after e or i is a soft hiss (ich); after a, o, u it is deeper (Bach).",
           "ß is a sharp double s; ä, ö, ü are separate vowels, not decoration.",
           "Every noun starts with a capital letter and has der, die or das: learn them together.",
           "Verbs go second in a main clause: Ich trinke Tee."],
    "it": ["Double consonants are held longer: pena and penna sound different.",
           "C before e or i is ch (ciao); before a, o, u it is k (casa). Add h to keep k: che.",
           "GN is like ny (gnocchi); GLI is like lli in million.",
           "Vowels are pure and every letter is pronounced; stress is usually the second-to-last syllable.",
           "Lo, uno and gli go before z, s+consonant and gn: lo zaino."],
    "pt": ["Nasal endings (ão, ãe, em) are said through the nose: pão, mãe.",
           "In European Portuguese unstressed vowels are swallowed: falar sounds like f'lar.",
           "LH is like lli in million; NH is like ny; CH is sh.",
           "S at the end of a word sounds like sh in Portugal.",
           "The tilde ~ and accents mark stress and nasal sounds: learn them with each word."],
    "ja": ["Five pure vowels: a, i, u, e, o. Say each short and clear.",
           "Every syllable takes about the same time; a bar over a vowel (ō, ū) means say it twice as long.",
           "Doubled consonants like kippu have a tiny pause before the second p.",
           "R is a quick tap between English r, d and l.",
           "Words are written in hiragana, katakana or kanji; romaji here just shows the sound."],
}
