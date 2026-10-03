# Gëstukaay

Le moteur de réponse officiel des données statistiques du Sénégal — web, WhatsApp, français et wolof.

> **Gëstukaay ne génère jamais un chiffre. Il retrouve un chiffre officiel et le met en forme.**

Hackathon ANSD 20 ans — Challenge Open Data. Équipe : Khalifa Babacar DIOUF (KBD) · Serigne Abdoul Aziz NDIAYE (SAN).

## Organisation du dépôt

| Dossier | Contenu | Responsable |
|---|---|---|
| `contracts/` | Contrat d'échange (Pydantic → JSON Schema → TypeScript), exemples de réponses | KBD + SAN |
| `engine/` | Moteur : compréhension (LLM), résolution déterministe, gabarits | KBD |
| `socle/` | Construction et contrôles du socle de données | KBD |
| `canaux/` | WhatsApp, Telegram, voix | KBD |
| `backend/` | API FastAPI, persistance, exports, graphiques | SAN |
| `web/` | Interface Next.js | SAN |
| `docs/` | [Contrat d'API](docs/api/contrat-v1.md) · [Méthode de travail](docs/methode-de-travail.md) · [Décisions](docs/decisions/) | KBD + SAN |

## Démarrage

```bash
brew install uv          # gestionnaire Python (installe aussi Python 3.12)
uv sync                  # dépendances
uv run pytest            # tout doit être vert
cp .env.example .env     # puis remplir
```

Ou, sans rien installer d'autre que Docker :

```bash
docker compose up --build   # site : http://localhost:3000 · API : http://localhost:8000/docs
```

Pour le vrai moteur : `GESTUKAAY_MOTEUR=reel`, la chaîne LLM dans `.env` (`LLM_CHAINE`,
`LLM_PRINCIPAL_CLE`… ; sans elle, compréhension par règles locales), et le socle extrait dans
`../socle_gestukaay` (ou le chemin donné par `GESTUKAAY_SOCLE_EXTRAIT`). Il est monté en lecture seule
dans l'API. La voix et « Où je me situe » ne sont pas encore construits dans le vrai moteur (décision 0019).

Les réponses, le journal des requêtes et les retours sont gardés dans PostgreSQL (service `db`), donc
les liens `/r/…` survivent à un redémarrage. Hors Docker, l'API utilise SQLite en mémoire, ou un
fichier avec `GESTUKAAY_BASE=sqlite:///gestukaay.db`. Le journal se lit sur `/admin/journal` (et
`/admin/journal.csv`) avec l'en-tête `Authorization: Bearer <GESTUKAAY_ADMIN_JETON>`. Sans ce jeton,
le back-office est fermé.

Référence fonctionnelle : cahier des charges v1.1 (30 septembre 2026).
