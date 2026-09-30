# Contribuer à Gëstukaay

Le détail est dans [docs/methode-de-travail.md](docs/methode-de-travail.md). L'essentiel :

1. On ne pousse jamais sur `main` : une tâche = une branche courte (`kbd/…`, `san/…`, `contrat/…`) = une PR.
2. `main` est toujours vert et démontrable.
3. On relit la PR de l'autre dans les 2 heures.
4. Le contrat (`contracts/`) ne change que par une PR `contrat/…` approuvée par les deux.
5. Aucun secret dans Git : `.env.example` documente, `.env` reste local.
6. Une décision qui engage l'autre s'écrit dans `docs/decisions/`.

Démarrage :

```bash
brew install uv
uv sync
uv run pytest
```
