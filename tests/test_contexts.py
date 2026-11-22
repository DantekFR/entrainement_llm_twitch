import random
from datetime import datetime, timedelta, timezone

from scripts.contexts import PARIS_TZ, add_minutes, load_pools, sample_system, sample_context
from scripts.prompt_format import render_category, render_emotes, render_facts, render_now

POOLS = load_pools()
SEEDS = range(300)
CONTEXTS = [sample_context(random.Random(seed), POOLS) for seed in range(1000)]


def test_same_seed_same_context():
    assert sample_system(random.Random(42), POOLS) == sample_system(random.Random(42), POOLS)


def test_system_contexts_are_consistent():
    for seed in SEEDS:
        inputs, streamer = sample_system(random.Random(seed), POOLS)
        now = datetime.fromisoformat(inputs["now"])
        assert now.tzinfo is not None
        if inputs["stream_start"]:
            start = datetime.fromisoformat(inputs["stream_start"])
            assert timedelta(minutes=5) <= now - start <= timedelta(hours=5)
            assert inputs["category"] and "{category}" not in inputs["title"]
        else:
            assert inputs["category"] is None and inputs["title"] == ""
        assert len(inputs["facts"]) <= 20
        if inputs["facts"]:
            assert streamer["name"] in inputs["facts"][0]
        assert all("{streamer}" not in fact for fact in inputs["facts"])
        assert len(inputs["emotes"]) <= 12
        # Les blocs se rendent sans erreur.
        render_facts(inputs["facts"])
        render_emotes(inputs["emotes"])
        render_category(inputs["category"], inputs["genres"], inputs["description"])
        render_now(now, datetime.fromisoformat(inputs["stream_start"]) if inputs["stream_start"] else None, inputs["title"])


def test_some_lives_cross_midnight():
    """Le dataset doit contenir des lives qui passent minuit."""
    crossings = 0
    for seed in SEEDS:
        inputs, _ = sample_system(random.Random(seed), POOLS)
        if inputs["stream_start"]:
            start, now = (datetime.fromisoformat(inputs[key]) for key in ("stream_start", "now"))
            crossings += now.date() != start.date()
    assert crossings > 0


def test_full_contexts_render():
    """Un contexte complet (textes remplis bidon) passe par le même chemin que les cas d'évaluation."""
    from scripts.eval_cases import case_to_inputs
    from scripts.prompt_format import build_messages

    for seed in SEEDS:
        inputs, meta = sample_context(random.Random(seed), POOLS)
        assert inputs["profiles"][0]["name"] == inputs["author"]
        assert len({p["name"] for p in inputs["profiles"]}) == len(inputs["profiles"])
        statuses = {p["name"]: p["status"] for p in inputs["profiles"]}

        now = datetime.fromisoformat(inputs["now"])
        times = [datetime.fromisoformat(m["sent_at"]) for m in inputs["history"]]
        assert times == sorted(times) and all(t <= now for t in times)
        for message in inputs["history"]:
            if message["author"] in statuses:
                assert message["status"] == statuses[message["author"]]
            message["text"] = "texte"
        inputs["message"] = " ".join(["@" + name for name in meta["mentioned"]] + ["question"])

        build_messages(case_to_inputs({"inputs": inputs}))

def test_non_gaming_titles_do_not_name_the_category():
    for seed in SEEDS:
        inputs, _ = sample_system(random.Random(seed), POOLS)
        if inputs["category"] in POOLS["categories"]["non_gaming"]:
            assert inputs["category"] not in inputs["title"]

def test_unfollowed_mentions_have_no_profile():
    total = 0
    for seed in SEEDS:
        inputs, meta = sample_context(random.Random(seed), POOLS)
        unfollowed = set(meta["without_profile"])
        names = {p["name"] for p in inputs["profiles"]}
        assert unfollowed <= set(meta["mentioned"])
        assert names == {inputs["author"], *meta["mentioned"]} - unfollowed
        for message in inputs["history"]:
            if message["author"] in unfollowed:
                assert message["status"] == "viewer"
        total += len(unfollowed)
    assert total > 0  # le cas existe bien dans les tirages

def test_bot_never_speaks_first_or_twice_in_a_row():
    for seed in SEEDS:
        inputs, _ = sample_context(random.Random(seed), POOLS)
        statuses = [message["status"] for message in inputs["history"]]
        if statuses:
            assert statuses[0] != "bot"
        assert all(not (b == "bot" and a in ("bot", "viewer")) for a, b in zip(statuses, statuses[1:]))


def test_every_game_family_gets_generic_titles():
    """Bug d'indentation (live 6) : un jeu avec fiche n'avait jamais de titre générique."""
    families = {
        family: {c["name"] if isinstance(c, dict) else c for c in categories}
        for family, categories in POOLS["categories"].items()
    }
    generic = set(POOLS["generic_titles"])
    for family, names in families.items():
        titles = [inputs["title"] for inputs, _ in CONTEXTS if inputs["category"] in names]
        assert any(title in generic for title in titles), f"aucun titre générique pour {family}"
        if family != "non_gaming":
            assert any(title not in generic for title in titles), f"aucun titre de jeu pour {family}"


def test_first_visit_has_no_memory():
    """Un viewer en première visite : le bot n'a encore rien retenu de lui."""
    for inputs, _ in CONTEXTS:
        for profile in inputs["profiles"]:
            if profile["last_seen"] is None:
                assert profile["summary"] == ""


def test_lives_follow_the_schedule():
    """Un live tombe un jour annoncé, peu après l'heure annoncée, sauf quelques lives exceptionnels."""
    schedules = {s["text"]: s for s in POOLS["schedules"]}
    matching = total = 0
    for inputs, _ in CONTEXTS:
        drawn = [schedules[fact] for fact in inputs["facts"] if fact in schedules]
        assert len(drawn) <= 1  # au plus un horaire
        if drawn and inputs["stream_start"]:
            start = datetime.fromisoformat(inputs["stream_start"])
            hour, minute = (int(part) for part in drawn[0]["start"].split(":"))
            announced = start.replace(hour=hour, minute=minute)
            total += 1
            matching += start.weekday() in drawn[0]["days"] and announced <= start <= announced + timedelta(minutes=30)
    assert total > 50
    assert 0.75 <= matching / total < 1  # environ 85 % à l'heure, le reste exceptionnel


def test_history_lengths():
    """Le plus souvent 1 à 15 messages, parfois un chat animé de 30 à 50 messages."""
    lengths = [len(inputs["history"]) for inputs, _ in CONTEXTS]
    assert max(lengths) <= 50
    long_share = sum(length > 15 for length in lengths) / len(lengths)
    assert 0.05 <= long_share <= 0.15
    assert all(length == 0 or 1 <= length <= 15 or 30 <= length <= 50 for length in lengths)


def test_streamer_writes_little():
    statuses = [m["status"] for inputs, _ in CONTEXTS if inputs["stream_start"] for m in inputs["history"]]
    assert 0 < statuses.count("streamer") / len(statuses) < 0.1


def test_add_minutes_across_daylight_saving_time():
    """La nuit du passage à l'heure d'été, 1 h réelle après 01h30 donne 03h30 (et non 02h30, qui n'existe pas)."""
    start = datetime(2027, 3, 28, 1, 30, tzinfo=PARIS_TZ)
    later = add_minutes(start, 60)
    assert (later.hour, later.minute) == (3, 30)
    assert later.astimezone(timezone.utc) - start.astimezone(timezone.utc) == timedelta(hours=1)


def test_last_seen_excludes_the_current_live():
    """Live commencé avant minuit : le dernier passage est avant le jour du début du live."""
    for inputs, _ in CONTEXTS:
        reference = datetime.fromisoformat(inputs["stream_start"] or inputs["now"]).date()
        for profile in inputs["profiles"]:
            if profile["last_seen"]:
                assert profile["followed_at"] <= profile["last_seen"] < reference.isoformat()


def test_scheduled_weekdays_are_balanced():
    """Chaque jour annoncé reçoit sa part de lives (le samedi absorbait 83 % des « week-ends »)."""
    from collections import Counter

    schedules = {s["text"]: s for s in POOLS["schedules"]}
    counts = {text: Counter() for text in schedules}
    for seed in range(4000):
        inputs, _ = sample_system(random.Random(seed), POOLS)
        drawn = [fact for fact in inputs["facts"] if fact in schedules]
        if drawn and inputs["stream_start"]:
            weekday = datetime.fromisoformat(inputs["stream_start"]).weekday()
            if weekday in schedules[drawn[0]]["days"]:
                counts[drawn[0]][weekday] += 1
    for text, counter in counts.items():
        share = 1 / len(schedules[text]["days"])
        for day in schedules[text]["days"]:
            assert counter[day] / sum(counter.values()) > share * 0.6, (text, counter)


def test_regulars_are_never_on_a_first_visit():
    for inputs, _ in CONTEXTS:
        for profile in inputs["profiles"]:
            if profile["status"] in ("modo", "VIP"):
                assert profile["last_seen"] is not None


def test_long_histories_only_during_a_live():
    for inputs, _ in CONTEXTS:
        if len(inputs["history"]) > 15:
            assert inputs["stream_start"] is not None
