"""Tirage aléatoire des contextes du dataset (phase 3), à partir de configs/pools.yaml.

Les contextes ont le même format que le champ "inputs" des cas d'évaluation
(dates en texte ISO 8601), pour être rendus avec scripts.eval_cases.case_to_inputs.
"""

import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from scripts.prompt_format import PARIS_TZ, format_status

POOLS_PATH = Path(__file__).parent.parent / "configs" / "pools.yaml"
MATRIX_PATH = Path(__file__).parent.parent / "configs" / "seed_matrix.yaml"


OFF_LIVE_RATE = 0.15        # part des contextes hors live
NO_FACTS_RATE = 0.05        # part des contextes sans aucun fait
EXCLUSIVE_GROUP_RATE = 0.6  # chance de tirer un fait dans chaque groupe exclusif (horaire compris)
UNSCHEDULED_LIVE_RATE = 0.15  # live exceptionnel : hors des jours et heures de l'horaire tiré
OPAQUE_EMOTE_RATE = 0.2     # part des emotes à suffixe opaque
CATEGORY_WEIGHTS = {        # famille de catégorie -> poids
    "games_with_card": 50,
    "invented_with_card": 15,
    "games_without_card": 15,
    "non_gaming": 20,
}
MENTION_WEIGHTS = {0: 70, 1: 22, 2: 8}  # nombre de viewers mentionnés -> poids
NEW_VIEWER_RATE = 0.25    # profil sans souvenir
FIRST_VISIT_RATE = 0.2    # pas de dernier passage (et donc aucun souvenir) ; jamais pour un modo ou un VIP
REGULAR_STATUSES = ("vip", "moderator")  # rôles donnés à des habitués : le bot les a déjà vus écrire
EMPTY_HISTORY_RATE = 0.1  # historique vide
LONG_HISTORY_RATE = 0.1   # chat animé pendant un live (rarement tronqué au plafond de 1 300 tokens)
LONG_HISTORY_SIZE = (30, 50)  # nombre de messages d'un historique long
LONG_HISTORY_OTHERS = 8   # viewers en plus des profils dans un historique long (3 sinon)
STREAMER_WEIGHT = 0.25    # le streamer parle au micro : il écrit peu dans le chat (~5 % des messages)
UNFOLLOWED_MENTION_RATE = 0.2  # viewer mentionné qui ne suit pas la chaîne : pas de profil
ROLES = {  # statut tiré -> rôles TwitchIO (tous suivent la chaîne)
    "follower": {"follower"},
    "subscriber": {"subscriber", "follower"},
    "vip": {"vip", "follower"},
    "moderator": {"moderator", "follower"},
}


def load_pools(path: Path = POOLS_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def add_minutes(moment: datetime, minutes: int) -> datetime:
    """Ajoute (ou retire) des minutes réelles : le calcul se fait en UTC, juste même la nuit du changement d'heure."""
    return (moment.astimezone(timezone.utc) + timedelta(minutes=minutes)).astimezone(PARIS_TZ)


def sample_datetime(rng: random.Random, day: date, start_hour: int, end_hour: int) -> datetime:
    """Heure de Paris au hasard ce jour-là, entre start_hour et end_hour."""
    minutes = rng.randint(start_hour * 60, end_hour * 60 - 1)
    return datetime(day.year, day.month, day.day, minutes // 60, minutes % 60, tzinfo=PARIS_TZ)


def sample_scheduled_start(rng: random.Random, day: date, schedule: dict) -> datetime:
    """Début d'un live prévu par l'horaire : un jour annoncé (tiré au hasard) à partir de day, peu après l'heure annoncée."""
    weekday = rng.choice(schedule["days"])  # uniforme : chaque jour annoncé a autant de lives
    day += timedelta(days=(weekday - day.weekday()) % 7)
    hour, minute = (int(part) for part in schedule["start"].split(":"))
    start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=PARIS_TZ)
    return add_minutes(start, rng.randint(0, 30))


def sample_live(rng: random.Random, pools: dict, schedule: dict | None = None) -> dict:
    """Heure de l'appel, début du live, catégorie, genres, description et titre.

    schedule : horaire tiré dans les faits (ou None). Le live tombe alors un jour et à une heure
    annoncés, sauf pour un live exceptionnel (UNSCHEDULED_LIVE_RATE).
    """
    day = date(2026, 1, 1) + timedelta(days=rng.randint(0, 729))
    if rng.random() < OFF_LIVE_RATE:
        now = sample_datetime(rng, day, 8, 24)
        return {"now": now.isoformat(), "stream_start": None, "title": "",
                "category": None, "genres": None, "description": None}

    if schedule and rng.random() >= UNSCHEDULED_LIVE_RATE:
        start = sample_scheduled_start(rng, day, schedule)
    else:
        start = sample_datetime(rng, day, 18, 23)
    now = add_minutes(start, rng.randint(5, 300))  # peut passer minuit

    family = rng.choices(list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()))[0]
    choice = rng.choice(pools["categories"][family])
    if isinstance(choice, dict):  # jeu avec fiche
        category, genres, description = choice["name"], choice["genres"], choice["description"]
    else:  # jeu sans fiche ou catégorie non gaming
        category, genres, description = choice, None, None

    titles = pools["generic_titles"]  # valables pour toutes les familles
    if family != "non_gaming":  # un titre qui nomme la catégorie n'a de sens que pour un jeu
        titles = titles + pools["game_titles"]
    title = rng.choice(titles).replace("{category}", category)

    return {"now": now.isoformat(), "stream_start": start.isoformat(), "title": title,
            "category": category, "genres": genres, "description": description}


def sample_facts(rng: random.Random, pools: dict, streamer: dict) -> tuple[list[str], dict | None]:
    """L'intro du streamer, puis au plus un horaire, un fait par groupe exclusif et quelques faits libres.

    Renvoie aussi l'horaire tiré (ou None), pour que le live tiré ensuite le respecte.
    """
    if rng.random() < NO_FACTS_RATE:
        return [], None
    schedule = rng.choice(pools["schedules"]) if rng.random() < EXCLUSIVE_GROUP_RATE else None
    facts = [schedule["text"]] if schedule else []
    facts += [fact_group[rng.randrange(len(fact_group))]
              for fact_group in pools["exclusive_facts"].values()
              if rng.random() < EXCLUSIVE_GROUP_RATE]
    facts += rng.sample(pools["facts"], k=rng.randint(0, 8))
    rng.shuffle(facts)
    intro = pools["streamer_intro"][streamer["gender"]]
    return [fact.replace("{streamer}", streamer["name"]) for fact in [intro, *facts]], schedule


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
    bot_name = rng.choice(pools["bot_names"])
    facts, schedule = sample_facts(rng, pools, streamer)
    inputs = {
        "bot_name": bot_name,
        "facts": facts,
        "emotes": sample_emotes(rng, pools),
        **sample_live(rng, pools, schedule),
    }
    return inputs, streamer


def sample_profile(rng: random.Random, pools: dict, name: str, today: date) -> dict:
    """Profil cohérent : ancienneté d'abonnement <= ancienneté de follow, dernier passage avant today.

    today : jour du début du live en cours (le live en cours est exclu du dernier passage), sinon jour de l'appel.
    Un viewer en première visite n'a aucun souvenir : le résumé se construit à partir de ses messages passés.
    Un modo ou un VIP n'est jamais en première visite : le streamer donne ces rôles à des habitués.
    """
    status = rng.choices(list(pools["status_weights"]), weights=list(pools["status_weights"].values()))[0]
    sub_months = rng.randint(*pools["sub_months"]) if status == "subscriber" else 0
    regular = status in REGULAR_STATUSES
    followed_at = today - timedelta(days=max(rng.randint(0, 900), sub_months * 31, 1 if regular else 0))

    days_since_follow = (today - followed_at).days
    last_seen = None
    if days_since_follow >= 1 and (regular or rng.random() >= FIRST_VISIT_RATE):
        # Le plus souvent un passage récent ; parfois un retour après une longue absence.
        max_days = min(days_since_follow, 30) if rng.random() < 0.8 else days_since_follow
        last_seen = (today - timedelta(days=rng.randint(1, max_days))).isoformat()

    summary = ""
    if rng.random() >= NEW_VIEWER_RATE:
        summary = " ".join(rng.sample(pools["memories"], k=rng.randint(1, 3)))
    if last_seen is None:
        summary = ""  # première visite : le bot n'a encore rien retenu de lui

    return {
        "name": name,
        "status": format_status(ROLES[status], sub_months),
        "followed_at": followed_at.isoformat(),
        "last_seen": last_seen,
        "summary": summary,
    }


def sample_history(rng, pools, now, profiles, unfollowed, streamer, bot_name, on_live) -> list[dict]:
    """Squelette de l'historique : auteurs, statuts et heures (texte vide, écrit par le générateur)."""
    if rng.random() < EMPTY_HISTORY_RATE:
        return []
    long_history = rng.random() < LONG_HISTORY_RATE and on_live  # un chat animé, c'est pendant un live
    speakers = [(p["name"], p["status"]) for p in profiles]
    speakers += [(name, "viewer") for name in unfollowed]
    taken = {name for name, _ in speakers}
    others = rng.sample([n for n in pools["viewer_names"] if n not in taken],
                        k=LONG_HISTORY_OTHERS if long_history else 3)
    speakers += [(name, "viewer" if rng.random() < 0.2 else "follower") for name in others]
    speakers.append((bot_name, "bot"))
    if on_live:
        speakers.append((streamer["name"], "streamer"))

    if long_history:  # chat animé : beaucoup de messages, rapprochés
        n_messages, max_gap = rng.randint(*LONG_HISTORY_SIZE), 1
    else:
        n_messages, max_gap = rng.randint(1, 15), 4
    times, moment = [], now
    for _ in range(n_messages):
        moment = add_minutes(moment, -rng.randint(0, max_gap))
        times.append(moment)
    humans = [speaker for speaker in speakers if speaker[1] != "bot"]
    authors = []
    for _ in times:
        # Le bot répond à un follower ou plus : jamais en premier, ni après lui-même, ni après un non-follower.
        pool = speakers if authors and authors[-1][1] not in ("bot", "viewer") else humans
        weights = [STREAMER_WEIGHT if status == "streamer" else 1 for _, status in pool]
        authors.append(rng.choices(pool, weights=weights)[0])
    return [
        {"author": author, "status": status, "text": "", "sent_at": sent_at.isoformat()}
        for (author, status), sent_at in zip(authors, reversed(times))
    ]


def sample_context(rng: random.Random, pools: dict) -> tuple[dict, dict]:
    """Contexte complet (champs de PromptInputs, textes vides) et infos pour le générateur."""
    inputs, streamer = sample_system(rng, pools)
    now = datetime.fromisoformat(inputs["now"])

    n_mentions = rng.choices(list(MENTION_WEIGHTS), weights=list(MENTION_WEIGHTS.values()))[0]
    names = rng.sample(pools["viewer_names"], k=1 + n_mentions)
    author, mentioned = names[0], names[1:]
    unfollowed = [name for name in mentioned if rng.random() < UNFOLLOWED_MENTION_RATE]
    # Le dernier passage exclut le live en cours, même quand il a commencé avant minuit.
    today = datetime.fromisoformat(inputs["stream_start"]).date() if inputs["stream_start"] else now.date()
    profiles = [sample_profile(rng, pools, name, today) for name in names if name not in unfollowed]

    inputs["profiles"] = profiles
    inputs["history"] = sample_history(
        rng, pools, now, profiles, unfollowed, streamer, inputs["bot_name"],
        on_live=inputs["stream_start"] is not None,
    )
    inputs["author"] = author
    inputs["message"] = ""
    meta = {
        "streamer": streamer,
        "mentioned": mentioned,
        "without_profile": unfollowed,
        "history_count": len(inputs["history"]),  # nombre de textes d'historique à écrire
    }
    return inputs, meta


def load_matrix(path: Path = MATRIX_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def weighted_choice(rng: random.Random, weights: dict) -> str:
    """Une clé du dictionnaire, tirée selon son poids."""
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def sample_categories(rng: random.Random, matrix: dict, size: int) -> list[str]:
    """Catégories d'un lot : chacune a sa part entière (poids × taille), le reste est tiré selon les fractions."""
    weights = {name: c["weight"] for name, c in matrix["categories"].items()}
    total = sum(weights.values())
    shares = {name: weight * size / total for name, weight in weights.items()}
    categories = [name for name, share in shares.items() for _ in range(int(share))]
    remainders = {name: share - int(share) for name, share in shares.items()}
    while len(categories) < size:
        name = weighted_choice(rng, remainders)
        categories.append(name)
        remainders[name] = 0  # au plus une place de plus par catégorie
    rng.shuffle(categories)
    return categories


def sample_situation(rng: random.Random, matrix: dict, category: str | None = None) -> dict:
    """Situation à faire écrire au générateur : catégorie, consigne, registre, attitude."""
    categories = matrix["categories"]
    if category is None:
        category = weighted_choice(rng, {name: c["weight"] for name, c in categories.items()})
    return {
        "category": category,
        "instruction": categories[category]["instruction"],
        "register": weighted_choice(rng, matrix["registers"]),
        "attitude": weighted_choice(rng, matrix["attitudes"]),
    }


def situation_fits(category: str, inputs: dict) -> bool:
    """Le contexte permet-il la situation ? Une liste d'emotes pour emotes, un vrai fait pour fait_present."""
    if category == "emotes":
        return bool(inputs["emotes"])
    if category == "fait_present":
        return len(inputs["facts"]) > 1  # l'intro du streamer seule ne suffit pas
    return True
