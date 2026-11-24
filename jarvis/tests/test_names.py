import names


def test_misheard_chefmotso_is_put_right():
    assert "ChefMotso" in names.correct("open chef modzo for me")
    assert "ChefMotso" in names.correct("what did we do for chef mods")
    assert names.mentioned("tell me about chef motso website") == ["ChefMotso"]
    assert "TKS Consulting" in names.mentioned("any news on t k s")


def test_ordinary_words_are_left_alone():
    assert names.correct("set a timer for ten minutes") == "set a timer for ten minutes"
    assert names.mentioned("what's the weather like") == []


def test_misheard_web_addresses_of_our_sites():
    assert names.fix_url("https://chefmodzo.com") == "https://chefmotso.com"
    assert names.fix_url("https://www.chefmotzo.com/") == "https://chefmotso.com/"
    assert names.fix_url("https://bbc.co.uk/news") == "https://bbc.co.uk/news"
    assert names.prompt_section().count("ChefMotso") >= 2
