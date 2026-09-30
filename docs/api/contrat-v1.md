# Contrat d'API Gëstukaay — v1.0.0

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
| `POST /v1/ask/audio` | `multipart` : `fichier` (OGG/WebM Opus ≤ 60 s) + champs d'`AskRequest` sauf `question` | `AskResponse` (avec `transcription`) | SAN (route) · KBD (transcription) | EF-11 |
| `POST /v1/ask/{id}/confirm` | `ConfirmRequest` | `AskResponse` (issue `exacte`) | SAN | EF-06, US-03 |
| `GET /v1/answers/{id}` | — | `AskResponse` | SAN | EF-29 |
| `GET /v1/answers/{id}/export.pdf` | — | `application/pdf` (A4, 1 page) | SAN | EF-33 |
| `GET /v1/answers/{id}/export.csv` | — | `text/csv` (schéma EF-34) | SAN | EF-34 |
| `GET /v1/answers/{id}/chart.svg` | — | `image/svg+xml` | SAN | EF-26, EF-27 |
| `POST /v1/feedback` | `FeedbackRequest` | `204` | SAN | EF-49–51 |
| `POST /v1/situate` | *à définir (contrat v1.1.0)* | *à définir* | SAN · KBD | EF-37–40 |
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
- `graphique: null` pour une valeur unique (5.4) ; sinon `svg_url` pour l'image et `series` pour le tableau alternatif (EF-28).
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

Jamais de rouge, jamais de vocabulaire d'erreur (7.1, principe 6).

## 4. Règles communes (non négociables)

1. **Aucune valeur sans source** (engagement 01) : testé sur chaque exemple par `contracts/tests/`.
2. **Champs inconnus refusés** (`extra="forbid"`) : un champ ajouté d'un seul côté casse les tests. C'est voulu.
3. **Le moteur ne stocke rien.** Persistance, identifiants de conversation hachés, journal : backend.
4. **Le LLM ne voit jamais un chiffre du socle** (EF-04) : seul `RequeteStructuree` sort de la couche de compréhension.

## 5. Faire évoluer le contrat

Versionnage sémantique dans `VERSION_CONTRAT` :
- **correctif** (1.0.x) : documentation, exemples ;
- **mineur** (1.x.0) : ajout d'un champ **optionnel** ou d'une route — rien ne casse ;
- **majeur** (x.0.0) : renommage, suppression, champ rendu obligatoire — à éviter pendant le hackathon.

Procédure :
1. Branche `contrat/<sujet>`, modifier `models.py` et au besoin `examples/`.
2. `./scripts/generer_contrat.sh` puis `uv run pytest`.
3. PR avec l'étiquette `contrat` : **approbation des deux membres obligatoire** (CODEOWNERS).
4. Après fusion, chacun `git pull` et met à jour son côté.

## 6. Points ouverts

- [ ] **Licence** : le portail n'en renseigne aucune (`licence` vide dans les 376 jeux). Les exemples portent « CC BY 4.0 » conformément au cahier (1.4) ; à confirmer avec l'ANSD avant publication.
- [ ] **Codes de départements** (`SN-TH-THIES` dans `approchee.json`) : provisoires, fixés avec la table des zones du socle.
- [ ] **Codes d'indicateurs** des suggestions (`nombre_menages`, `taille_moyenne_menage`) : provisoires, fixés avec le socle curé.
- [ ] **Explication wolof** : les gabarits WO sont marqués « à valider par un linguiste » (7.4).
- [ ] **`/v1/situate`** : contrat à écrire (v1.1.0 du contrat) quand les distributions disponibles seront confirmées (quintiles EHCVM, pas de déciles sur le portail).
- [ ] **Domaine** : les URL d'exemple utilisent `app.gestukaay.test` (domaine réservé aux tests).
