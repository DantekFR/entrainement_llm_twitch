"""Vérifications automatiques des réponses (critères "checks" des cas d'évaluation).

Toutes les comparaisons ignorent les majuscules, regex comprises, et l'apostrophe typographique (’) vaut '.
Le même code contrôle les exemples du dataset (scripts/merge_batch.py).
"""

import re

from lingua import Language, LanguageDetectorBuilder

SENTENCE_END = re.compile(r"[.!?…]+(?=\s|$)")
SUSPENSION = re.compile(r"(?:\.\.\.|…)\s+(?=\w)")  # « Bon... je sais pas » : la phrase continue
# Gras, italique (*mot* ou _mot_), code, titre, citation, liste. Sur Twitch, les astérisques s'affichent tels quels.
# « 5* sur Steam », « m*rde », « ¯\_(ツ)_/¯ » et « -_- » ne sont pas du markdown.
MARKDOWN = re.compile(
    r"\*\*|\*[^*\s][^*\n]*\*|__|`|(?<!\w)_\w(?:[^_\n]*\w)?_(?!\w)|^\s*(?:[-*#>]|\d+\.)\s", re.MULTILINE
)
BRACKETS = re.compile(r"\[[^\]]*\]")  # [Dantek], [dantekfRage] : imitation des balises du prompt
EMOTE_LIKE = re.compile(r"\b[a-z]{3,}[A-Z]\w*")  # forme d'une emote de chaîne : préfixe + Suffixe (kiwiHype)
# Emotes globales de Twitch, autorisées par les règles : pas une emote de chaîne inventée, et pas de langue.
TWITCH_GLOBAL_EMOTES = (
    "Kappa", "LUL", "PogChamp", "SeemsGood", "NotLikeThis", "BibleThump", "Kreygasm", "ResidentSleeper",
    "VoHiYo", "HeyGuys", "CoolCat", "DansGame", "BabyRage", "FailFish", "CoolStoryBob", "TwitchUnity",
    "TwitchLit", "KonCha", "TehePelo", "PopCorn", "imGlitch", "bleedPurple", "twitchRaid", "panicBasket",
)


# Langues possibles des messages et des réponses (celles de la catégorie « langue » du dataset).
# Restreindre la liste rend la détection plus fiable.
LANGUAGES = {
    "fr": Language.FRENCH,
    "en": Language.ENGLISH,
    "es": Language.SPANISH,
    "de": Language.GERMAN,
    "it": Language.ITALIAN,
    "pt": Language.PORTUGUESE,
}
CODES = {language: code for code, language in LANGUAGES.items()}
DETECTOR = LanguageDetectorBuilder.from_languages(*LANGUAGES.values()).build()


def detect_language(text: str) -> str | None:
    """Code de la langue détectée ("fr", "en"…), ou None si lingua ne sait pas."""
    language = DETECTOR.detect_language_of(text)
    return CODES.get(language)


LANGUAGE_MIN_CONFIDENCE = 0.5
SHORT_FRENCH_WORDS = 5  # en dessous, lingua devine au hasard (« GG ! » vu comme de l'italien)
# Crochets, @pseudo, markdown et codes d'emote : pas de langue (lingua lit kiwiHype comme de l'anglais).
LANGUAGE_NOISE = re.compile(
    r"\[[^\]]*\]|@\w+|\*+|" + EMOTE_LIKE.pattern + r"|\b(?:" + "|".join(TWITCH_GLOBAL_EMOTES) + r")\b"
)


def language_ok(text: str, expected: str) -> bool:
    """Échoue seulement si une autre langue que celle attendue est détectée avec assurance.

    Une réponse française de moins de SHORT_FRENCH_WORDS mots passe toujours : trop courte pour trancher.
    """
    cleaned = LANGUAGE_NOISE.sub(" ", text)
    if expected == "fr" and len(re.findall(r"\w+", cleaned)) < SHORT_FRENCH_WORDS:
        return True
    detected = detect_language(cleaned)
    if detected is None or detected == expected:
        return True
    confidence = DETECTOR.compute_language_confidence(cleaned, LANGUAGES[detected])
    return confidence < LANGUAGE_MIN_CONFIDENCE


def count_sentences(text: str) -> int:
    """Nombre de fins de phrase (. ! ? …), au moins 1. Une emote après le point ne compte pas,
    ni des points de suspension suivis d'une minuscule."""
    text = SUSPENSION.sub(lambda m: " " if m.string[m.end()].islower() else m.group(), text.strip())
    return max(1, len(SENTENCE_END.findall(text)))


def has_markdown(text: str) -> bool:
    """Gras, italique, code, titre, liste, ou réponse sur plusieurs lignes."""
    return bool(MARKDOWN.search(text)) or "\n" in text.strip()


def includes_any(text: str, words: list[str]) -> bool:
    folded = text.casefold()
    return any(word.casefold() in folded for word in words)


def includes_all(text: str, words: list[str]) -> bool:
    folded = text.casefold()
    return all(word.casefold() in folded for word in words)


def matches(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def run_checks(answer: str, checks: dict) -> dict[str, bool]:
    """Résultat de chaque critère (True = réussi). Les critères communs sont toujours appliqués."""
    answer = answer.replace("’", "'")  # « je n’ai pas l’info » vaut « je n'ai pas l'info »
    results = {
        # Une réponse vide, ou faite seulement d'emotes et de mentions, ne réussit rien.
        "not_empty": re.search(r"\w", LANGUAGE_NOISE.sub(" ", answer)) is not None,
        "max_sentences": count_sentences(answer) <= checks["max_sentences"],
        "no_markdown": not has_markdown(answer),
        "no_brackets": not BRACKETS.search(answer),
    }
    for name, value in checks.items():
        if name == "max_sentences":
            continue
        elif name == "language":
            results[name] = language_ok(answer, value)
        elif name == "must_include_any":
            results[name] = includes_any(answer, value)
        elif name == "must_include_all":
            results[name] = includes_all(answer, value)
        elif name == "must_not_match":
            results[name] = not matches(answer, value)
        else:
            raise ValueError(f"Critère inconnu : {name}")
    return results


def summarize(results: list[dict]) -> dict:
    """Scores globaux, par catégorie et par critère.

    results : un dict par cas avec "category" et "checks" (résultat de run_checks).
    Un cas est réussi si tous ses critères le sont.
    """
    if not results:
        raise ValueError("Aucun résultat à résumer.")
    categories: dict[str, dict] = {}
    checks: dict[str, dict] = {}
    for result in results:
        passed = all(result["checks"].values())
        category = categories.setdefault(result["category"], {"cases": 0, "passed": 0})
        category["cases"] += 1
        category["passed"] += passed
        for name, ok in result["checks"].items():
            check = checks.setdefault(name, {"cases": 0, "passed": 0})
            check["cases"] += 1
            check["passed"] += ok

    for stats in [*categories.values(), *checks.values()]:
        stats["score"] = round(stats["passed"] / stats["cases"], 3)

    total_passed = sum(stats["passed"] for stats in categories.values())
    return {
        "score": round(total_passed / len(results), 3),
        "cases": len(results),
        "passed": total_passed,
        "categories": categories,
        "checks": checks,
    }


def print_summary(summary: dict) -> None:
    """Affiche le score global, puis par catégorie et par critère."""
    print(f"Score global : {summary['passed']}/{summary['cases']} ({summary['score']:.0%})")
    for name, stats in summary["categories"].items():
        print(f"  {name:<13} {stats['passed']}/{stats['cases']}")
    print("Par critère :")
    for name, stats in summary["checks"].items():
        print(f"  {name:<17} {stats['passed']}/{stats['cases']}")
