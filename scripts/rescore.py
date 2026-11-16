"""Recalcule les scores d'un run à partir des réponses enregistrées (sans GPU).

Usage : uv run python -m scripts.rescore runs/<run>/eval.json
"""

import argparse
import json
from pathlib import Path

from scripts.checks import print_summary, run_checks, summarize
from scripts.eval_cases import load_cases


def main():
    parser = argparse.ArgumentParser(description="Réapplique les vérifications actuelles à un eval.json.")
    parser.add_argument("report", type=Path, help="chemin du fichier eval.json")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in load_cases()}
    old_passed = report["summary"]["passed"]

    for result in report["results"]:
        result["checks"] = run_checks(result["answer"], cases[result["id"]]["checks"])
        failed = [name for name, ok in result["checks"].items() if not ok]
        print(f"{'OK' if not failed else 'KO'} {result['id']} {failed or ''}")

    report["summary"] = summarize(report["results"])
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nAvant : {old_passed}/{report['summary']['cases']}")
    print_summary(report["summary"])


if __name__ == "__main__":
    main()
