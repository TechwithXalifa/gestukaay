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

**Un indicateur = un jeu du portail × une valeur de sa dimension « Indicateur » × une unité.** Une
dimension de mesure (« Quota », « Mesure », « Unités ») porte aussi l'indicateur : production, rendement
et superficie sont trois indicateurs même quand le portail ne leur donne pas d'unité. Les
autres dimensions (sexe, âge, milieu…) sont des désagrégations (`desagregations`), les colonnes
géographiques donnent la zone (`niveaux_zone`). Tout le socle y est : 4 282 indicateurs, 373 jeux,
32 domaines.

```bash
uv run python socle/scripts/inventaire_indicateurs.py   # ~15 s, relançable
```

| Colonne | Contenu |
|---|---|
| `code` | identifiant interne stable (`dwibrlf`, `jcvcajc.taux-de-pauvrete`, `uipcgjd.total~courants`) ; jamais montré au public |
| `libelle_fr`, `libelle_wo`, `statut_wo` | **à la main** ; `libelle_fr` est pré-rempli depuis le portail, les doublons départagés (nom du jeu, unité, période) |
| `unite` / `unite_affichee` | unité du portail (identité, jamais modifiée) / **à la main** : unité montrée au public (« habitants », « ans ») ; vide = celle du portail |
| `priorite` | `P1` utilisé par le jeu de test · `P2` domaines des questions types du cahier · `P3` le reste |
| `verification` | **à la main** : `a_verifier` → `verifie` (ou `ecarte`) |
| `questions_test` | questions du jeu de test qui l'utilisent |
| `dimension_indicateur`, `valeur_portail` | où le retrouver dans le socle brut (graphies séparées par `\|`) |
| `niveaux_zone` | `pays\|region\|departement\|academie` ; vide = aucune zone dans les données (souvent national, à vérifier) |

L'inventaire **ne remplace jamais** les colonnes remplies à la main (`libelle_fr`, `libelle_wo`,
`statut_wo`, `unite_affichee`, `verification`, `note`) et signale les codes disparus si le socle change.

`referentiels/domaines.csv` : thème du portail → domaine Gëstukaay (doublons fusionnés, « Métadonnées »
exclu) ; `questions_types = oui` pour les 6 domaines des questions types du cahier.

Rapport : `rapports/indicateurs.md` (comptes par domaine, couverture des 100 questions, anomalies).

## Fiches des jeux et des indicateurs — `referentiels/jeux.csv` (issue #7)

```bash
uv run python socle/scripts/fiches.py   # quelques secondes
```

`jeux.csv` : une fiche par jeu, découpée dans la description du portail (rien n'est rédigé). Les 61 jeux
au modèle des annuaires ANSD donnent `intitule`, `definition`, `type_donnees`, `operation` (ENES, EHCVM,
RGPH-5… : le `Source.operation` du contrat), `methode`, `observations` ; les autres, une `description`
en texte libre (78 n'en ont aucune).

**Fiche d'un indicateur** = son référentiel (libellés, unité, périmètre) + la fiche de son jeu. Quand le
jeu décrit plusieurs indicateurs, la colonne manuelle `definition` d'`indicateurs.csv` porte la phrase
propre à l'indicateur, **citée mot pour mot du portail** (un test le vérifie).

Rapport de relecture : `rapports/fiches_p1.md`.

## Extraction — `scripts/extraire.py` (issue #4, décision 0006)

```bash
uv run python socle/scripts/extraire.py   # ~45 s
```

Écrit dans `$GESTUKAAY_SOCLE_EXTRAIT` (défaut `../socle_gestukaay/`, hors Git, ~100 Mo) :

| Fichier | Contenu |
|---|---|
| `observations.csv` | une ligne par valeur : `observation_id;indicateur;zone;zone_presumee;periode;desagregation;valeur;unite;echelle;source_id;nature;base_projection;ligne_origine` |
| `sources.csv` | une ligne par jeu du portail (producteur, titre, dates, licence, URL de la fiche) |
| `rejets.csv` | chaque valeur écartée, avec son motif et sa ligne d'origine |

- `valeur` est **telle que publiée**, en unités pleines ; `echelle` (1, 10⁶, 10⁹) ne sert qu'à l'affichage.
- `ligne_origine` = numéro de ligne dans `observations.csv` du socle brut ; `observation_id` = empreinte
  stable de (jeu, période, désagrégation brute, unité).
- `zone_presumee = oui` : jeu sans colonne géographique, rattaché au Sénégal faute de mieux.
  Exceptions dans `referentiels/zones_par_jeu.csv` (`feujxob` → Dakar).
- `nature` (`observee`, `estimation`, `projection`) et `base_projection` : `referentiels/natures.csv`, une
  règle par jeu et par période avec sa preuve ; une année postérieure à la dernière mise à jour du jeu est
  une projection ; sinon observée (décision 0007).
- Les corrections (Thiès permuté, doublons) viennent avec #6.

Contrôle : le script échoue si une valeur attendue du jeu de test n'est pas retrouvée à l'identique.
Rapport : `rapports/extraction.md`.

## Contrôles et corrections — `referentiels/corrections.csv` (issue #6, décision 0008)

Appliquées par `scripts/extraire.py` après l'extraction. Une ligne par correction, décidée à la main,
avec `motif` et `preuve` :

| Action | Effet |
|---|---|
| `exclure` | les valeurs visées (jeu, indicateur ou `unite:<motif>`, zones, période, condition `valeur=0` ou `journalier`) partent dans `rejets.csv` avec le motif « correction Cxx » |
| `unite_affichee` | unité montrée au public (reportée dans `indicateurs.csv`) ; le nombre n'est jamais modifié |

Les contrôles automatiques ne font que signaler : `rapports/controles.md`.

## Versions du socle — `../socle_gestukaay/<version>/` (issue #8, décision 0013)

```bash
uv run python socle/scripts/extraire.py                       # ../socle_gestukaay/brouillon/ (écrasable)
uv run python socle/scripts/extraire.py --version 2026.10.0   # version publiée : jamais réécrite
```

Chaque dossier contient `VERSION` et `MANIFEST.json` (date, commit Git, comptes, empreintes sha256 des
fichiers et des référentiels utilisés). L'extraction est déterministe : deux machines qui extraient le
même socle brut avec le même commit obtiennent les mêmes empreintes. Le moteur prend le dossier de
`GESTUKAAY_SOCLE_EXTRAIT` (ou la version publiée la plus récente qu'il contient) et refuse de démarrer
si un indicateur du socle manque au référentiel.
