# Couverture du référentiel des zones

Socle : `socle_opendata_par_themes/observations.csv` · référentiel : `socle/referentiels/zones.csv` (1 pays, 14 régions, 46 départements, 16 académies).

## Résumé

| | Valeurs |
|---|---|
| Valeurs non vides du socle | 673240 |
| Valeurs portant un libellé géographique | 325977 |
| → rattachées à une zone | 311172 (95.46 %) |
|   dont pays / régions / départements / académies | 35678 / 212575 / 25710 / 37209 |
| → infra-départementales, hors référentiel (décision #2) | 14297 |
| → regroupements non administratifs ou historiques | 345 |
| → écartées volontairement (Total, ALL…) | 163 |
| → **non rattachées** | **0** |

Codes du portail (`region_id`) sur les valeurs non vides : sans code 330893, SN 296099, étranger 46248.

## Contrôle : codes région du portail contre notre rattachement

| Colonne | Libellé | Code portail | Notre code | Valeurs |
|---|---|---|---|---|
| region | KEDOUGOU | SN-KG | SN-KE | 56 |

## Colonnes géographiques (18)

### `region` — 106 libellés, 151902 valeurs, 26 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| ALL | 45 | écarté : total ambigu, traité jeu par jeu (#4) |

### `régions` — 49 libellés, 39728 valeurs, 23 jeux

Tous les libellés sont rattachés.

### `regions` — 723 libellés, 39425 valeurs, 27 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| COMMUNES | 16 | écarté : total ambigu, traité jeu par jeu (#4) |
| *645 libellés* (ex. ARRONDISSEMENT  ALMADIES, CA MERMOZ SACRE CŒUR, CA NGOR, CA OUAKAM) | 14248 | infra-départemental : hors référentiel (décision #2) |

### `inspection-académique` — 17 libellés, 31582 valeurs, 5 jeux · niveau imposé : academie

Tous les libellés sont rattachés.

### `région` — 20 libellés, 24114 valeurs, 27 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Total | 54 | écarté : total ambigu, traité jeu par jeu (#4) |

### `régions-et-départements` — 45 libellés, 14376 valeurs, 1 jeux

Tous les libellés sont rattachés.

### `zone` — 19 libellés, 8799 valeurs, 2 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Ouest | 4 | regroupement non administratif ou historique : hors référentiel |
| Centre | 4 | regroupement non administratif ou historique : hors référentiel |
| Sud | 4 | regroupement non administratif ou historique : hors référentiel |
| NORD ET EST | 4 | regroupement non administratif ou historique : hors référentiel |

### `academie` — 17 libellés, 8030 valeurs, 4 jeux · niveau imposé : academie

Tous les libellés sont rattachés.

### `zones-géographiques` — 15 libellés, 3121 valeurs, 2 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Total | 26 | écarté : total ambigu, traité jeu par jeu (#4) |
| Notto-Diosmone-Palmarain | 66 | regroupement non administratif ou historique : hors référentiel |
| Gorom-Lampsar | 65 | regroupement non administratif ou historique : hors référentiel |
| Saint-Louis-Matam | 21 | regroupement non administratif ou historique : hors référentiel |

### `département` — 127 libellés, 2550 valeurs, 6 jeux · niveau imposé : departement

Tous les libellés sont rattachés.

### `région-et-département` — 47 libellés, 900 valeurs, 1 jeux

Tous les libellés sont rattachés.

### `localités` — 23 libellés, 402 valeurs, 2 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Zone OUEST | 32 | regroupement non administratif ou historique : hors référentiel |
| Zone CENTRE | 32 | regroupement non administratif ou historique : hors référentiel |
| Zone SUD | 31 | regroupement non administratif ou historique : hors référentiel |
| Zone NORD | 16 | regroupement non administratif ou historique : hors référentiel |
| Zone NORD-EST | 16 | regroupement non administratif ou historique : hors référentiel |
| Kaolack 2005 | 10 | regroupement non administratif ou historique : hors référentiel |
| Kolda 2005 | 10 | regroupement non administratif ou historique : hors référentiel |
| Tambacounda 2005 | 10 | regroupement non administratif ou historique : hors référentiel |

### `region-médicale` — 15 libellés, 384 valeurs, 6 jeux

Tous les libellés sont rattachés.

### `regions-name` — 15 libellés, 272 valeurs, 1 jeux

Tous les libellés sont rattachés.

### `régions-maritimes` — 8 libellés, 176 valeurs, 1 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Total | 22 | écarté : total ambigu, traité jeu par jeu (#4) |

### `départements` — 44 libellés, 120 valeurs, 1 jeux · niveau imposé : departement

Tous les libellés sont rattachés.

### `cmc` — 64 libellés, 64 valeurs, 1 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| *49 libellés* (ex. CMC DE GUINAWRAILS, CMC DE SEBIKOTANE, CMC DE WAKHINANE, CMC de NDANGALMA) | 49 | infra-départemental : hors référentiel (décision #2) |

### `pôles` — 8 libellés, 32 valeurs, 1 jeux

| Libellé | Valeurs | Statut |
|---|---|---|
| Kaolack et Kaffrine | 4 | regroupement non administratif ou historique : hors référentiel |
| Diourbel et Fatick | 4 | regroupement non administratif ou historique : hors référentiel |
| Saint-Louis, Louga et Matam | 4 | regroupement non administratif ou historique : hors référentiel |
| Ziguinchor, Sédhiou et Kolda | 4 | regroupement non administratif ou historique : hors référentiel |
| Tambacounda et Kédougou | 4 | regroupement non administratif ou historique : hors référentiel |

## Colonnes avec 1 ou 2 libellés rattachables (non comptées, à vérifier)

| Jeu | Colonne | Rattachables / distincts | Exemples rattachés |
|---|---|---|---|
| bdqbsrd | `regions` | 1 / 1 | Sénégal |
| beelsfd | `région` | 1 / 1 | Sénégal |
| clnhbsd | `régions` | 1 / 1 | Sénégal |
| dguabcd | `région` | 1 / 1 | Sénégal |
| dnfzlsc | `région` | 1 / 1 | Sénégal |
| hiuwwpg | `opérateurs` | 1 / 6 | SENEGAL |
| jderzfb | `région` | 1 / 1 | Sénégal |
| jjnifag | `pôles` | 1 / 9 | SENEGAL |
| kkyckxd | `opérateurs` | 1 / 6 | SENEGAL |
| qguwmb | `zones` | 1 / 3 | Senegal |
| qtreoj | `région` | 1 / 1 | Sénégal |
| rcyvruc | `regions` | 1 / 1 | Sénégal |
| rfegvpb | `zones` | 1 / 4 | Sénégal |
| rgohtcc | `région` | 1 / 1 | Sénégal |
| rtekraf | `milieu` | 1 / 5 | Senegal |
| thdeutd | `régions` | 1 / 1 | Sénégal |
| thtvbnb | `régions` | 1 / 1 | Sénégal |
| tnmoked | `régions` | 1 / 1 | Sénégal |
| xtpnxmb | `regions` | 1 / 1 | Sénégal |
| zqvwrce | `régions` | 1 / 1 | Sénégal |
