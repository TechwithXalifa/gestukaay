# Contrat d'API Gëstukaay — v1.5.0

> **Nouveautés v1.5.0** (décision 0033), **additif**, rien ne casse : motif `conversation` des réponses
> `aucune` (salutation, remerciement, « qui es-tu ? », définition, « pourquoi… », hors sujet).
> **Nouveautés v1.4.0** (décision 0023), **additif**, rien ne casse : catalogue `GET /v1/indicators`,
> fiche `GET /v1/indicators/{code}`, séries d'Explorer `GET /v1/series` (§4 bis).
> **Nouveautés v1.3.0** (décisions 0012 et 0019), **additif**, rien ne casse : tranches de dépenses
> `500k_750k`, `750k_1m`, `plus_1m` (`plus_500k` reste accepté, plus proposé) · motif de refus `non_disponible`.
> **Nouveautés v1.2.0** (additif comparaison & classement, issue #14) — **additif**, rien ne casse :
> `Periode.fin` (seconde borne d'une comparaison temporelle) · `RequeteStructuree.ordre` (`desc` par défaut, `asc`).
> **Nouveautés v1.1.0** (décisions 0002, 0003, 0004) : nature des valeurs (`observee` / `estimation` / `projection`) ·
> niveau de zone `academie` · route `POST /v1/transcrire` · route `POST /v1/situate` · graphique de contexte.

> **Source de vérité :** [`contracts/src/gestukaay_contracts/models.py`](../../contracts/src/gestukaay_contracts/models.py).
> Ce document l'explique ; en cas de désaccord, c'est le code qui a raison.
> Schémas JSON et types TypeScript générés : [`contracts/generated/`](../../contracts/generated/).
> Réponses d'exemple (utilisables comme données factices) : [`contracts/examples/`](../../contracts/examples/).

## 1. Qui parle à qui

```
                 ┌──────────────── SAN ────────────────┐
  Navigateur ──► │  web (Next.js)  ──HTTP──►  backend  │ ──appel Python──► moteur (KBD)
                 │                            (FastAPI)│                    ├─ compréhension (LLM)
  WhatsApp  ───► │  /webhooks/whatsapp ──────►   │     │                    ├─ résolution (socle)
  Telegram  ───► │  /webhooks/telegram ──────►   │     │                    └─ gabarits FR/WO
                 └──────────────────────────────┼─────┘
                                                └──► canaux (KBD) : mise en forme du
                                                     message WhatsApp/Telegram + audio
```

Deux frontières, deux contrats :

| Frontière | Forme | Défini par |
|---|---|---|
| **Moteur → backend** | Appel Python : `Moteur.repondre(AskRequest) -> AskResponse` | [`engine/src/gestukaay_engine/interface.py`](../../engine/src/gestukaay_engine/interface.py) |
| **Backend → web** | JSON sur HTTP, routes ci-dessous | Ce document + `contracts/` |

Les deux utilisent **les mêmes modèles**. Le backend ne transforme pas la réponse du moteur :
il la complète (`latence_ms`), la stocke, et la renvoie telle quelle.

## 2. Routes V1.0

| Méthode et chemin | Corps | Réponse | Propriétaire | Réf. |
|---|---|---|---|---|
| `POST /v1/ask` | `AskRequest` | `AskResponse` | SAN | EF-01, EF-05 |
| `POST /v1/transcrire` | `multipart` : `fichier` (WebM/OGG Opus ≤ 60 s) + `langue` facultatif | `TranscriptionResponse` | SAN (route) · KBD (transcription) | EF-11, EF-15, US-09 |
| `POST /v1/ask/audio` | `multipart` : `fichier` (OGG/WebM Opus ≤ 60 s) + champs d'`AskRequest` sauf `question` | `AskResponse` (avec `transcription`) — **WhatsApp / Telegram** | SAN (route) · KBD (transcription) | EF-11 |
| `POST /v1/ask/{id}/confirm` | `ConfirmRequest` | `AskResponse` (issue `exacte`) | SAN | EF-06, US-03 |
| `GET /v1/answers/{id}` | — | `AskResponse` | SAN | EF-29 |
| `GET /v1/answers/{id}/export.pdf` | — | `application/pdf` (A4, 1 page) | SAN | EF-33 |
| `GET /v1/answers/{id}/export.csv` | — | `text/csv` (schéma EF-34) | SAN | EF-34 |
| `GET /v1/answers/{id}/chart.svg` | — | `image/svg+xml` | SAN | EF-26, EF-27 |
| `POST /v1/feedback` | `FeedbackRequest` | `204` | SAN | EF-49–51 |
| `POST /v1/situate` | `SituateRequest` | `SituateResponse` — **rien n'est conservé** | SAN (route) · KBD (calcul) | EF-37–40 |
| `GET /v1/indicators` | `domaine`, `q`, `niveau`, `limite`, `decalage` | `CatalogueResponse` | SAN (route) · KBD (lecture) | 5.5 |
| `GET /v1/indicators/{code}` | — | `FicheIndicateur` (404 si inconnu) | SAN (route) · KBD (lecture) | 5.5, US-19 |
| `GET /v1/series` | `indicateur`, `zones` (6 au plus), `debut`, `fin` | `SeriesResponse` | SAN (route) · KBD (lecture) | 5.5, US-18 |
| `POST /webhooks/whatsapp` | charge utile Meta | `200` immédiat | SAN (route) · KBD (logique) | EF-19 |
| `POST /webhooks/telegram` | charge utile Telegram | `200` | SAN (route) · KBD (logique) | EF-24 |

Toutes les erreurs : **RFC 9457** (`application/problem+json`, modèle `Problem`).
Un refus (`issue: "aucune"`) **n'est pas une erreur** : c'est un `200` normal.

## 3. La réponse : trois issues, et seulement trois

`AskResponse.reponse.issue` vaut `exacte`, `approchee` ou `aucune`. Le front fait un `switch` dessus ;
TypeScript restreint alors automatiquement les champs disponibles.

```ts
import type { AskResponse } from "@contracts/ask_response";

switch (r.reponse.issue) {
  case "exacte":    /* r.reponse.resultats, .explication, .graphique, .citation */ break;
  case "approchee": /* r.reponse.reformulation, .choix — AUCUNE valeur ici */     break;
  case "aucune":    /* r.reponse.motif, .message, .suggestions */                 break;
}
```

### `exacte`
- `intention` : `valeur` (1 résultat), `comparaison` (2+), `classement` (14 régions, zone demandée `mise_en_evidence`).
- Chaque `Resultat` porte **sa propre** `source` : dans une comparaison, deux valeurs peuvent venir de deux publications.
- `valeur_affichee` est déjà formatée (`2 463 677` avec espaces fines U+202F, virgule décimale). **Le front ne reformate jamais un nombre** : il affiche `valeur_affichee`. `valeur` sert aux graphiques et au CSV.
- `periode_par_defaut: true` → afficher « dernière donnée publiée : 2023 » (US-06).
- **Graphique** (décision 0004 §3) : pour une **valeur unique**, graphique de **contexte** si les données
  existent, `null` sinon ; jamais un graphique d'un seul point (5.4). Selon le niveau de la zone :

  | Zone demandée | Graphique de contexte (même indicateur, même période) | À défaut |
  |---|---|---|
  | pays | — (rien à quoi la comparer à la même date) | évolution dans le temps |
  | région | classement des 14 régions, zone demandée en `mise_en_evidence` | évolution dans le temps |
  | département | classement des départements **de la même région** | évolution, sinon `null` |
  | académie | classement des 16 académies (libellé « académies », pas « régions ») | évolution, sinon `null` |

  `svg_url` pour l'image, `series` pour le tableau alternatif (EF-28). Exemple : `exacte_valeur.json`
  (population de Thiès, classement des 14 régions).
- **`nature`** (v1.1.0, décision 0002) : `observee`, `estimation` ou `projection`. Pour `estimation`
  et `projection`, afficher un **badge** avec `base_projection` (« Projection officielle ANSD —
  Projections démographiques 2023-2073 »). `null` = non renseigné, traiter comme observée.
  Exemple : `exacte_projection.json`.
- **`zone.niveau = "academie"`** (v1.1.0, décision 0003) : données d'éducation par inspection
  d'académie. Afficher « académie de Kolda », jamais « région de Kolda ».
- `citation` est prête à copier (EF-35).

### `approchee`
- `reformulation` + 2 ou 3 `choix`. **Aucun champ de valeur n'existe dans ce type** : il est structurellement impossible d'afficher un chiffre avant confirmation (EF-06).
- Confirmer = `POST /v1/ask/{id}/confirm` avec `{"choix_id": "1"}`. Le backend relit la réponse stockée, prend `choix[i].requete` et appelle `moteur.executer(requete, ...)`.

### `aucune`
| `motif` | Quand | Interface (7.3) |
|---|---|---|
| `hors_socle` | la donnée n'existe pas | icône neutre, `message`, 3 `suggestions` cliquables, lien « Suggérer cet indicateur » |
| `projection` | prévision demandée | `message` qui renvoie vers les projections officielles de l'ANSD |
| `incomprehension` | question inintelligible, transcription vide | « Je n'ai pas bien compris » + exemples + réessayer au micro |
| `non_disponible` (v1.3.0) | type de question que le moteur ne sait pas encore traiter | `message` (« Ce type de question n'est pas encore disponible. »), sans suggestion ; jamais « cette donnée n'existe pas » (décision 0019) |
| `conversation` (v1.5.0) | le message n'est pas une question de statistique : salutation, merci, « qui es-tu ? », langue, aide, définition d'un indicateur, « pourquoi… », hors sujet (décision 0033) | une **bulle de message ordinaire** (pas l'icône de refus), `message` = texte fixe de KBD ; `suggestions` éventuelles (le chiffre lié à une définition ou à un « pourquoi ») ; jamais « cette donnée n'existe pas » |

Jamais de rouge, jamais de vocabulaire d'erreur (7.1, principe 6).

## 4. Voix sur le web et « Où je me situe » (v1.1.0)

### Voix (décision 0004 §1)
1. Le web enregistre (arrêt après 2 s de silence, 7.3), envoie l'audio à `POST /v1/transcrire`.
2. Il affiche `transcription` dans le champ de question, **modifiable** (US-09). Transcription vide →
   état « je n'ai pas bien compris » (7.3).
3. À l'envoi : `POST /v1/ask` avec `question` = texte final, `source = "voix"`,
   `transcription_brute` = texte reçu à l'étape 1 (sert à mesurer les erreurs, jamais affiché).

WhatsApp et Telegram gardent `POST /v1/ask/audio` (transcription + réponse en un appel ; la
correction se fait en répondant « non » / « déet »).

### « Où je me situe » (décision 0004 §2)
Le portail ne publie **aucun seuil** de décile ni de quintile : on compare le ménage aux
**moyennes publiées**, sans tranches.

- Entrée `SituateRequest` : `region` (code `SN-XX`), `taille_menage` (nombre exact, 1 à 40),
  `depenses_mensuelles` (tranche : `moins_50k`, `50k_100k`, `100k_200k`, `200k_350k`, `350k_500k`,
  `500k_750k`, `750k_1m`, `plus_1m` ; `plus_500k` reste accepté depuis la v1.3.0 mais n'est plus
  proposé, décision 0012), `niveau_instruction_chef` (facultatif, pas encore exploité).
- Sortie `SituateResponse` :
  - `depense_par_personne_an` : **intervalle** calculé sur les seules données saisies
    (dépenses × 12 / taille) ;
  - `moyenne_region`, `moyenne_pays` : consommation moyenne par tête publiée (EHCVM) ;
  - `position_region`, `position_pays` : `en_dessous` / `au_dessus` si tout l'intervalle est d'un
    côté de la moyenne, sinon `autour` ;
  - `contexte` : repères publiés (pauvreté des ménages de même taille — **niveau national** : le
    portail ne la publie pas par région —, part de la région dans le quintile de bien-être le plus
    bas, accès à l'électricité…) ;
  - `explication` : gabarit, avec l'encadré « C'est quoi une moyenne ? » (EF-39). Elle **doit**
    signaler les deux biais de la comparaison : la moyenne est mesurée à sa date (2022, en FCFA de
    2022) face à une dépense actuelle, et la consommation de l'enquête (EHCVM) inclut
    l'autoconsommation et les loyers imputés, souvent absents des dépenses déclarées. Sinon un ménage
    peut se croire plus aisé qu'il ne l'est.
- **Rien n'est conservé** : ni base, ni journal, ni compte (EF-40, US-21).
- Exemple : `situer.json` (Kolda, 7 personnes, 100 000 à 200 000 FCFA par mois).

## 4 bis. Catalogue, fiche et séries (v1.4.0, décision 0023)

Lecture seule, sans LLM : tout vient du référentiel des indicateurs et du socle servi.

- **Catalogue** : une `IndicateurResume` par indicateur qui a des valeurs (libellé, domaine, unité,
  producteur, opération, niveaux publiés, première et dernière période, `verifie`). Exemple : `catalogue.json`.
- **Fiche** : la définition est **citée mot pour mot du portail**, `null` s'il n'en publie pas ; la
  couverture donne, par niveau, le nombre de zones et les périodes publiées ; `citation` suit EF-35.
  Exemple : `fiche_indicateur.json`.
- **Séries** : une `Serie` par zone avec les **seules périodes publiées**, jamais d'interpolation ; une zone
  sans valeur sur la période va dans `absents` (signalée à l'écran) ; chaque point garde `valeur_affichee`
  et `observation_id`. `graphique` est prêt à dessiner. Exemple : `series.json` (taux de pauvreté,
  Sénégal, Dakar et Kolda, 2011 à 2022).
- Le code d'indicateur sert aux adresses partageables (EF-29), jamais comme texte affiché.

## 5. Règles communes (non négociables)

1. **Aucune valeur sans source** (engagement 01) : testé sur chaque exemple par `contracts/tests/`.
2. **Champs inconnus refusés** (`extra="forbid"`) : un champ ajouté d'un seul côté casse les tests. C'est voulu.
3. **Le moteur ne stocke rien.** Persistance, identifiants de conversation hachés, journal : backend.
4. **Le LLM ne voit jamais un chiffre du socle** (EF-04) : seul `RequeteStructuree` sort de la couche de compréhension.

## 6. Faire évoluer le contrat

Versionnage sémantique dans `VERSION_CONTRAT` :
- **correctif** (1.0.x) : documentation, exemples ;
- **mineur** (1.x.0) : ajout d'un champ **optionnel** ou d'une route — rien ne casse ;
- **majeur** (x.0.0) : renommage, suppression, champ rendu obligatoire — à éviter pendant le hackathon.

Procédure :
1. Branche `contrat/<sujet>`, modifier `models.py` et au besoin `examples/`.
2. `./scripts/generer_contrat.sh` puis `uv run pytest`.
3. PR avec l'étiquette `contrat` : **approbation des deux membres obligatoire** (CODEOWNERS).
4. Après fusion, chacun `git pull` et met à jour son côté.

## 7. Points ouverts

- [ ] **Licence** : le portail n'en renseigne aucune (`licence` vide dans les 376 jeux). Les exemples portent « CC BY 4.0 » conformément au cahier (1.4) ; à confirmer avec l'ANSD avant publication.
- [x] **Codes de départements** : ceux du référentiel des zones (`socle/referentiels/zones.csv`, décision 0003), ex. `SN-TH-THIES`.
- [x] **Codes d'indicateurs** : ceux du référentiel des indicateurs (`socle/referentiels/indicateurs.csv`, décision 0005), ex. `pvswjnd`, `jcvcajc.taux-de-pauvrete`. Jamais affichés au public.
- [ ] **Explication wolof** : les gabarits WO sont marqués « à valider par un linguiste » (7.4).
- [x] **`/v1/situate`** : écrit en v1.1.0 (décision 0004 §2).
- [x] **Tranches de dépenses** de « Où je me situe » : les 6 tranches sont validées par SAN.
- [ ] **Écarts à noter pour la v1.2 du cahier** : taille du ménage saisie en nombre (sélecteur) et non
  par tranches ; niveau d'instruction **non demandé** par le web tant qu'il n'est pas exploité
  (minimisation, EF-40) — écart à EF-37.
- [ ] **Domaine** : les URL d'exemple utilisent `app.gestukaay.test` (domaine réservé aux tests).

## 8. Historique des versions

| Version | Date | Changements |
|---|---|---|
| 1.0.0 | 2026-09-30 | Version initiale : `/v1/ask`, trois issues, exports, feedback |
| 1.1.0 | 2026-10-01 | `Resultat.nature` + `base_projection` ; `RefZone.niveau = academie` ; `AskRequest.source` + `transcription_brute` ; `POST /v1/transcrire` ; `POST /v1/situate` ; graphique de contexte (doc) |
| 1.1.1 | 2026-10-02 | Retours de SAN, sans changement de format : exemple `exacte_valeur.json` avec graphique de contexte ; graphique de contexte par niveau de zone (doc) ; biais à signaler dans l'explication de « Où je me situe » ; citation d'une projection ; tests en UTF-8 (Windows) ; version du paquet |
| 1.1.2 | 2026-10-02 | Exemples seuls, sans changement de format : codes d'indicateurs du référentiel (`pvswjnd`…) ; `aucune_hors_socle.json` = FR-071 (« sérère »), « voitures à Kolda » étant devenue une question approchée (décision 0005) |
| 1.2.0 | 2026-10-03 | Additif comparaison & classement (#14) : `Periode.fin` (deuxième borne temporelle) ; `RequeteStructuree.ordre` (`"desc"` / `"asc"`) |
| 1.3.0 | 2026-10-04 | Additif (décisions 0012 et 0019) : `TrancheDepense` gagne `500k_750k`, `750k_1m`, `plus_1m`, `plus_500k` gardé mais plus proposé ; `ReponseAucune.motif` gagne `non_disponible` |
| 1.4.0 | 2026-10-04 | Additif (décision 0023) : `GET /v1/indicators`, `GET /v1/indicators/{code}`, `GET /v1/series` ; modèles `CatalogueResponse`, `FicheIndicateur`, `SeriesResponse` |
| 1.5.0 | 2026-10-07 | Additif (décision 0033) : `ReponseAucune.motif` gagne `conversation` |
