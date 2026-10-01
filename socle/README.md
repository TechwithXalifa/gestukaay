# Socle de données

Construction et contrôles du socle officiel sur lequel Gëstukaay répond (cahier 10.3, 10.8).
Les données brutes (`socle_opendata_par_themes/`, 2,7 Go) restent **hors Git** ; leur chemin est
donné par `GESTUKAAY_SOCLE_BRUT` (voir `.env.example`).

## Référentiel des zones — `referentiels/zones.csv` (issue #2, décision 0003)

| Niveau | Nombre | Codes |
|---|---|---|
| pays | 1 | `SN` |
| région | 14 | ISO 3166-2 (`SN-TH`), identiques au portail |
| département | 46 | Gëstukaay, lisibles : `SN-TH-MBOUR` |
| académie | 16 | `SN-IA-KOLDA` ; colonne `couvre` = zones administratives recouvertes |

Colonnes : `code;niveau;parent;libelle_fr;libelle_wo;statut_wo;variantes;couvre`.
Les libellés wolof sont un **brouillon à valider** (`statut_wo = a_valider`, tâche #26).

`gestukaay_socle.zones.resoudre(libelle, niveau=None)` rattache un libellé du portail à un code :
- un nom seul désigne la **région** (« Kaolack ») ; le département ou l'académie seulement si le
  contexte le dit (« Dpt Kaolack », « IA Kolda », ou `niveau` donné par `niveau_de_colonne()`) ;
- « Total », « ALL », « Ensemble » ne sont jamais rattachés (traités jeu par jeu, #4).

## Rapport de couverture — `rapports/couverture_zones.md`

```bash
uv run python socle/scripts/couverture_zones.py
```

Pour chaque colonne géographique du socle : libellés rattachés, écartés, et pourquoi.
