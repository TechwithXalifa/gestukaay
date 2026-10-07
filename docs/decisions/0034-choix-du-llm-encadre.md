# 0034 — Choix du LLM encadré : doublons et précisions inventées

**Date** : 2026-10-07 · **Statut** : accepté (KBD) · **Issue** : #21 · **Complète** : 0010, 0011, 0031

## Contexte

Passe Gemini du 07/10 (benchmark complet) : 4 chiffres faux, dont 2 nouveaux, et 2 refus à tort. Le LLM
choisit bien un candidat pertinent, mais :
- parfois un **doublon** moins bon : la projection de 2013 (`uzptmtd`, 412 932) au lieu du recensement
  RGPH-5 (`pvswjnd`, 403 522) pour les femmes de Matam ; un jeu arrêté en 2023 (`qqjyoh`) au lieu de 2025
  (`ervtjfc`). Les bons étaient en tête de liste et marqués vérifiés ; le 4/10, le LLM les avait pris ;
- parfois une **précision absente de la question** (« femmes » sur la vaccination des enfants, « âge 0-5 »
  sur la mortalité des moins de 5 ans), que la résolution stricte refuse.

## Décisions (choix de KBD)

- **A1 (consigne)** : la liste des candidats marque les jeux de projection (natures.csv) ; la consigne
  préfère une valeur observée à une projection pour une année passée ou la dernière donnée. « La plus
  récente » (0031) est retiré : il poussait vers les jeux de projection, qui vont plus loin dans le temps.
- **A2 (garde-fou déterministe)** : si le LLM choisit un indicateur non vérifié alors que le premier
  candidat est vérifié, du même domaine, et couvre la zone et l'année demandées, on prend le vérifié.
- **B** : une précision du LLM que les règles retrouvent dans la question prend leur forme (vocabulaire
  validé) ; une précision qu'elles ne trouvent pas et que le jeu ne publie pas du tout est retirée, au lieu
  d'un refus. Citée par l'utilisateur, elle reste stricte (0011).

## Conséquences

- Jeu de test (changements.csv) : FR-059, FR-060, FR-063, WO-025, WO-026 attendent `conversation` (0033) ;
  FR-051 attend région de Diourbel ou Sénégal (0030). Cinq vrais refus « donnée absente » à ajouter (KBD).
- À confirmer par une nouvelle passe Gemini.

## Revue de SAN (07/10)

- Hors sujet par règles resserré : plus « recette », « foot », « match » ni « président » seuls (« recette
  touristique », « terrains de foot » sont des questions de chiffre) ; et une règle de conversation ne
  contredit plus le LLM quand il a trouvé un indicateur.
- B repère la dimension absente par un champ de la résolution (`Introuvable.dimension_absente`), plus par le
  texte du message.
- A2 : sans année demandée, un choix observé qui va plus loin dans le temps n'est pas remplacé par un vérifié
  plus ancien ; une projection l'est toujours (RGPH-5 2023 plutôt que la projection de 2013).
