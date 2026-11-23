"""Assemble les lots fusionnés en train.jsonl et val.jsonl (90/10, stratifié par catégorie).

Usage : uv run python -m scripts.assemble_seed
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_DIR = ROOT / "data" / "seed"
BATCHES_DIR = SEED_DIR / "batches"
VAL_FRACTION = 0.1
SPLIT_SEED = 42  # graine du découpage : le même découpage à chaque lancement


def load_examples() -> list[dict]:
    """Lit tous les merged.jsonl, dans l'ordre des lots, et refuse un id en double."""
    examples, seen = [], set()
    for path in sorted(BATCHES_DIR.glob("batch_*/merged.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            example = json.loads(line)
            if example["id"] in seen:
                raise SystemExit(f"id en double : {example['id']} ({path})")
            seen.add(example["id"])
            examples.append(example)
    return examples


def split(examples: list[dict]) -> tuple[list[dict], list[dict]]:
    """Prend environ 10 % de chaque catégorie pour la validation (au moins 1)."""
    rng = random.Random(SPLIT_SEED)
    by_category = defaultdict(list)
    for example in examples:
        by_category[example["category"]].append(example)
    train, val = [], []
    for category in sorted(by_category):  # ordre fixe : le tirage ne dépend pas de l'ordre de lecture
        group = by_category[category][:]
        rng.shuffle(group)
        n_val = max(1, round(len(group) * VAL_FRACTION))
        val += group[:n_val]
        train += group[n_val:]
    rng.shuffle(train)  # mélange les catégories pour l'entraînement
    return train, val


def write_jsonl(path: Path, examples: list[dict]) -> None:
    lines = [json.dumps(example, ensure_ascii=False) for example in examples]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    examples = load_examples()
    train, val = split(examples)
    write_jsonl(SEED_DIR / "train.jsonl", train)
    write_jsonl(SEED_DIR / "val.jsonl", val)
    print(f"{len(examples)} exemples : {len(train)} train, {len(val)} val")
    train_counts, val_counts = Counter(e["category"] for e in train), Counter(e["category"] for e in val)
    for category in sorted(train_counts | val_counts):
        print(f"  {category:<13} train {train_counts[category]:>3}   val {val_counts[category]:>2}")


if __name__ == "__main__":
    main()