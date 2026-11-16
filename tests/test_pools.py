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
    return exclusive + pools["facts"]


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
