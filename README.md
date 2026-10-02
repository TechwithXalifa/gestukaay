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

Pour le vrai moteur : `GESTUKAAY_MOTEUR=reel` et la clé `LLM_PRINCIPAL_CLE` dans `.env`, et le socle
extrait dans `../socle_gestukaay` (ou le chemin donné par `GESTUKAAY_SOCLE_EXTRAIT`). Il est monté en
lecture seule dans l'API.

Référence fonctionnelle : cahier des charges v1.1 (30 septembre 2026).
