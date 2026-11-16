from datetime import datetime

import pytest

from scripts.eval_cases import CATEGORIES, case_to_inputs, load_cases
from scripts.prompt_format import build_messages

CASES = load_cases()


def test_ids_are_unique():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_case_is_valid(case):
    """Chaque cas se lit, se rend, et contient les critères communs."""
    assert case["category"] in CATEGORIES
    assert {"language", "max_sentences"} <= case["checks"].keys()

    inputs = case_to_inputs(case)
    assert inputs.now.tzinfo is not None
    assert inputs.profiles and inputs.profiles[0].name == inputs.author  # l'auteur en premier

    messages = build_messages(inputs)
    assert "{bot_name}" not in messages[0]["content"]
