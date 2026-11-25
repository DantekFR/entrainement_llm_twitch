"""Évaluation d'un modèle sur eval/cases.jsonl (phase 2).

Usage : uv run python -m scripts.evaluate --name base
        uv run python -m scripts.evaluate --name base-3b --model unsloth/Ministral-3-3B-Instruct-2512-unsloth-bnb-4bit
"""

from unsloth import FastModel  # en premier : Unsloth modifie transformers à l'import

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoTokenizer

from scripts.checks import run_checks, summarize, print_summary
from scripts.eval_cases import case_to_inputs, load_cases
from scripts.prompt_format import PROMPT_FORMAT_VERSION, apply_limits, build_messages

MODEL_ID = "unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit"
MAX_SEQ_LENGTH = 4096
MAX_NEW_TOKENS = 150
RUNS_DIR = Path(__file__).parent.parent / "runs"


def load_model(model_id: str = MODEL_ID, adapter: str | None = None):
    """Modèle en 4 bits (texte seul), éventuellement avec un adaptateur LoRA, et tokenizer corrigé."""
    model, _processor = FastModel.from_pretrained(
        model_id, max_seq_length=MAX_SEQ_LENGTH, load_in_4bit=True, text_only=True
    )
    if adapter:
        adapter_config = json.loads((Path(adapter) / "adapter_config.json").read_text(encoding="utf-8"))
        trained_on = adapter_config["base_model_name_or_path"]
        if trained_on != model_id:
            raise ValueError(f"adaptateur entraîné sur {trained_on}, pas sur {model_id} : passer --model")
        model = PeftModel.from_pretrained(model, adapter)
    tokenizer = AutoTokenizer.from_pretrained(model_id, fix_mistral_regex=True, padding_side="left")
    FastModel.for_inference(model)
    return model, tokenizer


def generate(model, tokenizer, messages: list[dict]) -> tuple[str, int, float]:
    """Réponse du modèle (décodage glouton), nombre de tokens générés, durée en secondes."""
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, add_special_tokens=False, return_tensors="pt").to(model.device)
    start = time.time()
    output = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    new_tokens = output[0, inputs["input_ids"].shape[1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return answer, len(new_tokens), time.time() - start


def main():
    parser = argparse.ArgumentParser(description="Évalue un modèle sur eval/cases.jsonl.")
    parser.add_argument("--name", default="base", help="nom du run (ex. base, v0)")
    parser.add_argument("--model", default=MODEL_ID, help=f"modèle Hugging Face (défaut : {MODEL_ID})")
    parser.add_argument("--adapter", help="dossier d'un adaptateur LoRA (ex. runs/<id>/adapter)")
    parser.add_argument("--cases", default="eval/cases.jsonl", help="fichier de cas (défaut : eval-v1)")
    args = parser.parse_args()

    model, tokenizer = load_model(args.model, args.adapter)
    vram_gb = round(torch.cuda.memory_allocated() / 1e9, 2)
    print(f"VRAM après chargement : {vram_gb} Go")

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False))

    cases = load_cases(Path(args.cases))
    results = []
    for index, case in enumerate(cases, start=1):
        inputs = apply_limits(case_to_inputs(case), count_tokens)
        answer, n_tokens, seconds = generate(model, tokenizer, build_messages(inputs))
        checks = run_checks(answer, case["checks"])
        results.append({
            "id": case["id"],
            "category": case["category"],
            "answer": answer,
            "tokens": n_tokens,
            "seconds": round(seconds, 1),
            "checks": checks,
        })
        failed = [name for name, ok in checks.items() if not ok]
        print(f"[{index}/{len(cases)}] {'OK' if not failed else 'KO'} {case['id']} {failed or ''}")
        print(f"    {answer}")

    summary = summarize(results)
    run_dir = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M}_{args.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "name": args.name,
        "model": args.model,
        "adapter": args.adapter,
        "cases": args.cases,
        "vram_after_load_gb": vram_gb,
        "prompt_format": PROMPT_FORMAT_VERSION,
        "max_new_tokens": MAX_NEW_TOKENS,
        "summary": summary,
        "results": results,
    }
    (run_dir / "eval.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print_summary(summary)

if __name__ == "__main__":
    main()
