# 0005 — Indicateurs V1 : unité de compte, périmètre, domaines

**Date** : 2026-10-02 · **Statut** : accepté (KBD) ; liste des domaines à partager avec SAN · **Issue** : #3

## Contexte

Le cahier vise « 200+ indicateurs, 6 domaines » (2.3) et un modèle `indicateur` avec code, libellés
FR/WO, unité et domaine (10.3). Dans le socle, **un jeu du portail n'est pas un indicateur** : 225 jeux
sur 376 ont une dimension « Indicateur » qui en regroupe plusieurs, souvent avec des unités différentes
(`jcvcajc` : taux de pauvreté, profondeur, sévérité…). 261 couples (jeu, indicateur) sont publiés en
plusieurs unités (comptes nationaux en prix courants et constants, captures en tonnes et en FCFA).

## Décisions

1. **Un indicateur = jeu × valeur de la dimension « Indicateur » × unité.** Les autres dimensions sont
   des désagrégations. Un jeu sans dimension « Indicateur » compte pour un indicateur par unité. Les
   graphies d'une même valeur (« Effectif » / « effectif ») sont fusionnées.
2. **Tout le socle entre dans le référentiel** (4 149 indicateurs), pas une sélection de 200. La colonne
   `verification` dit ce qui a été contrôlé à la main, par priorité : **P1** jeu de test (26), **P2**
   domaines des questions types du cahier (1 272), **P3** le reste.
3. **Noms wolof des indicateurs : écrits par KBD, pour les prioritaires** (P1 d'abord). Aucun nom wolof
   n'est généré. Sans nom wolof, une réponse en wolof cite le nom français.
4. **Domaines : tous ceux du socle, doublons du portail fusionnés** (38 thèmes → 32 domaines,
   `socle/referentiels/domaines.csv`). La limite « 6 domaines » n'est pas retenue (suite de 0002).

## Conséquences

- **Écarts au cahier** :
  - 2.3 parle de 200+ indicateurs « curés » ; ici tout est servi, mais seuls les indicateurs `verifie`
    sont garantis relus. Le benchmark (#19) ne porte que sur des P1 ;
  - 12.1 prévoit 100 questions, 70 FR / 30 WO : le jeu en compte **103, 72 FR / 31 WO** (voir plus bas) ;
  - §5 et annexe : « Nombre de voitures à Kolda » n'est plus l'exemple de refus (voir plus bas).
- **#4 (extraction)** filtre le socle brut par `dataset_id` + `dimension_indicateur` /
  `valeur_portail` + unité. Deux points y restent à régler : le sens de la colonne `echelle`
  (189 indicateurs à 10⁶ ou 10⁹) et l'unité « prix constants de 1999… 2041 » incrémentée à tort dans
  `uipcgjd`, `fsrvlqe`, `chnqiuf`.
- **Web (SAN)** : 32 domaines au lieu de 6 pour la navigation de l'accueil ; les 6 domaines des
  questions types (`questions_types = oui`) peuvent rester en tête.
- **Jeu de test** : les questions approchées indiquent désormais l'indicateur à proposer
  (`dataset_id`, `filtres`).
- **Jeu de test (103 questions)** : « Nombre de voitures à Kolda », exemple de refus du cahier (§5,
  annexe), devient une question **approchée** : le parc de véhicules par région existe (`qbvttzc`, DTT).
  Idem pour Ziguinchor (WO-024) et la criminalité (FR-067, nationale seulement). Trois refus ajoutés
  pour garder 20 refus ; l'exemple de refus de la démo devient FR-071 (langues parlées).

## Révision du 2026-10-02 (relecture de SAN, #56)

- **Dimension de mesure** : « Quota », « Mesure », « Unités » portent aussi l'indicateur, seules ou avec
  « Indicateur ». Sans cela, `ovothxc` (P1) mélangeait production, rendement et superficie, et une dizaine
  de jeux de comptes nationaux mélangeaient prix courants et volume, faute d'unité sur le portail.
  4 282 indicateurs (au lieu de 4 149) ; 307 codes changent, dont deux P1 (`wrqfsxb.quantite`,
  `ovothxc.production`), repris à la main.
- **`unite_affichee`** : colonne manuelle, unité montrée au public. `unite` reste celle du portail, qui
  fait partie de l'identité ; on ne la modifie jamais.
- **Libellés** : les doublons générés sont départagés par le nom du jeu, puis l'unité, puis la période
  (440 libellés partagés → 1).
- **P1 vérifiés : 24 sur 26.** Vérifié = libellé FR et nom wolof écrits, unité affichable, zone confirmée
  (description du jeu), valeurs du jeu de test retrouvées. Restent `a_verifier`, avec leur raison dans
  `note` : `qjyrtof.gini` (portail arrondi à 0,1 : 118 valeurs sur 187 à 0,0, à exclure en #6) et
  `ovothxc.production` (unité « tonnes » déduite de l'ordre de grandeur).

## Fiches (#7, 2026-10-02)

- Fiche d'un indicateur = référentiel + fiche de son jeu (`jeux.csv`, découpée dans la description du
  portail). Définition propre à un indicateur : **citée mot pour mot du portail, jamais rédigée**.
- 17 des 26 P1 ont une définition publiée ; 9 n'en ont aucune sur le portail (taux brut de
  scolarisation, prix du mil et du riz, salaire moyen, production de céréales, espérance de vie, Gini,
  taux d'urbanisation, captures) : la fiche le dit, sans combler le vide.
