# Gëstukaay

Les statistiques officielles du Sénégal, en réponse à une question posée en français ou en wolof, à l'écrit ou à
la voix, sur le web, WhatsApp et Telegram.

> **Gëstukaay ne génère jamais un chiffre. Il retrouve un chiffre officiel et le met en forme.**

Hackathon ANSD 20 ans, Challenge Open Data. Équipe : Khalifa Babacar DIOUF (KBD) et Serigne Abdoul Aziz NDIAYE
(SAN).

**Déployer la solution depuis zéro : [DEPLOIEMENT.md](DEPLOIEMENT.md).**

## Ce que fait Gëstukaay

- **Une question, le chiffre officiel.** « Combien coûte le riz à Thiès ? », « Ñata nit ñoo dëkk Cees ? » : la
  réponse donne la valeur, sa source (producteur, publication, date), la zone et la période. Elle est accompagnée
  d'un graphique, d'exports PDF et CSV, d'une citation et d'une adresse stable à partager.
- **Français et wolof, écrit et voix.** Une note vocale en wolof est transcrite (M-Kiriku), et la réponse peut
  revenir en note vocale wolof (Oolel-Voices). Les deux modèles tournent sur la machine qui héberge la solution.
- **Jamais un chiffre inventé.** Quand la donnée n'existe pas, Gëstukaay refuse et propose des indicateurs proches.
  Quand la question est ambiguë (une ville, une année non publiée, une catégorie), il propose des choix et
  n'affiche aucune valeur avant la confirmation.
- **Web, WhatsApp et Telegram** passent par le même moteur et donnent les mêmes réponses.
- **Sur le site aussi** :
  - le catalogue des indicateurs, une fiche par indicateur et l'explorateur (courbes par zone) ;
  - « Où je me situe » : comparer les dépenses de son ménage aux moyennes publiées ;
  - un back-office : journal des questions, tableau de bord, jeu de test.

## En chiffres

| | |
|---|---|
| Socle de données | **642 125** valeurs officielles de **376** jeux du portail Open Data du Sénégal (ANSD et 48 producteurs), version 2026.10.1 |
| Exactitude mesurée (avec Gemini 2.5 Flash) | **98,8 %** (83 sur 84 questions à chiffre), **0 chiffre faux**, **100 %** de refus pertinents |
| Temps de réponse | **1,4 s** en médiane (texte) |
| Voix sur GPU NVIDIA T4 | une note de 10 s transcrite en 1,9 s ; une réponse vocale de 10 s calculée en 8,7 s |

La mesure porte sur 113 questions de référence (78 en français, 35 en wolof), pour la plupart écrites avant le
développement, avec leurs erreurs publiées : [rapport de mesure](mesure/rapports/rapport_de_mesure.md).

## Comment ça marche

```
question (texte ou note vocale)
  │  note vocale : transcription M-Kiriku
  ▼
compréhension ── Gemini 2.5 Flash, puis Flash-Lite ; règles locales en secours
  │              → une requête structurée : indicateur, zones, période, catégorie
  ▼
résolution ───── déterministe, dans le socle : la valeur publiée, sa source et sa date
  │              ou une réponse approchée (des choix) ou un refus (des indicateurs proches)
  ▼
mise en forme ── phrases fixes (gabarits) en français et en wolof, graphique, exports
  │              voix wolof : Oolel-Voices
  ▼
site web · WhatsApp · Telegram
```

- **Le LLM ne voit jamais un chiffre.** Il traduit seulement la question en requête. La valeur vient toujours du
  socle, et chaque nombre affiché est contrôlé : l'invariant « zéro chiffre inventé » est vérifié sur chaque
  réponse du jeu de test.
- **Le socle** est une extraction figée et versionnée du portail Open Data
  ([socle/README.md](socle/README.md)). Les erreurs des données publiées sont exclues, jamais réparées : par
  exemple, des lignes régionales décalées sur le portail ([décision 0008](docs/decisions/0008-controles-et-corrections.md)).
- **Le contrat d'API** est versionné : [docs/api/contrat-v1.md](docs/api/contrat-v1.md), et le schéma OpenAPI est
  servi par l'API sur `/docs`.
- **Les choix du projet** sont consignés dans [docs/decisions/](docs/decisions/), une décision par fichier.

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `engine/` | Moteur : compréhension, résolution, réponses approchées, refus, gabarits, voix |
| `socle/` | Construction, contrôles et référentiels du socle de données (zones, indicateurs, corrections) |
| `backend/` | API FastAPI, persistance PostgreSQL, exports PDF et CSV, back-office |
| `web/` | Site Next.js |
| `canaux/` | WhatsApp et Telegram |
| `transcription/`, `synthese/` | Services de voix sur GPU (M-Kiriku, Oolel-Voices) |
| `contracts/` | Contrat d'échange (Pydantic → JSON Schema → TypeScript) |
| `mesure/` | Jeu de test, benchmark, rapports de mesure |
| `docs/` | Contrat d'API, décisions, méthode de travail |

## Développer

```bash
brew install uv          # gestionnaire Python (installe aussi Python 3.12)
uv sync --all-packages   # dépendances
uv run pytest            # tout doit être vert
cp .env.example .env     # puis remplir (voir DEPLOIEMENT.md, section 4)
./scripts/recuperer_socle.sh
```

- **Mesurer** :
  - `uv run python mesure/scripts/benchmark.py --regles` : gratuit et sans réseau ;
  - `--llm` : la mesure de référence, avec la clé Gemini.
- **Lancer avec Docker** : suivre [DEPLOIEMENT.md](DEPLOIEMENT.md). Sans `.env`, `docker compose up` démarre le
  faux moteur (réponses d'exemple du contrat), qui sert à développer le site. Sur un poste sans GPU NVIDIA, vider
  `COMPOSE_PROFILES` dans `.env` : la voix en a besoin.
- **Le socle hors Docker** : `./scripts/recuperer_socle.sh` le met dans `./socle_gestukaay`, le chemin de
  `.env.example` (`GESTUKAAY_SOCLE_EXTRAIT`).
- **Lancer la voix hors Docker** : `uv run transcription/serveur.py` et `uv run synthese/serveur.py`, sur une machine
  avec GPU. L'API les joint à `TRANSCRIPTION_URL` et `SYNTHESE_URL`.
- **Back-office** : un compte nominatif, créé en ligne de commande (décision 0037). Sans compte, le back-office
  est fermé.

  ```bash
  docker compose exec api python -m gestukaay_backend.comptes creer <identifiant>
  ```

  Aussi : `changer` (nouveau mot de passe), `desactiver`, `lister`.

## Licences

- **Données** : portail Open Data du Sénégal (ANSD et producteurs officiels), citées avec leur source à chaque
  réponse.
- **Modèles de voix**, utilisés tels quels : M-Kiriku-ASR (AIHubSN, Apache 2.0) et Oolel-Voices (Soynade
  Research, AGPL-3.0).

Référence fonctionnelle : cahier des charges v1.1 (30 septembre 2026).
