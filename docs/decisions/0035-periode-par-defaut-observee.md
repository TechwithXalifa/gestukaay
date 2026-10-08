# 0035 — Période par défaut : jamais une année future

**Date** : 2026-10-08 · **Statut** : accepté (KBD) · **Issue** : #116 · **Complète** : 0002, 0007

## Contexte

Sans année dans la question, le moteur servait la période la plus récente de la série, quelle que soit sa
nature. « Quelle est l'espérance de vie ? » et « Combien de naissances ? » répondaient donc 2035 (projection
RGPHAE 2013) en disant « dernière donnée publiée » (signalé deux fois par SAN). Dans le socle 2026.10.0,
80 séries (indicateur × zone) finissent par une projection après des valeurs observées, et environ 450 n'ont
que des projections ou des estimations (`pexioke`, `wpwbyw`, `mddqcg`…).

## Décision (choix de KBD)

- Sans année demandée : la **dernière période jusqu'à l'année en cours** (2026), quelle que soit sa nature ;
  **jamais une année future**. Une projection pour une année passée ou en cours est le chiffre que l'ANSD
  publie elle-même (ISF 2025 des Projections 2023-2073) : elle est servie avec son badge.
- « Dernière donnée publiée » : si c'est la fin de la série, ou une valeur observée suivie seulement de
  projections futures. Une projection servie pour 2026 alors que la série va jusqu'en 2035 ne l'est pas ; la
  mention « il s'agit d'une projection officielle (base) » reste.
- Série qui ne commence qu'après l'année en cours : sa première période.
- Une année demandée (« en 2035 ») est servie telle quelle (FR-027 inchangé).
- Même règle pour les repères de « Où je me situe ».

## Conséquences

- `periode_par_defaut` vaut `false` pour une projection servie pour l'année en cours : le site et les
  exports n'affichent plus « dernière donnée publiée » dans ce cas. Aucun texte wolof nouveau.
- Reste ouvert : le choix de l'indicateur. En règles, « indice synthétique de fécondité » prend encore un
  jeu de projection (`mddqcg`, 2026) plutôt que l'observé `elwxsmc` (2023).

## Révision du 08/10 (KBD)

La première version (#151) prenait la dernière valeur **observée**. Elle faisait régresser FR-009 (ISF :
4,0 de l'EDS 2023 au lieu de 4,2, projection 2025 attendue), benchmark en règles 76 -> 75/84, chiffres faux
5 -> 6. Le défaut signalé par SAN était une projection dans le futur : la règle ne retire plus que le futur.
Benchmark en règles revenu à 76/84, 5 chiffres faux.
