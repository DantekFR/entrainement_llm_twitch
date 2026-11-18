"""Fusionne la sortie du chat générateur avec les contextes d'un lot (phase 3).

Vérifie chaque exemple, le rend au format d'entraînement (messages system / user / assistant)
et écrit les exemples acceptés dans data/seed/batches/batch_NNN_merged.jsonl.

Usage : uv run python -m scripts.merge_batch --batch 1
"""

import argparse
import copy
import json
import re
from pathlib import Path

from scripts.checks import LANGUAGE_NOISE, detect_language, run_checks
from scripts.eval_cases import case_to_inputs
from scripts.prompt_format import apply_limits, build_messages
from scripts.export_batch import batch_dir

MODEL_ID = "unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit"
EMOTE_LIKE = re.compile(r"\b[a-z]{3,}[A-Z]\w*")  # forme d'une emote de chaîne : préfixe + Suffixe


def fill_item(item: dict, row: dict) -> dict:
    """Copie du contexte, avec les textes écrits par le générateur."""
    inputs = copy.deepcopy(item["inputs"])  # on ne modifie pas le lot d'origine
    for message, text in zip(inputs["history"], row["history"]):
        message["text"] = text
    inputs["message"] = row["message"]
    return inputs


def find_problems(item: dict, row: dict) -> list[str]:
    """Raisons de rejeter un exemple (liste vide = exemple accepté)."""
    inputs, meta = item["inputs"], item["meta"]
    problems = []
    if len(row["history"]) != len(inputs["history"]):
        problems.append(f"historique : {len(row['history'])} textes au lieu de {len(inputs['history'])}")
    if not row["message"].startswith("@" + inputs["bot_name"]):
        problems.append("le message ne commence pas par @" + inputs["bot_name"])
    for name in meta["mentioned"]:
        if "@" + name not in row["message"]:
            problems.append("mention manquante : @" + name)

    language = "fr"
    if item["situation"]["category"] == "langue":
        language = detect_language(LANGUAGE_NOISE.sub(" ", row["message"]))
        if language in (None, "fr"):
            problems.append("catégorie langue, mais le message n'est pas clairement étranger")
            language = "fr"
    results = run_checks(row["response"], {"max_sentences": 2, "language": language})
    problems += [f"critère {name} échoué" for name, ok in results.items() if not ok]

    for word in EMOTE_LIKE.findall(row["response"]):
        if word not in inputs["emotes"]:
            problems.append("emote inconnue : " + word)
    return problems


def main():
    parser = argparse.ArgumentParser(description="Fusionne et vérifie la sortie du générateur.")
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()

    folder = batch_dir(args.batch)
    items = json.loads((folder / "batch.json").read_text(encoding="utf-8"))
    lines = (folder / "output.jsonl").read_text(encoding="utf-8").splitlines()
    rows = {row["id"]: row for row in (json.loads(line) for line in lines if line.strip())}

    from transformers import AutoTokenizer  # import lent : seulement ici, pas dans les tests
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, fix_mistral_regex=True)

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False))

    accepted, max_tokens = [], 0
    for item in items:
        row = rows.get(item["id"])
        problems = ["absent de la sortie du générateur"] if row is None else find_problems(item, row)
        if problems:
            print(f"REJETÉ {item['id']} : " + " ; ".join(problems))
            continue
        inputs = apply_limits(case_to_inputs({"inputs": fill_item(item, row)}), count_tokens)
        messages = build_messages(inputs, row["response"])
        max_tokens = max(max_tokens, count_tokens(tokenizer.apply_chat_template(messages, tokenize=False)))
        accepted.append({"id": item["id"], "category": item["situation"]["category"], "messages": messages})

    path = folder / f"merged.jsonl"
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in accepted), encoding="utf-8")
    print(f"{len(accepted)}/{len(items)} exemples acceptés -> {path}")
    print(f"Exemple le plus long : {max_tokens} tokens (max_seq_length = 4096)")


if __name__ == "__main__":
    main()
