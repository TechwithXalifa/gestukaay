# 0038 — Délai du LLM tenu pour de bon, et relais en parallèle

**Date** : 2026-10-08 · **Statut** : accepté (KBD) · **Issue** : #156 · **Complète** : 0010, 0034

## Contexte

Recette du 08/10 (237 questions, vrai moteur) : avec `LLM_PRINCIPAL_DELAI_S=3`, Flash était coupé sur
48 % des questions, et toute la chaîne LLM échouait sur 35 %. L'utilisateur attendait alors environ 10 s,
puis les règles locales répondaient, souvent avec un chiffre vrai pour une autre question (« Population de
Paris » → population du Sénégal). Deux causes :

- le délai n'était pas tenu : le chronomètre global n'était regardé qu'à l'arrivée d'un morceau de
  réponse, et le délai de lecture de httpx repartait après chaque morceau. Un délai de 3 s durait jusqu'à
  7,3 s, un délai de 2 s jusqu'à 5 s ;
- les maillons passaient l'un après l'autre : Flash lent, puis Flash-Lite lent, puis les règles.

Latence mesurée sans coupure (40 questions, 08/10) :

| | médiane | 75 % | 90 % | 95 % | sans réponse après 20 s |
|---|---|---|---|---|---|
| Gemini 2.5 Flash | 1,9 s | 2,7 s | 3,6 s | 5,6 s | 4 sur 40 |
| Gemini 2.5 Flash-Lite | 1,3 s | 2,0 s | 3,8 s | 8,1 s | 0 (2 JSON invalides) |

## Décision (choix de KBD : « la réponse la plus rapide et la meilleure »)

- Le délai d'un maillon est une **échéance réelle** : chaque maillon tourne dans un fil, abandonné à
  l'échéance, quoi que fasse le fournisseur.
- **Relais** (`LLM_<N>_RELAIS_S`) : si le maillon N n'a pas répondu au bout de ce temps, le suivant part en
  parallèle. La réponse du premier dans l'ordre de la chaîne reste préférée tant qu'il est dans son délai.
- Réglages : Flash `DELAI_S=4` (90 % de ses réponses), `RELAIS_S=2` ; Flash-Lite `DELAI_S=3`. Flash est
  servi chaque fois qu'il répond en moins de 4 s ; au-delà, la réponse de Flash-Lite, souvent déjà prête.
  Au pire, les règles locales répondent à 5 s au lieu de 10 s.
- Sans `RELAIS_S`, la chaîne reste séquentielle (comportement d'avant).

## Conséquences

- Un appel de Flash-Lite en plus quand Flash dépasse 2 s (environ 3 questions sur 10), à 0,0003 $ l'appel.
- `Appel.latence_ms` est la durée réelle de l'appel ; une tentative abandonnée parce qu'un maillon préféré a
  répondu est notée `abandon`.
- Les valeurs sont à remesurer sur le réseau de la préproduction (#38) : on ne change que l'environnement.
