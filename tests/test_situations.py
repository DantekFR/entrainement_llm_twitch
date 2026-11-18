import random
from collections import Counter

from scripts.contexts import load_matrix, sample_situation, sample_categories
from scripts.eval_cases import CATEGORIES

MATRIX = load_matrix()


def test_matrix_covers_eval_categories():
    # mêmes catégories que l'éval : ni oubli, ni catégorie en trop
    assert set(MATRIX["categories"]) == set(CATEGORIES)


def test_same_seed_same_situation():
    assert sample_situation(random.Random(7), MATRIX) == sample_situation(random.Random(7), MATRIX)


def test_proportions_follow_weights():
    rng = random.Random(0)
    counts = Counter(sample_situation(rng, MATRIX)["category"] for _ in range(10_000))
    total_weight = sum(c["weight"] for c in MATRIX["categories"].values())
    for name, category in MATRIX["categories"].items():
        expected = category["weight"] / total_weight
        assert abs(counts[name] / 10_000 - expected) < 0.02


def test_every_batch_covers_all_categories():
    for seed in range(50):
        categories = sample_categories(random.Random(seed), MATRIX, 20)
        assert len(categories) == 20
        assert set(categories) == set(MATRIX["categories"])
