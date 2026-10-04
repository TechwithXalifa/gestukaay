# 0022 — « Où je me situe » : calcul réel dans le moteur

**Date** : 2026-10-04 · **Statut** : accepté (KBD) · **Issue** : #95 · **Exigences** : EF-37 à EF-40, US-20, US-21 ; décisions 0004 §2 et 0012

## Contexte

Seul le faux moteur répondait à `/v1/situate`, avec les chiffres fixes de Kolda quelle que soit la
saisie. Le contrat 1.3.0 (#99) fixe les tranches de dépenses et la forme de la réponse ; la 0004 §2
fixe la méthode (comparaison aux moyennes publiées), la 0012 la règle des tranches ouvertes.

## Décisions

1. **Calcul sur les seules données saisies** : tranche mensuelle × 12 / taille du ménage, arrondi à
   l'unité ; tranche ouverte (`plus_1m`, `plus_500k` dépréciée) sans maximum.
2. **Moyennes** : consommation moyenne par tête (`jcvcajc.total`), dernière période publiée, milieu
   « Ensemble » : on ne demande pas ville ou campagne, et ajouter la question changerait le parcours.
3. **Position** : règle du contrat ; une tranche ouverte n'est `au_dessus` que si sa borne basse
   dépasse la moyenne, sinon `autour` (0012).
4. **Repères**, chacun lu dans le socle, jamais calculé :
   - pauvreté des ménages de même taille (`jcvcajc.taux-de-pauvrete`, national : pas publié par
     région). Le portail publie 1-4, 5-9, 10-14, 15-19 et « 22 personnes ou plus » : **aucun repère
     pour 20 ou 21 personnes** (le chiffre d'un autre groupe serait faux) ;
   - part de la région dans le quintile de bien-être le plus bas (`qjyrtof.le-plus-bas`) ;
   - ménages éclairés à l'électricité dans la région (`asongtc`).
   **L'accès à l'eau, cité par la 0004, est omis** : il n'est publié qu'au niveau national
   (`ahjjzgc`, 2019), et un chiffre national parmi des repères régionaux induirait en erreur.
   Libellés affichés : ceux de l'exemple du contrat, plus clairs que ceux du référentiel ; le groupe de
   taille est dans le libellé, car le site n'affiche pas la désagrégation des repères.
5. **Explication** (FR seulement, 0009) : le texte de `contracts/examples/situer.json`, reproduit à
   l'identique pour Kolda ; « au moins X » pour une tranche ouverte, « moins de X » pour la plus basse ;
   positions différentes pour la région et le pays : « c'est moins que celle de …, et autour de celle
   du Sénégal ».
6. **Saisie invalide** (région inconnue, département, pays) : `SaisieInvalide`, exportée par
   `gestukaay_engine`. Niveau d'instruction : accepté, ignoré (aucune donnée publiée ne le croise).

## Conséquences

- `MoteurReel.situer` répond ; l'exemple du contrat est reproduit à l'identique sur le socle 2026.10.0
  (seule différence : « 63 » au lieu de « 63,0 », règle d'affichage du moteur).
- **SAN** : rendre `SaisieInvalide` en **422** (aujourd'hui 500 ; le site ne propose que les 14 régions).
- Le seuil de pauvreté officiel (`ahjjzgc.seuil-de-pauvrete`, 2018) reste pour #59 (V1.1).
