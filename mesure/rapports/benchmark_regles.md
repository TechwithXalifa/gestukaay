# Rapport de Benchmark — Gëstukaay (regles)

- **Date** : 2026-10-05 15:39:36 UTC
- **Mode** : `regles`
- **Jeu de test** : 104 questions officielles

## 1. Cibles du cahier des charges (§12)

| Mesure | Cible | Obtenu | Statut |
|---|---|---|---|
| **Chiffres faux affichés** (confiance) | 0 | **10** | indicatif |
| **Exactitude** (sourcée, sur 84 questions) | ≥ 85 % | **81.0 %** (68/84) | indicatif |
| **Refus pertinent** (sur 20 refus) | ≥ 95 % | **80.0 %** (16/20) | indicatif |
| **Invariant « zéro chiffre inventé »** | Tolérance 0 | **0 violation(s)** | **CONFORME** |
| **Latence médiane** | < 3,0 s | **2.0 ms** (P95: 6.7 ms) | indicatif |

## 2. Sous-scores par type de question

| Type | Réussite | Pourcentage |
|---|---|---|
| Correspondance approchée (choix vivants) | 6/11 | 54.5 % |
| Classement (14 régions ou 16 académies) | 9/10 | 90.0 % |
| Comparaison spatiale (multi-zones) | 10/10 | 100.0 % |
| Comparaison temporelle (deux périodes) | 5/5 | 100.0 % |
| Refus officiel (hors socle, projection, inintelligible) | 16/20 | 80.0 % |
| Simple (valeur exacte directe) | 34/43 | 79.1 % |
| Suivi contextuel (suite_de) | 4/5 | 80.0 % |

## 3. Sous-scores par langue

| Langue | Réussite | Pourcentage |
|---|---|---|
| Français | 64/73 | 87.7 % |
| Wolof | 20/31 | 64.5 % |

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

## 6. Détail des écarts (20 questions non conformes)

| Id | Type | Langue | Attendu | Obtenu | Détail |
|---|---|---|---|---|---|
| FR-018 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-025 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-047 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-049 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-051 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-054 | approchee | fr | approchee | exacte | issue attendue approchee, obtenu exacte |
| FR-062 | refus | fr | aucune | exacte | issue attendue aucune, obtenu exacte |
| FR-066 | refus | fr | aucune | approchee | issue attendue aucune, obtenu approchee |
| FR-073 | simple | fr | exacte | exacte | attendu [('SN', '2026-T1', 1590818.0)] != obtenu [('SN', '2025', 20.4)] |
| WO-001 | simple | wo | exacte | exacte | attendu [('SN-TH', '2023', 2463677.0)] != obtenu [('SN-TH', '2023', 57.5)] |
| WO-002 | simple | wo | exacte | exacte | attendu [('SN', '2026-T1', 1590818.0)] != obtenu [('SN', '2025', 20.4)] |
| WO-005 | simple | wo | exacte | exacte | attendu [('SN-IA-LOUGA', '2025', 86.6806)] != obtenu [('SN-IA-LOUGA', '2025', 56.3)] |
| WO-009 | simple | wo | exacte | approchee | issue attendue exacte, obtenu approchee |
| WO-017 | classement | wo | exacte | exacte | classement: attendu SN-DK=4004426.0, obtenu SN-DK=5958.0 |
| WO-020 | approchee | wo | approchee | aucune | issue attendue approchee, obtenu aucune |
| WO-021 | simple | wo | exacte | aucune | issue attendue exacte, obtenu aucune |
| WO-024 | approchee | wo | approchee | exacte | issue attendue approchee, obtenu exacte |
| WO-026 | refus | wo | aucune | aucune | motif attendu 'hors_socle', obtenu 'incomprehension' |
| WO-031 | refus | wo | aucune | exacte | issue attendue aucune, obtenu exacte |
| WO-029 | suivi | wo | exacte | exacte | attendu [('SN-KL', '2023', 1336720.0)] != obtenu [('SN-KL', '2023', 38.2)] |
