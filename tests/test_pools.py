import re
from pathlib import Path

import yaml

from scripts.eval_cases import load_cases

POOLS_PATH = Path(__file__).parent.parent / "configs" / "pools.yaml"
DOC_NAMES = {"pixou", "dantekf"}  # exemple de docs/prompt_format.md


def load_pools() -> dict:
    return yaml.safe_load(POOLS_PATH.read_text(encoding="utf-8"))


def test_bot_names_not_in_eval():
    eval_names = {case["inputs"]["bot_name"].casefold() for case in load_cases()} | DOC_NAMES
    overlap = {name for name in load_pools()["bot_names"] if name.casefold() in eval_names}
    assert not overlap, f"Noms de bot déjà utilisés dans l'évaluation : {overlap}"


def test_emote_prefixes_not_in_eval():
    eval_codes = [code.casefold() for case in load_cases() for code in case["inputs"]["emotes"]]
    eval_codes += list(DOC_NAMES)
    overlap = {
        prefix for prefix in load_pools()["emote_prefixes"]
        if any(code.startswith(prefix.casefold()) for code in eval_codes)
    }
    assert not overlap, f"Préfixes d'emotes déjà utilisés dans l'évaluation : {overlap}"


def test_pools_have_no_duplicates():
    pools = load_pools()
    for key in ("bot_names", "emote_prefixes", "emote_opaque_suffixes"):
        assert len(pools[key]) == len(set(pools[key])), f"Doublon dans {key}"


def all_fact_templates(pools: dict) -> list[str]:
    """Faits tirés au hasard. L'intro (« Le streamer s'appelle… ») est exclue : c'est une partie fixe du format."""
    exclusive = [fact for group in pools["exclusive_facts"].values() for fact in group]
    return [schedule["text"] for schedule in pools["schedules"]] + exclusive + pools["facts"]


def all_strings(value) -> list[str]:
    """Tous les textes d'un réservoir (listes et dictionnaires parcourus récursivement)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in all_strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in all_strings(item)]
    return []


def test_no_eval_game_in_pool_texts():
    """Aucun jeu de l'évaluation n'est cité dans un texte des réservoirs (faits, souvenirs, titres, fiches)."""
    pools = load_pools()
    non_gaming = {name.casefold() for name in pools["categories"]["non_gaming"]}
    eval_games = {case["inputs"]["category"] for case in load_cases() if case["inputs"]["category"]}
    eval_games = {game for game in eval_games if game.casefold() not in non_gaming} | {"Hollow Knight"}
    texts = all_strings(pools)
    for game in eval_games:
        pattern = re.compile(r"\b" + re.escape(game) + r"\b", re.IGNORECASE)
        cited = [text for text in texts if pattern.search(text)]
        assert not cited, f"{game} (jeu de l'évaluation) cité dans les réservoirs : {cited}"


WEEKDAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def test_schedules_match_their_text():
    """Les jours et l'heure de chaque horaire sont ceux que son texte annonce."""
    for schedule in load_pools()["schedules"]:
        text = schedule["text"]
        named = [day for day, name in enumerate(WEEKDAY_NAMES) if name in text]
        expected = [0, 1, 2, 3, 4] if "soirs de semaine" in text else named
        assert schedule["days"] == expected, text
        hour, minute = schedule["start"].split(":")
        announced = f"{int(hour)}h{minute if minute != '00' else ''}"
        assert re.search(rf"\b{announced}(?!\d)", text), text  # « 21h » ne doit pas valider « 21h30 »


def test_next_game_is_never_a_category():
    """Le prochain jeu prévu ne peut pas être le jeu en cours."""
    categories = load_pools()["categories"]
    names = [c["name"] if isinstance(c, dict) else c for family in categories.values() for c in family]
    for fact in load_pools()["exclusive_facts"]["next_game"]:
        assert not any(name in fact for name in names), fact


def test_emote_codes_are_ascii():
    """Twitch n'accepte que des lettres et des chiffres sans accent dans un code d'emote."""
    pools = load_pools()
    for part in [*pools["emote_prefixes"], *pools["emote_suffixes"], *pools["emote_opaque_suffixes"]]:
        assert part.isascii() and part.isalnum(), part


def test_streamer_names_need_no_elision():
    """« Config de {streamer} » : un nom qui commence par une voyelle donnerait « de Ondine »."""
    for streamer in load_pools()["streamers"]:
        assert streamer["name"][0].casefold() not in "aeiouéèêàâîôûœ", streamer["name"]  # « de Yanis » est correct


def test_streamers_not_in_eval():
    names = {s["name"].casefold() for s in load_pools()["streamers"]}
    assert not names & {"dantek", "plumetis"}
    assert all(s["gender"] in ("m", "f") for s in load_pools()["streamers"])


def test_facts_not_in_eval():
    """Aucun fait du réservoir (rendu avec Dantek) n'est identique à un fait de l'évaluation."""
    eval_facts = {fact.casefold() for case in load_cases() for fact in case["inputs"]["facts"]}
    rendered = {t.replace("{streamer}", "Dantek").casefold() for t in all_fact_templates(load_pools())}
    overlap = rendered & eval_facts
    assert not overlap, f"Faits identiques à l'évaluation : {overlap}"


def eval_viewer_names() -> set[str]:
    """Tous les pseudos de l'évaluation : auteurs, profils, historique, plus ceux de l'exemple du document."""
    names = {"lunariz", "kraken_bleu", "dantek"}
    for case in load_cases():
        inputs = case["inputs"]
        names.add(inputs["author"].casefold())
        names |= {p["name"].casefold() for p in inputs["profiles"]}
        names |= {m["author"].casefold() for m in inputs["history"]}
    return names


def test_viewer_names_not_in_eval():
    overlap = {n for n in load_pools()["viewer_names"] if n.casefold() in eval_viewer_names()}
    assert not overlap, f"Pseudos déjà utilisés dans l'évaluation : {overlap}"


def test_memories_not_in_eval():
    """Aucun souvenir n'est identique à une phrase d'un résumé de l'évaluation."""
    eval_sentences = set()
    for case in load_cases():
        for profile in case["inputs"]["profiles"]:
            eval_sentences |= {s.strip().casefold() for s in profile["summary"].split(".") if s.strip()}
    memories = {m.rstrip(".").casefold() for m in load_pools()["memories"]}
    overlap = memories & eval_sentences
    assert not overlap, f"Souvenirs identiques à l'évaluation : {overlap}"


def test_status_weights():
    pools = load_pools()
    assert set(pools["status_weights"]) == {"follower", "subscriber", "vip", "moderator"}
    assert len(pools["viewer_names"]) == len(set(pools["viewer_names"]))


def test_games_not_in_eval():
    """Aucun jeu du réservoir n'est un jeu de l'évaluation (les catégories non gaming sont autorisées)."""
    categories = load_pools()["categories"]
    eval_categories = {
        case["inputs"]["category"].casefold() for case in load_cases() if case["inputs"]["category"]
    } | {"hollow knight"}  # exemple du document
    games = [c["name"] for c in categories["games_with_card"] + categories["invented_with_card"]]
    games += categories["games_without_card"]
    overlap = {g for g in games if g.casefold() in eval_categories}
    assert not overlap, f"Jeux déjà utilisés dans l'évaluation : {overlap}"
    for card in categories["games_with_card"] + categories["invented_with_card"]:
        assert card["genres"] and card["description"], f"Fiche incomplète : {card['name']}"
