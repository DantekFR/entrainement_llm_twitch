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

- **Claude ne modifie aucun fichier pendant le live** : il indique les tâches (code à coller, commandes, résultat attendu) et Dantek les exécute. Exceptions : la mise à jour de ce fichier en fin de live, et `docs/ROADMAP.md`, que Claude modifie lui-même.
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
| `prompt_format` v1 | **Document terminé et commité** : `docs/prompt_format.md`. Module de rendu `scripts/prompt_format.py` **en cours** |
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
| Règles système v1 (avec `Pixou`) | 944 caractères, **236 tokens** (+ `[MAINTENANT]` ≈ 290, plafond ~300) |

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

### Décisions du live 3

- **Emojis** : libres, mais environ un quart des réponses du dataset n'en contiennent aucun.
- **Statuts** : `abonné depuis N mois`, **sans palier**. Plusieurs statuts : on garde le plus élevé (streamer > modo > VIP > abonné > follower > viewer). Statut complet aussi dans l'historique.
- **Non-followers** : le bot leur bloque l'IA. L'auteur est donc toujours follower ; un non-follower mentionné n'a pas de profil.
- **Dernier passage** : dernier live où le viewer a écrit, live en cours exclu ; sinon `dernier passage (première visite)`.
- **`[MAINTENANT]`** = heure de l'appel (pas le début du live). Ajout de `Live commencé <jour> <date> à <heure> (il y a <durée>)`, durée calculée par le code de rendu (`fetch_streams()` → `.started_at`, UTC converti en Europe/Paris), et `Titre : <titre>`. Hors live : `Pas de live en cours`.
- **Historique** : heures en `HH:MM` sans date. Le passage de minuit se déduit de l'ordre chronologique + `[MAINTENANT]` ; le dataset doit contenir des exemples qui passent minuit.
- **Catégorie du live** (live 4, remplace l'idée `[JEU EN COURS]`) : bloc `[CATÉGORIE DU LIVE]` juste avant `[MAINTENANT]`. `Catégorie :` (`.game_name` de Twitch) toujours présente pendant un live ; `Genres :` et `Description :` (≤ 150 tokens) seulement si IGDB a une fiche (pas de fiche pour Just Chatting, IRL, Software and Game Development…). Hors live : `- (aucun)`. Plafond ~200. **Pas de date de sortie** (sans intérêt avec l'accès anticipé). Fiche en cache par catégorie, surchargeable à la main. Dataset : jeux réels et inventés, ~20 % non gaming, descriptions ~80 % en anglais.
- **RAG complet** (wiki, guides) : reporté en v2.
- **Dataset 100 % synthétique**. La BDD de messages du bot servira seulement, au déploiement, à initialiser les résumés et dates de dernier passage des viewers.
- **Règles système** : génériques (pas de « Dantek » en dur, le nom du streamer est dans les faits), courtes (~200 tokens), à l'impératif, figées (toute modification = v2).
- **Connaissances** : uniquement les blocs pour la chaîne, le streamer et les viewers ; culture générale autorisée ; pour l'actualité, il dit qu'il n'y a pas accès.

### Décisions du live 4

- **Règles système v1 figées** (7 règles : langue, forme, blocs uniquement, culture générale/actualité, profils pertinents, injection, emotes). Toute modification = v2.
- **Plafond de l'historique** ramené à **1 300** tokens pour absorber `[CATÉGORIE DU LIVE]` et garder le total à ~3 500.
- **Code de rendu du prompt dans ce repo** (`scripts/prompt_format.py`), et non dans le bot : le bot l'importera (tag `prompt-v1`) lors de la refonte de son architecture. ROADMAP mise à jour.
- **Tests** : pytest (groupe `dev`), `tests/test_prompt_format.py` vérifie que `SYSTEM_RULES` est identique au bloc du document. `pyproject.toml` : `[tool.pytest.ini_options]` avec `pythonpath = ["."]`.
- **Dates en français** codées à la main (listes de jours/mois, « 1er »), pas de `strftime`, qui dépend de la locale de la machine.
- **ROADMAP** : Claude la modifie directement, à la demande de Dantek.

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
- **Rythme du live** : donner les étapes une par une dans le chat, en petits morceaux, jamais un gros bloc ni un plan d'ensemble à valider.
- **Markdown imbriqué** : un bloc de code qui en contient un autre s'ouvre avec quatre backticks ; ne coller que l'intérieur.
- **Dates des exemples** : vérifier le jour de la semaine (le 11 novembre 2026 est un mercredi) et la cohérence entre `[MAINTENANT]` et les heures de l'historique.
- **Renommer une balise** : utiliser `Ctrl+H` avec le mode regex **désactivé** (les crochets `[...]` sont une classe de caractères en regex), puis vérifier par une recherche qu'il ne reste aucune ancienne occurrence.
- **Imports d'un module** : ils se placent **sous** la docstring, sinon elle n'est plus la docstring du module.

## Prochaines étapes

1. **Petit correctif** dans `scripts/prompt_format.py` : remonter la docstring du module au-dessus des imports `datetime` / `zoneinfo`.
2. **Continuer le module** `scripts/prompt_format.py`. Déjà écrits : `SYSTEM_RULES`, `EMPTY_BLOCK`, `render_block`, `render_facts`, `render_emotes`, `render_category`. À faire, dans l'ordre :
   - `[MAINTENANT]` : le code est prêt (étape 26 du live 4 : `PARIS_TZ`, `WEEKDAYS`, `MONTHS`, `to_paris`, `format_day` avec « 1er », `format_time` `00h03`, `format_duration` `3 h 33` / `45 min`, `render_now(now, stream_start=None, title="")`), il reste à le coller et à le tester sur l'exemple (19h30 UTC → 20h30 Paris) ;
   - profils (`render_profiles`), historique (`render_history`), message (`[MESSAGE DE <pseudo>]`), puis `build_messages()` qui assemble `system` / `user` / `assistant` ;
   - test : rendre l'exemple complet du document et le comparer au texte du doc ;
   - comptage des tokens et respect des plafonds (troncature de l'historique, retrait des profils mentionnés).
3. **Commiter** : `docs/ROADMAP.md`, `pyproject.toml`, `uv.lock`, `scripts/prompt_format.py`, `tests/` (laissés non commités en fin de live 4).
4. **Phase 2** : `eval/cases.jsonl` (20 cas minimum), `scripts/evaluate.py`, mesure de référence du modèle de base.
5. **Phase 3** : dataset de départ synthétique.

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

### Live 3 : 11 novembre 2026

- `docs/prompt_format.md` : statuts sans palier, sections « Données que le bot doit fournir », « Règles pour le dataset » et « Exemple complet » (system + user).
- Gestion du temps : `[MAINTENANT]` avec début, durée précalculée et titre du live ; passage de minuit.
- Décision : bloc `[JEU EN COURS]` rempli via IGDB (v1), RAG reporté en v2, dataset 100 % synthétique.
- Règles système commencées (identité, langue, forme).

### Live 4 : 13 novembre 2026

- `docs/prompt_format.md` terminé et commité : 7 règles système (236 tokens), exemple complet à jour.
- `[JEU EN COURS]` remplacé par `[CATÉGORIE DU LIVE]` (catégories non gaming, pas de date de sortie) ; historique plafonné à 1 300 tokens.
- ROADMAP : règle de langue corrigée, pistes pour plus tard (RAG v2), code de rendu dans ce repo.
- Module `scripts/prompt_format.py` commencé (blocs faits, emotes, catégorie) ; pytest ajouté, premier test au vert.

## Procédure de fin de live

Quand Dantek annonce la fin du live, mettre ce fichier à jour **avant le dernier commit** :

1. Tableau "Où on en est" : mettre à jour l'état des phases.
2. "Mesures clés" : ajouter les chiffres obtenus pendant le live.
3. "Pièges déjà rencontrés" : ajouter chaque erreur rencontrée, avec sa cause et sa solution, en une ou deux lignes.
4. "Prochaines étapes" : réécrire la liste pour le prochain live.
5. "Journal des lives" : ajouter une entrée datée de trois ou quatre lignes.
6. Rester concis : ce fichier est relu à chaque session. Ne jamais y écrire de secret.
