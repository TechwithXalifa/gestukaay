# 0030 — Retours de la recette du moteur : approchées, voitures, refus sans lien

**Date** : 2026-10-06 · **Statut** : accepté (KBD) · **Issue** : #116 · **Modifie** : 0015, 0017

## Contexte

La recette d'Aziz (#116, vrai moteur, chaîne Gemini 2.5 Flash) donne 93/103 conformes, mais 5 approchées
sur 11 finissent en refus « Cette donnée n'existe pas… », alors que la donnée voisine existe :

- **Touba, ville de Kaolack, ville de Thiès** : la population (`pvswjnd`, RGPH-5) n'est publiée que pour le
  Sénégal et les régions, en 2023. Le département déclaré dans `rattachements.csv` ne se vérifie pas, il
  reste un seul choix, et le repli (c) de la 0015 bascule en refus.
- **Voitures** : le LLM range « voitures » dans la désagrégation (`produit = voitures`). Les choix TOTAL et
  VPP gardaient ce filtre, aucun ne se vérifiait. En règles, le moteur servait directement le parc total.

Aziz signale aussi que, sans indicateur lié (« sérère »), le refus présente les 3 indicateurs phares
comme « proches ».

## Décisions (choix de KBD)

1. **Lieu rattaché : niveaux au-dessus après les zones déclarées.** On applique le repli (a) de la 0015
   aux lieux de `rattachements.csv` : après les propositions déclarées, la chaîne des parents
   (région, puis Sénégal), chaque choix vérifié. Touba donne « Région de Diourbel » et « Sénégal ». La
   population par département du Tableau 1.1 (`rnumqzf`, projection de 2013) n'est **pas** utilisée.
2. **« Voitures » : toujours une approchée**, même quand le parc total existe : « voitures » n'est pas le
   parc total (camions, motos…). Sauf si la catégorie est déjà précisée (« véhicules particuliers »).
   Le terme ambigu lui-même est retiré de la désagrégation avant de proposer TOTAL et VPP.
3. **Refus sans indicateur lié** : les phares gardés, sous « Les chiffres les plus demandés : » au lieu
   de « Voici des indicateurs proches : ». Le titre « proches » reste quand au moins une suggestion vient
   des candidats proches de la question.
4. **Aucun chiffre hors années dans une approchée** (EF-06, volet (d) de l'invariant) : dans les libellés
   des choix, « RGPH-5 » s'écrit « recensement de 2023 ». Forme écrite pour ce seul sigle, sans règle
   générale ; l'outil de mesure n'est pas modifié.
5. « ville de Thiès » est cité avec l'article : « pour la ville de Thiès ».

## Hors de cette décision

- Riz (FR-018 production, WO-021 prix à Kaolack) : le moteur choisit `feujxob` (relevés à Dakar). À
  traiter dans la compréhension.
- WO-009 : « nappkat yu ndaw yi » = « les jeunes pêcheurs » (KBD), pas la pêche artisanale ; l'approchée
  obtenue n'est pas une erreur du moteur.
- WO-002 : le nombre de chômeurs est l'attendu depuis la 0024.

## Conséquences

- `approchee.py` (`modalite_citee`, parents des lieux rattachés, `SIGLES_SANS_CHIFFRE`), `moteur.py`
  (approchée d'emblée pour une modalité ambiguë), `refus.py` (`MESSAGE_HORS_SOCLE_PHARES`).
- Benchmark en règles : exactitude 68/84 → 72/84, chiffres faux 10 → 8, invariant 0.
