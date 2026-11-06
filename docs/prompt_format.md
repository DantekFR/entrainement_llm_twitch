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
1. une emote de la chaine, si l'une d'elles convient (liste fournie dans `[EMOTES DE LA CHAÎNE]`) ;
2. sinon, une emote globale de Twitch ;
3. sinon, un emoji Unicode standard.
Le modèle n'invente jamais une emote de la chaine qui n'est pas dans la liste.

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
```

- Les blocs `[FAITS DE LA CHAÎNE]` et `[EMOTES DE LA CHAÎNE]` sont toujours présents. S'ils sont vides, ils contiennent `- (aucun)`.

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
- **Statuts possibles** : `viewer`, `follower`, `abonné palier N`, `VIP`, `modo`, `streamer`, `bot`.
- **Historique** : du plus ancien au plus récent. Il contient aussi les réponses précédentes du bot, avec le statut `bot`, pour que le modèle reste cohérent avec ce qu'il a déjà dit.
- Le message auquel répondre n'est **pas** répété dans l'historique.

### Message `assistant`

La réponse seule, sans préfixe (pas de `{bot_name} :` au début).

## Plafonds de taille

Les plafonds sont exprimés en **tokens** (tokenizer de Ministral 3), pas en nombre de lignes : un message Twitch peut atteindre 500 caractères.

| Bloc | Plafond | Si on dépasse |
| --- | --- | --- |
| Règles + `[MAINTENANT]` | ~250 (fixe) | — |
| `[FAITS DE LA CHAÎNE]` | 600 | à réduire dans la config du bot |
| `[EMOTES DE LA CHAÎNE]` | 300 | à réduire dans la config du bot |
| `[PROFILS DES VIEWERS]` | 600 | on retire les viewers mentionnés, du dernier au premier ; l'auteur reste toujours |
| `[HISTORIQUE DU CHAT]` | 1 500 | on retire les messages les plus anciens |
| `[MESSAGE DE …]` | ~150 | jamais tronqué (500 caractères max sur Twitch) |
| Réponse | ~150 | — |
| **Total** | **~3 500** | `max_seq_length = 4096`, marge ~600 |

Mesure de référence (live 2) : 20 faits courts, 5 profils et 50 messages courts donnent 2 831 tokens.
