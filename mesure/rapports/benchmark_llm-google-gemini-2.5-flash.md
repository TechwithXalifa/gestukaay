# Rapport de Benchmark — Gëstukaay (llm-google-gemini-2.5-flash)

- **Date** : 2026-10-08 11:26:19 UTC
- **Mode** : `llm-google-gemini-2.5-flash`
- **Jeu de test** : 104 questions officielles

## 1. Cibles du cahier des charges (§12)

| Mesure | Cible | Obtenu | Statut |
|---|---|---|---|
| **Chiffres faux affichés** (confiance) | 0 | **1** | NON CONFORME |
| **Exactitude** (sourcée, sur 84 questions) | ≥ 85 % | **97.6 %** (82/84) | CONFORME |
| **Refus pertinent** (sur 20 refus) | ≥ 95 % | **95.0 %** (19/20) | CONFORME |
| **Invariant « zéro chiffre inventé »** | Tolérance 0 | **0 violation(s)** | **CONFORME** |
| **Latence médiane** | < 3,0 s | **1812.0 ms** (P95: 2805.0 ms) | CONFORME |

## 2. Sous-scores par type de question

| Type | Réussite | Pourcentage |
|---|---|---|
| Correspondance approchée (choix vivants) | 11/11 | 100.0 % |
| Classement (14 régions ou 16 académies) | 10/10 | 100.0 % |
| Comparaison spatiale (multi-zones) | 10/10 | 100.0 % |
| Comparaison temporelle (deux périodes) | 5/5 | 100.0 % |
| Refus officiel (hors socle, projection, inintelligible) | 19/20 | 95.0 % |
| Simple (valeur exacte directe) | 41/43 | 95.3 % |
| Suivi contextuel (suite_de) | 5/5 | 100.0 % |

## 3. Sous-scores par langue

| Langue | Réussite | Pourcentage |
|---|---|---|
| Français | 72/73 | 98.6 % |
| Wolof | 29/31 | 93.5 % |

## 4. Invariant « zéro chiffre inventé »

> **Invariant strictement vérifié** : aucune violation détectée sur les 104 questions.
- Volet (a) : 100 % des `Resultat` servis proviennent d'une observation du socle avec la valeur exacte.
- Volet (b) : 100 % des points de graphiques correspondent à des observations du socle.
- Volet (c) : tous les chiffres figurant dans les explications appartiennent à la liste blanche des données officielles affichées.
- Volet (d) : aucune valeur numérique statistique n'apparaît dans une réponse approchée ou un refus.

## 5. Changements du jeu de test

Attendus modifiés ou questions ajoutées depuis la première mesure, avec leur raison (`mesure/jeu_de_test/changements.csv`).

| Id | Date | Décision | Changement | Raison |
|---|---|---|---|---|
| WO-002 | 2026-10-04 | 0024 | Attendu changé : le taux de chômage annuel (20,4 %, 2025) devient le nombre de personnes au chômage (T1 2026), suivi du taux publié au même trimestre. | KBD, locuteur natif : « Ñi amul ligéey ci Senegaal ? » demande combien de personnes, pas un taux. Changé après la passe LLM du 4/10, où le moteur servait déjà le nombre et la question comptait comme chiffre faux : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| FR-073 | 2026-10-04 | 0024 | Question ajoutée : « Combien de personnes sont au chômage au Sénégal ? » (nombre puis taux). | La même demande en français, pour mesurer les deux langues. Le jeu passe de 103 à 104 questions. |
| FR-059 | 2026-10-07 | 0033 | Motif attendu changé : hors_socle devient conversation. | KBD : un message hors sujet (président, météo, poème) reçoit une réponse de conversation (« je ne réponds qu'aux statistiques… »), pas « cette donnée n'existe pas », réservé aux données absentes. Changé après la passe LLM du 7/10, où ces 5 questions comptaient comme refus non conformes : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| FR-060 | 2026-10-07 | 0033 | Motif attendu changé : hors_socle devient conversation. | KBD : un message hors sujet (président, météo, poème) reçoit une réponse de conversation (« je ne réponds qu'aux statistiques… »), pas « cette donnée n'existe pas », réservé aux données absentes. Changé après la passe LLM du 7/10, où ces 5 questions comptaient comme refus non conformes : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| FR-063 | 2026-10-07 | 0033 | Motif attendu changé : hors_socle devient conversation. | KBD : un message hors sujet (président, météo, poème) reçoit une réponse de conversation (« je ne réponds qu'aux statistiques… »), pas « cette donnée n'existe pas », réservé aux données absentes. Changé après la passe LLM du 7/10, où ces 5 questions comptaient comme refus non conformes : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| WO-025 | 2026-10-07 | 0033 | Motif attendu changé : hors_socle devient conversation. | KBD : un message hors sujet (président, météo, poème) reçoit une réponse de conversation (« je ne réponds qu'aux statistiques… »), pas « cette donnée n'existe pas », réservé aux données absentes. Changé après la passe LLM du 7/10, où ces 5 questions comptaient comme refus non conformes : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| WO-026 | 2026-10-07 | 0033 | Motif attendu changé : hors_socle devient conversation. | KBD : un message hors sujet (président, météo, poème) reçoit une réponse de conversation (« je ne réponds qu'aux statistiques… »), pas « cette donnée n'existe pas », réservé aux données absentes. Changé après la passe LLM du 7/10, où ces 5 questions comptaient comme refus non conformes : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| FR-051 | 2026-10-07 | 0030 | Choix attendus changés : département de Mbacké devient région de Diourbel ou Sénégal. | La population (RGPH-5) n'est publiée que par région  |

## 6. Détail des écarts (3 questions non conformes)

| Id | Type | Langue | Attendu | Obtenu | Détail |
|---|---|---|---|---|---|
| FR-020 | simple | fr | exacte | exacte | attendu [('SN', '2019', 17.9)] != obtenu [('SN', '2023', 17.5)] |
| WO-009 | simple | wo | exacte | approchee | issue attendue exacte, obtenu approchee |
| WO-028 | refus | wo | aucune | aucune | motif attendu 'incomprehension', obtenu 'conversation' |
