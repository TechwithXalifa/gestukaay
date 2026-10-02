# Contrôles du socle

Les **corrections** (`socle/referentiels/corrections.csv`) sont décidées à la main, avec leur preuve. Les **contrôles** signalent seulement : rien n'est exclu sans une ligne de corrections.

## Corrections appliquées

| Id | Action | Jeu | Effet | Motif | Preuve |
|---|---|---|---|---|---|
| C01 | exclure | `rnumqzf` | 42 valeurs exclues | Kolda et Kédougou inversés par le portail | rnumqzf 2022 : Kolda 231 217, Kédougou 881 677 ; RGPH-5 2023 (pvswjnd) : Kolda 914 798, Kédougou 245 147 |
| C02 | exclure | `qjyrtof` | 118 valeurs exclues | Gini nul impossible : valeurs arrondies au dixième par le portail | 118 valeurs sur 187 à 0,0 |
| C03 | exclure | `idtepgd` | 1440 valeurs exclues | Doublons des séries annuelles 2016-2018 datés « 0016 », « 0017 », « 0018 » (fréquence D) | Mêmes effectifs que les lignes annuelles 2016-2018 (475, 470, 495 valeurs) |
| C04 | exclure | `dwehszb` | 18 valeurs exclues | Doublon de la série annuelle 2008 daté 2008-09-01 (fréquence D) | Mêmes valeurs à l'arrondi près (maïs : 263 427,1 et 263 427,138) |
| C05 | unite_affichee | `uipcgjd` | unité affichée « milliards de FCFA aux prix constants de 1999 » (43 indicateurs) | Unité incrémentée d'un indicateur à l'autre (« constants de 1999 » … « de 2041 ») | Première ligne « de 1999 » ; base 1999 des jeux voisins (fruuksc, efrliqb) |
| C06 | unite_affichee | `fsrvlqe` | unité affichée « milliards de FCFA aux prix constants de 1999 » (43 indicateurs) | Unité incrémentée d'un indicateur à l'autre (« constants de 1999 » … « de 2041 ») | Première ligne « de 1999 » ; base 1999 des jeux voisins (fruuksc, efrliqb) |
| C07 | unite_affichee | `chnqiuf` | unité affichée « milliards de FCFA aux prix constants de 1999 » (43 indicateurs) | Unité incrémentée d'un indicateur à l'autre (« constants de 1999 » … « de 2041 ») | Première ligne « de 1999 » ; base 1999 des jeux voisins (fruuksc, efrliqb) |

## Contrôle entre sources : population régionale

`rnumqzf` 2022 comparé au RGPH-5 2023 (`pvswjnd`) : un écart de plus de 15 % trahit une permutation.

Aucun écart.

## Unités incrémentées (portail)

`chnqiuf` (43 années de base), `fsrvlqe` (43 années de base), `uipcgjd` (43 années de base)
(corrigées pour l'affichage par C05 à C07 ; l'unité du portail reste l'identité de l'indicateur)

## Signalements restants

| Contrôle | Signalements | Exemples |
|---|---|---|
| pourcentage hors de 0-100 | 2467 | `bdubwzf.effectif~%` SN-DB 2014 {"sexe": "Total"} = 6925.0<br>`bdubwzf.effectif~%` SN-DK 2014 {"sexe": "Total"} = 15260.0<br>`bdubwzf.effectif~%` SN-FK 2014 {"sexe": "Total"} = 3502.0<br>`bdubwzf.effectif~%` SN-KA 2014 {"sexe": "Total"} = 2890.0<br>`bdubwzf.effectif~%` SN-KD 2014 {"sexe": "Total"} = 3448.0 |
| Gini hors de ]0, 1[ | 0 |  |
| date impossible | 0 |  |
| rupture (×3 d'une année sur l'autre) | 6049 | `abavtn.dose-de-semences-utilisee-a-lhectare` SN {"culture": "Sorgho"} : 2017 = 38.52 → 2018 = 10.98<br>`abavtn.dose-de-semences-utilisee-a-lhectare` SN-SE {"culture": "Cultures horticoles"} : 2020 = 17.7444 → 2021 = 4.82941<br>`abavtn.dose-de-semences-utilisee-a-lhectare` SN-SE {"culture": "Cultures horticoles"} : 2021 = 4.82941 → 2022 = 46.3174<br>`abavtn.dose-de-semences-utilisee-a-lhectare` SN-SL {"culture": "Cultures horticoles"} : 2021 = 3.02873 → 2022 = 16.6987<br>`abavtn.dose-de-semences-utilisee-a-lhectare` SN-TH {"culture": "Cultures horticoles"} : 2017 = 9.56 → 2018 = 3.13 |

Ruptures par jeu (à examiner ; une vraie rupture reste servie) : `zctvxac` (1197), `ekihmme` (465), `ervtjfc` (335), `idtepgd` (284), `tnmoked` (239), `ezhih` (233), `fviclrf` (223), `qqjyoh` (176), `sdwnpyf` (144), `fruuksc` (119), `cmpqbvf` (108), `wkrkkpb` (94), `jomgwld` (89), `wrqfsxb` (88), `uipcgjd` (86), `cdykdyb` (80), `xmvgohb` (73), `gqgdsgc` (69), `kzxgnzd` (67), `thtvbnb` (61).
