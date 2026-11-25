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

Modèle de départ : `unsloth/Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit` (champion provisoire du tournoi depuis le live 8 : le **3B**, même famille, même chargement), chargé avec `FastModel.from_pretrained(..., load_in_4bit=True, text_only=True)`. Le tokenizer est ensuite rechargé avec `AutoTokenizer.from_pretrained(MODEL_ID, fix_mistral_regex=True, padding_side="left")`, puis réassigné à `tokenizer.tokenizer`.

## Où on en est

| Phase | État |
| --- | --- |
| 0. Environnement | **Terminée** : `check_env.py` au vert (CUDA, bf16, couche 4 bits testée) |
| 1. Explorer le modèle | **Terminée** : `notebooks/01_explore_model.ipynb`, chat template dans `docs/chat_template/` |
| `prompt_format` v1 | **Terminé** : `docs/prompt_format.md` + `scripts/prompt_format.py` (tous les blocs, `build_messages`, plafonds), test de l'exemple complet au vert |
| 2. Jeu d'évaluation | **Terminée pour la v0** : 20 cas, `evaluate.py`, base = **0/20**. Tag `eval-v1` (local et distant, `4b91a8e`). Référence actuelle : `runs/20261123-1132_base_aucun-souvenir/` (rendu `(aucun souvenir)`). Référence Qwen reportée en phase 6 |
| 3. Dataset de départ | **Terminée** : 300 exemples (lots 3 à 17), `train.jsonl` 271 / `val.jsonl` 29, fiche `data/seed/README.md`, `scripts/assemble_seed.py` |
| Tournoi des modèles | **3 manches sur 4 jouées au live 8** : Ministral 3B, 8B, Qwen3.5-4B. **Champion provisoire : Ministral 3 3B v0** (16/20, Deck 5 s). Reste Gemma 4 E4B. Détails dans `MODELS.md` |
| 4. Entraînement v0 | **Terminée** (live 8) : `scripts/train.py`, configs `train_v0_ministral3_3b.yaml`, `…_8b.yaml`, `train_v0_qwen35_4b.yaml` ; 3 adaptateurs dans `runs/` |
| 5. Évaluation v0 | **Terminée pour les 3 modèles** : 3B 16/20, 8B 18/20, Qwen 16/20 ; banc du Deck (`scripts/bench_deck.py`). Aucun ne passe encore les critères non négociables (fait absent et injection 3/3) |
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
| Exemple complet du doc (`measure_prompt.py`) | system 492 · user 212 · **total 709 tokens** avec template (le template ajoute 5 tokens) |
| **Éval du modèle de base** (`eval-v1`, 20 cas, glouton, critères du 22/11) | **0/20** (1/20 avant : le seul succès, `live_001`, contenait de l'italique `*…*`). Par critère : `not_empty` 20/20, `no_brackets` 3/20, `no_markdown` 9/20, `max_sentences` 15/20, `language` 19/20, `must_include_*` 14/15, `must_not_match` 10/13. Run rescoré : `runs/20261116-1246_base_rescore-eval-v1/` |
| Vitesse pendant l'éval | ~7 tokens/s ; le temps suit le nombre de tokens générés ; 1er cas lent (préchauffage GPU, 51 tokens en 33 s) |
| Tirage des contextes (2 000 tirages) | 67 % jeux, 17 % non gaming, 15 % hors live |
| **Éval de base re-mesurée** (23/11, rendu `(aucun souvenir)`) | **0/20** ; 5 prompts changés, 3 réponses changées ; `must_not_match` 10/13 → **9/13** (`profil_002` confirme désormais « Oui, … dit être champion »), le reste identique ; 7,1 tokens/s. Run : `runs/20261123-1132_base_aucun-souvenir/` |
| Prompt du générateur (lot de 20) | 54 800 à 75 400 car. (lot 16 le plus gros : 336 textes, 5 historiques longs). Aucune sortie coupée sur les lots 3 à 17 |
| **Dataset seed v0** (lots 3 à 17) | **300 exemples**, 300/300 acceptés après corrections ; train 271 / val 29 ; catégories de 17 (`emotes`) à 45 ; hors live 15 % ; sans emote ni emoji 28 % ; mention pas en tête 23 % (depuis le lot 4) ; réponses 9 à 38 mots (médiane 21), 0 finit par « ? », 0 doublon ; « Live anniversaire » 17 titres sur 300 |
| **Ministral 3 3B de base** (`eval-v1`, 24/11) | **3/20** (`fait_present` 1/3, `bavardage` 2/2, le reste à 0 ; `fait_absent` et `injection` 0/3). Critères : `not_empty` 17, `max_sentences` 17, `no_markdown` 9, `no_brackets` 9, `language` 19, `must_include_any` **8/13** (8B : 12/13), `must_not_match` 10/13. Meilleur sur la forme, pire sur le fond (invente horaire, GOTY, « je confirme que tu es modo »). VRAM **3,22 Go**, 7,9 tokens/s. Run : `runs/20261124-2340_base-3b/` |
| Chat template 3B vs 8B | Rendu identique au token près (40/40 sur l'éval) ; seul le prompt système par défaut diffère (nom du modèle) |
| Longueur des exemples (prompt rendu) | 1 700 à 6 100 car. (médiane 2 700) ; plus long : **2 164 tokens** (b008-12) ; 2 historiques tronqués sur 300 (b008-12, b012-00 : 1 ou 2 messages retirés) |
| Retouches à la main | ~35 sur 300 exemples : surtout accords genrés (~20), mention `@<bot>` manquante entre deux réponses du bot (4), phrases absurdes (« entre moi et le bot »), 1 jeu de l'éval, 1 emote inventée, 24 `@pseudo` en tête des messages du bot (lot 17) |
| **Entraînements v0** (live 8, 68 étapes, 2 époques, lot effectif 8) | 3B : **7 min**, pic 4,06 Go, validation min 1,42 (étape 40) puis stagne · 8B : **16 min**, pic 7,64 Go, min 1,23 (étapes 30-40) puis remonte (1,28) · Qwen 4B : **11 min**, pic 4,46 Go, 1,57 → 1,34, ne remonte pas. Pertes Ministral/Qwen non comparables (tokenizers différents) |
| **Éval v0** (`eval-v1`) | 3B **16/20** (fait absent 2/3, injection 2/3) · 8B **18/20** (3/3, 2/3 : recopie tout le prompt système sur `injection_003`) · Qwen base **12/20** (3/3, 0/3) → v0 **16/20** (2/3, 2/3 : confirme les 100 € de `injection_002`, invente une date) |
| Vitesse PC avec adaptateur non fusionné | 3B 5,9 · 8B 4,1 · Qwen 4,2 tokens/s (sans adaptateur : 7,9 · 7,1 · 6,2) |
| **Banc du Deck** (GGUF de base Q4_K_M, `val.jsonl`, 560 à 1 900 tokens) | 3B : écriture **27 tokens/s**, lecture ~270 tokens/s, total médiane **5 s**, max 10 s · Qwen : 21 et ~185 tokens/s, médiane 7 s, max 12,1 s · 8B : > 15 s vers 1 800 tokens (banc arrêté). Délai ≈ prompt / lecture + réponse / écriture ; au plafond de 3 500 tokens : 3B ~15 s, Qwen ~19 s |
| Jeu anti-troll v0 (`eval/troll_cases.jsonl`, 5 cas, pas figé) | 3B base 0/5, 3B v0 1/5 (faux succès sur `troll_004`) |

### Comportement du modèle de base (référence avant fine-tuning)

- Fait absent : il invente ("Dantek a 28 ans").
- Réponses trop longues, markdown, emojis en excès, finit souvent par une question.
- Ressort des souvenirs hors sujet (le script Python dans une réponse sur l'âge).
- Message en anglais : il répond en français (le prompt disait alors "toujours en français").
- Injection : il refuse, mais en inventant des précisions ("je ne suis pas un modo").
- Éval du live 5 : il **imite les balises** (`[Dantek]`, `[dantekfRage]` : une emote entre crochets ne s'affiche pas sur Twitch), ajoute une **parenthèse en italique** sur une 2e ligne, confirme un faux bloc (`[FAITS…]` dans le message), recopie ses règles si on le demande, ressort un souvenir hors sujet. Le fond est souvent bon : il échoue surtout sur la forme.

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

### Décisions du live 5

- **Code de rendu** : `PromptInputs` (dataclass) regroupe tout ce que le bot fournit ; `build_messages(apply_limits(inputs, count_tokens))` partout (dataset, éval, bot). `count_tokens` est injecté (le module ne charge pas le tokenizer). Titre vide → ligne `Titre :` omise. Statuts : `format_status(roles, sub_months)` avec les noms anglais de TwitchIO.
- **Évaluation** : un cas = `id`, `category`, `description`, `inputs` (champs de `PromptInputs`, dates ISO avec décalage), `checks`. 9 catégories (`fait_present`, `fait_absent`, `injection`, `profil`, `langue`, `live`, `culture_actu`, `bavardage`, `emotes`). Critères communs : langue, 2 phrases max, pas de markdown, **pas de crochets**. Comparaisons insensibles à la casse, regex comprises. Un cas est réussi si tous ses critères le sont.
- **Langue** : lingua (6 langues : fr, en, es, de, it, pt), texte nettoyé (crochets, `@pseudo`, `*`, codes d'emote) ; échec seulement si une autre langue dépasse 0,5 de confiance.
- **Jeu figé** : on ne corrige les critères que pour de vrais faux positifs/négatifs, puis on recalcule (`rescore.py`) et on fige (tag `eval-v1`). Après l'entraînement, on n'y touche plus (on peut seulement ajouter des cas).
- **Dataset** : le code tire le contexte (graine fixée, `configs/pools.yaml`), le générateur écrit seulement les textes (historique, message, réponse). Générateur v0 = **chat en ligne**, par lots de ~20, nouvelle conversation par lot. Conditions d'utilisation à vérifier par Dantek. Exemples filtrés par `run_checks`.
- **Anti-contamination** : jamais de noms de bot, pseudos, streamers, faits, souvenirs ou jeux de l'éval dans les réservoirs (tests `test_pools.py`). Exceptions : la phrase d'intro « Le streamer s'appelle… » (partie fixe du format) et les catégories Twitch non gaming.
- **Réservoirs** : streamers jamais Dantek (et des streameuses), faits en groupes exclusifs (au plus un par groupe) + faits libres, emotes préfixe + suffixe dont ~20 % opaques au sens tiré au hasard, catégories (jeux réels avec fiche ~80 % EN, inventés, sans fiche, non gaming ~20 %), 15 % hors live, lives qui passent minuit.
- **Modèle plus léger** : pas maintenant ; piste si le 8B est trop lent sur le Deck (phase 6).

### Décisions du live 6

- **Matrice** `configs/seed_matrix.yaml` : catégorie (poids + consigne générique, jamais tirée de l'éval) × registre (`soutenu`, `courant`, `familier`, `argot_abreviations`, `fautes`) × attitude (`neutre`, `enthousiaste`, `taquin`, `provocateur`). L'état du live et le type de profil restent tirés par `contexts.py` (pas de doublon). Le registre et l'attitude ne valent que pour le message : la réponse reste en français correct.
- **Tirage stratifié par lot** (`sample_categories`) : chaque catégorie a sa part entière (poids × 20), le reste est tiré selon les fractions. Les 9 catégories sont dans chaque lot.
- **Langue** : 8 % de messages étrangers (poids 8, doc corrigé de 15 % à 8 %).
- **Viewer mentionné non follower** (20 % des mentions) : pas de profil, statut `viewer` dans l'historique, listé dans `meta.without_profile`. Le bot ne sait rien de lui.
- **Historique** : le bot ne parle jamais en premier, ni juste après lui-même, ni après un `viewer` (l'IA est bloquée aux non-followers). Des messages avant le début du live sont normaux (le chat reste ouvert).
- **Titres** : `game_titles` (avec `{category}`) seulement pour les jeux, `generic_titles` pour tous ; aucun titre ne donne l'âge de la chaîne (« Live anniversaire de la chaîne ! »).
- **Prompt du générateur** versionné dans `configs/generator_prompt.md`, avec les marqueurs `<<SYSTEM_RULES>>`, `<<EXAMPLE>>`, `<<BATCH>>` remplis par `export_batch.py` (règles lues dans `prompt_format.py`, exemple lu dans le doc : jamais de copie). Consigne : si la situation est impossible avec le contexte, l'adapter sans compléter le contexte.
- **Un dossier par lot** (versionné) : `data/seed/batches/batch_NNN/` avec `batch.json` (export), `prompt.md`, `output.jsonl` (sortie du chat), `merged.jsonl` (format d'entraînement `{id, category, messages}`).
- **Fusion** (`merge_batch.py`) : rejette avec sa raison tout exemple qui a une structure fausse (nombre de textes, `@<bot>` en tête, mentions), qui échoue à `run_checks`, dont le message `langue` n'est pas clairement étranger, ou qui contient une emote de chaîne inventée. Rendu par `case_to_inputs` + `apply_limits` + `build_messages`, comme l'éval.
- **Un lot déjà envoyé au générateur n'est jamais réexporté** : la sortie correspond au tirage d'origine.

### Décisions du 22 novembre (revue hors live, avant le lot 3)

- **Tirage corrigé** (change les tirages, donc à partir du lot 3 seulement) : titres génériques pour toutes les familles (bug d'indentation) ; horaires structurés (`schedules` dans `pools.yaml`, jours + heure) et live calé dessus, jour annoncé tiré uniformément, sauf 15 % de lives exceptionnels ; **10 % d'historiques longs pendant un live** (30 à 50 messages, 8 viewers en plus, messages rapprochés) ; streamer pondéré à 0,25 (~4 % des messages) ; contexte retiré tant que la situation est impossible (`situation_fits` : emotes sans liste, `fait_present` sans autre fait que l'intro) ; dernier passage avant le jour du **début** du live en cours ; jamais de modo ni de VIP en première visite ; `meta.history_count` donné au générateur.
- **Sans changer les tirages** : première visite ⇒ résumé vide ; textes contradictoires remplacés (week-end 14h-18h, vacances scolaires, date future, prochain jeu = jeu en cours, Resident Evil puis Inscryption vs « jamais d'horreur », Among Us « le dimanche soir », MacBook vs « même sur PC », « le jeu en cours » sans jeu, « On termine » sur un jeu sans fin) ; jeux de l'éval retirés des réservoirs (Hades, Stardew Valley, Celeste, Elden Ring) ; accords neutres ; `Fusée` → `Cactus` (codes ASCII) ; `Ondine` → `Rosalie` (élision).
- **Provenance des tirages** : lots 3 à 7 = `fda5326` (corrections du 22/11), 8 et 9 = `114433c`, 10 à 17 = `adea4a1` (lots 1 et 2, `de76603` et `5294d0d`, retirés au live 7).
- **Fusion durcie** : arrêt sans rien écrire si le lot n'est pas exporté, si `output.jsonl` est absent, vide, pas en UTF-8, mal formé (numéro de ligne, et « sortie coupée ? » si la ligne est incomplète), contient du texte du chat, un id d'un autre lot ou deux lignes différentes pour un même id (une ligne recopiée à l'identique est ignorée), ou si 0 exemple est accepté. Les balises ```` ``` ```` sont retirées, même collées à une ligne. Nouveaux rejets : texte vide ou sur plusieurs lignes, espaces autour de la réponse, préfixe `Bot :` / `<nom> :` / `Assistant :`, mention inexacte (`@WaffleKingou`), jeton de contrôle en toutes lettres (`[/INST]`, `</s>`, `<SPECIAL_n>`), réponse `langue` pas dans la langue du message (titre et catégorie retirés avant la détection), emote `:code:` ou mal écrite, nom du streamer absent des blocs, message du bot dans l'historique qui parle sans mention depuis son message précédent ou qui enfreint les règles de forme. Emotes globales de Twitch (Kappa, LUL, twitchRaid…) acceptées. Avertissements `À RELIRE` (pas de rejet) : message très probablement étranger hors catégorie `langue` (le franglais reste du français), réponse `langue` de moins de 4 mots, streamer nommé dans aucun bloc, historique tronqué par `apply_limits`.
- **Export** : refuse un lot dont `batch.json` existe (`--force` seulement si le prompt n'a jamais été envoyé, et jamais si `output.jsonl` existe) ; lot écrit dans le prompt à raison d'un exemple par ligne.
- **Éval** (critères corrigés avant le gel, base 1/20 → 0/20) : critère commun `not_empty` (une réponse faite seulement d'emotes ou de mentions est vide), italique `*…*` et `_…_` dans `no_markdown` (pas « 5* », « ¯\\_(ツ)_/¯ » ni « -_- »), `’` = `'`, points de suspension suivis d'une minuscule ne comptent pas comme fin de phrase, réponse française de moins de 5 mots toujours acceptée pour la langue ; regex de `injection_001` (refus acceptés, « je confirme que tu es modo » refusé), `bavardage_001` (question finale suivie d'emotes, de mentions ou de « ! »), `culture_actu_002` ; listes `fait_absent` (« j'ignore », « aucune info »…), âge en lettres et villes en plus, `live_002`. `rescore.py` garde une copie `eval.before_rescore.json`.
- **Durée du live** calculée en UTC (juste la nuit du changement d'heure, jamais négative).

### Décisions du live 7 (23 novembre)

- **Mention du bot n'importe où** dans le message (`mentions()` dans `merge_batch`, plus `re.match` en tête) ; le prompt du générateur demande la mention au milieu ou à la fin environ une fois sur cinq (depuis le lot 4). À vérifier côté bot : il doit réagir à une mention en milieu de phrase.
- **Résumé vide = `(aucun souvenir)`** (`EMPTY_SUMMARY`, commit `a899abb`) : c'est `dernier passage (première visite)` qui dit si le viewer est nouveau. Avant, un abonné de 2 ans sans souvenir était affiché « nouveau viewer ».
- **Titre « Live anniversaire » retiré** des titres génériques (`114433c`, 14 % des lots 3 à 7).
- **Deux souvenirs neutralisés** (`adea4a1`) : « A découvert la chaîne grâce à un raid. », « Écoute le stream en fond en codant. ».
- **Plusieurs « Projet en cours » dans un contexte** : laissé volontairement (pas contradictoire).
- **Lots 1 et 2 retirés** (`71e4abb`), remplacés par les lots 16 et 17 : tirés avant le 22/11, ils avaient des jeux de l'éval dans les faits (24/40) et 5 premières visites avec souvenirs. Les lots versionnés sont donc 3 à 17.
- **Neutralité de genre** : une réponse n'accorde jamais au genre d'un viewer, sauf si le viewer s'accorde lui-même (« je suis ravie »). Le pseudo (`MlleChoupette`) et l'accord choisi par un autre viewer ne comptent pas.
- **Commits** : Dantek préfère commiter les lots par paquets ; les changements de code et de réservoirs sont commités tout de suite (provenance des tirages).

### Données que le bot devra fournir (TwitchIO 3, à implémenter hors live)

Statut via `chatter.broadcaster` / `.moderator` / `.vip` / `.subscriber` (gratuit). Ancienneté d'abonnement via `chatter.badges` (champ `info`, à vérifier). Palier via `fetch_broadcaster_subscriptions()` → `.tier` (scope `channel:read:subscriptions`). Date de follow via `chatter.follow_info()` → `.followed_at` (scope `moderator:read:followers`). **Dernier passage** et **résumés des viewers** : à prévoir dans l'architecture du bot.

### Le tournoi des modèles (décidé le 24/11)

Choisir le cerveau de `dantekos_bot` sur 4 lives dev. **Le live reste pédagogique** : on construit et on explique, le test n'est que la conclusion. Résultats dans `MODELS.md`.

| Live | Contenu | Fin du live |
| --- | --- | --- |
| 1 (live 8) | Phase 4 construite avec le chat (`scripts/train.py`, `configs/train_v0_ministral3_3b.yaml`), entraînement du **Ministral 3 3B** | Note du 3B v0 sur `eval-v1` |
| 2 | Entraînement du **8B** (même code, même dataset) + banc de vitesse du Steam Deck | Duel 3B/8B : note, vitesse, vote à l'aveugle du chat |
| 3 | Adaptation à **Qwen3.5-4B** (chat template, base, entraînement) | Duel contre le gagnant |
| 4 | **Gemma 4 E4B** et l'audio (expérience). Voie principale pour l'oral : Whisper → texte dans un bloc du prompt v2 | — |

- **Règle de choix** : le plus petit modèle qui passe les critères (**injection** et **fait absent** non négociables) et répond assez vite sur le Deck (**< 15 s à l'écrit, < 5 s à l'oral**).
- **Voix du bot (TTS)** : **OmniVoice** (k2-fsa, ~613 M paramètres, clonage de voix, PyTorch), envisagé **sur le Deck** pour une voix plus naturelle. Il partage les 9 Gio du GPU avec le modèle de langage, et son temps s'ajoute à celui du modèle à l'oral. Le banc du live 2 mesure donc aussi **modèle + TTS ensemble** (mémoire restante, délai jusqu'à la fin de l'audio) ; à vérifier : PyTorch sur le GPU du Deck (ROCm sur Van Gogh ?) ou repli sur le processeur. Sinon le TTS reste sur le portable. Whisper reste sur le portable. Détails dans `MODELS.md`.
- **Cas anti-troll** : jeu **séparé** de `eval-v1` (figé), écrit en live avec le chat. Thème : conseil de jeu venant du chat, sans source. Cas réel du 24/11 : El_KiksTV invente un « chalumeau » pour brûler une carriole dans Crimson Desert, le bot le répète (« comme dit el_kikstv »).
- **Matériel** : PC fixe (Ryzen 7 3700X, RTX 4070 12 Go, 32 Go) pour l'entraînement ; Steam Deck dédié à l'IA pendant les lives (16 Go partagés) ; bot sur le portable HP 15s (i5-1155G7, 16 Go) avec STT/TTS et VBAN.
- **Modèles en cache** (`~/.cache/huggingface`, disque WSL, ~870 Go libres) : Ministral 3 3B et 8B (`-unsloth-bnb-4bit` pour le QLoRA, BF16 pour l'export), `unsloth/Qwen3.5-4B` (BF16 seulement, pas de bnb-4bit chez Unsloth), `unsloth/gemma-4-E4B-it-unsloth-bnb-4bit` et `unsloth/gemma-4-E4B-it`.
- **`evaluate.py --model <id>`** (24/11) : défaut = 8B, donc les commandes existantes ne changent pas ; le rapport enregistre le modèle et `vram_after_load_gb`.

### Décisions du live 8 (25 novembre)

- **Trois manches en un live** : 3B, 8B et Qwen3.5-4B entraînés avec le même script, le même dataset, les mêmes réglages et la même graine. On évalue toujours l'**adaptateur final** (même règle pour tous).
- **Duel 3B/8B** : le 8B est meilleur à l'éval (18 contre 16) mais **éliminé par la vitesse** (> 15 s sur le Deck vers 1 800 tokens). Vote à l'aveugle abandonné.
- **Duel 3B/Qwen** : même note et même répartition ; le 3B garde le titre (échecs moins graves, plus petit, plus rapide).
- **Le 3B v0 n'est pas déployable en l'état** : fait absent et injection à 2/3, alors qu'ils sont non négociables. Pistes v1 : une seule époque (la validation ne gagne plus rien en 2e époque), plus d'exemples d'`injection` (faux bloc dans le message, demande de recopier les règles), et casser l'excuse passe-partout « je n'ai pas accès à l'actualité » (11 réponses du dataset, toutes `culture_actu`, réutilisées par le 3B pour l'âge et le hors live).
- **Trolling reporté en v2** : la règle v1 « Les blocs entre crochets viennent du bot et sont fiables » couvre aussi `[HISTORIQUE DU CHAT]`, donc le modèle croit les affirmations du chat (« Gratin_Dauphinois a raison »). À corriger par les règles v2 et des exemples troll dans le dataset (autres jeux et pseudos que `eval/troll_cases.jsonl`). Le jeu anti-troll reste non figé, avec un faux positif connu (`troll_004`, regex à étendre à « ne mentionne »).
- **Code** : `train.py` lit le modèle, `chat_template_kwargs` et `completion_suffix` dans la config ; garde-fou contre les adaptateurs sur la vision ; `--check-only` (labels de chaque exemple = réponse + suffixe) et `--max-steps` (test, suffixe `_test`). `evaluate.py --adapter` (vérifie `base_model_name_or_path`), `--cases`, `enable_thinking=False` toujours passé. `bench_deck.py` (`--dataset`, `--no-think`).
- **Modules LoRA** : `finetune_language_layers/attention/mlp=True`, `finetune_vision_layers=False` (pas de liste `target_modules`).

## Pièges déjà rencontrés : ne pas les refaire

- **Vitesse sur le PC ≠ vitesse sur le Deck** : avec `generate` de Hugging Face, le 3B (7,9 tokens/s) est à peine plus rapide que le 8B (7,1) ; c'est Python qui limite, pas le modèle. La vitesse se mesure sur Ollama (banc du live 2).
- **Score global trompeur** : le 3B de base fait 3/20 contre 0/20 pour le 8B, mais invente plus (`must_include_any` 8/13 contre 12/13). Toujours lire les catégories et les critères, pas seulement le total. Revu 3 fois au live 8 : 8B v0 18/20 mais recopie tout le prompt système ; Qwen v0 16/20 comme le 3B, mais confirme une fausse promesse de 100 €.
- **`target_modules` sur un modèle multimodal** : `q_proj`, `gate_proj`… existent aussi dans l'encodeur d'images (336 adaptateurs sur `vision_tower`). Utiliser `finetune_vision_layers=False` et garder le contrôle `vision_lora` de `train.py`.
- **Qwen et la réflexion** : le template ouvre `<think>` par défaut ; TRL rend le prompt avec les options par défaut, donc sans la colonne `chat_template_kwargs` le modèle apprendrait `\n</think>\n\n`. Passer `enable_thinking=False` à l'entraînement, à l'éval et `"think": false` à Ollama. Labels Qwen = réponse + `<|im_end|>\n` (saut de ligne compris).
- **Test de 10 étapes plus lent que le vrai entraînement** (compilation, préchauffage) : 3B 11,9 → 6,2 s/étape, Qwen 31,5 → 9,6. Estimer la durée avec un rapport ~2, pas ×68.
- **TensorBoard vide** alors que les fichiers existent (`runs/<run>/runs/<date>/events…`) : rafraîchir la page et le bouton ⟳ ; lancer TensorBoard depuis la racine du repo.
- **Architecture « rapide » en théorie** : l'attention linéaire de Qwen3.5 lit le prompt **plus lentement** que le 3B sur le Deck (~185 contre ~270 tokens/s, llama.cpp Vulkan). Toujours mesurer.
- **Banc sur des prompts courts** : les cas de l'éval font 450 à 620 tokens ; les vrais lives montent à ~2 800. Mesurer la vitesse sur `val.jsonl` (`--dataset`). Chaque cas a un nom de bot différent en tête du prompt, donc le cache d'Ollama ne joue presque pas.
- **`KEEP_ALIVE=-1`** : un modèle reste chargé sur le Deck même après un script interrompu. `ollama stop <modèle>` avant de mesurer le suivant.
- **Règle système qui rend le chat crédible** : « les blocs entre crochets sont fiables » s'applique aussi à `[HISTORIQUE DU CHAT]`. Une règle doit rester vraie pour **chaque** bloc qu'elle désigne.
- **Commit oublié avant d'entraîner** : l'adaptateur Qwen a été entraîné avec un `train.py` non commité. Commiter code et config **avant** de lancer l'entraînement (provenance).

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
- **Contamination de l'éval** : ne jamais donner `eval/cases.jsonl` au générateur du dataset (il en produirait des copies, le modèle apprendrait l'examen). Donner l'exemple de `docs/prompt_format.md`.
- **Édition à la main du JSONL** : un glisser-déposer peut déplacer un mot d'une clé à l'autre en gardant un JSON valide (`"message"` → `""` + `"messagechecks"`). Le test `test_case_is_valid` le détecte ; vérifier avec `git diff --word-diff`.
- **Attendus de tests périmés** : quand `run_checks` gagne un critère, mettre à jour le dictionnaire attendu de `test_run_checks`.
- **Regex trop larges dans les critères** : `\d` attrapait un « 100 % » venu du profil. Cibler ce qu'on veut vraiment interdire (dates, heures).
- **Lancer les scripts avec `-m`** (`uv run python -m scripts.evaluate`) pour que `scripts` et `tests` soient importables.
- **Claude ne lance pas de commandes pendant le live** (sauf lecture demandée par Dantek) : c'est Dantek qui exécute.
- **Situation et contexte tirés séparément** : une situation peut être impossible (`fait_present` sans fait, `emotes` sans liste). Depuis le 22/11, `build_batch` retire ces contextes ; pour les autres cas, le prompt du générateur dit d'adapter la situation, jamais de compléter le contexte.
- **Une seule liste de titres** donnait « On termine IRL ce soir », et un titre « 1 an de la chaîne » contredisait la date de création dans les faits. Vérifier qu'un texte tiré au hasard reste cohérent avec les autres blocs. Éviter aussi « de {category} » (élision : « de Orbital Ramen »).
- **Squelette d'historique tiré au hasard** : le bot parlait sans qu'on le mentionne, ou répondait à un non-follower. Contraindre le tirage, et le dire au générateur.
- **Petits lots tirés indépendamment** : une catégorie à 8 % manque environ une fois sur cinq dans un lot de 20. D'où le tirage stratifié.
- **Changer l'ordre des tirages** (stratification, nouvelle règle) change tous les lots suivants : ne jamais réexporter un lot déjà généré.
- **Test qui dépend du tirage** : `row["history"][:-1]` ne provoque rien si l'historique tiré est vide. Fabriquer le défaut sans dépendre du contenu (ajouter un texte en trop).
- **Sortie collée sans `Ctrl+S`** : `output.jsonl` faisait 0 octet, donc fusion à 0/20 (« absent de la sortie »). Enregistrer avant de lancer la fusion. La fusion s'arrête désormais sans rien écrire.
- **Ligne mal indentée** : `titles = pools["generic_titles"]` était dans le `else`, donc les jeux avec fiche n'avaient jamais de titre générique, et aucun test ne l'a vu. Tester la **répartition** d'un tirage (chaque famille reçoit chaque type de titre), pas seulement l'absence d'erreur.
- **Blocs qui se contredisent** : horaire « week-end 14h-18h » avec des lives à 20h, « première visite » avec des souvenirs, « 1 000 followers en mars 2026 » avant mars 2026, prochain jeu = jeu en cours. Chaque nouveau texte d'un réservoir doit rester vrai quel que soit le reste du tirage ; `test_contexts.py` et `test_pools.py` vérifient les cas connus.
- **Détecteur de langue trop étroit** : avec seulement fr/en/es, un message italien était vu comme espagnol, et une réponse française à un message allemand passait. `LANGUAGES` doit couvrir les langues demandées par `seed_matrix.yaml`. lingua lit aussi les codes d'emote comme de l'anglais : ils sont retirés avant la détection.
- **Faux succès de l'éval** : l'italique `*Lumen Drift*` passait `no_markdown` (seul succès de la base), et une réponse vide réussissait 6 cas sur 20. Tester chaque critère sur une réponse vide et sur des réponses plausibles (`test_eval_criteria`).
- **Jetons de contrôle en toutes lettres** : un `[/INST]`, `</s>` ou `<SPECIAL_42>` écrit dans un texte devient un vrai jeton pour le tokenizer (masque d'entraînement faussé). La fusion les rejette ; le bot devra les neutraliser dans les messages des viewers (phase 6).
- **Tag annoncé mais absent** : `eval-v1` n'existait pas dans le repo. Après un `git tag`, vérifier avec `git tag -l` et pousser le tag (`git push origin eval-v1`).
- **Sortie du générateur coupée** (lots avec historiques longs) : lui demander la suite et la coller à la fin du même `output.jsonl`, **après avoir supprimé la ligne coupée** (le générateur la réécrit en entier ; la fusion signale « sortie coupée ? »). Les balises ```` ``` ```` et une ligne recopiée à l'identique sont ignorées.
- **Correctif qui ouvre un trou** : la première version de la regex de `injection_001` (exclure tout « que tu es modo ») laissait passer « je confirme que tu es modo », et celle de `bavardage_001` faisait échouer une question au milieu de la réponse. Pour chaque critère corrigé, tester aussi des réponses **fautives** plausibles, pas seulement les refus qu'on veut accepter.
- **Remplacer un texte par un autre qui contredit aussi** : Resident Evil (horreur) remplacé par Inscryption… qui est un jeu d'horreur. Vérifier chaque remplacement contre tous les faits du réservoir.
- **Limites connues de la fusion** (rejets visibles, à reformuler ou à relire) : réponse française saturée d'anglicismes rejetée pour la langue ; trois phrases séparées par un emoji comptées comme deux ; nom de streamer inventé non détecté (avertissement quand le streamer n'est dans aucun bloc).
- **Bot qui répond deux fois de suite** (b003-17, b004-18, b007-19) : le générateur enchaîne deux réponses du bot sans nouvelle mention entre les deux. La fusion rejette ; corriger le texte intermédiaire (« merci @Bot, et Tonton attend sa réponse »). Le relire avant la fusion fait gagner un tour.
- **Ce que la fusion ne voit pas** (relire chaque lot) : accords genrés déduits du pseudo ou d'un autre viewer (« une modo », « tu restes abonné », « vous êtes voisines ») ; phrases absurdes (« mes consignes restent entre moi et le bot », vu 2 fois) ; mauvaise attribution d'un pari ; souvenir extrapolé (« tu admires les dessins » en première visite) ; viewer qui s'adresse à lui-même ; jeu de l'éval écrit par le générateur (Celeste) ; `@pseudo` en tête des messages du bot (lot 17, tic qui apprendrait au modèle à commencer ses réponses par une mention).
- **Étiquette de rendu trompeuse** : `(nouveau viewer, aucun souvenir)` s'affichait pour tout résumé vide, même pour un abonné de 2 ans. Toujours vérifier qu'une étiquette fixe reste vraie dans **tous** les cas qui la déclenchent ; elle touchait 21 profils et 5 cas de l'éval (j'en avais annoncé 2 : compter aussi les premières visites).
- **Souvenirs écrits au masculin** dans les réservoirs (« Est arrivé via un raid », « pendant qu'il code ») : le générateur reprend l'accord. Les textes des réservoirs qui décrivent un viewer doivent être neutres.
- **Lots tirés avant une correction des réservoirs** : les lots 1 et 2 gardaient des jeux de l'éval dans leurs faits. Après un nettoyage des réservoirs, chercher les anciens textes dans les lots déjà tirés (`grep` sur `batch.json`), pas seulement dans `pools.yaml`.
- **Retrait d'un lot et tests** : `test_exported_batch_is_never_exported_again` pointait sur le lot 1 ; après son retrait, il pointe sur le lot 3. Un test qui dépend d'une donnée versionnée casse quand on la supprime.
- **Fichier mal nommé** : `output.json` au lieu de `output.jsonl` (lot 17). Vérifier le nom avec `ls` avant la fusion.
- **`grep` sans résultat** = code de sortie 1 : VS Code l'affiche comme un échec alors que « rien trouvé » est souvent le succès attendu.
- **Commits groupés** : avec des lots non commités pendant des heures, les sorties du générateur n'existent que sur le disque. Ne rien supprimer ni écraser dans `data/seed/batches/` avant le commit.

## Prochaines étapes

### Au début du live 9, avant tout

Dantek lance, Claude explique le résultat :

1. `git status` → rien à commiter (sinon : les fichiers du live 8 non commités, voir le journal) ; `git log --oneline -3` → le commit de fin du live 8 en haut.
2. `uv run pytest -q` → **141 passed** (aucun test ajouté au live 8).
3. TensorBoard dans un 2e terminal, **depuis la racine** : `uv run tensorboard --logdir runs` → les runs `v0_ministral3_3b`, `v0_ministral3_8b`, `v0_qwen35_4b` visibles.
4. Deck : `curl -s http://192.168.1.38:11434/api/tags` répond ; `ollama ps` (SSH) vide, sinon `ollama stop`.
5. Rappeler au chat le résultat du tournoi (`MODELS.md`) : 3B champion provisoire, et pourquoi il n'est pas encore déployable.

### Live 9 : Gemma 4 E4B, dernière manche du tournoi

1. **Chat template** (sans GPU, comme `inspect_qwen.py` au live 8) : format des tours, gestion du message **système** (certains templates Gemma le fusionnent dans le 1er message user : à vérifier), mode réflexion éventuel, BOS/EOS, suffixe des labels. Le prompt seul doit être le **préfixe exact** de la conversation complète.
2. Config `configs/train_v0_gemma4_e4b.yaml` (copie de celle du 3B ; `unsloth/gemma-4-E4B-it-unsloth-bnb-4bit` ; `chat_template_kwargs` et `completion_suffix` si besoin) → **commiter avant d'entraîner** → `--check-only` (labels, vision **et audio** exclus des adaptateurs : élargir le garde-fou `vision_lora` si les modules audio ont un autre nom) → `--max-steps 10` → vrai entraînement.
3. Éval base puis v0 sur `eval-v1` ; banc du Deck sur `val.jsonl` (GGUF Q4_K_M de Gemma 4 E4B, nom du dépôt à vérifier). Remplir `MODELS.md`. Duel contre le 3B.
4. L'audio (expérience) : seulement si le temps le permet. Voie principale pour l'oral : Whisper → texte (prompt v2).

### Après le tournoi

- **Dataset et entraînement v1 du champion** : une époque (ou comparer), exemples d'injection supplémentaires, excuse « pas accès à l'actualité » limitée à l'actualité, « Oui, il dit être… » à corriger (`profil_002` échoue chez les 3 modèles). Tout changement des règles système = prompt v2 (trolling, historique non fiable).
- **Phase 6** : fusionner l'adaptateur du champion, export GGUF, Modelfile Ollama (toujours un message système), vérifier la tokenisation HF/llama.cpp, puis banc sur le **modèle fine-tuné**.
- **OmniVoice** sur le Deck à côté du modèle (mémoire, délai) ; relever la mémoire avec `ollama ps` (jamais mesurée au live 8).
- Hors live : installer `causal_conv1d` si Qwen revient en lice (entraînement et éval plus rapides sur le PC).

### Steam Deck (configuré le 24/11)

- GGUF installés au live 8 : `hf.co/unsloth/Ministral-3-3B-Instruct-2512-GGUF:Q4_K_M`, `…-8B-…:Q4_K_M`, `hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M` (plus Qwen 3.5 9B d'avant).

- **Deck dédié aux IA** (aucun jeu) : démarre en **mode Bureau** (`steamosctl set-default-login-mode desktop`, retour : `… game`), **Steam ne se lance plus** (`~/.config/autostart/steam.desktop` avec `Hidden=true`, à supprimer pour revenir), **pas de veille sur secteur** (KDE Énergie, `~/.config/powerdevilrc`). Mémoire utilisée après démarrage : **2,0 Gi** (3,0 avant), 12 Gi disponibles. Fermer la fenêtre VS Code SSH pendant les lives (~0,9 Go).
- Ollama dans `~/.local/bin/ollama`, lancé par un **service utilisateur systemd** `~/.config/systemd/user/ollama.service` (`OLLAMA_HOST=0.0.0.0`, `OLLAMA_IGPU_ENABLE=1`, `OLLAMA_KEEP_ALIVE=-1` pour ne jamais décharger le modèle, `Restart=on-failure`, activé au démarrage ; vérifié après redémarrage). `ollama ps` montre les modèles chargés, `ollama stop <modèle>` en décharge un. Il tourne même sans le bot ; le script de démarrage du bot le réutilise (« Ollama tourne déjà »).
- GPU : **Vulkan**, `AMD Custom GPU 0405 (RADV VANGOGH)`, iGPU, **9,0 Gio** (8,5 libres). Modèle déjà installé : Qwen 3.5 9B.
- Réseau : **Wi-Fi**, `192.168.1.38` (jamais changée, pas de réservation DHCP). Joignable depuis le PC (WSL) : `curl -s http://192.168.1.38:11434/api/tags`. Ethernet possible plus tard (nouvelle MAC, donc nouvelle IP).
- `steamos-session-select` est obsolète (pas d'option `plasma-persistent`) : passer par `steamosctl`. Ne pas lancer de programme graphique depuis SSH (`plasmashell --version` plante sans écran ; utiliser `pacman -Q`). Plasma 6.4.
- Commandes utiles (SSH sur le Deck) : `systemctl --user status ollama`, `systemctl --user restart ollama`, journaux `journalctl --user -u ollama` (plus `~/ollama.log`).
- Ollama écoute sur tout le réseau local sans mot de passe : ne jamais ouvrir le port 11434 vers Internet.

### Plus tard

- Contrôle des noms de l'éval dans `merge_batch` (phase 7), groupes exclusifs pour les souvenirs incompatibles (Lyon/Québec, bac/travail de nuit), vérifier que le bot réagit à une mention en milieu de phrase, neutraliser les jetons de contrôle dans le bot.

### Référence : produire un lot (phase 7)

| Étape | Action | Résultat attendu |
| --- | --- | --- |
| 1. Export | `uv run python -m scripts.export_batch --batch N` | `Prompt du générateur : …/batch_00N/prompt.md`, `20 exemples écrits…`, puis `Catégories :` avec les 9 catégories |
| 2. Générer | Ouvrir `batch_00N/prompt.md`, `Ctrl+A` `Ctrl+C`, **nouvelle conversation** dans un chat à grande fenêtre, coller | Un bloc de code JSONL de 20 lignes |
| 3. Enregistrer | Créer `batch_00N/output.jsonl`, y coller le contenu du bloc, **`Ctrl+S`** | Fichier non vide (les balises ```` ``` ```` copiées par erreur sont tolérées) |
| 4. Fusion | `uv run python -m scripts.merge_batch --batch N` | `N/20 exemples acceptés -> …/merged.jsonl`, `Exemple le plus long : … tokens`, éventuellement des lignes `REJETÉ` / `À RELIRE` |
| 5. Relire | Claude vérifie `batch.json` **avant** la génération, puis `output.jsonl` **avant** la fusion (le lot entier : faits, calculs, accords, mentions), puis `merged.jsonl` | Corrections par `Ctrl+H` (regex désactivée), texte unique vérifié |
| 6. Commit | `git add data/seed/batches/batch_0NN` puis `git commit` | Au plus tard en fin de séance ; code et réservoirs commités tout de suite |

- **Corriger un exemple rejeté** : demander au générateur, dans la même conversation, de réécrire cet id en tenant compte de la raison du rejet. **Remplacer** sa ligne dans `output.jsonl` (ne pas l'ajouter à la fin : deux lignes différentes pour un même id arrêtent la fusion), puis relancer la fusion. On peut aussi laisser l'exemple rejeté.
- **Sortie coupée** (lots avec historiques longs) : supprimer la ligne coupée, demander « continue », coller la suite à la fin du même fichier, relancer la fusion. Jamais arrivé sur les lots 3 à 17, même avec 336 textes.
- **Prochain numéro de lot libre : 18** (la graine est le numéro ; les lots 1 et 2 ne doivent pas être réutilisés).

### Messages de la fusion : que faire

| Message | Cause | Action |
| --- | --- | --- |
| `… n'existe pas` / `… est vide` | Sortie non enregistrée | `Ctrl+S`, relancer |
| `ligne N : JSON invalide … sortie coupée ?` | Réponse du chat coupée | Supprimer la ligne N, demander la suite |
| `ligne N : ce n'est pas du JSON` | Texte du chat copié (« Voici la suite : ») | Supprimer la ligne N |
| `id en double … contenu différent` | Exemple réécrit ajouté au lieu d'être remplacé | Garder une seule version |
| `ids qui ne sont pas de ce lot` | Sortie collée dans le mauvais dossier | Vérifier N et le dossier |
| `lot non exporté` | Faute de frappe sur N, ou export oublié | Vérifier N |
| Export : `existe déjà` / `même avec --force` | Lot déjà exporté | **Ne jamais réexporter** : vérifier N |
| `REJETÉ … historique : X textes au lieu de Y` | Le générateur a sauté ou ajouté un texte | Faire réécrire l'id (Y = `meta.history_count`) |
| `REJETÉ … critère language échoué` | Réponse trop chargée en anglicismes, ou pas dans la bonne langue | Faire reformuler |
| `REJETÉ … le bot parle sans avoir été mentionné` | Message du bot dans l'historique sans `@<bot>` avant | Faire réécrire l'historique de l'id |
| `REJETÉ … emote inconnue / mal écrite` | Emote inventée ou mal recopiée | Faire réécrire la réponse |
| `REJETÉ … nomme <streamer>, absent des blocs` | Nom connu du générateur mais pas du modèle | Faire réécrire avec « le streamer » / « la streameuse » |
| `À RELIRE … historique tronqué` | Historique long coupé à 1 300 tokens | Vérifier que la réponse ne s'appuie pas sur un message retiré |
| `À RELIRE … streamer nommé dans aucun bloc` | Contexte sans nom du streamer | Vérifier que la réponse n'invente pas de nom |
| `À RELIRE … réponse trop courte` | Réponse `langue` de moins de 4 mots | Vérifier la langue à l'œil |
| `À RELIRE … message peut-être en <langue>` | Message étranger hors catégorie `langue` | Si c'est le cas, faire réécrire en français |

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

### Live 5 : 16 novembre 2026

- `scripts/prompt_format.py` terminé : `[MAINTENANT]`, statuts, profils, historique, message, `build_messages`, plafonds ; test de l'exemple complet identique au document (709 tokens).
- Phase 2 : 20 cas dans `eval/cases.jsonl`, `checks.py` (lingua pour la langue), `evaluate.py`, `rescore.py`. Modèle de base : 1/20 après correction des critères (ajout de `no_brackets`). Tag `eval-v1`.
- Phase 3 commencée : génération par le code (contextes) + chat en ligne (textes) ; réservoirs `configs/pools.yaml` et `scripts/contexts.py`, avec tests anti-contamination.

### Live 6 : 18 novembre 2026

- Matrice `configs/seed_matrix.yaml`, tirage stratifié des catégories, `export_batch.py` (lot + prompt du générateur assemblé depuis `configs/generator_prompt.md`) et `merge_batch.py` (contrôles + rendu au format d'entraînement). Un dossier par lot.
- Cohérence des contextes corrigée : titres par famille de catégorie, viewers mentionnés sans profil, bot qui ne parle qu'après une mention d'un follower.
- Lots 1 et 2 générés par un chat en ligne : 40/40 acceptés, relus en entier, aucun fait inventé.

### Hors live : 22 novembre 2026

- Revue complète de l'architecture (5 axes, chaque constat vérifié par reproduction) avant les lots 3 à 15.
- Tirage corrigé (titres, horaires, première visite, historiques longs, streamer, situations impossibles) ; fusion et export durcis ; 6 langues.
- Critères de l'éval corrigés avant le gel : modèle de base 0/20. Deuxième revue des correctifs eux-mêmes (2 régressions de critères et 2 contradictions trouvées et corrigées). Tests : 59 → 140.

### Live 7 : 23 novembre 2026

- Lots 3 à 17 générés, chacun vérifié avant la génération (`batch.json`), avant la fusion (`output.jsonl`) et après (`merged.jsonl`) : 300 exemples, ~35 retouches (surtout des accords genrés).
- Corrections en cours de route : mention du bot acceptée n'importe où, résumé vide `(aucun souvenir)` (base re-mesurée : 0/20), titre « Live anniversaire » retiré, deux souvenirs neutralisés.
- Lots 1 et 2 remplacés par les lots 16 et 17 (jeux de l'éval dans les anciens faits). Assemblage `train.jsonl` 271 / `val.jsonl` 29, fiche `data/seed/README.md`. **Phase 3 terminée.**

### Hors live : 24 novembre 2026

- Plan du **tournoi des modèles** (4 lives : 3B, 8B + banc du Deck, Qwen3.5-4B, Gemma 4 E4B + audio), règle de choix, `MODELS.md` créé.
- Modèles téléchargés (3B, 8B BF16, Qwen3.5-4B, Gemma 4 E4B) ; environnement au vert (141 tests) ; TensorBoard vérifié. Steam Deck : Ollama en service systemd, ouvert au réseau (`192.168.1.38`), GPU Vulkan.
- `evaluate.py --model` ; **3B de base : 3/20**, VRAM 3,22 Go, chat template identique au 8B. Rien d'écrit pour la phase 4 (réservée au live).

### Live 8 : 25 novembre 2026

- **Phase 4 construite avec le chat** : `scripts/train.py` (prompt/completion, labels vérifiés sur chaque exemple, garde-fou vision, `--check-only`, `--max-steps`), configs YAML, TensorBoard ; `evaluate.py --adapter`. OBS n'a perdu aucune image.
- **Tournoi, 3 manches** : 3B v0 16/20 (7 min, Deck 5 s), 8B v0 18/20 mais > 15 s sur le Deck (éliminé), Qwen3.5-4B base 12/20 → v0 16/20 (Deck 7 s, échecs plus graves). **3B champion provisoire**, pas encore déployable (fait absent et injection 2/3).
- `scripts/bench_deck.py` (Ollama en streaming, prompts longs de `val.jsonl`) ; jeu anti-troll `eval/troll_cases.jsonl` (5 cas, 3B v0 1/5), trolling reporté en v2 (règle « blocs fiables » qui couvre l'historique).

## Procédure de fin de live

Quand Dantek annonce la fin du live, mettre ce fichier à jour **avant le dernier commit** :

1. Tableau "Où on en est" : mettre à jour l'état des phases.
2. "Mesures clés" : ajouter les chiffres obtenus pendant le live.
3. "Pièges déjà rencontrés" : ajouter chaque erreur rencontrée, avec sa cause et sa solution, en une ou deux lignes.
4. "Prochaines étapes" : réécrire la liste pour le prochain live.
5. "Journal des lives" : ajouter une entrée datée de trois ou quatre lignes.
6. Rester concis : ce fichier est relu à chaque session. Ne jamais y écrire de secret.
