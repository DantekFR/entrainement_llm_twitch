import re
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.prompt_format import (
    SYSTEM_RULES,
    ChatMessage,
    PromptInputs,
    ViewerProfile,
    build_messages,
    fit_history,
    fit_profiles,
    apply_limits,
    render_profiles,
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


def count_lines(text: str) -> int:
    """Faux compteur pour les tests : une ligne = un « token »."""
    return text.count("\n") + 1


def test_fit_history_drops_oldest():
    history = example_inputs().history  # 4 messages -> 5 lignes
    kept = fit_history(history, count_lines, max_tokens=3)
    assert [m.text for m in kept] == ["yo", "salut Luna, ça faisait une semaine"]
    assert len(history) == 4  # la liste d'origine n'est pas modifiée


def test_fit_profiles_keeps_author():
    luna = example_inputs().profiles[0]
    kraken = ViewerProfile("Kraken_Bleu", "follower", date(2026, 11, 11))
    zed = ViewerProfile("Zed", "viewer", date(2026, 11, 1))
    profiles = [luna, kraken, zed]  # 1 + 3 x 2 = 7 lignes
    assert [p.name for p in fit_profiles(profiles, count_lines, max_tokens=5)] == ["LunaRiz", "Kraken_Bleu"]
    assert [p.name for p in fit_profiles(profiles, count_lines, max_tokens=1)] == ["LunaRiz"]


def test_apply_limits():
    inputs = example_inputs()
    huge = lambda text: 10_000  # tout texte dépasse les plafonds
    limited = apply_limits(inputs, huge)
    assert limited.history == []
    assert [p.name for p in limited.profiles] == ["LunaRiz"]
    assert limited.message == inputs.message  # le message n'est jamais touché
    assert len(inputs.history) == 4  # l'original n'est pas modifié

    # Avec de vrais plafonds, l'exemple du document passe sans rien perdre.
    assert apply_limits(inputs, count_lines) == inputs


def test_duration_across_daylight_saving_time():
    """Live commencé à 22h45 le 27 mars 2027, il est 03h48 : 4 h 03 réelles (et non 5 h 03)."""
    from scripts.prompt_format import render_now

    block = render_now(datetime(2027, 3, 28, 1, 48, tzinfo=timezone.utc),
                       datetime(2027, 3, 27, 21, 45, tzinfo=timezone.utc))
    assert "à 22h45 (il y a 4 h 03)" in block
    assert "03h48" in block

def test_empty_summary_is_not_a_new_viewer():
    """Un habitué sans souvenir n'est pas présenté comme nouveau : seul le dernier passage le dit."""
    regular = ViewerProfile("Habitue_42", "abonné depuis 25 mois", date(2025, 6, 6), date(2025, 11, 26))
    newcomer = ViewerProfile("Nouveau_42", "follower", date(2026, 11, 1))
    block = render_profiles([regular, newcomer])
    assert "nouveau" not in block
    assert block.count("Résumé : (aucun souvenir)") == 2
    assert "dernier passage 2025-11-26" in block
    assert "dernier passage (première visite)" in block