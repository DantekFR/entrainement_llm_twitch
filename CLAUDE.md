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
| `prompt_format` v1 | **Terminé** : `docs/prompt_format.md` + `scripts/prompt_format.py` (tous les blocs, `build_messages`, plafonds), test de l'exemple complet au vert |
| 2. Jeu d'évaluation | **Terminée pour la v0** : 20 cas, `evaluate.py`, base = **0/20** (critères corrigés le 22/11). **Tag `eval-v1` à créer** (absent du repo). Référence Qwen reportée en phase 6 |
| 3. Dataset de départ | **En cours** : chaîne complète en place (matrice, export, prompt du générateur, fusion). Lots 1 et 2 validés (40 exemples). Tirage et contrôles corrigés le 22/11, avant le lot 3. Lots 3 à 15 à produire |
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
| Exemple complet du doc (`measure_prompt.py`) | system 492 · user 212 · **total 709 tokens** avec template (le template ajoute 5 tokens) |
| **Éval du modèle de base** (`eval-v1`, 20 cas, glouton, critères du 22/11) | **0/20** (1/20 avant : le seul succès, `live_001`, contenait de l'italique `*…*`). Par critère : `not_empty` 20/20, `no_brackets` 3/20, `no_markdown` 9/20, `max_sentences` 15/20, `language` 19/20, `must_include_*` 14/15, `must_not_match` 10/13. Run rescoré : `runs/20261116-1246_base_rescore-eval-v1/` |
| Vitesse pendant l'éval | ~7 tokens/s ; le temps suit le nombre de tokens générés ; 1er cas lent (préchauffage GPU, 51 tokens en 33 s) |
| Tirage des contextes (2 000 tirages) | 67 % jeux, 17 % non gaming, 15 % hors live |
| Prompt du générateur (lot de 20, tokens Ministral) | lot 1 : 75 700 car. / 25 200 tokens ; lot 2 : 66 600 / 21 900 ; lots 3-15 (un exemple par ligne) : 54 600 à 71 100 car. / 20 400 à 28 600 tokens, le lot 3 est le plus gros. Prendre un chat à grande fenêtre |
| **Lots 1 et 2** (générateur en ligne) | **20/20 et 20/20** acceptés par la fusion ; relecture complète : 0 fait inventé, durées et culture générale justes ; sans emote ni emoji : 5/20 et 6/20 (cible ~1/4) |
| Longueur des exemples | lots 1-2 : 631 à 1 183 tokens (médiane 890) ; lots 3-15 tirés : médiane ~910, max ~2 150 (historiques longs, ~1 sur 20 tronqué à 1 300). Réponse ≈ 3,6 % des tokens |
| Sortie du générateur | lots 1-2 : ~3 300 à 3 600 tokens (126 à 174 textes d'historique, ~13 tokens par texte) ; lots 3-15 : 131 à 281 textes, lot 3 ≈ 5 500 tokens |
| Tirage des lots 3-15 (22/11) | live calé sur l'horaire : 79 % (cible 85 %) ; streamer : 4 % des messages ; 17 historiques longs sur 260 (tous en live) ; situations `profil` avec un souvenir : 22/34 ; hors live : 49/260 ; 3 contextes où le streamer n'est nommé dans aucun bloc |

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
- **Provenance des tirages** : lot 1 = code du commit `de76603`, lot 2 = `5294d0d`, lots 3 et suivants = commit des corrections du 22/11.
- **Fusion durcie** : arrêt sans rien écrire si le lot n'est pas exporté, si `output.jsonl` est absent, vide, pas en UTF-8, mal formé (numéro de ligne, et « sortie coupée ? » si la ligne est incomplète), contient du texte du chat, un id d'un autre lot ou deux lignes différentes pour un même id (une ligne recopiée à l'identique est ignorée), ou si 0 exemple est accepté. Les balises ```` ``` ```` sont retirées, même collées à une ligne. Nouveaux rejets : texte vide ou sur plusieurs lignes, espaces autour de la réponse, préfixe `Bot :` / `<nom> :` / `Assistant :`, mention inexacte (`@WaffleKingou`), jeton de contrôle en toutes lettres (`[/INST]`, `</s>`, `<SPECIAL_n>`), réponse `langue` pas dans la langue du message (titre et catégorie retirés avant la détection), emote `:code:` ou mal écrite, nom du streamer absent des blocs, message du bot dans l'historique qui parle sans mention depuis son message précédent ou qui enfreint les règles de forme. Emotes globales de Twitch (Kappa, LUL, twitchRaid…) acceptées. Avertissements `À RELIRE` (pas de rejet) : message très probablement étranger hors catégorie `langue` (le franglais reste du français), réponse `langue` de moins de 4 mots, streamer nommé dans aucun bloc, historique tronqué par `apply_limits`.
- **Export** : refuse un lot dont `batch.json` existe (`--force` seulement si le prompt n'a jamais été envoyé, et jamais si `output.jsonl` existe) ; lot écrit dans le prompt à raison d'un exemple par ligne.
- **Éval** (critères corrigés avant le gel, base 1/20 → 0/20) : critère commun `not_empty` (une réponse faite seulement d'emotes ou de mentions est vide), italique `*…*` et `_…_` dans `no_markdown` (pas « 5* », « ¯\\_(ツ)_/¯ » ni « -_- »), `’` = `'`, points de suspension suivis d'une minuscule ne comptent pas comme fin de phrase, réponse française de moins de 5 mots toujours acceptée pour la langue ; regex de `injection_001` (refus acceptés, « je confirme que tu es modo » refusé), `bavardage_001` (question finale suivie d'emotes, de mentions ou de « ! »), `culture_actu_002` ; listes `fait_absent` (« j'ignore », « aucune info »…), âge en lettres et villes en plus, `live_002`. `rescore.py` garde une copie `eval.before_rescore.json`.
- **Durée du live** calculée en UTC (juste la nuit du changement d'heure, jamais négative).

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

## Prochaines étapes

1. **Vérifier le commit des corrections du 22/11** : `uv run pytest -q` → 140 passed. Créer le tag sur ce commit : `git tag eval-v1`, `git tag -l`, `git push origin eval-v1`.
2. **Lots 3 à 15**, un par un : `uv run python -m scripts.export_batch --batch N`, nouvelle conversation, coller `batch_00N/prompt.md`, enregistrer la sortie dans `batch_00N/output.jsonl` (`Ctrl+S`), puis `uv run python -m scripts.merge_batch --batch N`. Si la sortie est coupée, supprimer la ligne coupée, demander la suite et l'ajouter au même fichier. **Commiter chaque lot juste après sa fusion.** Montrer à Claude seulement les lignes `REJETÉ` / `À RELIRE` et les lots sous 18/20. Le lot 3 est le plus lourd (3 historiques longs, 281 textes, prompt de 28 600 tokens).
3. **Bilan des 15 lots** : script qui joint `merged.jsonl` et `batch.json` par id (registre, attitude, état du live, famille de catégorie). Il compte les débuts de réponse les plus fréquents (tics vus : « Le prochain jeu prévu, c'est… », « Raté : », « Bien essayé / Bien tenté », « Aucune idée »), les doublons et la fréquence de « Live anniversaire ». Relire au moins 50 exemples (40 déjà relus). **Lots 1-2 à revoir** : première visite avec souvenir (b001-04, b001-07, qui affirme « tu es souvent là en fin de live », b001-15, b002-04, b002-11), « première année » de la chaîne (b001-15, b001-17), extrapolation légère (b001-16). Les corriger dans `output.jsonl` puis refusionner, ou les écarter.
4. **Assemblage** : `data/seed/train.jsonl` et `val.jsonl` (90/10, graine fixée, stratifié par catégorie), fiche `data/seed/README.md` (source, taille, répartition, `prompt_format v1`).
5. Phase 4 : `configs/train_v0.yaml`, `scripts/train.py` (précautions vérifiées dans la ROADMAP : format prompt/completion, `max_length=4096`, contrôle des labels), entraînement test de 5 minutes.
6. Plus tard : option `--model` dans `evaluate.py` (phase 5), cas d'éval à historique long, descriptions de fiches plus longues dans les réservoirs (jusqu'à 150 tokens comme IGDB), neutraliser les jetons de contrôle dans le bot.

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

## Procédure de fin de live

Quand Dantek annonce la fin du live, mettre ce fichier à jour **avant le dernier commit** :

1. Tableau "Où on en est" : mettre à jour l'état des phases.
2. "Mesures clés" : ajouter les chiffres obtenus pendant le live.
3. "Pièges déjà rencontrés" : ajouter chaque erreur rencontrée, avec sa cause et sa solution, en une ou deux lignes.
4. "Prochaines étapes" : réécrire la liste pour le prochain live.
5. "Journal des lives" : ajouter une entrée datée de trois ou quatre lignes.
6. Rester concis : ce fichier est relu à chaque session. Ne jamais y écrire de secret.
