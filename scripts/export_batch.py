"""Exporte un lot de contextes + situations à donner au chat générateur (phase 3).

Le générateur remplit les textes vides (historique, message) et écrit la réponse idéale.
La graine est le numéro du lot : avec le même code et les mêmes réservoirs, un lot est toujours identique.
Un lot déjà exporté ne se réexporte jamais (sa sortie correspond au tirage d'origine).

Usage : uv run python -m scripts.export_batch --batch 3
"""

import argparse
import json
import random
from pathlib import Path

from scripts.contexts import (
    load_matrix, load_pools, sample_categories, sample_context, sample_situation, situation_fits,
)
from scripts.prompt_format import SYSTEM_RULES

ROOT = Path(__file__).parent.parent
BATCHES_DIR = ROOT / "data" / "seed" / "batches"
TEMPLATE_PATH = ROOT / "configs" / "generator_prompt.md"
DOC_PATH = ROOT / "docs" / "prompt_format.md"


def batch_dir(batch_id: int) -> Path:
    """Dossier d'un lot : contextes, prompt, sortie du générateur, exemples fusionnés."""
    return BATCHES_DIR / f"batch_{batch_id:03d}"


def build_batch(batch_id: int, size: int, pools: dict, matrix: dict) -> list[dict]:
    rng = random.Random(batch_id)
    categories = sample_categories(rng, matrix, size)
    items = []
    for index in range(size):
        while True:  # on retire le contexte tant qu'il rend la situation impossible
            inputs, meta = sample_context(rng, pools)
            if situation_fits(categories[index], inputs):
                break
        items.append({
            "id": f"b{batch_id:03d}-{index:02d}",
            "situation": sample_situation(rng, matrix, categories[index]),
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
        # Une ligne par exemple (JSONL), comme la sortie attendue : ~25 % de caractères en moins qu'indenté.
        "<<BATCH>>": "\n".join(json.dumps(item, ensure_ascii=False) for item in items),  # en dernier
    }
    for marker, value in replacements.items():
        assert marker in prompt, f"marqueur absent du modèle : {marker}"
        prompt = prompt.replace(marker, value)
    return prompt


def check_not_exported(folder: Path, force: bool = False) -> None:
    """Arrête le script si le lot a déjà été exporté : sa sortie ne correspondrait plus au tirage."""
    if (folder / "output.jsonl").exists():
        raise SystemExit(f"{folder} a déjà une sortie du générateur : ce lot ne se réexporte jamais, même avec --force.")
    if (folder / "batch.json").exists() and not force:
        raise SystemExit(
            f"{folder} existe déjà : un lot déjà exporté ne se réexporte jamais. "
            "Si son prompt n'a jamais été envoyé au générateur, relance avec --force."
        )


def main():
    parser = argparse.ArgumentParser(description="Exporte un lot pour le chat générateur.")
    parser.add_argument("--batch", type=int, required=True, help="numéro du lot (sert de graine)")
    parser.add_argument("--size", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="réécrit un lot jamais envoyé au générateur")
    args = parser.parse_args()

    folder = batch_dir(args.batch)
    check_not_exported(folder, args.force)  # avant toute écriture
    items = build_batch(args.batch, args.size, load_pools(), load_matrix())
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "batch.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    categories = [item["situation"]["category"] for item in items]
    prompt_path = folder / "prompt.md"
    prompt_path.write_text(build_generator_prompt(items), encoding="utf-8")
    print(f"Prompt du générateur : {prompt_path}")
    print(f"{len(items)} exemples écrits dans {path}")
    print("Catégories :", ", ".join(sorted(set(categories), key=categories.index)))


if __name__ == "__main__":
    main()
