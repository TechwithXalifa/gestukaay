# 0008 — Contrôles et corrections du socle

**Date** : 2026-10-02 · **Statut** : accepté (KBD) · **Issue** : #6

## Contexte

L'extraction (0006) est fidèle au portail, erreurs comprises. Certaines sont connues (Thiès permuté
dans le tableau 1.1), d'autres sont apparues en #4-#6 : Kolda et Kédougou inversés dans `rnumqzf` de
2016 à 2022, Gini publiés à 0,0, doublons datés de l'an « 0016 », unités « prix constants de 1999 … de
2041 ».

## Décisions

1. **Exclure, jamais réparer.** Une valeur fausse part dans les rejets, avec le motif de sa correction.
   On ne réattribue jamais un chiffre à une autre zone : le moteur répond avec une autre source (RGPH-5)
   ou refuse. Seules les métadonnées évidentes se corrigent (unité affichée), jamais le nombre.
2. **Corrections à la main, contrôles en rapport.** `socle/referentiels/corrections.csv` déclare chaque
   correction (exclure ou unité affichée), avec son motif et sa **preuve**. Les contrôles automatiques
   (pourcentage hors 0-100, Gini hors ]0, 1[, date impossible, rupture ×3, population comparée au
   RGPH-5) **signalent seulement** : une vraie rupture ou un taux de pénétration mobile de 117 % sont
   justes.
3. **Doublons conflictuels : restent exclus** (règle de 0006), aucune règle « la plus grande valeur est
   la région ».
4. **Gini** : seules les valeurs à 0,0 sont exclues ; les autres sont servies avec la mention « arrondi
   au dixième par le portail ».

## Conséquences

- 7 corrections : 1 618 valeurs exclues (C01-C04), 129 unités affichées corrigées (C05-C07) ;
  644 827 valeurs servies ; les 216 valeurs attendues du jeu de test restent retrouvées.
- `socle/rapports/controles.md` liste ce qui reste signalé (6 049 ruptures, surtout de petits effectifs
  agricoles ; 2 467 « pourcentages » hors 0-100, dont des effectifs étiquetés « % » par le portail). Ils
  sont à examiner au fil de la vérification ; une nouvelle correction = une ligne de `corrections.csv`.
