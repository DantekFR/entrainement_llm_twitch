import random
from datetime import datetime, timedelta

from scripts.contexts import load_pools, sample_system, sample_context
from scripts.prompt_format import render_category, render_emotes, render_facts, render_now

POOLS = load_pools()
SEEDS = range(300)


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
