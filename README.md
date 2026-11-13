# entrainement_llm_twitch

Fine-tuning de **Ministral 3 8B Instruct** (QLoRA, Unsloth) pour en faire l'assistant IA de la chaîne Twitch DantekFR. Le projet se fait **en live sur Twitch**, dans un but pédagogique.

L'assistant répond en une ou deux phrases, en français par défaut, en s'appuyant sur des blocs de contexte fournis par le bot (faits de la chaîne, emotes, catégorie du live, profils des viewers, historique du chat). Il dit « je ne sais pas » plutôt que d'inventer et résiste aux tentatives d'injection. Le modèle final sera exporté en GGUF pour Ollama, sur un Steam Deck.

Le bot lui-même vit dans un autre repo : [dantek_bot_twitch](https://github.com/DantekFR/dantek_bot_twitch).

## Où on en est

| Phase | État |
| --- | --- |
| 0. Environnement | Terminée |
| 1. Explorer le modèle | Terminée |
| Format du prompt v1 | Document terminé, module de rendu en cours |
| 2. Jeu d'évaluation | À faire |
| 3. Dataset de départ | À faire |
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
uv run pytest                            # tests du format de prompt
```

## Contenu

- `scripts/check_env.py` : vérification de l'environnement (CUDA, bf16, couche 4 bits).
- `scripts/prompt_format.py` : construction des prompts au format v1.
- `tests/` : tests pytest.
- `notebooks/01_explore_model.ipynb` : exploration du modèle (tokenizer, chat template, tailles de prompt, premières générations).

## Licence

MIT, voir [LICENSE](LICENSE).
