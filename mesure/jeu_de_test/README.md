# Jeu de test de référence (issue #18)

103 questions qui servent d'examen au moteur (cahier 12.1). Le benchmark (#19) les pose au
moteur et compare ses réponses aux réponses attendues. Elles servent aussi à choisir les
indicateurs du socle (#3).

## Répartition

| Type | Ce qu'on teste | FR | WO |
|---|---|---|---|
| simple | une valeur | 28 | 12 |
| comparative | 2 zones ou 2 périodes | 11 | 4 |
| classement | « quelle région… le plus… » | 7 | 3 |
| approchee | ville → département, « Dakar » → 3 académies, période voisine, catégorie non publiée | 9 | 4 |
| refus | donnée absente, prévision non publiée, hors statistique, inintelligible | 14 | 6 |
| suivi | « et pour Kaolack ? » (colonne `suite_de`) | 3 | 2 |

Le cahier (12.1) prévoit 100 questions, 70 FR / 30 WO. En #3, trois refus se sont révélés couverts
par le socle (voitures à Kolda et à Ziguinchor : `qbvttzc` ; criminalité : `iocwzud`, national) et sont
devenus des approchées ; trois refus ont été ajoutés pour garder **20 refus** (avec 17, une seule erreur
ferait passer sous la cible de 95 %). D'où 103 questions, 72 FR / 31 WO.

Origine des questions : `cahier`, `persona` et `besoin` (besoins réels, posés même si la donnée
peut manquer) ; `socle` (pour couvrir les domaines) ; `piège` (problèmes connus des données).

## Colonnes de `questions.csv` (séparateur `;`, UTF-8)

| Colonne | Contenu |
|---|---|
| `id` | `FR-001`… `WO-030` |
| `question` | la question telle qu'un utilisateur la poserait. **WO : à écrire par un locuteur natif** |
| `equivalent_fr` | WO seulement : le sens de la question en français |
| `suite_de` | type `suivi` : la question précédente de la conversation |
| `issue_attendue` | `exacte`, `approchee` ou `aucune` (EF-05) |
| `motif` | refus : `hors_socle`, `projection` ou `incomprehension` |
| `dataset_id`, `colonne_zone`, `filtres` | où se trouve la réponse dans le socle brut ; approchée : l'indicateur à proposer |
| `zones_attendues` | codes du référentiel (`SN-TH`, `SN-IA-KOLDA`…) ; approchée : les choix à proposer |
| `periode` | `2023`, `2026-03`, `2023-T2` ; plusieurs périodes séparées par `\|` |
| `valeurs_attendues` | `SN-TH=2463677` ; comparaison de périodes : `SN@2011=46.7\|SN@2022=37.5` ; classement : dans l'ordre attendu |
| `periode_par_defaut` | `oui` si la question ne donne pas de période : la réponse doit dire « dernière donnée publiée » (US-06) |
| `note` | piège, périmètre, point à vérifier (en français : destinée à l'équipe) |
| `ecriture` | WO seulement : `officielle` (orthographe de référence) ou `usage` (comme on tape sur WhatsApp : gnata, thieb, deukk…). Le benchmark donne un score par type |

Les valeurs sont **brutes**, telles que publiées. L'arrondi d'affichage est le travail du moteur.

## Règle d'or : aucune valeur sans preuve

Aucune valeur attendue n'est tapée à la main. Chacune a été lue dans le socle brut et se
re-vérifie à tout moment :

```bash
uv run python mesure/scripts/verifier_attendus.py   # sur le socle brut (local)
uv run pytest mesure                                # structure du jeu (CI)
```

## Questions wolof

Écrites par KBD (locuteur natif) : 9 en orthographe officielle, 21 en écriture d'usage, avec des
graphies volontairement variées (ñata / nata / gnata, ceeb / thieb, dëkk / deukk, Cees / Tiés / thies).
`WO-028` est un bavardage sans question statistique : le moteur doit avouer qu'il n'a pas compris.

## `variantes_wolof.csv` : les 70 questions françaises traduites en wolof

Une ligne par question `FR-…` : sa traduction wolof et son type d'écriture. Ce n'est **pas** le jeu
de test (qui reste 70 FR / 30 WO, cahier 12.1) : c'est la matière première de la normalisation
(#22) et du lexique (#23), et d'un éventuel benchmark wolof élargi.

## Fichier modifié par un outil ? Toujours re-vérifier

Un outil (tableur, assistant IA) peut modifier des valeurs ou des issues sans le dire. Avant
toute PR qui touche `questions.csv` :

```bash
uv run python mesure/scripts/verifier_attendus.py && uv run pytest mesure
```
