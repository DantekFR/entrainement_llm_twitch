# entrainement_llm_twitch

Fine-tuning de **Ministral 3 8B Instruct** (QLoRA, Unsloth) pour en faire l'assistant IA de la chaîne Twitch DantekFR. Le projet se fait **en live sur Twitch**, dans un but pédagogique.

L'assistant répond en une ou deux phrases, en français par défaut, en s'appuyant sur des blocs de contexte fournis par le bot (faits de la chaîne, emotes, catégorie du live, profils des viewers, historique du chat). Il dit « je ne sais pas » plutôt que d'inventer et résiste aux tentatives d'injection. Le modèle final sera exporté en GGUF pour Ollama, sur un Steam Deck.

Le bot lui-même vit dans un autre repo : [dantek_bot_twitch](https://github.com/DantekFR/dantek_bot_twitch).

## Où on en est

| Phase | État |
| --- | --- |
| 0. Environnement | Terminée |
| 1. Explorer le modèle | Terminée |
| Format du prompt v1 | Terminé : document et module de rendu testés |
| 2. Jeu d'évaluation | 20 cas (tag `eval-v1`), modèle de base mesuré : 1/20 |
| 3. Dataset de départ | En cours : chaîne de production en place, 2 lots sur 15 validés (40 exemples) |
| 4. Entraînement v0 | À faire |
| 5. Évaluation v0 | À faire |
| 6. Export GGUF / Ollama | À faire |
| 7. Boucle d'amélioration | À faire |

## Documents

- [docs/ROADMAP.md](docs/ROADMAP.md) : feuille de route complète, phase par phase.
- [docs/prompt_format.md](docs/prompt_format.md) : format exact des prompts (référence pour le dataset, l'évaluation et le bot).
- [docs/chat_template/](docs/chat_template/) : chat template de Ministral et exemple de rendu.
- [CLAUDE.md](CLAUDE.md) : mémoire du projet (décisions, mesures, pièges rencontrés, journal des lives).

## Démarrer

Prérequis : WSL 2 avec un GPU NVIDIA (pilote installé côté Windows), et [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                  # recrée l'environnement à l'identique (uv.lock)
uv run python scripts/check_env.py       # doit finir par "Environnement prêt pour la phase 1"
uv run pytest                            # tests (format, évaluation, réservoirs)
uv run python -m scripts.evaluate --name base               # évalue le modèle de base (GPU)
uv run python -m scripts.rescore runs/<run>/eval.json       # recalcule les scores, sans GPU
uv run python -m scripts.export_batch --batch 3             # lot 3 du dataset + prompt du générateur
uv run python -m scripts.merge_batch --batch 3              # contrôle la sortie du générateur et la met au format d'entraînement
```

## Contenu

- `scripts/check_env.py` : vérification de l'environnement (CUDA, bf16, couche 4 bits).
- `scripts/prompt_format.py` : construction des prompts au format v1 (blocs, assemblage, plafonds en tokens).
- `scripts/measure_prompt.py` : mesure en tokens de l'exemple du document.
- `eval/cases.jsonl` : jeu d'évaluation (un cas par ligne), à ne jamais montrer au générateur du dataset.
- `scripts/eval_cases.py`, `scripts/checks.py`, `scripts/evaluate.py`, `scripts/rescore.py` : lecture des cas, vérifications automatiques, évaluation d'un modèle, recalcul des scores.
- `configs/pools.yaml`, `scripts/contexts.py` : réservoirs et tirage aléatoire des contextes du dataset.
- `configs/seed_matrix.yaml` : situations à couvrir (catégories et leurs poids, registres, attitudes).
- `configs/generator_prompt.md`, `scripts/export_batch.py`, `scripts/merge_batch.py` : prompt du générateur, export d'un lot, contrôle et fusion de la sortie.
- `data/seed/batches/batch_NNN/` : un dossier par lot (contextes, prompt, sortie du générateur, exemples acceptés).
- `tests/` : tests pytest (dont les garde-fous contre la contamination du jeu d'évaluation).
- `notebooks/01_explore_model.ipynb` : exploration du modèle (tokenizer, chat template, tailles de prompt, premières générations).

## Licence

MIT, voir [LICENSE](LICENSE).
