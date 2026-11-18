from scripts.contexts import load_matrix, load_pools
from scripts.eval_cases import load_cases
from scripts.export_batch import build_batch, build_generator_prompt
from scripts.prompt_format import SYSTEM_RULES

ITEMS = build_batch(1, 20, load_pools(), load_matrix())
PROMPT = build_generator_prompt(ITEMS)


def test_prompt_is_complete():
    assert "<<" not in PROMPT  # tous les marqueurs remplacés
    assert SYSTEM_RULES in PROMPT
    assert "Hollow Knight Silksong" in PROMPT  # réponse de l'exemple du doc
    assert all(item["id"] in PROMPT for item in ITEMS)


def test_prompt_contains_no_eval_message():
    # le générateur ne doit jamais voir l'examen
    for case in load_cases():
        assert case["inputs"]["message"] not in PROMPT
