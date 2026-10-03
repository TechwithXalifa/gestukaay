# Extraction du socle

Socle brut : `socle_opendata_par_themes/observations.csv` · sortie : `socle_gestukaay/` (hors Git) · schéma du cahier 10.3 (décision #4).

## Résumé

| | Valeurs |
|---|---|
| Valeurs non vides lues | 673240 |
| → extraites | 644827 |
| → doublons identiques fusionnés | 1654 |
| → rejetées (voir `rejets.csv`) | 26759 |
| Indicateurs représentés | 4247 |
| Zones : pays / régions / départements / académies | 334315 / 247797 / 25506 / 37209 |
| Zone présumée (jeu sans colonne géographique → Sénégal) | 274329 valeurs, 218 jeux |

## Contrôle de bout en bout : jeu de test

218 valeurs attendues (questions exactes) cherchées dans la table extraite : **218 trouvées à l'identique**, 0 échec(s).

Réponses attendues qui ne sont pas des valeurs observées (le badge doit s'afficher) :

- FR-009 SN@2025 : projection (Projections démographiques 2023-2073)
- FR-027 SN@2035 : projection (Projections démographiques RGPHAE 2013)

## Nature des valeurs (#5, décision 0007)

| Nature | Valeurs | Jeux |
|---|---|---|
| observee | 550184 | 361 |
| estimation | 1346 | 3 |
| projection | 93297 | 15 |

Projections repérées par la règle automatique (année postérieure à la dernière mise à jour du jeu), sans base déclarée dans `natures.csv` : aucune.

## Rejets par motif

| Motif | Valeurs | Jeux | Exemples |
|---|---|---|---|
| infra | 14297 | 2 | infra : ARD MBADAKHOUNE, infra : ARD NGUELOU, infra : ARD. KOUMBAL |
| doublon conflictuel | 10451 | 20 | SN 1980 : 19.6132776013803 / 4.7067671255767, SN 1980 : 24.7587639167721 / 4.71790090867977, SN 1980 : 73.1083585755478  |
| correction C03 | 1440 | 1 | Doublons des séries annuelles 2016-2018 datés « 0016 », « 0017 », « 0018 » (fréquence D) |
| non_admin | 345 | 5 | non_admin : Centre, non_admin : Diourbel et Fatick, non_admin : Gorom-Lampsar |
| correction C02 | 118 | 1 | Gini nul impossible : valeurs arrondies au dixième par le portail |
| total ambigu (colonne non nationale) | 48 | 2 | total ambigu (colonne non nationale) |
| correction C01 | 42 | 1 | Kolda et Kédougou inversés par le portail |
| correction C04 | 18 | 1 | Doublon de la série annuelle 2008 daté 2008-09-01 (fréquence D) |

### Doublons conflictuels (à trancher en #6)

Même indicateur, zone, période et désagrégation, mais valeurs différentes (souvent une région et un département de même nom rangés dans la même colonne).

| Jeu | Valeurs |
|---|---|
| `amkfcsb` | 6731 |
| `ykwfqkb` | 935 |
| `cimkorc` | 460 |
| `vwhpbjb` | 404 |
| `vihpdpe` | 280 |
| `rnumqzf` | 252 |
| `cirzjwg` | 242 |
| `gmjuys` | 200 |
| `bdubwzf` | 192 |
| `qrnvwbc` | 185 |
| `fuccbbg` | 98 |
| `xfgtfjb` | 92 |
| `cvmvpxg` | 78 |
| `sehuhqg` | 64 |
| `sfuarzb` | 60 |

## Jeux à zone présumée

Sans colonne géographique ni code région : rattachés au Sénégal. À confirmer à la vérification des indicateurs ; une exception se déclare dans `socle/referentiels/zones_par_jeu.csv`.

218 jeux ; parmi eux, utilisés par le jeu de test : aucun.
