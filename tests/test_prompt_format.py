import re
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.prompt_format import (
    SYSTEM_RULES,
    ChatMessage,
    PromptInputs,
    ViewerProfile,
    build_messages,
)

DOC_PATH = Path(__file__).parent.parent / "docs" / "prompt_format.md"


def read_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def first_text_block(section: str) -> str:
    """Contenu du premier bloc ```text d'une section du document."""
    return re.search(r"```text\n(.*?)```", section, re.S).group(1).strip()


def doc_example(role: str) -> str:
    """Bloc du message `role` (system, user, assistant) dans l'exemple complet du document."""
    section = read_doc().split("## Exemple complet")[1]
    return first_text_block(section.split(f"### `{role}`")[1])


def utc(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=timezone.utc)


def example_inputs() -> PromptInputs:
    """Les données de l'exemple complet du document (heures en UTC, Paris = UTC+1)."""
    luna_status = "abonné depuis 4 mois"
    return PromptInputs(
        bot_name="Pixou",
        facts=[
            "Le streamer s'appelle Dantek.",
            "Le stream a lieu le lundi, le mercredi et le vendredi à partir de 20h30.",
            "Projet en cours : fine-tuner un modèle d'IA pour en faire l'assistant de la chaîne.",
            "Prochain jeu prévu : Hollow Knight Silksong.",
        ],
        emotes={
            "dantekfHi": "salutations",
            "dantekfLOL": "rire",
            "dantekfLove": "amour",
            "dantekfOK": "acceptation",
        },
        category="Hollow Knight",
        genres=["Platform", "Adventure", "Indie"],
        description=(
            "A 2D action-adventure game set in Hallownest, a vast ruined kingdom of insects. "
            "Explore twisting caverns, fight tainted creatures and uncover ancient secrets."
        ),
        now=utc(11, 23, 3),
        stream_start=utc(11, 19, 30),
        title="On termine enfin Hollow Knight avant Silksong !",
        profiles=[
            ViewerProfile(
                name="LunaRiz",
                status=luna_status,
                followed_at=date(2026, 3, 14),
                last_seen=date(2026, 11, 6),
                summary=(
                    "Vient souvent le mercredi. Joue à Hollow Knight, bloquée au boss final. "
                    "A un chat qui s'appelle Biscotte."
                ),
            ),
        ],
        history=[
            ChatMessage("Kraken_Bleu", "follower", "bonsoir tout le monde", utc(11, 21, 21)),
            ChatMessage("Pixou", "bot", "Salut Kraken_Bleu, bon stream à toi !", utc(11, 21, 22)),
            ChatMessage("LunaRiz", luna_status, "yo", utc(11, 23, 1)),
            ChatMessage("Dantek", "streamer", "salut Luna, ça faisait une semaine", utc(11, 23, 2)),
        ],
        author="LunaRiz",
        message="@Pixou c'est quoi le prochain jeu ? et Dantek il a quel âge ?",
    )


def test_system_rules_match_doc():
    """Les règles du code doivent être identiques à celles du document."""
    section = read_doc().split("## Règles système")[1].split("## Exemple complet")[0]
    assert SYSTEM_RULES == first_text_block(section)


def test_full_example_matches_doc():
    """L'exemple complet rendu par le code doit être identique à celui du document."""
    messages = build_messages(example_inputs(), answer=doc_example("assistant"))
    assert [m["role"] for m in messages] == ["system", "user", "assistant"]
    assert messages[0]["content"] == doc_example("system")
    assert messages[1]["content"] == doc_example("user")
