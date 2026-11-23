"""Fusionne la sortie du chat générateur avec les contextes d'un lot (phase 3).

Vérifie chaque exemple, le rend au format d'entraînement (messages system / user / assistant)
et écrit les exemples acceptés dans data/seed/batches/batch_NNN/merged.jsonl.
La fusion est déterministe : on peut durcir les contrôles et refusionner un lot sans le réexporter.

Usage : uv run python -m scripts.merge_batch --batch 3
"""

import argparse
import copy
import json
import re
from pathlib import Path

from scripts.checks import (
    DETECTOR, EMOTE_LIKE, LANGUAGE_NOISE, LANGUAGES, TWITCH_GLOBAL_EMOTES,
    detect_language, language_ok, run_checks,
)
from scripts.eval_cases import case_to_inputs
from scripts.prompt_format import apply_limits, build_messages
from scripts.export_batch import batch_dir

MODEL_ID = "unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit"
# Jetons de contrôle de Ministral. Écrits dans un texte, le tokenizer en fait de vrais jetons :
# un « [/INST] » dans un message fausserait le masque d'entraînement, un « </s> » couperait la séquence.
CONTROL_TOKENS = (
    "<unk>", "<s>", "</s>", "<pad>", "[INST]", "[/INST]", "[SYSTEM_PROMPT]", "[/SYSTEM_PROMPT]",
    "[AVAILABLE_TOOLS]", "[/AVAILABLE_TOOLS]", "[TOOL_RESULTS]", "[/TOOL_RESULTS]", "[TOOL_CALLS]",
    "[TOOL_CONTENT]", "[IMG]", "[IMG_BREAK]", "[IMG_END]", "[PREFIX]", "[MIDDLE]", "[SUFFIX]",
    "[AUDIO]", "[BEGIN_AUDIO]", "[ARGS]", "[CALL_ID]", "[THINK]", "[/THINK]",
)
SPECIAL_TOKEN = re.compile(r"<SPECIAL_\d+>")  # les 1 000 premiers ids sont tous des jetons réservés
COLON_EMOTE = re.compile(r":[A-Za-z]\w*:")      # :kiwiHype: ne s'affiche pas sur Twitch
CODE_FENCE = re.compile(r"^`{3,}\w*|`{3,}\w*$")  # balise ``` ou ```jsonl collée au début ou à la fin d'une ligne
FOREIGN_WARNING_CONFIDENCE = 0.9  # message très probablement étranger hors catégorie langue : à relire
SHORT_RESPONSE_WORDS = 4  # réponse « langue » trop courte pour vérifier sa langue : à relire


def schema_problem(row) -> str | None:
    """Ce qui ne va pas dans la structure d'une ligne de output.jsonl (None si elle est correcte)."""
    if not isinstance(row, dict):
        return "une ligne doit être un objet JSON {...}"
    for key in ("id", "message", "response"):
        if not isinstance(row.get(key), str):
            return f"champ « {key} » absent ou qui n'est pas un texte"
    if not isinstance(row.get("history"), list) or not all(isinstance(text, str) for text in row["history"]):
        return "champ « history » absent ou qui n'est pas une liste de textes"
    return None


def read_output(path: Path, items: list[dict]) -> dict[str, dict]:
    """Lignes de output.jsonl par id. Arrête le script, sans rien écrire, si le fichier est inutilisable."""
    if not path.exists():
        raise SystemExit(f"{path} n'existe pas : enregistre la sortie du générateur (Ctrl+S).")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise SystemExit(f"{path.name} n'est pas en UTF-8 : enregistre-le en UTF-8 (en bas à droite de VS Code).")
    rows = {}
    for number, line in enumerate(text.splitlines(), start=1):
        line = CODE_FENCE.sub("", line.strip()).strip()
        if not line:
            continue  # ligne vide, ou balise du bloc de code copiée avec la sortie
        if not line.startswith("{"):
            raise SystemExit(
                f"{path.name}, ligne {number} : ce n'est pas du JSON (texte du chat copié avec la sortie ?) : "
                "supprime cette ligne."
            )
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            hint = "" if line.endswith("}") else (
                " Ligne incomplète (sortie coupée ?) : supprime-la et demande au générateur de la réécrire en entier."
            )
            raise SystemExit(
                f"{path.name}, ligne {number} : JSON invalide ({error.msg}, colonne {error.colno}).{hint}"
            )
        problem = schema_problem(row)
        if problem:
            raise SystemExit(f"{path.name}, ligne {number} : {problem}.")
        if row["id"] in rows:
            if row == rows[row["id"]]:
                continue  # même ligne recopiée par le générateur en reprenant la suite
            raise SystemExit(f"{path.name}, ligne {number} : id en double ({row['id']}) avec un contenu différent.")
        rows[row["id"]] = row
    if not rows:
        raise SystemExit(f"{path} est vide (sortie collée sans Ctrl+S ?) : rien n'est écrit.")
    unknown = sorted(set(rows) - {item["id"] for item in items})
    if unknown:
        raise SystemExit(
            f"{path.name} contient des ids qui ne sont pas de ce lot ({', '.join(unknown[:3])}) : "
            "sortie collée dans le mauvais dossier ? Rien n'est écrit."
        )
    return rows


def fill_item(item: dict, row: dict) -> dict:
    """Copie du contexte, avec les textes écrits par le générateur."""
    inputs = copy.deepcopy(item["inputs"])  # on ne modifie pas le lot d'origine
    for message, text in zip(inputs["history"], row["history"]):
        message["text"] = text
    inputs["message"] = row["message"]
    return inputs


def mentions(text: str, name: str) -> bool:
    """Le texte mentionne-t-il exactement @name (et pas @nameXYZ) ?"""
    return re.search("@" + re.escape(name) + r"(?![\w-])", text) is not None


def language_text(text: str, inputs: dict) -> str:
    """Texte sans ce qui n'a pas de langue : crochets, @pseudo, emotes, titre et nom de la catégorie."""
    for name in (inputs["title"], inputs["category"]):  # le titre d'abord : il contient souvent la catégorie
        if name:
            text = text.replace(name, " ")
    return LANGUAGE_NOISE.sub(" ", text)


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def emote_problems(text: str, emotes: dict[str, str]) -> list[str]:
    """Emote de chaîne inventée, entre deux-points, ou mal écrite (Twitch respecte la casse)."""
    problems = [
        "emote inconnue : " + word for word in EMOTE_LIKE.findall(text)
        if word not in emotes and word not in TWITCH_GLOBAL_EMOTES
    ]
    colon = COLON_EMOTE.search(text)
    if colon:
        problems.append("emote entre deux-points : " + colon.group())
    folded = {code.casefold(): code for code in emotes}
    for word in re.findall(r"\w+", text):
        code = folded.get(word.casefold())
        if code and word != code:
            problems.append(f"emote mal écrite : {word} au lieu de {code}")
    return problems


def streamer_pattern(name: str) -> re.Pattern:
    return re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", re.IGNORECASE)


def streamer_in_blocks(item: dict) -> bool:
    """Le nom du streamer figure-t-il dans les faits ou parmi les auteurs de l'historique ?"""
    inputs = item["inputs"]
    blocks = " ".join([*inputs["facts"], *(message["author"] for message in inputs["history"])])
    return streamer_pattern(item["meta"]["streamer"]["name"]).search(blocks) is not None


def find_problems(item: dict, row: dict) -> list[str]:
    """Raisons de rejeter un exemple (liste vide = exemple accepté)."""
    inputs, meta = item["inputs"], item["meta"]
    bot_name, response = inputs["bot_name"], row["response"]
    texts = [row["message"], *row["history"]]  # textes écrits par le générateur, hors réponse
    problems = []

    # Structure
    if len(row["history"]) != len(inputs["history"]):
        problems.append(f"historique : {len(row['history'])} textes au lieu de {len(inputs['history'])}")
    if any(not text.strip() for text in texts):
        problems.append("message ou texte d'historique vide")
    if any("\n" in text for text in texts):
        problems.append("retour à la ligne dans le message ou l'historique")
    if not mentions(row["message"], bot_name):
        problems.append("le message ne mentionne pas @" + bot_name)
    for name in meta["mentioned"]:
        if not mentions(row["message"], name):
            problems.append("mention manquante : @" + name)
    tokens = sorted({token for text in [*texts, response] for token in CONTROL_TOKENS if token in text}
                    | {token for text in [*texts, response] for token in SPECIAL_TOKEN.findall(text)})
    if tokens:
        problems.append("jeton de contrôle écrit en toutes lettres : " + ", ".join(tokens))

    # Messages du bot dans l'historique : mêmes règles que sa réponse, et toujours après une mention.
    if len(row["history"]) == len(inputs["history"]):
        since_last_bot = []
        for message, text in zip(inputs["history"], row["history"]):
            if message["status"] != "bot":
                since_last_bot.append(text)
                continue
            if not any(mentions(previous, bot_name) for previous in since_last_bot):
                problems.append("historique : le bot parle sans avoir été mentionné avec @" + bot_name)
            checks = run_checks(text, {"max_sentences": 2})
            problems += [f"historique : message du bot, critère {name} échoué" for name, ok in checks.items() if not ok]
            problems += ["historique : " + problem for problem in emote_problems(text, inputs["emotes"])]
            since_last_bot = []

    # Forme de la réponse
    if response != response.strip():
        problems.append("espaces ou saut de ligne autour de la réponse")
    if re.match(r"\s*@?(?:" + re.escape(bot_name) + r"|bot|assistant)\s*:", response, re.IGNORECASE):
        problems.append("réponse préfixée par un nom (« Bot : »)")
    results = run_checks(response, {"max_sentences": 2})
    problems += [f"critère {name} échoué" for name, ok in results.items() if not ok]

    # Langue
    language, check_language = "fr", True
    if item["situation"]["category"] == "langue":
        language = detect_language(language_text(row["message"], inputs))
        if language in (None, "fr"):
            problems.append("catégorie langue, mais le message n'est pas clairement étranger")
            language = "fr"
        elif word_count(language_text(response, inputs)) < SHORT_RESPONSE_WORDS:
            check_language = False  # trop court pour trancher : signalé par find_warnings
        elif detect_language(language_text(response, inputs)) != language:
            problems.append(f"catégorie langue : la réponse n'est pas en {language} comme le message")
    if check_language and not language_ok(language_text(response, inputs), language):
        problems.append(f"critère language échoué (attendu : {language})")

    # Emotes de la réponse
    problems += emote_problems(response, inputs["emotes"])

    # Le streamer ne peut être nommé que si son nom figure dans un bloc ou dans le chat.
    streamer = meta["streamer"]["name"]
    named = streamer_pattern(streamer)
    if named.search(response) and not streamer_in_blocks(item) and not any(named.search(t) for t in texts):
        problems.append(f"la réponse nomme {streamer}, absent des blocs")
    return list(dict.fromkeys(problems))  # sans doublon, dans l'ordre


def find_warnings(item: dict, row: dict) -> list[str]:
    """Points à relire à la main, sans rejeter l'exemple."""
    inputs, warnings = item["inputs"], []
    if item["situation"]["category"] != "langue":  # le franglais reste du français : on ne rejette pas
        cleaned = LANGUAGE_NOISE.sub(" ", row["message"])
        language = detect_language(cleaned)
        if language not in (None, "fr"):
            confidence = DETECTOR.compute_language_confidence(cleaned, LANGUAGES[language])
            if confidence >= FOREIGN_WARNING_CONFIDENCE:
                warnings.append(f"message peut-être en {language} ({confidence:.2f}) hors catégorie langue")
    elif word_count(language_text(row["response"], inputs)) < SHORT_RESPONSE_WORDS:
        warnings.append("réponse trop courte pour vérifier sa langue")
    if not streamer_in_blocks(item):
        warnings.append("streamer nommé dans aucun bloc : vérifier que la réponse n'invente pas de nom")
    return warnings


def main():
    parser = argparse.ArgumentParser(description="Fusionne et vérifie la sortie du générateur.")
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()

    folder = batch_dir(args.batch)
    if not (folder / "batch.json").exists():
        raise SystemExit(f"{folder} : lot non exporté (lance d'abord scripts.export_batch --batch {args.batch}).")
    items = json.loads((folder / "batch.json").read_text(encoding="utf-8"))
    rows = read_output(folder / "output.jsonl", items)

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
        for warning in find_warnings(item, row):
            print(f"À RELIRE {item['id']} : {warning}")
        inputs = apply_limits(case_to_inputs({"inputs": fill_item(item, row)}), count_tokens)
        if len(inputs.history) < len(row["history"]):
            print(f"À RELIRE {item['id']} : historique tronqué ({len(row['history'])} → {len(inputs.history)} messages),"
                  " la réponse ne doit pas s'appuyer sur un message retiré")
        messages = build_messages(inputs, row["response"])
        max_tokens = max(max_tokens, count_tokens(tokenizer.apply_chat_template(messages, tokenize=False)))
        accepted.append({"id": item["id"], "category": item["situation"]["category"], "messages": messages})

    if not accepted:
        raise SystemExit("0 exemple accepté : merged.jsonl n'est pas modifié.")
    path = folder / "merged.jsonl"
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in accepted), encoding="utf-8")
    print(f"{len(accepted)}/{len(items)} exemples acceptés -> {path}")
    print(f"Exemple le plus long : {max_tokens} tokens (max_seq_length = 4096)")


if __name__ == "__main__":
    main()
