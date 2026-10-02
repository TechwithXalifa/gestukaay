# 0007 — Nature de chaque valeur : observée, estimation, projection

**Date** : 2026-10-02 · **Statut** : accepté (KBD) · **Issue** : #5 · **Complète** : 0002 (décision 3)

## Contexte

0002 garde les projections officielles et les étiquette. Le contrat porte `Resultat.nature` et
`base_projection`. Il faut savoir, valeur par valeur, laquelle est observée. Le portail ne le dit pas :
seuls les titres et les descriptions des jeux le disent, et parfois rien.

## Décisions

1. **Référentiel `socle/referentiels/natures.csv`** : nature par jeu et par période, avec la base de
   projection et la **preuve** (citation de la description ou du titre). L'extraction applique, dans
   l'ordre : la règle déclarée ; sinon **projection** si l'année est postérieure à la dernière mise à
   jour du jeu (une valeur 2035 publiée en 2022 ne peut pas être observée) ; sinon **observée**.
2. **`pexioke` (espérance de vie) et `mddqcg`** (2013-2035, sans description) : toute la série est une
   projection RGPHAE 2013, comme `bkcoat`, `phfdqm`, `wpwbyw`, publiés le même jour sur la même plage.
3. **Taux rapportés à une population projetée = observés** (scolarisation `ervtjfc`, `vyadqbb`,
   criminalité, téléphonie) : les effectifs sont comptés, seul le dénominateur est projeté. **Corrige
   0002**, qui comptait la scolarisation parmi les projections cachées.
4. **`xmobtrb` (Cadre Harmonisé) = estimation** : situation « courante et projetée » sans dire laquelle
   est publiée.

## Conséquences

- 551 760 valeurs observées, 1 388 estimations, 93 297 projections (`socle/rapports/extraction.md`).
- Jeu de test : FR-009 (fécondité 2025) et FR-027 (espérance de vie 2035) sont des projections. La
  réponse est exacte, avec le badge « projection » et sa base.
- **Moteur (#11)** : `uzptmtd` donne la population 2023 **projetée en 2013**, alors que le RGPH-5
  (`pvswjnd`) l'observe. Quand une valeur observée existe pour la même question, le moteur la préfère.
- `mwxxnab` 2022 : base 2013-2063 supposée (la description ne cite que 2016-2021).
