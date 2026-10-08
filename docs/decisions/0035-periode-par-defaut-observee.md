# 0035 — Période par défaut : la dernière valeur observée, jamais une projection future

**Date** : 2026-10-08 · **Statut** : accepté (KBD) · **Issue** : #116 · **Complète** : 0002, 0007

## Contexte

Sans année dans la question, le moteur servait la période la plus récente de la série, quelle que soit sa
nature. « Quelle est l'espérance de vie ? » et « Combien de naissances ? » répondaient donc 2035 (projection
RGPHAE 2013) en disant « dernière donnée publiée » (signalé deux fois par SAN). Dans le socle 2026.10.0,
80 séries (indicateur × zone) finissent par une projection après des valeurs observées, et environ 450 n'ont
que des projections ou des estimations (`pexioke`, `wpwbyw`, `mddqcg`…).

## Décision (choix de KBD)

- Sans année demandée : la **dernière période observée** de la série, annoncée « dernière donnée publiée ».
- Série sans aucune valeur observée : **l'année en cours** (2026), sinon la plus récente avant ; jamais une
  année future. Elle n'est annoncée « dernière donnée publiée » que si c'est bien la dernière de la série
  (estimation qui s'arrête en 2025) ; la mention « il s'agit d'une projection officielle (base) » reste.
- Une année demandée (« en 2035 ») est servie telle quelle (FR-027 inchangé).
- Même règle pour les repères de « Où je me situe ».

## Conséquences

- `periode_par_defaut` vaut `false` pour une projection servie pour l'année en cours : le site et les
  exports n'affichent plus « dernière donnée publiée » dans ce cas. Aucun texte wolof nouveau.
- Reste ouvert : le choix de l'indicateur. En règles, « indice synthétique de fécondité » prend encore un
  jeu de projection (`mddqcg`, 2026) plutôt que l'observé `elwxsmc` (2023).
