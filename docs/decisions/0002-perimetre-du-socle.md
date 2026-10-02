# 0002 — Périmètre du socle V1 : sources, domaines, projections

**Date** : 2026-10-01 · **Statut** : accepté (KBD) · **Issue** : #1

## Contexte

Socle de référence : `socle_opendata_par_themes/` (collecte du 30/09/2026, hors Git). Il contient
376 jeux, 48 producteurs et 673 240 valeurs non vides. Les données sont identiques à la collecte
du 14/09.

Trois constats mesurés dans le socle :
- **L'ANSD domine sans tout couvrir.** Elle fournit 70 % des valeurs (158 jeux). La scolarisation
  par académie, utilisée par une question type du cahier (Ibrahima, Kolda), vient du MEN.
- **Les projections ne sont pas toujours signalées dans le titre.** Huit jeux le disent dans leur
  titre. Huit autres ne le disent que dans leur description : `rnumqzf` (1.1 population, 2023 = RGPH-5,
  2024-2025 = projections), `elwxsmc` (fécondité), `hydkglc` et `mwxxnab` (natalité, mortalité),
  `ervtjfc` et `vyadqbb` (scolarisation 2016-2022 recalculée), `uzptmtd`, `xmobtrb`. *(Révisé par 0007 :
  la scolarisation reste observée, seul son dénominateur est projeté.)*
- **Il y a deux sortes de projections, toutes deux publiées par l'ANSD** : des prévisions pour des
  années futures (jusqu'en 2038) et des estimations pour des années passées.

## Décisions

1. **Sources : tous les producteurs du portail.** Chaque réponse affiche le **producteur réel**
   (ANSD, MEN, MSAS, DAPSA, BCEAO…) dans son bloc source. Aucune valeur n'est présentée comme
   « ANSD » si elle vient d'un autre producteur.
2. **Domaines : le maximum de domaines couverts par le socle.** La règle « 6 domaines » du cahier
   (2.3) n'est pas retenue comme limite. La priorité de curation suit le jeu de test (#18) : d'abord
   les domaines des questions types du cahier (démographie, emploi, prix, éducation, conditions de
   vie et pauvreté, santé), puis les autres.
3. **Projections officielles : gardées et étiquetées.** Prévisions et estimations publiées par
   l'ANSD sont restituées, jamais recalculées. Elles sont toujours signalées comme
   « projection officielle ANSD », avec leur base (ex. projections démographiques 2023-2073).
   Une année absente du socle (ex. 2040) reste refusée. Gëstukaay ne produit **aucune** prévision
   propre : c'est l'exclusion visée par le cahier (2.4).

## Conséquences

- **Écarts au cahier à acter** : 2.3 (« 6 domaines »), 2.4 (projections) et annexe B. Le cas
  « Population du Sénégal en 2040 » reste un refus, puisque les séries s'arrêtent en 2038. Un cas
  « 2035 » devient une réponse exacte, étiquetée projection.
- **Contrat d'API** : le badge « projection » exige de savoir, valeur par valeur, si elle est
  observée, estimée ou projetée. Le contrat v1.0.0 n'a pas ce champ. **Évolution mineure à proposer
  à SAN** (champ optionnel sur `Resultat`, contrat v1.1.0), via une PR `contrat/…` approuvée par les deux.
- **Socle** : la nature de chaque valeur (observée, estimation, projection) est déterminée **par
  période**, pas par jeu, à partir des descriptions (#5, reformulée : « étiqueter » au lieu
  d'« exclure »).
- **Charge** : plus de producteurs et de domaines, donc plus de contrôles (#6). Le périmètre
  effectivement curé avant le 06/10 est fixé par le jeu de test.
