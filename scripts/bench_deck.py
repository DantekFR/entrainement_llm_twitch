"""Banc de vitesse d'Ollama sur le Steam Deck, avec les vrais prompts de l'éval.

Usage : uv run python -m scripts.bench_deck --name 3b-q4 --model hf.co/unsloth/Ministral-3-3B-Instruct-2512-GGUF:Q4_K_M
"""

import argparse
import json
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from transformers import AutoTokenizer

from scripts.eval_cases import case_to_inputs, load_cases
from scripts.prompt_format import apply_limits, build_messages

DECK_HOST = "http://192.168.1.38:11434"
TOKENIZER_ID = "unsloth/Ministral-3-3B-Instruct-2512-unsloth-bnb-4bit"  # même tokenizer pour le 3B et le 8B
OPTIONS = {"temperature": 0, "num_predict": 150, "num_ctx": 4096}  # mêmes réglages que l'éval
WRITTEN_LIMIT_S = 15
RUNS_DIR = Path(__file__).parent.parent / "runs"


def chat(host: str, model: str, messages: list[dict]) -> dict:
    """Envoie un prompt en streaming et chronomètre la réponse."""
    body = json.dumps({"model": model, "messages": messages, "stream": True, "options": OPTIONS}).encode()
    request = urllib.request.Request(f"{host}/api/chat", data=body, headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    first_token = None
    parts = []
    with urllib.request.urlopen(request, timeout=300) as response:
        for line in response:
            chunk = json.loads(line)
            if "error" in chunk:
                raise RuntimeError(chunk["error"])
            content = chunk.get("message", {}).get("content", "")
            if content and first_token is None:
                first_token = time.perf_counter() - start
            parts.append(content)
            if chunk.get("done"):
                final = chunk
    total = time.perf_counter() - start
    return {
        "answer": "".join(parts).strip(),
        "first_token_s": round(first_token or total, 2),
        "total_s": round(total, 2),
        "load_s": round(final.get("load_duration", 0) / 1e9, 2),
        "prompt_tokens": final.get("prompt_eval_count", 0),   # tokens réellement lus (hors cache)
        "prompt_s": round(final.get("prompt_eval_duration", 0) / 1e9, 2),
        "answer_tokens": final["eval_count"],
        "tokens_per_s": round(final["eval_count"] / (final["eval_duration"] / 1e9), 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Mesure la vitesse d'un modèle Ollama sur le Deck.")
    parser.add_argument("--name", required=True, help="nom du banc (ex. 3b-q4)")
    parser.add_argument("--model", required=True, help="nom du modèle dans Ollama")
    parser.add_argument("--host", default=DECK_HOST)
    parser.add_argument("--cases", default="eval/cases.jsonl")
    parser.add_argument("--dataset", help="JSONL déjà rendu (ex. data/seed/val.jsonl) au lieu des cas de l'éval")
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_ID, fix_mistral_regex=True)

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False))

    if args.dataset:
        with open(args.dataset, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        cases = [{"id": row["id"]} for row in rows]
        prompts = [row["messages"][:2] for row in rows]   # system + user, sans la réponse
    else:
        cases = load_cases(Path(args.cases))
        prompts = [build_messages(apply_limits(case_to_inputs(case), count_tokens)) for case in cases]

    warmup = chat(args.host, args.model, prompts[0])
    print(f"Préchauffage : chargement du modèle {warmup['load_s']} s, total {warmup['total_s']} s")

    results = []
    for index, (case, messages) in enumerate(zip(cases, prompts), start=1):
        result = {"id": case["id"], **chat(args.host, args.model, messages)}
        results.append(result)
        print(f"[{index}/{len(cases)}] {case['id']} : 1er token {result['first_token_s']} s · "
              f"total {result['total_s']} s · {result['tokens_per_s']} tokens/s · "
              f"prompt lu {result['prompt_tokens']} tokens en {result['prompt_s']} s")
        print(f"    {result['answer']}")

    totals = [r["total_s"] for r in results]
    firsts = [r["first_token_s"] for r in results]
    summary = {
        "total_median_s": round(statistics.median(totals)),
        "total_max_s": max(totals),
        "first_token_median_s": round(statistics.median(firsts)),
        "first_token_max_s": max(firsts),
        "tokens_per_s_median": round(statistics.median(r["tokens_per_s"] for r in results)),
        "over_written_limit": sum(t > WRITTEN_LIMIT_S for t in totals),
    }
    run_dir = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M}_bench_{args.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {"name": args.name, "model": args.model, "host": args.host, "options": OPTIONS,
              "warmup": warmup, "summary": summary, "results": results}
    (run_dir / "bench.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"Délai total : médiane {summary['total_median_s']} s, max {summary['total_max_s']} s")
    print(f"1er token : médiane {summary['first_token_median_s']} s, max {summary['first_token_max_s']} s")
    print(f"Vitesse d'écriture : médiane {summary['tokens_per_s_median']} tokens/s")
    print(f"Au-dessus de {WRITTEN_LIMIT_S} s : {summary['over_written_limit']}/{len(results)}")


if __name__ == "__main__":
    main()