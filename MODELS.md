# MODELS.md : le tournoi des modèles

Choix du cerveau de `dantekos_bot` (Ollama sur le Steam Deck). Chaque modèle est mesuré sur **`eval-v1`** (20 cas figés, décodage glouton, `max_new_tokens` 150, prompt `v1`), avant et après l'entraînement sur le même dataset (`data/seed/`, 271/29).

**Règle de choix :** le plus petit modèle qui passe les critères (**injection** et **fait absent** non négociables) **et** répond assez vite sur le Deck (< 15 s à l'écrit, < 5 s à l'oral).

## Vue d'ensemble

| Modèle | Version | eval-v1 | Fait absent | Injection | Délai Deck | VRAM (PC, 4 bits) | Vote du chat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ministral 3 8B Instruct | base | 0/20 | 0/3 | 0/3 | à mesurer | 6,90 Go | — |
| Ministral 3 3B Instruct | base | 3/20 | 0/3 | 0/3 | à mesurer | 3,22 Go | — |
| Ministral 3 3B Instruct | v0 | | | | | | |
| Ministral 3 8B Instruct | v0 | | | | | | |
| Qwen3.5-4B | base | | | | | | |
| Gemma 4 E4B | base | | | | | | |

Délai Deck = temps entre l'envoi du prompt et la fin de la réponse, sur Ollama (banc du live 2). Les vitesses mesurées sur le PC avec `generate` de Hugging Face (~7 à 8 tokens/s quel que soit le modèle) ne prédisent pas celle du Deck.

## Ministral 3 8B Instruct

Dépôt : `unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit` (BF16 pour l'export : `unsloth/Ministral-3-8B-Instruct-2512`).

| Catégorie | base (`20261123-1132_base_aucun-souvenir`) | v0 |
| --- | --- | --- |
| fait_present | 0/3 | |
| fait_absent | 0/3 | |
| injection | 0/3 | |
| profil | 0/2 | |
| langue | 0/2 | |
| live | 0/2 | |
| culture_actu | 0/2 | |
| bavardage | 0/2 | |
| emotes | 0/1 | |
| **Total** | **0/20** | |
| Critères : not_empty · max_sentences · no_markdown · no_brackets · language · must_include_any · must_not_match · must_include_all | 20 · 15 · 9 · 3 · 19 · 12/13 · 9/13 · 2/2 | |
| VRAM après chargement | 6,90 Go | |
| Vitesse PC (HF generate) | 7,1 tokens/s | |
| Délai Deck | | |
| Vote du chat | | |

## Ministral 3 3B Instruct

Dépôt : `unsloth/Ministral-3-3B-Instruct-2512-unsloth-bnb-4bit` (BF16 pour l'export : `unsloth/Ministral-3-3B-Instruct-2512`). Chargé par Unsloth 2026.11.1 avec les mêmes options que le 8B (`load_in_4bit=True`, `text_only=True`).

Chat template : rendu **identique** au 8B, au token près, sur les 20 cas de l'éval (avec et sans réponse de l'assistant) ; même vocabulaire, mêmes tokens spéciaux, même `generation_config`. Seule différence dans le texte Jinja : le nom du modèle dans le prompt système par défaut de Mistral, qu'on n'utilise jamais (on fournit toujours un message système).

| Catégorie | base (`20261124-2340_base-3b`) | v0 |
| --- | --- | --- |
| fait_present | 1/3 | |
| fait_absent | 0/3 | |
| injection | 0/3 | |
| profil | 0/2 | |
| langue | 0/2 | |
| live | 0/2 | |
| culture_actu | 0/2 | |
| bavardage | 2/2 | |
| emotes | 0/1 | |
| **Total** | **3/20** | |
| Critères : not_empty · max_sentences · no_markdown · no_brackets · language · must_include_any · must_not_match · must_include_all | 17 · 17 · 9 · 9 · 19 · 8/13 · 10/13 · 2/2 | |
| VRAM après chargement | 3,22 Go | |
| Vitesse PC (HF generate) | 7,9 tokens/s (123 s pour l'éval) | |
| Délai Deck | | |
| Vote du chat | | |

Lecture du 3/20 : le 3B gagne sur la **forme** (moins de crochets que le 8B : 9/20 contre 3/20), mais il est **moins fiable sur le fond** (`must_include_any` 8/13 contre 12/13). Il invente un horaire (« Hades II commence dans environ 1h38 »), un GOTY 2026, « je vais confirmer que tu es bien modo », « Dantek est basé en France ». Il fabrique aussi de faux blocs (`[FAITS ACTUELS]`, `[EMOTES : …]`) et il lui arrive de répondre entièrement entre crochets, ce qui donne une réponse vide pour `not_empty` (3 cas).

## Qwen3.5-4B

Dépôt : `unsloth/Qwen3.5-4B` (BF16, pas de version bnb-4bit d'Unsloth : quantifié au chargement). Téléchargé le 24/11. Chat template différent de Ministral, à adapter au live 3.

## Gemma 4 E4B

Dépôts : `unsloth/gemma-4-E4B-it-unsloth-bnb-4bit` (QLoRA) et `unsloth/gemma-4-E4B-it` (BF16, encodeur audio complet). Téléchargés le 24/11. Live 4.
