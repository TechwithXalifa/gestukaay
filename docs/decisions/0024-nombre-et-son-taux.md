# 0024 — Un nombre accompagné de son taux

**Date** : 2026-10-04 · **Statut** : accepté (KBD) · **Issues** : #16, #21 · **Exigences** : 5.4, 12.1

## Contexte

La passe LLM du benchmark comptait WO-002 (« Ñi amul ligéey ci Senegaal ? ») comme un chiffre faux :
le moteur servait la population au chômage (1 590 818 personnes, 1er trimestre 2026), le jeu de
test attendait le taux annuel de 2025. KBD : en wolof, cette question (comme « Ñaata nit ñoo amul
ligeey ci Senegaal ? ») demande d'abord **combien de personnes** sont sans emploi ; la bonne réponse
donne le nombre, puis le taux pour le rendre parlant. Le moteur avait donc raison, l'attendu était
trop étroit.

## Décisions

1. **Paires déclarées et vérifiées à la main** (`socle/referentiels/indicateurs_compagnons.csv` :
   code, compagnon, phrase, preuve), jamais devinées. Départ : population au chômage → taux de
   chômage (`muhgux`, `puummg`), dans le même jeu.
2. **Même zone, même période, mêmes modalités**, sinon pas de taux : on ne mélange jamais deux
   périodes, rien n'est calculé.
3. Le taux est le **2e élément de `resultats`** (contrat inchangé) : il a sa source, il est vérifié
   par l'invariant, et la phrase le cite : « Le taux de chômage est de 22,9 % des personnes actives
   (celles qui travaillent ou cherchent un emploi). » Le taux se calcule **parmi les actifs**, pas
   sur toute la population : la phrase le dit (en wolof aussi, #25 : « téeméer boo jël… » doit
   préciser les actifs).
4. **Jeu de test** : WO-002 attend désormais la population au chômage (`muhgux`, 2026-T1), et
   FR-073 « Combien de personnes sont au chômage au Sénégal ? » est ajoutée (variante wolof : la
   phrase de KBD). L'exactitude porte sur le nombre demandé ; le compagnon reste soumis à l'invariant.

Gabarits naturels ajoutés pour la population au chômage et le taux trimestriel, dont la phrase
neutre reprenait le titre brut du portail ; libellé FR « Population au chômage » (référentiel).

## Conséquences

- En **règles locales**, WO-002 et FR-073 choisissent encore le taux annuel (`dwibrlf`) : les règles
  ne savent pas que « Ñi amul ligéey » ou « combien de personnes… au chômage » demandent un nombre.
  À traiter par le lexique bilingue (#23, mots wolof de KBD), pas par une règle ad hoc.
- `puummg` n'a pas de total pour l'âge (10 ans et plus, 15-35 ans, 15 ans et plus) : « Combien de
  chômeurs à Thiès ? » finit en refus. Défaut distinct, à traiter par `defauts_desagregation.csv`.
- Nom wolof de la population au chômage : à écrire (KBD).
