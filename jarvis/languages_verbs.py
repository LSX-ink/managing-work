"""Verb conjugation tables for the language studio: common regular verbs and the key irregular ones, in the
present, the past and the future. Regular verbs are built from their endings; irregular verbs are written out.

The past tense is the everyday one: preterite (Spanish, Portuguese), passé composé (French), Perfekt (German) and
passato prossimo (Italian). Japanese verbs don't change for person, so its tables list the polite and plain forms.
"""

PERSONS = {
    "es": ["yo", "tú", "él/ella", "nosotros", "vosotros", "ellos/ellas"],
    "fr": ["je", "tu", "il/elle", "nous", "vous", "ils/elles"],
    "de": ["ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie"],
    "it": ["io", "tu", "lui/lei", "noi", "voi", "loro"],
    "pt": ["eu", "tu", "ele/ela", "nós", "eles/elas"],
}
TENSE_NAMES = {
    "es": ("Present", "Past (preterite)", "Future"),
    "fr": ("Present", "Past (passé composé)", "Future"),
    "de": ("Present", "Past (Perfekt)", "Future"),
    "it": ("Present", "Past (passato prossimo)", "Future"),
    "pt": ("Present", "Past (pretérito perfeito)", "Future"),
    "ja": ("Present", "Past", "Future"),
}


def _add(stem: str, endings: str) -> list[str]:
    return [stem + e for e in endings.split()]


def _spanish(inf: str, meaning: str) -> dict:
    stem, kind = inf[:-2], inf[-2:]
    present = {"ar": "o as a amos áis an", "er": "o es e emos éis en", "ir": "o es e imos ís en"}[kind]
    past = "é aste ó amos asteis aron" if kind == "ar" else "í iste ió imos isteis ieron"
    return {"meaning": meaning, "present": _add(stem, present), "past": _add(stem, past),
            "future": _add(inf, "é ás á emos éis án")}


def _french_er(inf: str, meaning: str) -> dict:
    stem = inf[:-2]
    return {"meaning": meaning, "present": _add(stem, "e es e ons ez ent"), "past": _french_past(stem + "é"),
            "future": _add(inf, "ai as a ons ez ont")}


def _french_ir(inf: str, meaning: str) -> dict:
    stem = inf[:-1]
    return {"meaning": meaning, "present": _add(stem, "s s t ssons ssez ssent"), "past": _french_past(stem + "i"),
            "future": _add(inf, "ai as a ons ez ont")}


def _french_past(participle: str) -> list[str]:
    return [f"{aux} {participle}" for aux in "ai as a avons avez ont".split()]


def _german_past(participle: str, aux: str = "haben") -> list[str]:
    forms = "habe hast hat haben habt haben" if aux == "haben" else "bin bist ist sind seid sind"
    return [f"{f} {participle}" for f in forms.split()]


def _german_future(inf: str) -> list[str]:
    return [f"{f} {inf}" for f in "werde wirst wird werden werdet werden".split()]


def _german(inf: str, meaning: str, present: str, participle: str, aux: str = "haben") -> dict:
    return {"meaning": meaning, "present": present.split(), "past": _german_past(participle, aux),
            "future": _german_future(inf)}


def _italian_past(participle: str, aux: str = "avere") -> list[str]:
    if aux == "avere":
        return [f"{f} {participle}" for f in "ho hai ha abbiamo avete hanno".split()]
    stem = participle[:-1]
    return [f"sono {stem}o/a", f"sei {stem}o/a", f"è {stem}o/a", f"siamo {stem}i/e", f"siete {stem}i/e",
            f"sono {stem}i/e"]


def _portuguese(inf: str, meaning: str) -> dict:
    stem, kind = inf[:-2], inf[-2:]
    present = {"ar": "o as a amos am", "er": "o es e emos em"}[kind]
    past = "ei aste ou ámos aram" if kind == "ar" else "i este eu emos eram"
    return {"meaning": meaning, "present": _add(stem, present), "past": _add(stem, past),
            "future": _add(inf, "ei ás á emos ão")}


def _japanese(plain: str, roman: str, meaning: str, polite: str, polite_roman: str, past: str, past_roman: str,
              plain_past: str, plain_past_roman: str, negative: str, negative_roman: str) -> dict:
    return {
        "meaning": meaning,
        "present": [["polite", f"{polite} ({polite_roman})"], ["plain", f"{plain} ({roman})"],
                    ["polite negative", f"{negative} ({negative_roman})"]],
        "past": [["polite", f"{past} ({past_roman})"], ["plain", f"{plain_past} ({plain_past_roman})"]],
        "future": [["polite", f"{polite} ({polite_roman})"], ["plain", f"{plain} ({roman})"]],
        "note": "Japanese uses the present form for the future too; add a time word like tomorrow (ashita).",
    }


VERBS = {
    "es": {
        "ser": {"meaning": "to be (permanent things)", "present": "soy eres es somos sois son".split(),
                "past": "fui fuiste fue fuimos fuisteis fueron".split(),
                "future": "seré serás será seremos seréis serán".split()},
        "estar": {"meaning": "to be (places, feelings)", "present": "estoy estás está estamos estáis están".split(),
                  "past": "estuve estuviste estuvo estuvimos estuvisteis estuvieron".split(),
                  "future": _add("estar", "é ás á emos éis án")},
        "tener": {"meaning": "to have", "present": "tengo tienes tiene tenemos tenéis tienen".split(),
                  "past": "tuve tuviste tuvo tuvimos tuvisteis tuvieron".split(),
                  "future": "tendré tendrás tendrá tendremos tendréis tendrán".split()},
        "ir": {"meaning": "to go", "present": "voy vas va vamos vais van".split(),
               "past": "fui fuiste fue fuimos fuisteis fueron".split(),
               "future": "iré irás irá iremos iréis irán".split()},
        "hacer": {"meaning": "to do, to make", "present": "hago haces hace hacemos hacéis hacen".split(),
                  "past": "hice hiciste hizo hicimos hicisteis hicieron".split(),
                  "future": "haré harás hará haremos haréis harán".split()},
        "hablar": _spanish("hablar", "to speak"),
        "comer": _spanish("comer", "to eat"),
        "vivir": _spanish("vivir", "to live"),
    },
    "fr": {
        "être": {"meaning": "to be", "present": "suis es est sommes êtes sont".split(),
                 "past": _french_past("été"), "future": "serai seras sera serons serez seront".split()},
        "avoir": {"meaning": "to have", "present": "ai as a avons avez ont".split(),
                  "past": _french_past("eu"), "future": "aurai auras aura aurons aurez auront".split()},
        "aller": {"meaning": "to go", "present": "vais vas va allons allez vont".split(),
                  "past": ["suis allé(e)", "es allé(e)", "est allé(e)", "sommes allé(e)s", "êtes allé(e)(s)",
                           "sont allé(e)s"],
                  "future": "irai iras ira irons irez iront".split()},
        "faire": {"meaning": "to do, to make", "present": "fais fais fait faisons faites font".split(),
                  "past": _french_past("fait"), "future": "ferai feras fera ferons ferez feront".split()},
        "prendre": {"meaning": "to take", "present": "prends prends prend prenons prenez prennent".split(),
                    "past": _french_past("pris"), "future": "prendrai prendras prendra prendrons prendrez prendront".split()},
        "parler": _french_er("parler", "to speak"),
        "finir": _french_ir("finir", "to finish"),
    },
    "de": {
        "sein": _german("sein", "to be", "bin bist ist sind seid sind", "gewesen", "sein"),
        "haben": _german("haben", "to have", "habe hast hat haben habt haben", "gehabt"),
        "gehen": _german("gehen", "to go", "gehe gehst geht gehen geht gehen", "gegangen", "sein"),
        "machen": _german("machen", "to do, to make", "mache machst macht machen macht machen", "gemacht"),
        "sprechen": _german("sprechen", "to speak", "spreche sprichst spricht sprechen sprecht sprechen",
                            "gesprochen"),
        "essen": _german("essen", "to eat", "esse isst isst essen esst essen", "gegessen"),
        "wollen": _german("wollen", "to want", "will willst will wollen wollt wollen", "gewollt"),
    },
    "it": {
        "essere": {"meaning": "to be", "present": "sono sei è siamo siete sono".split(),
                   "past": _italian_past("stato", "essere"), "future": "sarò sarai sarà saremo sarete saranno".split()},
        "avere": {"meaning": "to have", "present": "ho hai ha abbiamo avete hanno".split(),
                  "past": _italian_past("avuto"), "future": "avrò avrai avrà avremo avrete avranno".split()},
        "andare": {"meaning": "to go", "present": "vado vai va andiamo andate vanno".split(),
                   "past": _italian_past("andato", "essere"),
                   "future": "andrò andrai andrà andremo andrete andranno".split()},
        "fare": {"meaning": "to do, to make", "present": "faccio fai fa facciamo fate fanno".split(),
                 "past": _italian_past("fatto"), "future": "farò farai farà faremo farete faranno".split()},
        "volere": {"meaning": "to want", "present": "voglio vuoi vuole vogliamo volete vogliono".split(),
                   "past": _italian_past("voluto"), "future": "vorrò vorrai vorrà vorremo vorrete vorranno".split()},
        "parlare": {"meaning": "to speak", "present": "parlo parli parla parliamo parlate parlano".split(),
                    "past": _italian_past("parlato"), "future": "parlerò parlerai parlerà parleremo parlerete parleranno".split()},
        "mangiare": {"meaning": "to eat", "present": "mangio mangi mangia mangiamo mangiate mangiano".split(),
                     "past": _italian_past("mangiato"),
                     "future": "mangerò mangerai mangerà mangeremo mangerete mangeranno".split()},
    },
    "pt": {
        "ser": {"meaning": "to be (permanent things)", "present": "sou és é somos são".split(),
                "past": "fui foste foi fomos foram".split(), "future": "serei serás será seremos serão".split()},
        "estar": {"meaning": "to be (places, feelings)", "present": "estou estás está estamos estão".split(),
                  "past": "estive estiveste esteve estivemos estiveram".split(),
                  "future": "estarei estarás estará estaremos estarão".split()},
        "ter": {"meaning": "to have", "present": "tenho tens tem temos têm".split(),
                "past": "tive tiveste teve tivemos tiveram".split(),
                "future": "terei terás terá teremos terão".split()},
        "ir": {"meaning": "to go", "present": "vou vais vai vamos vão".split(),
               "past": "fui foste foi fomos foram".split(), "future": "irei irás irá iremos irão".split()},
        "fazer": {"meaning": "to do, to make", "present": "faço fazes faz fazemos fazem".split(),
                  "past": "fiz fizeste fez fizemos fizeram".split(),
                  "future": "farei farás fará faremos farão".split()},
        "falar": _portuguese("falar", "to speak"),
        "comer": _portuguese("comer", "to eat"),
    },
    "ja": {
        "taberu": _japanese("食べる", "taberu", "to eat", "食べます", "tabemasu", "食べました", "tabemashita",
                            "食べた", "tabeta", "食べません", "tabemasen"),
        "iku": _japanese("行く", "iku", "to go", "行きます", "ikimasu", "行きました", "ikimashita",
                         "行った", "itta", "行きません", "ikimasen"),
        "suru": _japanese("する", "suru", "to do", "します", "shimasu", "しました", "shimashita",
                          "した", "shita", "しません", "shimasen"),
        "nomu": _japanese("飲む", "nomu", "to drink", "飲みます", "nomimasu", "飲みました", "nomimashita",
                          "飲んだ", "nonda", "飲みません", "nomimasen"),
        "miru": _japanese("見る", "miru", "to see, to watch", "見ます", "mimasu", "見ました", "mimashita",
                          "見た", "mita", "見ません", "mimasen"),
        "kuru": _japanese("来る", "kuru", "to come", "来ます", "kimasu", "来ました", "kimashita",
                          "来た", "kita", "来ません", "kimasen"),
        "hanasu": _japanese("話す", "hanasu", "to speak", "話します", "hanashimasu", "話しました", "hanashimashita",
                            "話した", "hanashita", "話しません", "hanashimasen"),
    },
}


def verb_names(lang: str) -> list[str]:
    return list(VERBS[lang])


def find_verb(lang: str, name: str) -> str | None:
    """The verb in that language for a spelling, an unaccented spelling or an English meaning like "to go"."""
    want = " ".join(str(name or "").lower().split())
    if not want:
        return None
    for key, info in VERBS[lang].items():
        senses = [m.strip() for m in info["meaning"].lower().split(" (")[0].split(",")]
        senses += [m.replace("to ", "", 1) for m in senses]
        if want in senses + [key.lower(), key.lower().replace("ê", "e")]:
            return key
    return None


def table(lang: str, verb: str) -> dict:
    """The tenses of a verb as rows of [person, form]."""
    info = VERBS[lang][verb]
    tenses = []
    for name, key in zip(TENSE_NAMES[lang], ("present", "past", "future")):
        forms = info[key]
        if lang == "ja":
            rows = [list(r) for r in forms]
        else:
            rows = [[p, f] for p, f in zip(PERSONS[lang], forms)]
            if lang == "fr":
                rows = [_french_row(r) for r in rows]
        tenses.append({"name": name, "rows": rows})
    return {"verb": verb, "meaning": info["meaning"], "tenses": tenses, "note": info.get("note", "")}


def _french_row(row: list[str]) -> list[str]:
    person, form = row
    if person == "je" and form[:1] in "aeiouéèêhàâ":
        return ["j'", form]
    return row
