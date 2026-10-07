# 0033 — Messages qui ne sont pas des questions de statistique : comprendre, ne pas rédiger

**Date** : 2026-10-07 · **Statut** : accepté (KBD), contrat 1.5.0 à approuver par SAN · **Modifie** : 0017

## Contexte

« Comment tu vas ? » recevait « Cette donnée n'existe pas dans les publications de l'ANSD… », et en wolof
(la détection de langue penchait vers le wolof faute de mot connu). Tout message qui n'est pas une question
de statistique finissait en refus, sur le site comme sur les messageries.

## Décisions (choix de KBD)

1. **Le LLM classe, il ne rédige pas.** Dans le même appel qu'aujourd'hui (aucun coût en plus), il range le
   message dans une catégorie de conversation : salutation, remerciement, au revoir, à propos du bot, langue,
   aide, définition d'un indicateur, « pourquoi / opinion », hors sujet, impoli. Les règles locales font de
   même, plus simplement, si le LLM ne répond pas.
2. **Chaque catégorie a une réponse fixe**, en français et en wolof écrit par KBD (0009) ; la définition
   vient du socle (colonne `definition`), le « pourquoi » renvoie au chiffre lié (suggestion).
3. **Contrat 1.5.0** (additif) : `ReponseAucune.motif` gagne `conversation`. Le site l'affiche comme un
   message ordinaire, pas comme un refus. « Cette donnée n'existe pas » reste réservé aux vraies données
   absentes.
4. Pas de bavardage généré (option B écartée) : risque d'affirmation inventée et de wolof non validé.
   Une variante encadrée (français seul, deux phrases, aucun chiffre) pourra être étudiée plus tard.

## Conséquences

- Contrat 1.5.0, exemple `aucune_conversation.json` ; moteur : catégorie dans `SortieLLM`, textes fixes,
  repli par règles ; site : bulle de message et libellé « Conversation » au tableau de bord (SAN).

## Revue de SAN (07/10)

- **Politesse de tête retirée avant la compréhension** : « Bonjour, combien d'habitants à Thiès ? », « Merci.
  Et à Dakar ? » ; le LLM gardait parfois la politesse seule. Seules des formules fixes sont retirées (bonjour,
  salam, merci, naka nga def…) ; la réponse garde la question telle que posée.
- **« naka » + un mot** (règle de KBD) reste une salutation, sauf si un mot suivant est un sujet du vocabulaire
  ou un lieu : « Naka njëg ceeb », « Naka Kaolack ? » sont des questions (moteur et canaux).
- **« Pourquoi » sans chiffre vérifiable** : seulement la première phrase de KBD, sans « Voici le chiffre : ».
