# Dataset de départ (seed v0)

300 exemples synthétiques au format d'entraînement `{id, category, messages}` (`system`, `user`, `assistant`), rendus avec `prompt_format v1` (`scripts/prompt_format.py`).

## Fichiers

| Fichier | Contenu |
| --- | --- |
| `train.jsonl` | 271 exemples |
| `val.jsonl` | 29 exemples (environ 10 % de chaque catégorie, graine 42) |
| `batches/batch_NNN/` | un dossier par lot : `batch.json` (contexte tiré), `prompt.md` (prompt envoyé), `output.jsonl` (sortie du générateur), `merged.jsonl` (exemples rendus) |

Recréer `train.jsonl` et `val.jsonl` : `uv run python -m scripts.assemble_seed` (résultat identique à chaque lancement).

## Répartition

| Catégorie | Total | Train | Val |
| --- | --- | --- | --- |
| fait_present | 45 | 41 | 4 |
| fait_absent | 45 | 41 | 4 |
| profil | 39 | 35 | 4 |
| live | 36 | 32 | 4 |
| injection | 34 | 31 | 3 |
| bavardage | 30 | 27 | 3 |
| culture_actu | 30 | 27 | 3 |
| langue | 24 | 22 | 2 |
| emotes | 17 | 15 | 2 |

Hors live : environ 15 %. Réponses sans emote ni emoji : environ 28 %. Mention du bot ailleurs qu'en tête du message : environ 23 %. Réponses de 9 à 38 mots (médiane 21), aucune ne finit par une question, aucun doublon.

## Comment il a été produit

1. **Contexte tiré par le code** (`scripts/export_batch.py`, graine = numéro du lot) : faits, emotes, profils, catégorie, horaires, squelette d'historique, situation (catégorie × registre × attitude, `configs/seed_matrix.yaml`).
2. **Textes écrits par un chat en ligne** (prompt `configs/generator_prompt.md`, une nouvelle conversation par lot) : historique, message, réponse.
3. **Fusion et contrôles** (`scripts/merge_batch.py`) : structure, critères de l'éval, emotes, mentions, langue, nom du streamer, jetons de contrôle.
4. **Relecture complète** de chaque lot avant la fusion (faits, calculs de durée, culture générale, accords).
5. **Contrôle anti-contamination** : aucun pseudo, nom de bot ni jeu de l'évaluation dans le dataset ; les messages les plus proches de l'éval posent le même type de question sur un autre contexte.

## Provenance des tirages

| Lots | Commit du code de tirage |
| --- | --- |
| 3 à 7 | `fda5326` |
| 8 et 9 | `114433c` (titre « Live anniversaire » retiré) |
| 10 à 17 | `adea4a1` (deux souvenirs neutralisés) |

Les lots 1 et 2 ont été retirés (commit `71e4abb`) : tirés avant le nettoyage des réservoirs du 22 novembre, ils contenaient des noms de jeux de l'évaluation et des premières visites avec souvenirs. Ils sont remplacés par les lots 16 et 17 et restent dans l'historique Git.

## Retouches à la main

- Accords genrés neutralisés dans des réponses et des messages du bot : le genre d'un viewer n'est jamais déduit de son pseudo ni de l'accord choisi par un autre viewer.
- Mention `@<bot>` ajoutée dans l'historique quand le bot répondait deux fois sans être mentionné entre les deux.
- Lot 12 : un jeu de l'évaluation (Celeste) retiré d'un historique, une emote inventée remplacée.
- Lot 17 : mention `@pseudo` retirée en tête des 24 messages du bot de l'historique (tic du générateur).
- Tous les lots refusionnés avec le résumé vide `(aucun souvenir)` au lieu de « nouveau viewer » (commit `a899abb`).

## Limites connues

- Données 100 % synthétiques, un seul générateur.
- Trois profils tirent deux souvenirs peu compatibles (Lyon et Québec, bac et travail de nuit) ; aucune réponse ne s'appuie sur les deux.
- Plusieurs faits « Projet en cours » peuvent coexister dans un même contexte (laissé volontairement).
- Les lives qui ne respectent pas l'horaire annoncé sont un peu plus fréquents que prévu (environ 20 % au lieu de 15 %).
