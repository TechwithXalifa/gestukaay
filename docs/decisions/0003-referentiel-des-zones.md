# 0003 — Référentiel des zones

**Date** : 2026-10-01 · **Statut** : accepté (KBD) · **Issue** : #2

## Contexte

Sur les 673 240 valeurs du socle, les codes région du portail (ISO 3166-2) sont fiables, mais pas
ses codes départementaux : Vélingara est rangé sous Matam et les suffixes sont incohérents.
331 000 valeurs n'ont aucun code : la zone n'apparaît que dans un libellé (« Dpt M'bour »,
« Kaolack »…), écrit de façons variées (« Malem Hoddar », « ARD. KOUMBAL », « COOMUNE »…).
Les données d'éducation sont ventilées par **inspection d'académie**, qui ne correspond pas
toujours à une zone administrative. Par exemple, l'IA Pikine-Guédiawaye couvre trois départements.

## Décisions

1. **Niveaux** : pays, 14 régions, 46 départements. Pas de communes ni d'arrondissements en V1.
2. **Codes** : ISO 3166-2 pour les régions ; codes lisibles Gëstukaay `SN-<région>-<NOM>`
   pour les départements. Les libellés du portail sont rattachés **par leur nom**.
3. **Wolof** : libellés en brouillon, marqués « à valider » par les locuteurs (#26).
4. **Homonymes** : un nom seul désigne la **région**. Le département n'est retenu que si le contexte
   l'indique (préfixe « Dpt », colonne « département »).
5. **Académies** : niveau de zone à part (16 académies `SN-IA-…`), jamais choisi par défaut.
   Chacune indique les zones administratives qu'elle recouvre : 13 = leur région ; IA Dakar =
   département de Dakar ; IA Rufisque = département de Rufisque ; IA Pikine-Guédiawaye = Pikine +
   Guédiawaye + Keur Massar. Une réponse dit « académie de Kolda », jamais « région de Kolda ».

## Résultat (rapport `socle/rapports/couverture_zones.md`)

325 977 valeurs à libellé géographique : 95,46 % rattachées. Le reste est **écarté explicitement**,
avec sa raison : infra-départemental (14 297), regroupements non administratifs ou historiques
(345), totaux ambigus (163). **0 valeur non rattachée.**

## Conséquences

- **Contrat d'API** : `RefZone.niveau` n'accepte pas « academie ». Il faut l'ajouter dans la même
  évolution mineure v1.1.0 que le champ « nature » (décision 0002), à faire approuver par SAN.
- **Moteur** : « scolarisation à Dakar » (région) n'a pas de valeur régionale. Le moteur fera une
  correspondance approchée qui propose les 3 académies de la région (#12).
- **Valeurs historiques** : une valeur publiée pour Pikine avant 2021, date de création de Keur
  Massar, reste telle quelle, sans recalcul (engagement 02).
- **Portail** : le portail utilise le code `SN-KG` pour Kédougou dans un jeu (56 valeurs). Le code
  ISO correct est `SN-KE` ; c'est le nôtre.
