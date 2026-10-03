# 0012 · « Où je me situe » : tranches de dépenses au-delà de 500 000 FCFA

**Date** : 2026-10-02 · **Statut** : proposé par SAN, **à valider par KBD** · **Complète** : 0004 §2
· **Touche** : contrat (`TrancheDepense`), donc PR `contrat/…` approuvée par les deux

## Contexte

La décision 0004 §2 compare la dépense annuelle par personne du ménage, calculée sur les seules
données saisies (`dépenses × 12 / taille`), à la consommation moyenne par tête publiée (`jcvcajc`).
La position renvoyée est `au_dessus` ou `en_dessous` quand tout l'intervalle est d'un côté de la
moyenne, sinon `autour`.

Vérification sur le socle (collecte du 30/09, valeurs 2022) : tous les chiffres de
`contracts/examples/situer.json` sont exacts (Kolda 387 934, Sénégal 542 706, pauvreté des ménages
de 5 à 9 personnes 24,2 %, Kolda dans le quintile le plus bas 63,0 %, électricité à Kolda 39,6 %).

**Le problème vient de la dernière tranche, « plus de 500 000 FCFA par mois », qui est ouverte.**
Sa borne basse par personne vaut `6 000 000 / taille`. Dès que cette borne passe sous la moyenne,
l'intervalle contient la moyenne et la réponse est `autour`, quelle que soit la dépense réelle :

| Région | Moyenne 2022 (FCFA/pers./an) | Réponse forcément `autour` dès |
|---|---|---|
| Dakar | 861 364 | 7 personnes |
| Thiès | 540 343 | 12 personnes |
| Sénégal | 542 706 | 12 personnes |

À Dakar, un ménage de 7 personnes qui dépense 1,5 million par mois reçoit « autour de la moyenne ».
C'est faux, et c'est la région où le module sera le plus utilisé.

## Décision

1. **Remplacer la tranche ouverte par trois tranches** dans `TrancheDepense` :
   `500k_750k`, `750k_1m`, `plus_1m`. Avec une borne ouverte à 1 000 000, la réponse ne devient
   `autour` par construction qu'à partir de 14 personnes à Dakar et de 23 personnes au niveau national.
2. **Huit tranches au total**, ce qui tient dans une liste WhatsApp (10 lignes au maximum) pour
   EF-41. Libellés de ligne ≤ 24 caractères : « 500 000 à 750 000 », « Plus de 1 000 000 ».
3. **Pas d'autre changement de méthode.** Le niveau d'instruction reste hors de l'interface (déjà le
   cas dans `web/app/situer/page.tsx`) tant qu'aucune donnée publiée ne le croise.

## Conséquences

- **Contrat** : supprimer `plus_500k` est un changement **majeur** au sens de `contrat-v1.md` §5.
  Aucune version n'étant en production, on propose de le faire maintenant, en v1.2.0, plutôt que de
  traîner une tranche fausse pendant le hackathon. À défaut, ajouter les trois tranches et conserver
  `plus_500k` comme alias déprécié (mineur, v1.1.2).
- **Moteur** (`situer`) et **web** (`TRANCHES`, libellés FR/WO) à mettre à jour dans la même PR.
- **Tests** : ajouter un cas « Dakar, 7 personnes, `plus_1m` » qui doit renvoyer `au_dessus`.
- **Point resté ouvert, hors de cette décision** : les exemples affichent « CC BY 4.0 », alors que le
  champ licence est vide sur les 376 jeux du portail (contrat-v1 §6).
