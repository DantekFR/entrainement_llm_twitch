from scripts.contexts import load_matrix, load_pools
from scripts.export_batch import build_batch
from scripts.merge_batch import fill_item, find_problems

ITEM = build_batch(1, 1, load_pools(), load_matrix())[0]


def good_row(item=ITEM):
    inputs = item["inputs"]
    mentions = " ".join("@" + name for name in item["meta"]["mentioned"])
    return {
        "id": item["id"],
        "history": ["salut tout le monde"] * len(inputs["history"]),
        "message": f"@{inputs['bot_name']} {mentions} tu vas bien ce soir ?",
        "response": "Oui, tout va bien, merci de demander.",
    }


def test_good_row_is_accepted():
    assert find_problems(ITEM, good_row()) == []


def test_problems_are_detected():
    item = {**ITEM, "meta": {**ITEM["meta"], "mentioned": ["Pseudo_Test"]}}
    row = good_row(ITEM)  # sans la mention de Pseudo_Test
    row["history"] = row["history"] + ["un texte en trop"]
    row["response"] = "Salut [Pseudo_Test] zzzFake"
    problems = " | ".join(find_problems(item, row))
    for expected in ["historique", "mention manquante", "no_brackets", "emote inconnue : zzzFake"]:
        assert expected in problems


def test_fill_item_keeps_the_batch_untouched():
    inputs = fill_item(ITEM, good_row())
    assert inputs["message"].startswith("@")
    assert ITEM["inputs"]["message"] == ""
