# Gëstukaay côté web : ce que SAN a construit

Ce document résume tout le travail de SAN sur le backend (`backend/`) et le site (`web/`), du squelette du 1er octobre jusqu'au 3 octobre 2026. Il sert à KBD pour savoir ce qui existe, comment c'est fait, ce qui attend le vrai moteur et ce qui reste à faire.

Le principe n'a pas changé : le backend et le site ne calculent jamais un chiffre. Le backend reçoit la réponse du moteur, la complète (adresse stable, latence), la garde en base et la renvoie telle quelle. Le site affiche `valeur_affichee` sans jamais reformater un nombre.

## 1. Vue d'ensemble

```
Navigateur ──► web (Next.js, port 3000) ──HTTP──► API (FastAPI, port 8000) ──appel Python──► moteur (KBD)
                     │ rendu serveur de /r/{id}            │
                     └───── réseau interne (API_INTERNE) ──┘──► PostgreSQL (réponses, journal, retours)
```

Tout se lance avec une seule commande :

```bash
docker compose up --build   # site : http://localhost:3000 · API : http://localhost:8000/docs
```

Trois services : `api` (backend + moteur), `web` (Next.js en mode standalone) et `db` (PostgreSQL 17). Le socle extrait est monté en lecture seule dans l'API sur `/socle`. Le moteur est choisi par `GESTUKAAY_MOTEUR` : `fake` par défaut, `reel` pour ton moteur.

Hors Docker, l'API tourne avec `uv run uvicorn gestukaay_backend.app:app --port 8000` et le site avec `cd web && npm run dev`.

## 2. Historique des PR de SAN

| PR | Ce qu'elle apporte |
|---|---|
| [#48](https://github.com/TechwithXalifa/gestukaay/pull/48) | Squelette de bout en bout : web → `/v1/ask` → faux moteur → réponse affichée, Docker, CI |
| [#50](https://github.com/TechwithXalifa/gestukaay/pull/50) | Page réponse complète et adresse stable `/r/{id}` |
| [#51](https://github.com/TechwithXalifa/gestukaay/pull/51) | Exports CSV (EF-34) et PDF A4 (EF-33) |
| [#52](https://github.com/TechwithXalifa/gestukaay/pull/52) | Version mobile, états hors ligne et micro refusé |
| [#53](https://github.com/TechwithXalifa/gestukaay/pull/53) | Bascule FR/WO de l'interface, logo baobab dans le PDF |
| [#57](https://github.com/TechwithXalifa/gestukaay/pull/57) | Question à voix haute sur le web (`/v1/transcrire`, écran Écoute) |
| [#58](https://github.com/TechwithXalifa/gestukaay/pull/58) | Module « Où je me situe » |
| [#67](https://github.com/TechwithXalifa/gestukaay/pull/67) | Socle monté dans l'API pour le vrai moteur |
| [#68](https://github.com/TechwithXalifa/gestukaay/pull/68) | Domaines sur l'accueil et page `/domaines` |
| [#70](https://github.com/TechwithXalifa/gestukaay/pull/70) | Lecture des gros CSV sous Windows |
| [#71](https://github.com/TechwithXalifa/gestukaay/pull/71) | Graphique de la réponse et badge projection |
| [#72](https://github.com/TechwithXalifa/gestukaay/pull/72) | Décision 0012 : tranches de dépenses au-delà de 500 000 FCFA |
| [#73](https://github.com/TechwithXalifa/gestukaay/pull/73) | Réponses, journal et retours gardés en base |
| [#75](https://github.com/TechwithXalifa/gestukaay/pull/75) | Page du journal des requêtes (back-office minimal) |
| [#76](https://github.com/TechwithXalifa/gestukaay/pull/76) | Graphique et badge projection dans le PDF, adresse de la citation corrigée |
| [#78](https://github.com/TechwithXalifa/gestukaay/pull/78) | Polices auto-hébergées et budget JavaScript en CI |
| [#80](https://github.com/TechwithXalifa/gestukaay/pull/80) | Tests de bout en bout et d'accessibilité, avec les corrections trouvées |
| [#82](https://github.com/TechwithXalifa/gestukaay/pull/82) | Pages Méthode, À propos et Confidentialité |
| [#84](https://github.com/TechwithXalifa/gestukaay/pull/84) | Lecteur audio de la réponse |
| [#85](https://github.com/TechwithXalifa/gestukaay/pull/85) | Page réponse rendue côté serveur, mesure Lighthouse en 3G |
| [#86](https://github.com/TechwithXalifa/gestukaay/pull/86) | Limites de requêtes sur l'API, en-têtes de sécurité et CSP |
| [#87](https://github.com/TechwithXalifa/gestukaay/pull/87) | Suggérer un indicateur manquant depuis un refus (EF-51) |
| [#88](https://github.com/TechwithXalifa/gestukaay/pull/88) | Décision 0016 : graphiques dessinés par le navigateur, licence dans les exports |
| [#90](https://github.com/TechwithXalifa/gestukaay/pull/90) | Titre de la décision 0017 aligné sur son numéro |
| [#93](https://github.com/TechwithXalifa/gestukaay/pull/93) | Les barres gardent l'ordre envoyé par le moteur (classement « le plus faible ») |

SAN a aussi relu et approuvé les PR de KBD (contrat 1.1.0 à 1.2.0, socle, moteur), avec des correctifs croisés : encodage UTF-8 des tests sous Windows, `csv.field_size_limit` sous Windows, renumérotation de la décision 0017.

## 3. Backend (`backend/src/gestukaay_backend/`)

### 3.1 Routes (`app.py`)

| Route | Rôle | Exigences |
|---|---|---|
| `GET /health` | état de l'API et version du socle | |
| `POST /v1/ask` | question → réponse du moteur, adresse stable, latence, enregistrement | EF-01, EF-05 |
| `POST /v1/ask/{id}/confirm` | confirme un choix d'une réponse approchée : relit la réponse stockée, prend `choix[i].requete` et appelle `moteur.executer()` | EF-06, US-03 |
| `GET /v1/answers/{id}` | relit une réponse (lien partageable) | EF-29 |
| `GET /v1/answers/{id}/export.csv` | export CSV ; `?decimale=virgule` en option | EF-34 |
| `GET /v1/answers/{id}/export.pdf` | export PDF A4 d'une page | EF-33 |
| `POST /v1/transcrire` | audio WebM/OGG Opus (2 Mo au plus) → transcription corrigeable | EF-11, EF-15, décision 0004 |
| `POST /v1/situate` | « Où je me situe » : rien n'est stocké ni journalisé | EF-37 à EF-40 |
| `POST /v1/feedback` | vote, signalement, suggestion d'indicateur | EF-49 à EF-51 |
| `GET /admin/journal` et `/admin/journal.csv` | journal des requêtes, avec un jeton | back-office |

Les erreurs suivent la RFC 9457 (`application/problem+json`) : 404 réponse introuvable, 409 export d'une réponse non exacte ou confirmation impossible, 415 format audio, 413 audio trop long, 422 audio vide ou choix inconnu, 429 trop de requêtes. Un refus (`issue: "aucune"`) n'est pas une erreur, c'est un 200 normal.

**Adresse stable.** Le backend remplace l'URL du moteur par `GESTUKAAY_URL_PUBLIQUE/r/{id}` et remplace aussi l'adresse dans la `citation` (expression `https?://…/r/<id>`). Ton moteur peut donc mettre n'importe quelle adresse de la forme `…/r/<id>`.

### 3.2 Stockage (`stockage.py`)

- Dans Docker : PostgreSQL. Hors Docker : SQLite en mémoire, ou un fichier avec `GESTUKAAY_BASE=sqlite:///gestukaay.db`. Seulement `sqlite3` et `psycopg`, sans SQLAlchemy.
- Trois tables : `reponses` (la réponse complète en JSON, pour les liens `/r/…` qui survivent aux redémarrages), `journal` et `retours`.
- Le journal garde : heure, canal, texte ou voix, langue, question, transcription brute (pour mesurer la transcription), issue, indicateur, latence, version du socle, conversation hachée, choix confirmé.
- Aucune donnée personnelle : `conversation_id` est haché avec un sel (`GESTUKAAY_SEL`). Un choix confirmé garde le canal et la conversation de la question d'origine.
- Si PostgreSQL redémarre, l'API se reconnecte toute seule.

### 3.3 Exports (`exports.py`)

- **CSV** : colonnes EF-34 dans l'ordre, UTF-8 avec BOM pour Excel, séparateur `;`, valeur brute jamais reformatée.
- **PDF** (fpdf2, polices de la charte v2 embarquées : Unbounded, Bricolage Grotesque, Space Mono, licence OFL) : une **fiche statistique officielle**, pas une copie de la page. Bandeau sombre et frise ; titre = l'indicateur, puis zone et période ; statut (sceau « correspondance exacte », ou projection / estimation avec sa base) ; chiffre clé à côté d'une fiche technique (zone, période, producteur, opération, publication, nature) ; lecture ; mise en perspective (barres, 8 au plus, zone demandée en baobab, ordre du moteur conservé) ; source et méthode, citation EF-35 ; pied avec adresse, licence et page. Toujours une seule page : s'il manque de place, on met moins de barres.
- **Licence (décision 0016)** : en pied, « Export Gëstukaay sous licence CC BY 4.0 » pour notre mise en forme ; dans le bloc source, la licence publiée par le portail, sinon « non précisée par le portail ». On n'écrit jamais qu'un jeu de l'ANSD est sous CC BY sans preuve.

### 3.4 Sécurité (`securite.py`)

- Limites par adresse IP et par minute, en fenêtre glissante : questions 30, transcription 10, situer 30, retours 20, exports 30, admin 20. Au-delà : 429 avec `Retry-After`.
- Derrière le proxy de l'hébergeur : `GESTUKAAY_PROXY_DE_CONFIANCE=1` lit `X-Forwarded-For`. Sans proxy, cet en-tête est ignoré.
- En-têtes : `nosniff`, `no-referrer`, interdiction des cadres, CSP `default-src 'none'` (sauf `/docs`). Le journal admin n'est jamais mis en cache.
- Back-office : comptes nominatifs, identifiant et mot de passe haché par scrypt, session dans un cookie `HttpOnly` `SameSite=Strict` (8 h sans activité, 12 h au plus), compte bloqué 15 min après 5 essais manqués, `POST /admin/*` d'une autre origine refusé. Fermé (404) tant qu'aucun compte n'existe (décision 0037).
- `GESTUKAAY_LIMITES=off` coupe les limites pour les tests.

## 4. Site (`web/`, Next.js + TypeScript)

Les types viennent directement de `contracts/generated/` : si le contrat change sans régénération, la CI casse. Les couleurs, tailles, rayons et durées viennent de `web/app/tokens.css`, design system v2 « Terre et baobab » (décision 0036).

### 4.1 Pages

| Adresse | Contenu | Maquette |
|---|---|---|
| `/` | accueil : promesse, champ de question, micro, exemples FR et WO, lien vers « Où je me situe », 6 domaines principaux avec une question d'exemple chacun | Main, M-Accueil |
| `/r/{id}` | page réponse, rendue côté serveur | Reponse, M-Reponse, ReponseComparee |
| `/situer` | « Où je me situe » en 3 étapes puis le résultat | M-SituerIntro, M-Situer, M-SituerResultat |
| `/domaines` | les 32 domaines du socle | |
| `/methode` | méthode et transparence : taux de bonnes réponses aux tests (`lib/mesure.ts`, décision 0036), 5 étapes, données | Methode |
| `/a-propos` | ce que fait Gëstukaay ; précise que ce n'est pas un service de l'ANSD | |
| `/confidentialite` | ce que le code garde vraiment | |
| `/admin/journal` | journal des requêtes, non indexé, absent des menus | BO-Journal |

### 4.2 Page réponse

- **Exacte** : badge « Correspondance exacte », badge projection ou estimation avec sa base (décision 0002), libellé indicateur · zone · période, « dernière donnée publiée » si `periode_par_defaut`, valeur en grand, ligne source sous la valeur, explication, lecteur audio si `audio_url`, graphique, bloc source complet avec note de périmètre et lien vers la publication.
- **Actions** : Exporter PDF, Exporter CSV, Copier la citation, Partager (partage natif sinon copie du lien), message de confirmation de 3 secondes.
- **Retours** : vote utile / pas utile et signalement avec les 4 motifs du contrat et un commentaire.
- **Approchée** : reformulation et boutons de choix ; aucune valeur avant le choix (EF-06). Le choix passe par `/v1/ask/{id}/confirm`.
- **Refus** : icône neutre, jamais de rouge, message du moteur, suggestions cliquables qui posent directement la question, puis « Suggérer cet indicateur à l'équipe » (EF-51).
- **Rendu serveur** : le serveur web lit la réponse par le réseau interne (`API_INTERNE`) et envoie le chiffre dans le HTML. Si l'API ne répond pas en 1,5 s, la page reprend le chargement dans le navigateur.

### 4.3 Graphique (`components/Graphique.tsx`)

Dessiné par le navigateur à partir de `graphique.series` (décision 0016, `svg_url` reste à null) :

- barres horizontales : 8 au plus, dans l'ordre envoyé par le moteur, la zone en évidence en vert et toujours visible ;
- courbe pour l'évolution dans le temps ;
- `barres_empilees` et le reste passent directement en tableau ;
- bouton « Voir les N valeurs en tableau » : c'est l'alternative textuelle (EF-28) ;
- pied avec la source (EF-27).

### 4.4 Voix (`components/Ecoute.tsx`, `lib/enregistreur.ts`)

- Plein écran sombre, onde animée, minuteur ; arrêt automatique après 2 s de silence, 60 s au plus, arrêt si personne ne parle pendant 8 s.
- À l'arrêt, `/v1/transcrire` puis « Vérifiez votre question » : le texte reste modifiable (US-09). La transcription n'apparaît pas pendant qu'on parle (décision 0004).
- À l'envoi : `/v1/ask` avec `source: "voix"`, `transcription_brute`, la langue détectée et `audio_retour: true`.
- États prévus : micro refusé (explication en 2 étapes, la saisie texte reste possible), rien entendu, navigateur incapable d'enregistrer.
- Rien n'est gardé sur l'appareil : l'audio part vers l'API puis est oublié.

### 4.5 Lecteur audio (`components/LecteurAudio.tsx`)

Prêt pour l'audio wolof (#29) : seule la durée est chargée d'avance, l'audio n'est téléchargé qu'au clic, jamais de lecture automatique. Si le fichier est introuvable, le lecteur disparaît et le texte reste la réponse. Il faut un fichier servi en HTTP (OGG/Opus, 60 Ko au plus) et son adresse dans `audio_url`.

### 4.6 « Où je me situe » (`app/situer/page.tsx`, `components/ResultatSituer.tsx`)

- Introduction, puis une question par écran : région (les 14), taille du ménage en nombre exact avec + et −, dépenses du mois par tranches.
- Le niveau d'instruction n'est pas demandé tant qu'aucune donnée publiée ne le croise (minimisation, écart à EF-37 noté).
- Résultat : l'estimation du ménage dans un cadre pointillé, pour ne jamais ressembler à un chiffre officiel ; moyennes publiées de la région et du pays avec leur position et leur source ; repères de contexte ; encadré « C'est quoi une moyenne ? ».
- Les réponses ne vivent que dans l'état de la page : rien dans le navigateur, rien sur le serveur.

### 4.7 Langue de l'interface (`i18n/`)

- Les 71 textes de l'interface sont dans `web/i18n/fr.ts`. La bascule FR | WO est toujours visible dans l'en-tête et mémorisée sur l'appareil. Elle change la langue de l'interface, pas celle de la question.
- `web/i18n/wo.ts` est **vide par choix** : aucun wolof inventé (décision 0009). Un texte manquant reste en français avec une mention qui le dit, et `lang="wo"` n'est posé que si l'interface est vraiment en wolof.
- `cd web && npm run traductions` donne la couverture et la liste « clé ; texte français » à traduire. Chaque texte validé par KBD s'ajoute dans `wo.ts` et le site le prend tout de suite.

### 4.8 Hors ligne et états (§7.3)

- Les 10 dernières réponses consultées sont gardées sur l'appareil (`lib/historique.ts`) et restent lisibles sans réseau.
- Un service worker (`public/sw.js`) garde les pages déjà visitées ; les appels à l'API ne sont jamais mis en cache.
- États conçus : chargement par étapes avec squelettes, hors ligne, erreur système avec code d'incident discret, réponse introuvable.

### 4.9 Journal des requêtes (`app/admin/journal/page.tsx`)

Filtres canal, langue, issue et recherche ; tableau paginé par 50 ; une requête de plus de 3 s ressort en ocre ; détail de chaque requête (transcription brute, indicateur, version du socle, conversation hachée, choix confirmé, vote, signalement, suggestion) ; export CSV avec les mêmes filtres. Le jeton est demandé à l'ouverture et reste seulement dans l'onglet. Les textes restent en français : c'est un outil d'équipe.

### 4.10 Sécurité et performance du site

- CSP en production (nos scripts, notre API, l'audio, rien d'autre), `Permissions-Policy` (micro pour le site seulement), pas d'en-tête `X-Powered-By`.
- Polices Unbounded, Bricolage Grotesque et Space Mono auto-hébergées (next/font), sous-ensemble latin, `font-display: swap`. Plus aucune requête vers un tiers. Le PDF embarque les mêmes polices, en TTF statiques (`backend/src/gestukaay_backend/polices`).
- Mesures Lighthouse en 3G rapide simulée, processeur ralenti ×4, écran 360 × 640 (`docs/performance.md`) :

| | Cible | Accueil | Réponse | Où je me situe |
|---|---|---|---|---|
| LCP | ≤ 2,5 s | 2,2 s | 2,1 s | 1,9 s |
| JavaScript initial | ≤ 150 Ko | 118 Ko | 122 Ko | 115 Ko |
| Poids total | ≤ 400 Ko | 186 Ko | 213 Ko | 182 Ko |
| Accessibilité | | 100 | 100 | 100 |

Reste à mesurer sur la préproduction et sur un vrai téléphone : l'INP (le temps de blocage de la page réponse est de 440 ms en local).

### 4.11 Accessibilité

Lien « Aller au contenu », titre propre à chaque page (la question pour une réponse), fenêtre d'écoute qui garde le focus et le rend au micro, tableau du graphique atteignable au clavier, cibles tactiles de 44 px au moins, badges avec texte et icône, jamais la couleur seule. À faire à la main pendant la recette : TalkBack, NVDA et zoom à 200 %.

## 5. Tests et CI

- **Backend** (`backend/tests/`) : API, exports, sécurité, situer (la saisie n'apparaît ni en base ni dans les journaux), stockage (persistance après redémarrage, hachage, filtres, accès admin), transcription.
- **Site** (`web/e2e/`, Playwright + axe-core, sur bureau et sur l'appareil de référence 360 × 640) : exacte, approchée, refus, projection, comparaison, exports, adresse `/r/…`, vote, signalement, Où je me situe, domaines, hors ligne, bascule FR/WO, journal, audio, en-têtes et CSP, accessibilité WCAG 2.1 A et AA sur chaque écran (le mode sombre, prévu en V1.1 par le cahier §9.10, n'est pas activé). 81 tests verts, 5 ignorés exprès (propres au bureau ou au mobile).
- **CI** (`.github/workflows/ci.yml`) : job `web` (types TypeScript, build de production, budget JavaScript, tests de bout en bout) et job `docker` (les deux images démarrent, une question renvoie une réponse exacte).

```bash
uv run python -m pytest                              # Python, toute l'équipe
cd web && npm run build && npm run test:e2e          # site
cd web && npm run budget                             # budget JavaScript
```

Les tests du site tournent sur le faux moteur : ils ne dépendent ni du socle ni d'une clé LLM.

## 6. Configuration utile (`.env.example`)

| Variable | Rôle |
|---|---|
| `GESTUKAAY_MOTEUR` | `fake` ou `reel` |
| `GESTUKAAY_URL_PUBLIQUE` | adresse du site, utilisée pour `/r/{id}`, la citation et CORS |
| `GESTUKAAY_SOCLE_EXTRAIT` | dossier du socle sur la machine (défaut `../socle_gestukaay`) |
| `GESTUKAAY_BASE` | base de données (PostgreSQL dans Docker) |
| `GESTUKAAY_SEL` | sel du hachage des conversations, fixe en préproduction |
| `GESTUKAAY_LIMITES` | `off` seulement pour les tests |
| `GESTUKAAY_PROXY_DE_CONFIANCE` | `1` derrière le proxy de l'hébergeur |
| `NEXT_PUBLIC_API_URL`, `API_INTERNE` | adresse de l'API vue du navigateur et vue du serveur web |

## 7. Écarts au cahier assumés par SAN

- **EF-26** : graphiques dessinés par le navigateur et non par Plotly côté serveur (décision 0016).
- **EF-33** : deux mentions de licence distinctes, aucune supposée (décision 0016).
- **EF-37 / EF-38** : taille du ménage en nombre exact, niveau d'instruction non demandé, comparaison aux moyennes publiées et non aux déciles (décisions 0004 et 0012).
- **Interface en wolof** : vide tant que KBD n'a pas traduit et validé les textes (décision 0009).
- **Page Méthode** : objectifs affichés, résultats seulement après la première mesure officielle.

## 8. Ce qui attend KBD côté intégration

- **Interface wolof** : `npm run traductions`, puis les textes validés dans `web/i18n/wo.ts`.
- **Webhook WhatsApp** : passer le numéro dans `conversation_id` (le backend le hache) et ne jamais le journaliser ailleurs. C'est un engagement écrit dans la page Confidentialité.
- **Audio** : une adresse HTTP dans `audio_url`, le lecteur fait le reste.
- **Rapport de mesure (#21)** : dès qu'il existe, SAN met les vrais chiffres sur la page Méthode.
- **Gini et autres notes** : tout ce qui arrive dans `note_perimetre` s'affiche déjà sur le site et dans le PDF.

## 9. Ce qui reste à faire côté SAN

- Rendre `NonDisponible` en 503 « Pas encore disponible » dans `app.py`, pour le vrai moteur ([PR #96](https://github.com/TechwithXalifa/gestukaay/pull/96)).
- Contrat 1.3.0, en ajout seulement : tranches `500k_750k`, `750k_1m`, `plus_1m` (`plus_500k` accepté mais plus proposé), motif `non_disponible`, mise à jour du site et de la décision 0012. Le calcul réel de « Où je me situe » ([#95](https://github.com/TechwithXalifa/gestukaay/issues/95)) attend cette version.
- Passer au moteur les 3 derniers échanges de la conversation (EF-09) : le moteur l'accepte, le backend ne le transmet pas encore.
- Préproduction en ligne ([#38](https://github.com/TechwithXalifa/gestukaay/issues/38)) : clé OpenRouter dans les secrets, proxy de confiance, Lighthouse sur la vraie adresse.
- `.gitattributes` qui garde les CSV en fins de ligne LF, pour que les empreintes du manifeste du socle se comparent aussi sous Windows (branche `san/csv-lf`).
- Écrans des maquettes pas encore construits : Explorer, Catalogue, Fiche indicateur, barre latérale mobile, tableau de bord et jeu de test du back-office. Explorer, Catalogue et Fiches demandent des routes qui ne sont pas encore dans le contrat (`/v1/indicators`, `/v1/series`).
- Routes des webhooks WhatsApp et Telegram, pour brancher la logique de KBD.
