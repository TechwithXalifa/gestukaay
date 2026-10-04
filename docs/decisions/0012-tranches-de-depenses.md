# 0012 · « Où je me situe » : tranches de dépenses au-delà de 500 000 FCFA

**Date** : 2026-10-02 · **Statut** : accepté (SAN, KBD le 03/10) · **Complète** : 0004 §2
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

4. **Tranche ouverte `plus_1m`** (ajout de KBD) : le problème revient pour les très grands ménages
   (≈ 20 personnes à Dakar). Règle : si la borne basse par personne (`12 000 000 / taille`) dépasse la
   moyenne, la position est `au_dessus` ; sinon `autour`, et l'explication dit « au moins X FCFA par
   personne » au lieu d'une fourchette.

## Conséquences

- **Contrat v1.3.0, additif** (révisé le 03/10, #91) : supprimer `plus_500k` serait un changement
  **majeur** au sens de `contrat-v1.md` §6, à éviter pendant le hackathon ; la première version de
  cette décision l'avait mal étiqueté. On retient donc l'option B : la v1.3.0 **ajoute** `500k_750k`,
  `750k_1m` et `plus_1m`, et garde `plus_500k` accepté mais plus proposé par le site. La période
  « entre A et B » est partie seule dans la v1.2.0.
- **`plus_500k` encore reçue** : même règle que `plus_1m`, avec une borne basse par personne de
  `500 000 × 12 / taille` (au-dessus si elle dépasse la moyenne, sinon autour avec « au moins X FCFA
  par personne »).
- **Web** (`TRANCHES`, libellés FR) : mis à jour avec le contrat 1.3.0. **Moteur** (`situer`, #95) :
  KBD, après la fusion de la 1.3.0.
- **Tests** : « Dakar, 7 personnes, `plus_1m` » -> `au_dessus` ; « Dakar, 25 personnes, `plus_1m` » ->
  `autour`, avec « au moins » dans l'explication.
- **Point resté ouvert, hors de cette décision** : les exemples affichent « CC BY 4.0 », alors que le
  champ licence est vide sur les 376 jeux du portail (contrat-v1 §6).
