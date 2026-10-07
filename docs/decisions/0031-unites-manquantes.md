# 0031 — Unités manquantes : le dire, préférer l'indicateur qui en a une, compléter les évidentes

**Date** : 2026-10-07 · **Statut** : accepté (KBD) · **Issue** : #132 (Aziz)

## Contexte

1 394 indicateurs sur 4 282 n'ont pas d'unité dans `indicateurs.csv` (8 P1 l'ont dans `unite_affichee`). La
cause est le portail lui-même : la colonne `Unit` des CSV est vide et les fiches n'ont pas de description.
L'unité ne se lit donc pas, elle se déduit, et la 0008 interdit toute réparation sans preuve. Exemple d'Aziz :
« Combien de ménages ont l'électricité ? » -> `ahjjzgc` « 70,3 », nombre nu.

## Décisions (choix de KBD)

1. **Le dire** : une réponse dont l'unité est vide porte « Unité non précisée par la source. » (notes des
   gabarits). Jamais un nombre nu présenté comme complet. Aziz affiche l'avertissement sur le site.
2. **Préférer** : la liste des candidats envoyée au LLM marque « (unité non précisée) », et la consigne
   ajoute, à sujet égal, de préférer l'indicateur dont l'unité est indiquée et la donnée la plus récente
   (`asongtc` 2023 en % plutôt qu'`ahjjzgc` 2019).
3. **Compléter les évidentes seulement** (146, liste validée par KBD), dans `unite_affichee` (colonne manuelle,
   conservée par l'inventaire) avec la preuve dans `note` (« unité déduite (#132) : … ») :
   - « % » (138) : le libellé le dit (« Pourcentage… », « (%) ») ET toutes les valeurs sont entre 0 et 100 ;
   - « pour 1 000 » (4) : TBM, TBN ; « pour 1 000 000 habitants » (4) : hôpitaux, centres de santé ;
   - `ahjjzgc` accès à l'électricité : même valeur qu'`asongtc` en % (Sénégal 2019 = 70,3).
   Écartés : 5 « % » dont les valeurs dépassent 100 (couvertures administratives), et tout le reste du tri
   d'Aziz (« part », « taux » sans %, effectifs, montants) : après le hackathon.

## Conséquences

- La consigne du LLM change : à revérifier par une passe réelle du benchmark (accord KBD, ~0,07 $).
- Reste 1 240 indicateurs sans unité, signalés à chaque réponse.
