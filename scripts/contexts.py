"""Tirage aléatoire des contextes du dataset (phase 3), à partir de configs/pools.yaml.

Les contextes ont le même format que le champ "inputs" des cas d'évaluation
(dates en texte ISO 8601), pour être rendus avec scripts.eval_cases.case_to_inputs.
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from scripts.prompt_format import PARIS_TZ, format_status

POOLS_PATH = Path(__file__).parent.parent / "configs" / "pools.yaml"

OFF_LIVE_RATE = 0.15        # part des contextes hors live
NO_FACTS_RATE = 0.05        # part des contextes sans aucun fait
EXCLUSIVE_GROUP_RATE = 0.6  # chance de tirer un fait dans chaque groupe exclusif
OPAQUE_EMOTE_RATE = 0.2     # part des emotes à suffixe opaque
CATEGORY_WEIGHTS = {        # famille de catégorie -> poids
    "games_with_card": 50,
    "invented_with_card": 15,
    "games_without_card": 15,
    "non_gaming": 20,
}
MENTION_WEIGHTS = {0: 70, 1: 22, 2: 8}  # nombre de viewers mentionnés -> poids
NEW_VIEWER_RATE = 0.25    # profil sans souvenir
FIRST_VISIT_RATE = 0.2    # pas de dernier passage
EMPTY_HISTORY_RATE = 0.1  # historique vide
ROLES = {  # statut tiré -> rôles TwitchIO (tous suivent la chaîne)
    "follower": {"follower"},
    "subscriber": {"subscriber", "follower"},
    "vip": {"vip", "follower"},
    "moderator": {"moderator", "follower"},
}


def load_pools(path: Path = POOLS_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sample_datetime(rng: random.Random, day: date, start_hour: int, end_hour: int) -> datetime:
    """Heure de Paris au hasard ce jour-là, entre start_hour et end_hour."""
    minutes = rng.randint(start_hour * 60, end_hour * 60 - 1)
    return datetime(day.year, day.month, day.day, minutes // 60, minutes % 60, tzinfo=PARIS_TZ)


def sample_live(rng: random.Random, pools: dict) -> dict:
    """Heure de l'appel, début du live, catégorie, genres, description et titre."""
    day = date(2026, 1, 1) + timedelta(days=rng.randint(0, 729))
    if rng.random() < OFF_LIVE_RATE:
        now = sample_datetime(rng, day, 8, 24)
        return {"now": now.isoformat(), "stream_start": None, "title": "",
                "category": None, "genres": None, "description": None}

    start = sample_datetime(rng, day, 18, 23)
    now = start + timedelta(minutes=rng.randint(5, 300))  # peut passer minuit

    family = rng.choices(list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()))[0]
    choice = rng.choice(pools["categories"][family])
    if isinstance(choice, dict):  # jeu avec fiche
        category, genres, description = choice["name"], choice["genres"], choice["description"]
    else:  # jeu sans fiche ou catégorie non gaming
        category, genres, description = choice, None, None

    title = rng.choice(pools["titles"]).replace("{category}", category)
    return {"now": now.isoformat(), "stream_start": start.isoformat(), "title": title,
            "category": category, "genres": genres, "description": description}


def sample_facts(rng: random.Random, pools: dict, streamer: dict) -> list[str]:
    """L'intro du streamer, puis au plus un fait par groupe exclusif et quelques faits libres."""
    if rng.random() < NO_FACTS_RATE:
        return []
    facts = [fact_group[rng.randrange(len(fact_group))]
             for fact_group in pools["exclusive_facts"].values()
             if rng.random() < EXCLUSIVE_GROUP_RATE]
    facts += rng.sample(pools["facts"], k=rng.randint(0, 8))
    rng.shuffle(facts)
    intro = pools["streamer_intro"][streamer["gender"]]
    return [fact.replace("{streamer}", streamer["name"]) for fact in [intro, *facts]]


def sample_emotes(rng: random.Random, pools: dict) -> dict[str, str]:
    """De 0 à 12 emotes avec un même préfixe ; certaines ont un suffixe opaque au sens tiré au hasard."""
    prefix = rng.choice(pools["emote_prefixes"])
    meanings = list(pools["emote_suffixes"].values())
    emotes = {}
    for suffix in rng.sample(list(pools["emote_suffixes"]), k=rng.randint(0, 12)):
        if rng.random() < OPAQUE_EMOTE_RATE:
            emotes[prefix + rng.choice(pools["emote_opaque_suffixes"])] = rng.choice(meanings)
        else:
            emotes[prefix + suffix] = pools["emote_suffixes"][suffix]
    return emotes


def sample_system(rng: random.Random, pools: dict) -> tuple[dict, dict]:
    """Partie system d'un contexte (champs de PromptInputs), plus le streamer tiré (pour l'historique)."""
    streamer = rng.choice(pools["streamers"])
    inputs = {
        "bot_name": rng.choice(pools["bot_names"]),
        "facts": sample_facts(rng, pools, streamer),
        "emotes": sample_emotes(rng, pools),
        **sample_live(rng, pools),
    }
    return inputs, streamer


def sample_profile(rng: random.Random, pools: dict, name: str, now: datetime) -> dict:
    """Profil cohérent : ancienneté d'abonnement <= ancienneté de follow, dernier passage avant aujourd'hui."""
    status = rng.choices(list(pools["status_weights"]), weights=list(pools["status_weights"].values()))[0]
    sub_months = rng.randint(*pools["sub_months"]) if status == "subscriber" else 0
    followed_at = now.date() - timedelta(days=max(rng.randint(0, 900), sub_months * 31))

    days_since_follow = (now.date() - followed_at).days
    last_seen = None
    if days_since_follow >= 1 and rng.random() >= FIRST_VISIT_RATE:
        # Le plus souvent un passage récent ; parfois un retour après une longue absence.
        max_days = min(days_since_follow, 30) if rng.random() < 0.8 else days_since_follow
        last_seen = (now.date() - timedelta(days=rng.randint(1, max_days))).isoformat()

    summary = ""
    if rng.random() >= NEW_VIEWER_RATE:
        summary = " ".join(rng.sample(pools["memories"], k=rng.randint(1, 3)))

    return {
        "name": name,
        "status": format_status(ROLES[status], sub_months),
        "followed_at": followed_at.isoformat(),
        "last_seen": last_seen,
        "summary": summary,
    }


def sample_history(rng, pools, now, profiles, streamer, bot_name, on_live) -> list[dict]:
    """Squelette de l'historique : auteurs, statuts et heures (texte vide, écrit par le générateur)."""
    if rng.random() < EMPTY_HISTORY_RATE:
        return []
    speakers = [(p["name"], p["status"]) for p in profiles]
    others = rng.sample([n for n in pools["viewer_names"] if n not in {p["name"] for p in profiles}], k=3)
    speakers += [(name, "viewer" if rng.random() < 0.2 else "follower") for name in others]
    speakers.append((bot_name, "bot"))
    if on_live:
        speakers.append((streamer["name"], "streamer"))

    times, moment = [], now
    for _ in range(rng.randint(1, 15)):
        moment -= timedelta(minutes=rng.randint(0, 4))
        times.append(moment)
    return [
        {"author": author, "status": status, "text": "", "sent_at": sent_at.isoformat()}
        for sent_at in reversed(times)
        for author, status in [rng.choice(speakers)]
    ]


def sample_context(rng: random.Random, pools: dict) -> tuple[dict, dict]:
    """Contexte complet (champs de PromptInputs, textes vides) et infos pour le générateur."""
    inputs, streamer = sample_system(rng, pools)
    now = datetime.fromisoformat(inputs["now"])

    n_mentions = rng.choices(list(MENTION_WEIGHTS), weights=list(MENTION_WEIGHTS.values()))[0]
    names = rng.sample(pools["viewer_names"], k=1 + n_mentions)
    profiles = [sample_profile(rng, pools, name, now) for name in names]

    inputs["profiles"] = profiles
    inputs["history"] = sample_history(
        rng, pools, now, profiles, streamer, inputs["bot_name"], on_live=inputs["stream_start"] is not None
    )
    inputs["author"] = names[0]
    inputs["message"] = ""
    meta = {"streamer": streamer, "mentioned": names[1:]}
    return inputs, meta
