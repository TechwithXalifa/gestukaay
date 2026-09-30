# 0001 — Monorepo et contrat d'API d'abord

**Date** : 2026-09-30 · **Statut** : proposé (à valider par SAN)

**Contexte.** Deux développeurs à distance, moins d'une semaine, deux moitiés (moteur / web)
qui doivent s'emboîter sans intégration de dernière minute.

**Décision.**
- Un seul dépôt Git ; propriété des dossiers par CODEOWNERS.
- Contrat d'échange écrit en Pydantic (`contracts/`), schéma JSON et types TypeScript générés.
- Moteur derrière une interface Python (`engine/interface.py`) avec un moteur factice.
- LLM appelé via une API compatible OpenAI (OpenRouter par défaut), configurée par variables
  d'environnement, pour changer de fournisseur sans toucher au code.

**Conséquences.** Le web et le backend avancent dès J0 sur le faux moteur. Tout changement de
format passe par une PR commune. Le backend doit être en Python pour appeler le moteur directement.
