"""Lecture des cas d'évaluation (eval/cases.jsonl) et conversion en PromptInputs."""

import json
from datetime import date, datetime
from pathlib import Path

from scripts.prompt_format import ChatMessage, PromptInputs, ViewerProfile

CASES_PATH = Path(__file__).parent.parent / "eval" / "cases.jsonl"

CATEGORIES = [
    "fait_present", "fait_absent", "injection", "profil", "langue",
    "live", "culture_actu", "bavardage", "emotes",
]


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    """Un cas par ligne non vide du fichier JSONL."""
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def parse_profile(data: dict) -> ViewerProfile:
    last_seen = data.get("last_seen")
    return ViewerProfile(
        name=data["name"],
        status=data["status"],
        followed_at=date.fromisoformat(data["followed_at"]),
        last_seen=date.fromisoformat(last_seen) if last_seen else None,
        summary=data.get("summary", ""),
    )


def parse_message(data: dict) -> ChatMessage:
    return ChatMessage(
        author=data["author"],
        status=data["status"],
        text=data["text"],
        sent_at=datetime.fromisoformat(data["sent_at"]),
    )


def case_to_inputs(case: dict) -> PromptInputs:
    """Convertit le bloc "inputs" d'un cas (texte JSON) en PromptInputs."""
    raw = dict(case["inputs"])  # copie : on ne modifie pas le cas d'origine
    raw["now"] = datetime.fromisoformat(raw["now"])
    if raw.get("stream_start"):
        raw["stream_start"] = datetime.fromisoformat(raw["stream_start"])
    raw["profiles"] = [parse_profile(p) for p in raw["profiles"]]
    raw["history"] = [parse_message(m) for m in raw["history"]]
    return PromptInputs(**raw)  # une clé inconnue lève une TypeError
