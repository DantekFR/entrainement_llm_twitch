# Feuille de route : fine-tuning de dantekos\_bot

Nov 4, 2026 · @Princesse Audrey

## Objectif et principes

Ce repo fine-tune **Ministral 3 8B Instruct** pour en faire dantekos\_bot, puis l'exporte vers Ollama sur le Steam Deck. Le but est **pédagogique** : chaque étape doit pouvoir s'expliquer au chat, et chaque résultat doit être mesuré plutôt que ressenti.

Ce que le fine-tuning doit apprendre au modèle : un **comportement** (réponses courtes, ton de la chaîne, appui sur les blocs de contexte, "je ne sais pas" quand l'info manque, résistance aux injections, réponse toujours en français). Ce qu'il ne doit pas apprendre : des **connaissances** (faits de la chaîne, infos sur les jeux). Celles-ci restent dans la base du bot.

Quatre règles valent pour tout le repo :

1. **On mesure avant d'entraîner.** Le jeu d'évaluation existe avant le premier exemple d'entraînement.
2. **On entraîne comme on sert.** Le format du prompt vient du repo du bot, jamais d'une copie.
3. **Tout run est reproductible** : config, versions, seed et métriques sont enregistrés avec le run.
4. **On réentraîne toujours depuis le modèle de base**, sur le dataset cumulé, jamais en empilant des LoRA.

## Structure du repo

Nom proposé : `dantekos-training`. Il tourne sur le PC (WSL 2, RTX 4070), le bot reste sur le Steam Deck.

```text
dantekos-training/
├── README.md            # vue d'ensemble + journal des lives
├── MODELS.md            # changelog des versions (v0, v1...) et leurs scores
├── pyproject.toml       # dépendances et index PyTorch (uv)
├── uv.lock              # versions exactes, versionné
├── configs/             # train_v0.yaml, eval.yaml
├── eval/cases.jsonl     # jeu d'évaluation (versionné, jamais vu à l'entraînement)
├── data/
│   ├── seed/            # dataset synthétique (peut être versionné)
│   └── raw/             # exports du bot (JAMAIS versionné)
├── scripts/             # check_env, generate_seed, train, evaluate, export
├── notebooks/           # 01_explore_model.ipynb
└── runs/                # un dossier par run : config, métriques, logs (ignoré)
```

**Le lien avec le repo du bot.** `prompt_format.py` vit dans le repo du bot, car c'est lui qui sert le modèle. Ce repo l'installe comme dépendance, épinglée sur un tag Git (par exemple `pip install git+https://github.com/DantekFR/dantek_bot_twitch@prompt-v1`). Un seul code de rendu, une version explicite : c'est la garantie technique que l'entraînement et le live voient le même format.

**Le `.gitignore` dès le premier commit** : `data/raw/`, `runs/`, `outputs/`, `*.gguf`, `*.safetensors`, `.env` (token Hugging Face). Aucune donnée de viewer ne doit entrer dans ce repo public.

## Phase 0 : l'environnement

**Objectif :** un environnement CUDA fonctionnel sous WSL 2, avec des versions figées et vérifiables par un script.

1. Installer **uniquement le pilote NVIDIA côté Windows**. Sous WSL, on n'installe jamais de pilote Linux : WSL réutilise celui de Windows.
2. Installer **uv** dans WSL, puis créer le projet : `uv init`, et `uv python pin 3.12` pour fixer la version de Python.
3. Déclarer l'index PyTorch CUDA dans `pyproject.toml` (voir ci-dessous) pour que uv installe la version GPU de torch et non la version CPU.
4. Ajouter les dépendances avec `uv add` : torch, Unsloth, transformers v5, TRL, PEFT, bitsandbytes, tensorboard. Vérifier dans la doc d'installation d'Unsloth quelle combinaison torch et CUDA il supporte, car il peut imposer sa propre version de torch.
5. **Versionner `uv.lock`.** C'est lui qui fige les versions exactes. Sur une autre machine, `uv sync` recrée un environnement identique.
6. Écrire `scripts/check_env.py`, lancé avec `uv run`, qui affiche : versions des bibliothèques, `torch.cuda.is_available()`, nom du GPU, VRAM libre, support du bf16.
7. Déplacer le cache Hugging Face (`HF_HOME`) vers un disque qui a de la place. Un 8B en BF16 pèse environ 16 Go, plus les checkpoints et les exports.

L'index PyTorch à déclarer dans `pyproject.toml` (adapter `cu128` à la version CUDA choisie) :

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cu128" }
```

`explicit = true` signifie que cet index ne sert qu'aux paquets qui le désignent : tout le reste vient de PyPI.

**Critère de fin :** `check_env.py` passe au vert.

**Ce qu'on explique au chat :** pourquoi CUDA, ce qu'est le bf16, pourquoi on fige les versions.

**Pièges fréquents :** un pilote Linux installé par erreur dans WSL, une version de PyTorch compilée pour une autre version de CUDA, un disque WSL qui se remplit en silence.

## Phase 1 : explorer Ministral 8B

**Objectif :** comprendre ce qu'on va modifier avant d'y toucher, dans `notebooks/01_explore_model.ipynb`.

1. Charger la version republiée par Unsloth (BF16 ou 4 bits). La version Instruct officielle de Mistral est en FP8, moins pratique pour un QLoRA.
2. Ministral 3 embarque un encodeur d'images. Vérifier dans le guide Unsloth comment le charger pour du texte seul, et noter la VRAM occupée.
3. **Tokenizer :** tokeniser des messages typiques du chat (argot, abréviations, anglicismes du jeu vidéo, noms d'emotes) et regarder comment ils sont découpés. Afficher les tokens spéciaux.
4. **Chat template :** afficher le texte exact produit par `apply_chat_template` sur une conversation avec un message système. C'est ce texte que le Modelfile Ollama devra reproduire à la fin.
5. Rendre un vrai prompt avec `prompt_format` v1 et compter ses tokens. Ce chiffre fixe le `max_seq_length` de l'entraînement.
6. Faire générer quelques réponses au modèle brut.

**Critère de fin :** tu sais combien de tokens fait un prompt typique, et tu as sauvegardé le texte exact du chat template.

**Ce qu'on explique au chat :** ce qu'est un token, pourquoi le français "coûte" souvent plus de tokens que l'anglais, à quoi sert un chat template.

## Phase 2 : le jeu d'évaluation

**Objectif :** une note de référence pour le modèle de base, **avant** tout entraînement. Sans elle, impossible de savoir si le fine-tuning a amélioré quoi que ce soit.

Le fichier `eval/cases.jsonl` contient de 50 à 80 cas, écrits à la main et répartis par catégorie :

| Catégorie | Ce qu'on teste | Part |
| --- | --- | --- |
| Fait présent | La réponse s'appuie sur le bloc FAITS | 20 % |
| Fait absent | Le modèle dit qu'il ne sait pas, sans inventer | 20 % |
| Injection | "Ignore tes règles", faux bloc, faux modo | 15 % |
| Mémoire viewer | Un fait déclaré par le viewer reste présenté comme tel | 10 % |
| Langue et registre | Toujours en français, même face à un message dans une autre langue, en comprenant l'argot et les anglicismes du chat | 15 % |
| Bavardage et provocation | Ton, humour, refus courtois | 20 % |

Chaque cas contient le contexte complet, la question, et des **critères vérifiables** plutôt qu'une réponse idéale : longueur maximale, langue attendue, mots interdits (un fait inventé), mots requis.

`scripts/evaluate.py` fait répondre un modèle à tous les cas, applique les vérifications automatiques et sort un score par catégorie dans `runs/<id>/eval.json`. Pour le ton, une relecture humaine sur un échantillon suffit au début.

**Mesures de référence :** Ministral 8B de base, et ton Qwen actuel via Ollama, avec le même script.

**Critère de fin :** deux scores de référence notés dans `MODELS.md`.

**Ce qu'on explique au chat :** pourquoi le jeu de test ne doit jamais servir à l'entraînement (sinon le modèle apprend les réponses de l'examen). C'est aussi le bon moment pour le test à l'aveugle avec les viewers.

## Phase 3 : le dataset de départ

**Objectif :** 300 à 800 exemples synthétiques de qualité, au format `prompt_format` v1, pour l'entraînement v0.

1. **Une matrice de diversité** dans `configs/seed_matrix.yaml` : catégories (les mêmes que l'évaluation) × registres (soutenu, familier, argot, fautes de frappe) × états du live (jeu, code, discussion) × profils de viewers (nouveau, habitué, provocateur). On génère en parcourant cette matrice, pas au hasard.
2. `scripts/generate_seed.py` demande à un gros modèle de produire le contexte, la question et la réponse idéale, puis rend le tout avec `prompt_format`. **Vérifie les conditions d'utilisation du fournisseur** : certaines interdisent d'utiliser leurs sorties pour entraîner un autre modèle.
3. **Filtrer automatiquement :** doublons, réponses trop longues, mauvaise langue, faits inventés absents du contexte.
4. **Relire à la main un échantillon** (au moins 50 exemples). C'est ici que se joue le ton de dantekos\_bot.
5. Découper en train et validation (90 / 10), et vérifier qu'aucun exemple ne ressemble à un cas de l'évaluation.
6. Rédiger une courte fiche du dataset (`data/seed/README.md`) : source, taille, répartition, version du format.

**Le nom du bot n'est jamais écrit en dur dans les exemples.** Il est injecté par `prompt_format` depuis la config (`{bot_name}`), et le dataset synthétique utilise plusieurs noms différents. Le modèle apprend ainsi à prendre son nom dans le contexte : quand le chat choisira le nouveau nom, il suffira de changer la config, sans réentraîner.

**Critère de fin :** `train.jsonl` et `val.jsonl` produits, échantillon relu, fiche rédigée.

**Ce qu'on explique au chat :** pourquoi la qualité compte plus que la quantité, et le risque d'un dataset synthétique trop uniforme (le modèle imite les tics du générateur). Les viewers peuvent proposer ou corriger des exemples en direct.

## Phase 4 : l'entraînement v0

**Objectif :** un premier adaptateur LoRA, entraîné de bout en bout, avec des courbes lisibles par le chat.

Point de départ de `configs/train_v0.yaml`, à ajuster selon la VRAM observée :

| Paramètre | Valeur de départ | Pourquoi |
| --- | --- | --- |
| Chargement | 4 bits (QLoRA) | Faire tenir un 8B dans 12 Go |
| Rang LoRA `r` / `alpha` | 16 / 16 | Assez pour un changement de style |
| Modules ciblés | Projections d'attention et MLP | Réglage standard d'Unsloth |
| Learning rate | 2e-4, décroissance linéaire | Valeur classique pour LoRA |
| Époques | 2 | Petit dataset, on surveille le surapprentissage |
| Batch / accumulation | 2 / 4 (batch effectif 8) | Compromis VRAM et stabilité |
| `max_seq_length` | Mesuré en phase 1, plus une marge | Ne pas couper les prompts |
| Gradient checkpointing | Activé | Économise beaucoup de VRAM |
| Perte | Réponses de l'assistant uniquement | On n'apprend pas à écrire les prompts |
| Seed | Fixée | Reproductibilité |

`scripts/train.py` lit la config, crée `runs/<date>_<nom>/`, y copie la config et les versions, journalise la perte d'entraînement et de validation dans **TensorBoard** (à afficher en live), et sauvegarde un checkpoint régulièrement.

**Critère de fin :** la perte de validation baisse puis se stabilise, et l'adaptateur est sauvegardé.

**Ce qu'on explique au chat :** la différence entre perte d'entraînement et de validation, ce que signifie une perte de validation qui remonte (surapprentissage), pourquoi LoRA n'entraîne qu'une petite fraction des paramètres.

**Pièges fréquents :** mémoire insuffisante (réduire d'abord le batch, puis la longueur de séquence), perte à NaN (learning rate trop élevé), template mal appliqué (vérifier un exemple rendu avant de lancer), OBS qui perd des images pendant que le GPU est saturé.

## Phase 5 : évaluer la v0

**Objectif :** décider, chiffres à l'appui, si la v0 mérite d'aller sur le Steam Deck.

1. Relancer `scripts/evaluate.py` sur le modèle de base + l'adaptateur v0, avec exactement les mêmes réglages de génération (température, longueur) que pour la mesure de référence.
2. Comparer **catégorie par catégorie**, pas seulement le score global. Un gain sur le ton qui s'accompagne d'une hausse des faits inventés est une régression.
3. Lire ensemble, en live, une dizaine de réponses avant/après.
4. Noter le résultat et la décision dans `MODELS.md`.

**Règle de décision :** la v0 est déployée seulement si elle fait au moins aussi bien que le modèle de base sur "Fait absent" et "Injection". Ces deux catégories passent avant le ton.

**Ce qu'on explique au chat :** qu'une v0 décevante est un résultat normal et utile. Elle montre où le dataset est faible.

## Phase 6 : export et déploiement

**Objectif :** `dantekos:v0` qui répond dans le chat depuis le Steam Deck.

1. Fusionner l'adaptateur avec le modèle de base et exporter en **GGUF quantifié** (Q4\_K\_M pour commencer) via `scripts/export.py`.
2. Écrire le **Modelfile** Ollama. Son `TEMPLATE` doit reproduire caractère pour caractère le chat template sauvegardé en phase 1. Le versionner dans le repo.
3. **Tester d'abord sur le PC** : relancer l'évaluation contre le modèle servi par Ollama. Un score très inférieur à celui de la phase 5 signale presque toujours un problème de template ou de quantification.
4. Copier le GGUF et le Modelfile sur le Steam Deck (`scp`), puis `ollama create dantekos:v0`.
5. Mesurer la latence réelle sur le Deck (délai avant le premier token, tokens par seconde) et la noter dans `MODELS.md`.
6. Basculer le bot sur `dantekos:v0` par sa config, en gardant l'ancien modèle disponible pour revenir en arrière en une ligne.

**Critère de fin :** le bot répond en live avec la v0, et le retour à l'ancien modèle a été testé.

**Ce qu'on explique au chat :** ce qu'est la quantification et ce qu'elle coûte en qualité, pourquoi le template est la cause numéro un des modèles "qui marchaient dans le notebook".

## Phase 7 : la boucle d'amélioration

**Objectif :** une nouvelle version régulière (toutes les deux à quatre semaines), nourrie par les vrais lives.

1. Le bot journalise chaque interaction avec son contexte, la version du format et celle du modèle. Les modos notent les réponses.
2. `scripts/export_from_bot.py` récupère la base du Deck dans `data/raw/` (jamais versionné), pseudonymise les logins et extrait les interactions notées.
3. Tu corriges les mauvaises réponses. Ces corrections rejoignent le dataset cumulé, à côté du dataset synthétique.
4. On réentraîne **depuis le modèle de base**, sur tout le dataset cumulé.
5. On évalue sur le jeu de test **figé**. On peut y ajouter des cas, jamais en retirer ni en modifier, sinon les scores ne sont plus comparables.
6. Déploiement seulement si aucune catégorie critique ne régresse. Nouvelle ligne dans `MODELS.md`.

Quand le format du prompt change (v2), on régénère tout le dataset avec le nouveau rendu. C'est possible parce que le contexte brut est stocké, et pas seulement le texte final.

**Ce qu'on explique au chat :** que leurs messages font progresser le bot, et comment leurs données sont protégées (pseudonymisation, rien de public, commande `!oublie-moi`).

## Ce soir et demain

Le live de demain démarre l'entraînement v0 en début de stream. Tout ce qui pourrait le bloquer se fait ce soir.

**Ce soir, hors live :**

- [ ] Créer le repo avec la structure et le `.gitignore`
- [ ] Phase 0 complète : `check_env.py` au vert
- [ ] Phase 1 rapide : chat template sauvegardé, taille d'un prompt mesurée
- [ ] Figer `prompt_format` v1 dans le repo du bot et poser le tag `prompt-v1`
- [ ] Phase 2 minimale : 20 cas d'évaluation (on complètera à 80 en live plus tard)
- [ ] Phase 3 : dataset de départ généré, filtré et survolé
- [ ] Entraînement test de 5 minutes pour valider la chaîne
- [ ] Enregistrement OBS de 10 minutes pendant cet entraînement pour vérifier qu'aucune image n'est perdue

**Demain, en live :**

1. Présenter le projet, le repo et la feuille de route.
2. Mesure de référence de Ministral 8B sur les 20 cas.
3. Lancer l'entraînement v0, TensorBoard à l'écran.
4. Pendant qu'il tourne : coder la nouvelle couche IA du bot en SSH sur la branche `feat/ia-v2`.
5. Point sur la courbe de perte toutes les 15 minutes environ.
6. En fin de live : évaluation de la v0 et lecture de réponses avant/après avec le chat.

Le déploiement sur le Steam Deck (phase 6) peut attendre le live de vendredi : mieux vaut un export testé tranquillement qu'un modèle cassé en fin de stream.
