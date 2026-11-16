from scripts.checks import count_sentences, has_markdown, run_checks, detect_language, summarize, language_ok
from scripts.eval_cases import load_cases


def test_count_sentences():
    assert count_sentences("Salut !") == 1
    assert count_sentences("Bravo ! plumeGG") == 1
    assert count_sentences("Une. Deux ! Trois ?") == 3
    assert count_sentences("pas de ponctuation") == 1
    assert count_sentences("La version 1.5 est sortie.") == 1


def test_has_markdown():
    assert has_markdown("Un mot en **gras**.")
    assert has_markdown("Voici :\n- un\n- deux")
    assert not has_markdown("Une réponse simple - sans liste.")


def test_run_checks():
    checks = {"language": "fr", "max_sentences": 2, "must_include_any": ["sais pas"], "must_not_match": r"\d+ ans"}
    assert all(run_checks("Je ne SAIS PAS quel âge il a.", checks).values())
    assert run_checks("Dantek a 28 ans. Il est cool. Voilà !", checks) == {
        "max_sentences": False,
        "no_markdown": True,
        "must_include_any": False,
        "must_not_match": False,
        "language": True,
        "no_brackets": True,
    }


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
