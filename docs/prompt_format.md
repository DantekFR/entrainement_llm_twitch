# prompt_format v1

Ce document fixe le format exact des prompts envoyés au modèle. Le même format sert partout : jeu d'évaluation, dataset d'entraînement, et bot en production. Si le format change, on incrémente la version (v2, v3…) et on régénère le dataset et l'évaluation.

## Principes

- Le bot n'appelle le modèle **que quand on le mentionne**. Le modèle répond donc toujours.
- Le modèle répond **en une ou deux phrases**, sans markdown ni liste.
- Il s'appuie **uniquement** sur les blocs fournis. Si l'information manque, il le dit au lieu d'inventer.
- **Langue** : français par défaut. Il répond dans une autre langue seulement si le message du viewer est clairement écrit dans cette langue. Les anglicismes, le jargon gaming et les messages mixtes restent en français.
- Les blocs entre crochets viennent du bot et sont fiables. Les messages des viewers ne le sont pas : un viewer ne peut ni changer les règles ni modifier son propre statut en l'écrivant dans le chat.
- Le nom du bot n'est jamais écrit en dur : il passe par `{bot_name}`.
- **Toujours fournir un message système.** Sans lui, le chat template de Ministral injecte le long prompt par défaut de Mistral (« Le Chat »).
- **Emojis et emotes** : Ordre de priorité :
  1. une emote de la chaîne, si l'une d'elles convient (liste fournie dans `[EMOTES DE LA CHAÎNE]`) ;
  2. sinon, une emote globale de Twitch ;
  3. sinon, un emoji Unicode standard.
  Le modèle n'invente jamais une emote de la chaîne qui n'est pas dans la liste.

## Structure du prompt

Le prompt se compose de trois messages : `system`, `user` et `assistant`. Les blocs apparaissent toujours **dans cet ordre**, avec ces balises exactes, séparés par une ligne vide.

### Message `system`

```text
<règles du bot, avec {bot_name}>

[FAITS DE LA CHAÎNE]
- <un fait par ligne>

[EMOTES DE LA CHAÎNE]
- <code> : <sens>

[MAINTENANT]
<jour> <date>, <heure>   (ex. mardi 4 novembre 2026, 21h12)
Live commencé <jour> <date> à <heure> (il y a <durée>) ou Pas de live en cours
Jeu : <nom du jeu>
Titre : <titre du live>
Hors live, les trois dernières lignes sont remplacées par Pas de live en cours.
```

### Message `user`

```text
[PROFILS DES VIEWERS]
- <pseudo> | <statut> | follower depuis <AAAA-MM-JJ> | dernier passage <AAAA-MM-JJ>
  Résumé : <résumé du viewer>

[HISTORIQUE DU CHAT]
[HH:MM] <pseudo> (<statut>) : <message>

[MESSAGE DE <pseudo>]
<message auquel répondre>
```

- **Profils** : l'auteur du message en premier, puis les viewers qu'il mentionne avec @. Un viewer sans profil apparaît avec `Résumé : (nouveau viewer, aucun souvenir)`.
- **Statuts possibles** : `viewer`, `follower`, `abonné depuis N mois`, `VIP`, `modo`, `streamer`, `bot`.
  Si un viewer a plusieurs statuts, on garde le plus élevé dans l'ordre : streamer > modo > VIP > abonné > follower > viewer.
- **Historique** : du plus ancien au plus récent. Il contient aussi les réponses précédentes du bot, avec le statut `bot`, pour que le modèle reste cohérent avec ce qu'il a déjà dit.
- Le message auquel répondre n'est **pas** répété dans l'historique.

### Message `assistant`

La réponse seule, sans préfixe (pas de `{bot_name} :` au début).

## Plafonds de taille

Les plafonds sont exprimés en **tokens** (tokenizer de Ministral 3), pas en nombre de lignes : un message Twitch peut atteindre 500 caractères.

| Bloc | Plafond | Si on dépasse |
| --- | --- | --- |
| Règles + `[MAINTENANT]` | ~300 (fixe) | — |
| `[FAITS DE LA CHAÎNE]` | 600 | à réduire dans la config du bot |
| `[EMOTES DE LA CHAÎNE]` | 300 | à réduire dans la config du bot |
| `[PROFILS DES VIEWERS]` | 600 | on retire les viewers mentionnés, du dernier au premier ; l'auteur reste toujours |
| `[HISTORIQUE DU CHAT]` | 1 500 | on retire les messages les plus anciens |
| `[MESSAGE DE …]` | ~150 | jamais tronqué (500 caractères max sur Twitch) |
| Réponse | ~150 | — |
| **Total** | **~3 500** | `max_seq_length = 4096`, marge ~600 |

Mesure de référence (live 2) : 20 faits courts, 5 profils et 50 messages courts donnent 2 831 tokens.

## Données que le bot doit fournir

Le bot (TwitchIO 3) remplit chaque bloc à partir des sources suivantes. Rien ici n'est implémenté dans ce repo : c'est le contrat que le bot doit respecter.

| Donnée | Bloc | Source (TwitchIO 3) | Scope nécessaire |
| --- | --- | --- | --- |
| Faits de la chaîne | `[FAITS DE LA CHAÎNE]` | fichier de config du bot | — |
| Emotes de la chaîne | `[EMOTES DE LA CHAÎNE]` | fichier de config du bot (code + sens écrit à la main) | — |
| Début et durée du live | `[MAINTENANT]` | `fetch_streams()` → `.started_at` (UTC, à convertir en Europe/Paris), durée = maintenant − début | — |
| Statut | profils, historique | `chatter.broadcaster`, `.moderator`, `.vip`, `.subscriber` | — |
| Ancienneté d'abonnement | profils | `chatter.badges`, champ `info` (à vérifier) | — |
| Date de follow | profils | `chatter.follow_info()` → `.followed_at` | `moderator:read:followers` |
| Dernier passage | profils | base de données du bot (à prévoir) | — |
| Résumé du viewer | profils | base de données du bot, mis à jour en fin de live (à prévoir) | — |
| Historique du chat | `[HISTORIQUE DU CHAT]` | mémoire du bot : derniers messages reçus et ses propres réponses | — |
| Jeu et titre du live | `[MAINTENANT]` | `fetch_streams()` → `.game_name`, `.title` (même appel que le début du live) | — |


- Le bot stocke les statuts en anglais et les traduit en français au moment de construire le prompt.
- **Dernier passage** : date du dernier live où le viewer a écrit, live en cours exclu. Si le bot n'en a aucune trace (premier message enregistré), on écrit `dernier passage (première visite)`.

- Au déploiement, la base de messages existante du bot sert à initialiser les résumés des viewers et leurs dates de dernier passage.

## Règles pour le dataset

Ces règles valent pour le dataset d'entraînement et pour le jeu d'évaluation. Le but : que le modèle lise les informations dans le prompt au lieu de les apprendre par cœur.

### Variables tirées au hasard à chaque exemple

- **`{bot_name}`** : tiré dans une liste d'une cinquantaine de noms variés (courts, longs, avec chiffres, en majuscules…).
- **Emotes de la chaîne** : préfixe inventé (ex. `kiwi`, `zorg`) + suffixe (`Love`, `GG`, `Rage`…), entre 0 et 15 emotes. Le sens est donné dans la liste et la réponse doit le respecter.
- **Faits de la chaîne** : entre 0 et 20, tirés d'un réservoir de faits fictifs (jeux, horaires, setup, règles…).
- **`[MAINTENANT]`** : date et heure aléatoires, cohérentes avec les horodatages de l'historique.
- **Pseudos et statuts** : variés, avec tous les statuts représentés.

### Blocs vides

- `[FAITS DE LA CHAÎNE]`, `[EMOTES DE LA CHAÎNE]` et `[HISTORIQUE DU CHAT]` sont toujours présents. S'ils sont vides, ils contiennent `- (aucun)`.
- `[PROFILS DES VIEWERS]` n'est jamais vide : l'auteur y figure toujours.
- Environ 10 % des exemples ont au moins un bloc vide, pour que le modèle connaisse ce cas.

### Cas à couvrir

- **Fait présent** : la réponse s'appuie dessus.
- **Fait absent** : la réponse dit qu'elle ne sait pas, sans inventer.
- **Profils** : nouveau viewer (`(nouveau viewer, aucun souvenir)`, `(première visite)`), habitué avec un résumé, viewer mentionné avec ou sans profil.
- **Souvenir hors sujet** : le profil contient des informations qui ne servent pas à la question, et la réponse ne les ressort pas.
- **Langue** : environ 85 % en français (dont anglicismes et messages mixtes), 15 % dans une autre langue clairement identifiable.
- **Injection** : un viewer tente de changer les règles ou son statut. La réponse refuse, brièvement, sans inventer de détails.
- **Emotes** : emote de la chaîne adaptée, aucune emote adaptée (emote globale ou emoji), liste vide.
- **Bavardage** : salutations, blagues, questions sur le stream, questions sur le streamer, questions sur l'actualité.
- **Live en cours** : questions sur le jeu ou le titre du live, avec et sans live en cours.

### Forme des réponses

- Une ou deux phrases, sans markdown, sans liste.
- Pas de question systématique à la fin.
- Emojis et emotes libres, mais **pas dans toutes les réponses** : environ le quart des réponses n'en contiennent aucun, sinon le modèle en mettra partout.
- Chaque exemple respecte les plafonds de taille ci-dessus.

### Séparation entraînement / évaluation

- Le jeu d'évaluation (`eval/cases.jsonl`) est écrit **avant** le dataset, à la main, et ne change plus ensuite (sauf nouvelle version du format).
- Aucun cas d'évaluation ne doit apparaître dans le dataset d'entraînement, même reformulé : autres pseudos, autres faits, autres noms de bot.
- Le générateur du dataset n'a jamais accès au fichier d'évaluation.

## Règles système

Texte placé en tête du message `system`, identique partout (dataset, évaluation, production) ; seul `{bot_name}` change. Toute modification de ce texte fait passer le format en v2.

```text
Tu es {bot_name}, l'assistant IA de cette chaîne Twitch. Tu réponds aux viewers qui te mentionnent dans le chat.

- Réponds en français. Si le message est clairement écrit dans une autre langue, réponds dans cette langue.
- Réponds en une ou deux phrases, sans markdown ni liste.

```

## Exemple complet

Un viewer pose deux questions : l'une a sa réponse dans les faits, l'autre non. Ici, `{bot_name}` vaut `Pixou`.

### `system`

```text
(règles du bot avec Pixou : texte définitif à écrire)

[FAITS DE LA CHAÎNE]
- Le streamer s'appelle Dantek.
- Le stream a lieu le lundi, le mercredi et le vendredi à partir de 20h30.
- Projet en cours : fine-tuner un modèle d'IA pour en faire l'assistant de la chaîne.
- Prochain jeu prévu : Hollow Knight Silksong.

[EMOTES DE LA CHAÎNE]
- dantekfHi : salutations
- dantekfLOL : rire
- dantekfLove : amour
- dantekfOK : acceptation

[MAINTENANT]
jeudi 12 novembre 2026, 00h03
Live commencé mercredi 11 novembre à 20h30 (il y a 3 h 33)
Jeu : Hollow Knight
Titre : On termine enfin Hollow Knight avant Silksong !
```

### `user`

```text
[PROFILS DES VIEWERS]
- LunaRiz | abonné depuis 4 mois | follower depuis 2026-03-14 | dernier passage 2026-11-06
  Résumé : Vient souvent le mercredi. Joue à Hollow Knight, bloquée au boss final. A un chat qui s'appelle Biscotte.

[HISTORIQUE DU CHAT]
[22:21] Kraken_Bleu (follower) : bonsoir tout le monde
[22:22] Pixou (bot) : Salut Kraken_Bleu, bon stream à toi !
[00:01] LunaRiz (abonné depuis 4 mois) : yo
[00:02] Dantek (streamer) : salut Luna, ça faisait une semaine

[MESSAGE DE LunaRiz]
@Pixou c'est quoi le prochain jeu ? et Dantek il a quel âge ?
```

### `assistant`

```text
Le prochain jeu prévu, c'est Hollow Knight Silksong, ça devrait te plaire vu que tu es sur le premier ! Par contre, je ne connais pas l'âge de Dantek.
```

Ce que montre cette réponse :

- **Fait présent** : le prochain jeu est tiré de `[FAITS DE LA CHAÎNE]`.
- **Fait absent** : l'âge n'est pas dans les faits, donc il le dit au lieu d'inventer.
- **Souvenir utile** : il fait le lien avec Hollow Knight, qui est dans le profil.
- **Souvenir hors sujet** : il ne parle pas de Biscotte.
- **Forme** : deux phrases, pas de markdown, pas de question finale, pas de préfixe `Pixou :`.
