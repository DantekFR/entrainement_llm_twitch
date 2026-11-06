# CLAUDE.md : mémoire du projet

Ce fichier est lu au début de chaque session Claude Code. Il dit où en est le projet, comment on travaille, et quelles erreurs ne pas refaire. **Il est mis à jour à la fin de chaque live** (voir la dernière section).

## Le projet

Fine-tuner **Ministral 3 8B Instruct** (QLoRA) pour en faire l'assistant IA de la chaîne Twitch DantekFR. L'assistant répond **en français par défaut**, dans la langue du viewer seulement si son message est clairement écrit dans une autre langue. Il répond court (une ou deux phrases), en s'appuyant sur des blocs de contexte injectés par le bot (faits de la chaîne, emotes, profils des viewers, historique du chat). Il dit "je ne sais pas" plutôt que d'inventer, et résiste aux tentatives d'injection. Le modèle final sera exporté en GGUF pour Ollama sur un Steam Deck.

- Feuille de route complète : `docs/ROADMAP.md`
- **Format du prompt (référence) : `docs/prompt_format.md`**
- Repo du bot (hors périmètre ici) : https://github.com/DantekFR/dantek_bot_twitch (TwitchIO 3 + aiohttp)
- Le nom du bot n'est **jamais écrit en dur** : il passe par `{bot_name}`, car il sera renommé par le chat.

## Comment on travaille

Le projet se fait **en live sur Twitch, dans un but pédagogique**. Les viewers voient VS Code et cette conversation.

- **Claude ne modifie aucun fichier pendant le live** : il indique les tâches (code à coller, commandes, résultat attendu) et Dantek les exécute. Seule exception : la mise à jour de ce fichier en fin de live.
- Avancer **une étape à la fois** et attendre la validation de Dantek avant la suivante.
- Avant chaque étape, expliquer simplement **quoi** et **pourquoi**, pour quelqu'un qui découvre le fine-tuning.
- Donner les commandes à lancer, avec ce qu'on doit s'attendre à voir.
- En cas d'échec, expliquer la cause avant de proposer une correction.
- **Noms de variables, fonctions et classes en anglais.** Commentaires, affichages et textes des prompts en français.
- Répondre en français, de façon concise.
- **Sécurité** : tout est affiché en live. Ne jamais lire ni afficher de token, de clé, de fichier `.env` ou d'identifiants, et ne jamais demander à les coller.
- Le live est consacré **uniquement à l'entraînement**. On ne touche pas au bot.

## Environnement

| Élément | Valeur |
| --- | --- |
| Machine | Windows + WSL 2, RTX 4070 (12 Go de VRAM) |
| Gestionnaire | uv (pas conda), Python 3.12 (`.python-version`) |
| PyTorch | index `pytorch-cu130` déclaré dans `pyproject.toml` (torch et torchvision) |
| Bibliothèques | transformers 5.x (≤ 5.17), TRL ≤ 1.15, PEFT, bitsandbytes, Unsloth 2026.11, TensorBoard |
| Versions exactes | figées dans `uv.lock` (versionné) |
| Notebooks | groupe `dev` (ipykernel) |

Commandes de base :

```bash
uv sync                                  # recrée l'environnement à l'identique
uv run python scripts/check_env.py       # doit finir par "Environnement prêt pour la phase 1"
```

Modèle utilisé : `unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit`, chargé avec `FastModel.from_pretrained(..., load_in_4bit=True, text_only=True)`. Le tokenizer est ensuite rechargé avec `AutoTokenizer.from_pretrained(MODEL_ID, fix_mistral_regex=True, padding_side="left")`, puis réassigné à `tokenizer.tokenizer`.

## Où on en est

| Phase | État |
| --- | --- |
| 0. Environnement | **Terminée** : `check_env.py` au vert (CUDA, bf16, couche 4 bits testée) |
| 1. Explorer le modèle | **Terminée** : `notebooks/01_explore_model.ipynb`, chat template dans `docs/chat_template/` |
| `prompt_format` v1 | **En cours** : `docs/prompt_format.md`, sections Principes, Structure et Plafonds écrites |
| 2. Jeu d'évaluation | À faire |
| 3. Dataset de départ | À faire |
| 4. Entraînement v0 | À faire |
| 5. Évaluation v0 | À faire |
| 6. Export GGUF / Ollama | À faire |
| 7. Boucle d'amélioration | À faire |

### Ce que contient le notebook 01

Chargement en 4 bits et VRAM occupée, comptage des paramètres (corrigé pour le 4 bits), architecture d'une couche, tokens spéciaux, tokenizer rechargé avec `fix_mistral_regex=True` (cellule 11), découpage de messages typiques du chat, comparaison français/anglais, rendu du chat template, différence tokenizer/processor, sauvegarde du template, prototype de prompt, mesure de sa taille, fonction de génération, tests de situations (cellule 15), puis **mesure d'un prompt réaliste** (cellule 16 : `build_prompt(n_facts, n_profiles, n_messages)`, `count_tokens`).

### Mesures clés

Les sorties du notebook ne sont pas versionnées : les chiffres importants doivent être reportés ici.

| Mesure | Valeur |
| --- | --- |
| VRAM après chargement 4 bits | 6,90 Go (pic 6,90 Go) |
| Paramètres | 8,92 Md (langage 7,95 · lm_head 0,54 · vision 0,40 · projecteur 0,03) |
| Ratio de tokens français/anglais | de 1,08 à 1,56 (sur 2 phrases) |
| Prompt prototype : 0 souvenir / 0 message → 5 / 20 → 10 / 50 | 328 → 979 → 1 883 tokens |
| Prompt réaliste (faits / profils / messages) : 3/1/20 · 15/1/20 · 15/3/50 · **20/5/50** · 25/5/80 | 1 105 · 1 315 · 2 562 · **2 831** · 4 005 tokens |
| Vitesse de génération (4070, 4 bits, HF generate) | 6 à 9 tokens/s |
| `max_seq_length` | **4096** (confirmé : budget du prompt v1 ≈ 3 500 tokens) |

### Comportement du modèle de base (référence avant fine-tuning)

- Fait absent : il invente ("Dantek a 28 ans").
- Réponses trop longues, markdown, emojis en excès, finit souvent par une question.
- Ressort des souvenirs hors sujet (le script Python dans une réponse sur l'âge).
- Message en anglais : il répond en français (le prompt disait alors "toujours en français").
- Injection : il refuse, mais en inventant des précisions ("je ne suis pas un modo").

### Décisions du `prompt_format` v1 (détails dans `docs/prompt_format.md`)

- **system** : règles (`{bot_name}`), `[FAITS DE LA CHAÎNE]`, `[EMOTES DE LA CHAÎNE]` (`code : sens`), puis `[MAINTENANT]` **en dernier**, pour que le début du prompt reste stable et réutilisable par le cache KV d'Ollama. Un bloc vide contient `- (aucun)`.
- **user** : `[PROFILS DES VIEWERS]` (l'auteur, puis les viewers mentionnés avec @ ; résumé par viewer mis à jour en fin de live), `[HISTORIQUE DU CHAT]` (`[HH:MM] pseudo (statut) : message`, réponses du bot incluses), `[MESSAGE DE <pseudo>]`.
- **assistant** : la réponse seule, une ou deux phrases. **Pas de `<silence>`** : c'est le bot qui décide d'appeler le modèle, seulement quand on le mentionne.
- **Langue** : français par défaut. Les anglicismes et les messages mixtes restent en français.
- **Emotes** : priorité aux emotes de la chaîne (liste injectée, jamais apprise par cœur), puis aux emotes globales de Twitch, puis aux emojis Unicode. Dès la v1.
- **Statuts** : libellés français dans le prompt (`streamer`, `modo`, `VIP`, `abonné…`, `follower`, `viewer`, `bot`). Le bot les stocke en anglais.
- **Plafonds en tokens** (pas en lignes) : faits 600, emotes 300, profils 600, historique 1 500, total ≈ 3 500.
- **Dataset** : `{bot_name}` et les listes d'emotes sont tirés au hasard, pour que le modèle lise ces informations dans le prompt au lieu de les mémoriser.

### Données que le bot devra fournir (TwitchIO 3, à implémenter hors live)

Statut via `chatter.broadcaster` / `.moderator` / `.vip` / `.subscriber` (gratuit). Ancienneté d'abonnement via `chatter.badges` (champ `info`, à vérifier). Palier via `fetch_broadcaster_subscriptions()` → `.tier` (scope `channel:read:subscriptions`). Date de follow via `chatter.follow_info()` → `.followed_at` (scope `moderator:read:followers`). **Dernier passage** et **résumés des viewers** : à prévoir dans l'architecture du bot.

## Pièges déjà rencontrés : ne pas les refaire

- **Double `<s>`** : le texte produit par `apply_chat_template` contient déjà le BOS. Le tokeniser ensuite avec `add_special_tokens=False`, sinon on obtient deux `<s>`.
- **Tokenizer ou processor** : `FastModel` renvoie un *processor* (modèle multimodal). Pour le texte, passer par `tokenizer.tokenizer`.
- **Comptage des paramètres en 4 bits** : `numel()` d'un `Params4bit` compte des octets compactés, soit deux poids par élément. Multiplier par 2.
- **Prompt système par défaut** : si aucun message `system` n'est fourni, le template de Ministral injecte un long prompt par défaut de Mistral ("Le Chat", outils, navigation web...). **Toujours fournir un message système**, à l'entraînement, à l'évaluation et dans le Modelfile Ollama.
- **Avertissement `incorrect regex pattern` (`fix_mistral_regex`)** : c'est une fausse alerte. Le `tokenizer.json` d'Unsloth contient déjà la regex corrigée (pré-tokenizer identique avec et sans l'option). On recharge quand même le tokenizer avec `fix_mistral_regex=True` pour faire taire l'avertissement, qui s'affiche toujours une fois au `FastModel.from_pretrained`. Unsloth ne transmet pas cette option, et le marqueur est posé sur `tok.backend_tokenizer`, pas sur `tok`. En phase 6, vérifier que la tokenisation de Hugging Face et celle du GGUF (llama.cpp) donnent les mêmes identifiants.
- **Avertissement `max_new_tokens` / `max_length (=262144)`** : sans gravité, c'est `max_new_tokens` qui s'applique.
- **`CLAUDE.md` doit être à la racine** du repo pour être chargé automatiquement (il était dans `docs/`).
- **Fichiers parasites** : Unsloth crée `unsloth_compiled_cache/`, et les copies depuis Windows créent des `*Zone.Identifier`. Les deux sont ignorés par Git.
- **`*.bin` est ignoré** globalement : si un fichier `.bin` doit un jour être versionné, ajouter une exception.
- **Identité Git** : le premier commit est parti avec un autre compte. Vérifier `git config user.name` et `git config user.email` avant de commiter.
- **Sorties de notebook** : elles ne sont pas versionnées, donc les résultats se perdent. Reporter les mesures clés dans ce fichier.
- **Sessions Claude Code** : reprendre une vieille conversation coûte cher (le cache a expiré). Repartir d'une session neuve, ce fichier sert de mémoire.

## Prochaines étapes

1. **Terminer `docs/prompt_format.md`** :
   - corriger la ligne des emojis (ajouter "un ou deux au maximum, à bon escient") ;
   - mettre à jour la ligne des statuts (libellés français, `abonné depuis N mois, palier N`) ;
   - ajouter la section "Données que le bot doit fournir" ;
   - écrire la section 4 "Règles pour le dataset" (`{bot_name}` et emotes aléatoires, cas sans profil, blocs vides) ;
   - écrire la section 5 "Exemple complet".
2. Écrire le texte définitif des **règles système** (avec la règle de langue et les emotes) et sortir les fonctions de construction du prompt (cellule 16) dans un module `scripts/`, avec des noms en anglais et le respect des plafonds.
3. **Phase 2** : `eval/cases.jsonl` (20 cas minimum : langue, fait absent, profil, viewer mentionné, injection, emotes de la chaîne / emote absente / liste vide, bavardage), `scripts/evaluate.py`, puis mesure de référence du modèle de base.
4. **Phase 3** : dataset de départ synthétique.

## Journal des lives

### Live 1 : 4 novembre 2026

- Repo créé, environnement uv + CUDA mis en place, `check_env.py` au vert.
- Exploration complète de Ministral 3 8B dans le notebook 01, chat template sauvegardé.
- Prototype du format de prompt et premiers tests de génération.

### Live 2 : 6 novembre 2026

- Ménage : `CLAUDE.md` déplacé à la racine, ligne `EOF` retirée du `.gitignore`. Mesures clés relevées.
- Avertissement `fix_mistral_regex` analysé (fausse alerte), tokenizer corrigé gardé.
- Mesure d'un prompt réaliste (cellule 16) : `max_seq_length = 4096` confirmé, plafonds en tokens par bloc.
- `docs/prompt_format.md` commencé : principes (langue, emotes, pas de `<silence>`), structure, plafonds ; données TwitchIO 3 identifiées.

## Procédure de fin de live

Quand Dantek annonce la fin du live, mettre ce fichier à jour **avant le dernier commit** :

1. Tableau "Où on en est" : mettre à jour l'état des phases.
2. "Mesures clés" : ajouter les chiffres obtenus pendant le live.
3. "Pièges déjà rencontrés" : ajouter chaque erreur rencontrée, avec sa cause et sa solution, en une ou deux lignes.
4. "Prochaines étapes" : réécrire la liste pour le prochain live.
5. "Journal des lives" : ajouter une entrée datée de trois ou quatre lignes.
6. Rester concis : ce fichier est relu à chaque session. Ne jamais y écrire de secret.
