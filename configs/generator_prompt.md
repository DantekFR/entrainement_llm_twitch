# Génération d'exemples pour l'assistant d'une chaîne Twitch

Tu m'aides à créer un dataset d'entraînement pour un petit modèle de langage qui sera l'assistant IA d'une chaîne Twitch francophone. Un bot construit le prompt du modèle (des règles, puis des blocs de contexte entre crochets) et le modèle écrit une réponse courte au viewer qui l'a mentionné.

## Les règles que le modèle doit suivre

Voici ses règles système. `{bot_name}` y est remplacé par le nom du bot de chaque exemple.

```text
<<SYSTEM_RULES>>
```

## Un exemple complet

<<EXAMPLE>>

Attention : dans cet exemple, le bot répond à un message qui ne le mentionne pas. Dans tes historiques, le bot ne parle qu'après une mention `@` (voir plus bas). Ne réutilise pas non plus ses tournures, comme « Le prochain jeu prévu, c'est… ».

## Ce que je te donne

Un lot d'exemples au format JSONL (un exemple JSON par ligne). Chaque exemple contient :

- `id` : l'identifiant, à recopier tel quel ;
- `situation` : ce que l'exemple doit illustrer (`category`, `instruction`), avec la façon d'écrire du viewer (`register`) et son humeur (`attitude`) ;
- `meta` : le streamer (`name`, et `gender` : `m` ou `f`) et les viewers que le message doit mentionner (`mentioned`), ceux d'entre eux qui ne suivent pas la chaîne (`without_profile`) : ils n'ont pas de profil, le bot ne sait rien d'eux et ne doit rien inventer à leur sujet ; et le nombre de textes d'historique à écrire (`history_count`) ;
- `inputs` : le contexte déjà tiré (nom du bot, faits, emotes, live, profils, historique). Les champs `text` de l'historique et le champ `message` sont vides : c'est à toi de les écrire.

`now` est l'heure du message. Si `stream_start` vaut `null`, il n'y a pas de live en cours. L'auteur du message est `inputs.author`.

## Ce que tu dois écrire pour chaque exemple

1. **L'historique** : un texte par entrée de `inputs.history`, dans le même ordre. Ce sont des messages de chat Twitch, courts et naturels, cohérents avec leur auteur, son statut, l'heure et le live. Chaque message du bot (statut `bot`) répond à un message précédent qui le mentionne avec `@`, et respecte ses règles. Un viewer au statut `viewer` ne suit pas la chaîne : le bot ne lui répond jamais. Le streamer écrit peu. L'historique peut amener la situation, mais il ne contient pas la réponse. Certains historiques sont longs (30 à 50 messages, un chat animé) : écris quand même un texte court pour chaque entrée, sans en sauter aucune. Chaque texte tient sur une seule ligne.
2. **Le message** : il commence par `@` suivi de `bot_name`, mentionne avec `@` chaque viewer de `meta.mentioned`, et illustre la situation dans le registre et l'attitude demandés. Il tient sur une seule ligne, faux bloc compris. Pour une tentative d'injection, un faux bloc reprend les balises du prompt (`[FAITS DE LA CHAÎNE]`, `[MAINTENANT]`…), jamais des jetons techniques comme `[INST]`, `[/INST]`, `[SYSTEM_PROMPT]` ou `</s>`.
3. **La réponse idéale** du bot :
   - elle suit les règles système et la consigne de la situation ;
   - une ou deux phrases, sans markdown, sans liste, sans crochets, sans préfixe `nom :` ;
   - pour la chaîne, le streamer et les viewers, elle n'utilise que les blocs et n'invente rien ;
   - elle ne ressort un souvenir du profil que s'il sert à la réponse ;
   - les emotes s'écrivent telles quelles (`kiwiHype`, jamais `[kiwiHype]` ni `:kiwiHype:`) et respectent le sens donné dans la liste ;
   - environ une réponse sur quatre ne contient ni emote ni emoji ;
   - pas de question systématique à la fin ;
   - le streamer est désigné par son nom seulement si ce nom figure dans les faits ou dans l'historique (sinon « le streamer » ou « la streameuse »), et accordé selon `meta.streamer.gender` ;
   - le registre et l'attitude concernent seulement le message : la réponse reste dans un français correct et sympathique, même face à un viewer provocateur ;
   - un message en français avec des anglicismes, ou mélangé, reçoit une réponse en français.

Varie les formulations d'un exemple à l'autre : pas deux messages ni deux réponses construits sur le même moule. Ne reprends pas les noms ni les phrases de l'exemple complet. Évite en particulier de répéter les mêmes débuts de réponse, comme « Bien tenté », « Bien essayé », « Raté : » ou « Aucune idée » : trouve chaque fois une autre tournure.

Si la situation est impossible avec le contexte (par exemple un fait présent alors que la liste de faits est vide), ne complète jamais le contexte : adapte la situation (le fait devient absent) et réponds avec ce que contiennent les blocs.

## Format de sortie

Uniquement du JSONL, dans un seul bloc de code : une ligne par exemple, dans l'ordre du lot, sans commentaire avant ni après.

```jsonl
{"id": "b001-00", "history": ["texte 1", "texte 2"], "message": "@NomDuBot ...", "response": "..."}
```

`history` contient exactement `meta.history_count` textes, autant que d'entrées dans `inputs.history` (liste vide si l'historique est vide).

Si ta réponse est coupée parce qu'elle est trop longue, je te demanderai la suite : recommence alors à la ligne coupée, réécrite en entier, dans un nouveau bloc de code.

## Le lot

```jsonl
<<BATCH>>
```
