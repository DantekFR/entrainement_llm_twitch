"""Exporte un lot de contextes + situations à donner au chat générateur (phase 3).

Le générateur remplit les textes vides (historique, message) et écrit la réponse idéale.
La graine est le numéro du lot : un même lot est toujours identique.
"""

import argparse
import json
import random
from pathlib import Path

from scripts.contexts import load_matrix, load_pools, sample_context, sample_situation
from scripts.prompt_format import SYSTEM_RULES

ROOT = Path(__file__).parent.parent
BATCHES_DIR = ROOT / "data" / "seed" / "batches"
TEMPLATE_PATH = ROOT / "configs" / "generator_prompt.md"
DOC_PATH = ROOT / "docs" / "prompt_format.md"


def build_batch(batch_id: int, size: int, pools: dict, matrix: dict) -> list[dict]:
    rng = random.Random(batch_id)
    items = []
    for index in range(size):
        inputs, meta = sample_context(rng, pools)
        items.append({
            "id": f"b{batch_id:03d}-{index:02d}",
            "situation": sample_situation(rng, matrix),
            "meta": meta,
            "inputs": inputs,
        })
    return items

def read_example(doc_path: Path = DOC_PATH) -> str:
    """Section « Exemple complet » de docs/prompt_format.md, sans son titre."""
    section = doc_path.read_text(encoding="utf-8").split("## Exemple complet\n", 1)[1]
    return section.split("\n## ", 1)[0].strip()


def build_generator_prompt(items: list[dict]) -> str:
    """Modèle configs/generator_prompt.md avec les règles, l'exemple et le lot."""
    prompt = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "<<SYSTEM_RULES>>": SYSTEM_RULES,
        "<<EXAMPLE>>": read_example(),
        "<<BATCH>>": json.dumps(items, ensure_ascii=False, indent=2),  # en dernier
    }
    for marker, value in replacements.items():
        assert marker in prompt, f"marqueur absent du modèle : {marker}"
        prompt = prompt.replace(marker, value)
    return prompt


def main():
    parser = argparse.ArgumentParser(description="Exporte un lot pour le chat générateur.")
    parser.add_argument("--batch", type=int, required=True, help="numéro du lot (sert de graine)")
    parser.add_argument("--size", type=int, default=20)
    args = parser.parse_args()

    items = build_batch(args.batch, args.size, load_pools(), load_matrix())
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    path = BATCHES_DIR / f"batch_{args.batch:03d}.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    categories = [item["situation"]["category"] for item in items]
    prompt_path = BATCHES_DIR / f"batch_{args.batch:03d}_prompt.md"
    prompt_path.write_text(build_generator_prompt(items), encoding="utf-8")
    print(f"Prompt du générateur : {prompt_path}")
    print(f"{len(items)} exemples écrits dans {path}")
    print("Catégories :", ", ".join(sorted(set(categories), key=categories.index)))


if __name__ == "__main__":
    main()
