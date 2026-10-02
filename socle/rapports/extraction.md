# Extraction du socle

Socle brut : `socle_opendata_par_themes/observations.csv` · sortie : `socle_gestukaay/` (hors Git) · schéma du cahier 10.3 (décision #4).

## Résumé

| | Valeurs |
|---|---|
| Valeurs non vides lues | 673240 |
| → extraites | 646445 |
| → doublons identiques fusionnés | 1654 |
| → rejetées (voir `rejets.csv`) | 25141 |
| Indicateurs représentés | 4114 |
| Zones : pays / régions / départements / académies | 334438 / 249292 / 25506 / 37209 |
| Zone présumée (jeu sans colonne géographique → Sénégal) | 289439 valeurs, 225 jeux |

## Contrôle de bout en bout : jeu de test

216 valeurs attendues (questions exactes) cherchées dans la table extraite : **216 trouvées à l'identique**, 0 échec(s).

## Rejets par motif

| Motif | Valeurs | Jeux | Exemples |
|---|---|---|---|
| infra | 14297 | 2 | infra : ARD MBADAKHOUNE, infra : ARD NGUELOU, infra : ARD. KOUMBAL |
| doublon conflictuel | 10451 | 20 | SN 1980 : 19.6132776013803 / 4.7067671255767, SN 1980 : 24.7587639167721 / 4.71790090867977, SN 1980 : 73.1083585755478  |
| non_admin | 345 | 5 | non_admin : Centre, non_admin : Diourbel et Fatick, non_admin : Gorom-Lampsar |
| total ambigu (colonne non nationale) | 48 | 2 | total ambigu (colonne non nationale) |

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

225 jeux, dont ceux du jeu de test : `cfulhc`, `iocwzud`, `muhgux`, `ovothxc`, `pexioke`, `tsghpfc`, `whkisxc`.
