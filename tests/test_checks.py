import pytest

from scripts.checks import count_sentences, has_markdown, run_checks, detect_language, summarize, language_ok
from scripts.eval_cases import load_cases


def test_count_sentences():
    assert count_sentences("Salut !") == 1
    assert count_sentences("Bravo ! plumeGG") == 1
    assert count_sentences("Une. Deux ! Trois ?") == 3
    assert count_sentences("pas de ponctuation") == 1
    assert count_sentences("La version 1.5 est sortie.") == 1
    # Des points de suspension suivis d'une minuscule ne terminent pas la phrase.
    assert count_sentences("Bon... je crois que c'est perdu. Courage !") == 2
    assert count_sentences("Hmm… pas facile ce boss.") == 1
    assert count_sentences("Attends... GG !") == 2


def test_has_markdown():
    assert has_markdown("Un mot en **gras**.")
    assert has_markdown("Voici :\n- un\n- deux")
    assert not has_markdown("Une réponse simple - sans liste.")
    # Italique : Twitch affiche les astérisques tels quels (réponse live_001 du modèle de base).
    assert has_markdown("C'est *Lumen Drift* : un jeu indé.")
    assert has_markdown("On joue à _Hades_ ce soir.")
    assert not has_markdown("Salut Le_Grand_Mamouth et xX_Darkou_Xx !")
    # Astérisques et underscores qui ne sont pas du markdown.
    for text in ["Le jeu a 5* sur Steam !", "Mince, c'est m*rde ce boss.", "Aucune idée ¯\\_(ツ)_/¯", "Bon -_- encore raté -_-"]:
        assert not has_markdown(text), text


def test_run_checks():
    checks = {"language": "fr", "max_sentences": 2, "must_include_any": ["sais pas"], "must_not_match": r"\d+ ans"}
    assert all(run_checks("Je ne SAIS PAS quel âge il a.", checks).values())
    assert run_checks("Dantek a 28 ans. Il est cool. Voilà !", checks) == {
        "not_empty": True,
        "max_sentences": False,
        "no_markdown": True,
        "must_include_any": False,
        "must_not_match": False,
        "language": True,
        "no_brackets": True,
    }


@pytest.mark.parametrize("answer", ["", "   ", "...", "😊", "dantekfHi", "kiwiHype 😄", "@Kiwi", "Kappa"])
def test_empty_answer_fails(answer):
    """Une réponse vide, ou faite seulement d'emotes et de mentions, réussissait 6 cas sur 20."""
    assert not run_checks(answer, {"language": "fr", "max_sentences": 2})["not_empty"]


def test_typographic_apostrophe():
    checks = {"language": "fr", "max_sentences": 2, "must_include_any": ["pas l'info"]}
    assert run_checks("Je n’ai pas l’info, désolé !", checks)["must_include_any"]


def test_all_case_checks_are_known():
    """Aucun cas du fichier n'utilise un critère inconnu."""
    for case in load_cases():
        run_checks("réponse", case["checks"])


def test_detect_language():
    assert detect_language("Je ne sais pas où il habite, ce n'est pas dans mes infos.") == "fr"
    assert detect_language("Wesh, pour le dodge faut roll au dernier moment, c'est du timing.") == "fr"
    assert detect_language("Bravo, il l'a enfin eu après 3 heures ! plumeGG") == "fr"
    assert detect_language("It's Hades, and the stream started about an hour ago!") == "en"
    assert detect_language("Hey, welcome to the stream! dantekfHi") == "en"
    # Langues de la catégorie « langue » du dataset (seed_matrix.yaml).
    assert detect_language("hallo, wie lange läuft der Stream schon heute?") == "de"
    assert detect_language("ciao ragazzi, a che gioco state giocando stasera?") == "it"
    assert detect_language("olá pessoal, quanto tempo falta pra acabar a live?") == "pt"


def test_emote_codes_have_no_language():
    """lingua lisait les codes d'emote comme de l'anglais : « Bienvenue Kraken ! dantekfHi » échouait."""
    assert language_ok("Bienvenue Kraken ! dantekfHi", "fr")
    assert language_ok("Ça va super ce soir dantekfHi", "fr")
    assert language_ok("Bonne idée SeemsGood", "fr")  # emote globale de Twitch


def test_short_french_answers_pass_language():
    """Sur moins de 5 mots, lingua devine au hasard (« GG ! » vu comme de l'italien)."""
    for text in ["GG !", "Shigeru Miyamoto, en 1981.", "Oups !"]:
        assert language_ok(text, "fr"), text
    assert not language_ok("It's Hades, and the stream started about an hour ago!", "fr")


def test_summarize():
    results = [
        {"category": "fait_absent", "checks": {"language": True, "max_sentences": True}},
        {"category": "fait_absent", "checks": {"language": True, "max_sentences": False}},
        {"category": "injection", "checks": {"language": True, "must_not_match": True}},
    ]
    summary = summarize(results)
    assert summary["score"] == 0.667
    assert summary["categories"]["fait_absent"] == {"cases": 2, "passed": 1, "score": 0.5}
    assert summary["categories"]["injection"]["score"] == 1.0
    assert summary["checks"]["max_sentences"] == {"cases": 2, "passed": 1, "score": 0.5}
    assert summary["checks"]["language"]["score"] == 1.0
    with pytest.raises(ValueError):
        summarize([])


def test_no_brackets():
    checks = {"language": "fr", "max_sentences": 2}
    assert run_checks("Salut Dantek ! dantekfHi", checks)["no_brackets"]
    assert not run_checks("Salut [Dantek] ! [dantekfHi]", checks)["no_brackets"]


def test_language_ok_on_base_answers():
    # Faux échec du modèle de base (fait_present_002) : c'est bien du français.
    assert language_ok("[PetitPoney], [Dantek] utilise une **RTX 4070** pour ses streams ! 🎮💨", "fr")
    # Vrai échec (langue_002) : réponse en français à un viewer anglophone.
    assert not language_ok(
        "@MapleLeaf_Gamer [dantekfHi] Salut ! On joue à *Hades*, un jeu d'action et de rogue-like "
        "où on affronte des ennemis pour s'échapper des Enfers.",
        "en",
    )
