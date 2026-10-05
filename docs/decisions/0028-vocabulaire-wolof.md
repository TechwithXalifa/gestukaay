# 0028 — Vocabulaire wolof : lieux, mots, marqueurs

**Date** : 2026-10-05 · **Statut** : accepté (KBD) · **Issues** : #22, #23 · **Exigences** : 7.4 ; décisions 0009, 0026

## Contexte

Sur 62 notes vocales réelles, M-Kiriku transcrit bien le wolof, mais en orthographe standard
(« seajo », « maatam », « kawlak », « ceeb ») que le moteur ne connaissait pas : « ñaata jigéen ñoo
dëkk seajo » répondait « cette donnée n'existe pas ». KBD a validé les fiches de travail préparées
à partir de ces transcriptions (hors Git : `../lexique_wolof/`).

## Décisions

1. **Lieux** (`socle/referentiels/zones.csv`) : noms wolof corrigés (Kédugu, Tambakunda, Géejawaay,
   Tiwaawan) et variantes ajoutées (Njaaréem pour Diourbel, Njaambuur pour Louga, kawlak, kaolag,
   seajo, seju, maatam, dakaar, kees…) ; les anciennes graphies restent reconnues ; `statut_wo =
   valide` pour les lignes relues par KBD (0009).
2. **Lieux hors référentiel** (`rattachements.csv`) : Tuubaa, Richard-Toll / Risaar Tol, ville de
   Kolda. Un lieu déclaré est reconnu **où qu'il soit dans la question**, sans préposition française :
   « Ñaata nit ñoo dëkk Tuubaa ? » répondait le chiffre du Sénégal entier.
3. **Mots** (`engine/…/candidats.py`, `SYNONYMES`) : ndóol, tolluwaay, mbëj, kuraŋ, njàng, dee, ndaw,
   góor, tëj, nàpp, ndab… **« ñakk » (vaccin) et « ñàkk » (manquer, pauvreté)** deviennent tous deux
   « nakk » une fois les accents retirés (le moteur les retire pour tolérer les fautes de frappe) :
   les deux notions sont proposées, le reste de la phrase tranche.
4. **Marqueurs** : classement « moo ëpp » / « moo gëna néew, tuuti » (le moins, sens croissant),
   « ban diiwaan / diwaan » ; évolution « yokku », « wàññiku », « suufe », « diggante » ; temps
   « ren », « daaw », « daawat ».

## Conséquences

- Mesure, M-Kiriku sur les 62 notes, compréhension par règles : 32/62 -> 34/62 (85 % du plafond au
  lieu de 76 %) ; benchmark du jeu de test inchangé (aucune régression).
- Limite connue des règles : « ñaata nit ñoo dëkk … » choisit le taux d'urbanisation plutôt que la
  population (le LLM choisit bien).
- À proposer : un glossaire wolof dans la consigne du LLM (Njaaréem = Diourbel, ñakk / ñàkk, ren /
  daaw…), à mesurer par une passe payante.
