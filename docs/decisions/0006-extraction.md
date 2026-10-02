# 0006 — Extraction du socle : format, zones, échelle

**Date** : 2026-10-02 · **Statut** : accepté (KBD) ; format de chargement à confirmer avec SAN en #8 ·
**Issue** : #4

## Contexte

Le référentiel (0005) dit *quoi* servir ; il faut une table au schéma du cahier (10.3) qui dise *quelle
valeur* pour chaque indicateur, zone, période et désagrégation, et d'où elle vient.

## Décisions

1. **Format : CSV hors Git** (`../socle_gestukaay/`, UTF-8, `;`) : `observations.csv`, `sources.csv`,
   `rejets.csv`. Neutre : SAN le charge dans PostgreSQL (COPY), le moteur le lit directement. Le
   chargement définitif et le versionnage se décident en #8.
2. **« Total » / « Ensemble » dans une colonne géographique = Sénégal** seulement si la colonne couvre
   les 14 régions ; sinon rejeté (total ambigu). Aucun recalcul.
3. **Jeu sans colonne géographique** : code région du portail s'il existe, sinon exception déclarée
   (`zones_par_jeu.csv`, ex. `feujxob` = Dakar), sinon **Sénégal, marqué `zone_presumee`**.
4. **Extraction fidèle, corrections en #6** : rien n'est corrigé ici. Deux valeurs différentes pour la
   même clé (indicateur, zone, période, désagrégation) sont toutes deux rejetées (« doublon
   conflictuel ») plutôt que choisies au hasard.

**Constat (pas un choix)** : `echelle` n'est pas un multiplicateur. Les valeurs sont déjà en unités
pleines (`cimkorc` : 4 023 500 000 000 FCFA, échelle 10⁹ = « affiché en milliards »).

## Conséquences

- 646 445 valeurs extraites, 25 141 rejetées et tracées ; les 216 valeurs attendues du jeu de test sont
  retrouvées à l'identique (`socle/rapports/extraction.md`).
- **#6** traite les 10 451 doublons conflictuels (région / département homonymes ; séries publiées en
  double : `amkfcsb`, `cimkorc`, `ykwfqkb`…) et les erreurs connues (Thiès dans `rnumqzf`).
- **Vérification** : 225 jeux ont une zone présumée, dont 7 du jeu de test (`tsghpfc` IHPC,
  `muhgux` salaires…) : à confirmer, ou à déclarer dans `zones_par_jeu.csv`.
