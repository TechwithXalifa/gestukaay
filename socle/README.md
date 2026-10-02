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

## Référentiel des indicateurs — `referentiels/indicateurs.csv` (issue #3, décision 0005)

**Un indicateur = un jeu du portail × une valeur de sa dimension « Indicateur » × une unité.** Les
autres dimensions (sexe, âge, milieu…) sont des désagrégations (`desagregations`), les colonnes
géographiques donnent la zone (`niveaux_zone`). Tout le socle y est : 4 149 indicateurs, 373 jeux,
32 domaines.

```bash
uv run python socle/scripts/inventaire_indicateurs.py   # ~15 s, relançable
```

| Colonne | Contenu |
|---|---|
| `code` | identifiant interne stable (`dwibrlf`, `jcvcajc.taux-de-pauvrete`, `uipcgjd.total~courants`) ; jamais montré au public |
| `libelle_fr`, `libelle_wo`, `statut_wo` | **à la main** ; `libelle_fr` est pré-rempli depuis le portail |
| `priorite` | `P1` utilisé par le jeu de test · `P2` domaines des questions types du cahier · `P3` le reste |
| `verification` | **à la main** : `a_verifier` → `verifie` (ou `ecarte`) |
| `questions_test` | questions du jeu de test qui l'utilisent |
| `dimension_indicateur`, `valeur_portail` | où le retrouver dans le socle brut (graphies séparées par `\|`) |
| `niveaux_zone` | `pays\|region\|departement\|academie` ; vide = aucune zone dans les données (souvent national, à vérifier) |

L'inventaire **ne remplace jamais** les colonnes remplies à la main (`libelle_fr`, `libelle_wo`,
`statut_wo`, `verification`, `note`) et signale les codes disparus si le socle change.

`referentiels/domaines.csv` : thème du portail → domaine Gëstukaay (doublons fusionnés, « Métadonnées »
exclu) ; `questions_types = oui` pour les 6 domaines des questions types du cahier.

Rapport : `rapports/indicateurs.md` (comptes par domaine, couverture des 100 questions, anomalies).
