# Rapport de Benchmark — Gëstukaay (llm-google-gemini-2.5-flash)

- **Date** : 2026-10-04 16:35:01 UTC
- **Mode** : `llm-google-gemini-2.5-flash`
- **Jeu de test** : 103 questions officielles

## 1. Cibles du cahier des charges (§12)

| Mesure | Cible | Obtenu | Statut |
|---|---|---|---|
| **Chiffres faux affichés** (confiance) | 0 | **2** | NON CONFORME |
| **Exactitude** (sourcée, sur 83 questions) | ≥ 85 % | **89.2 %** (74/83) | CONFORME |
| **Refus pertinent** (sur 20 refus) | ≥ 95 % | **100.0 %** (20/20) | CONFORME |
| **Invariant « zéro chiffre inventé »** | Tolérance 0 | **0 violation(s)** | **CONFORME** |
| **Latence médiane** (évaluée (< 3 s)) | < 3,0 s | **1392.7 ms** (P95: 1995.9 ms) | CONFORME |

## 2. Sous-scores par type de question

| Type | Réussite | Pourcentage |
|---|---|---|
| Correspondance approchée (choix vivants) | 6/11 | 54.5 % |
| Classement (14 régions ou 16 académies) | 10/10 | 100.0 % |
| Comparaison spatiale (multi-zones) | 10/10 | 100.0 % |
| Comparaison temporelle (deux périodes) | 5/5 | 100.0 % |
| Refus officiel (hors socle, projection, inintelligible) | 20/20 | 100.0 % |
| Simple (valeur exacte directe) | 38/42 | 90.5 % |
| Suivi contextuel (suite_de) | 5/5 | 100.0 % |

## 3. Sous-scores par langue

| Langue | Réussite | Pourcentage |
|---|---|---|
| Français | 67/72 | 93.1 % |
| Wolof | 27/31 | 87.1 % |

## 4. Invariant « zéro chiffre inventé »

> **Invariant strictement vérifié** : aucune violation détectée sur les 103 questions.
- Volet (a) : 100 % des `Resultat` servis proviennent d'une observation du socle avec la valeur exacte.
- Volet (b) : 100 % des points de graphiques correspondent à des observations du socle.
- Volet (c) : tous les chiffres figurant dans les explications appartiennent à la liste blanche des données officielles affichées.
- Volet (d) : aucune valeur numérique statistique n'apparaît dans une réponse approchée ou un refus.

## 6. Détail des écarts (9 questions non conformes)

| Id | Type | Langue | Attendu | Obtenu | Détail |
|---|---|---|---|---|---|
| FR-018 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-020 | simple | fr | exacte | exacte | attendu [('SN', '2019', 17.9)] != obtenu [('SN', '2023', 17.5)] |
| FR-047 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-051 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-054 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| WO-002 | simple | wo | exacte | exacte | attendu [('SN', '2025', 20.4)] != obtenu [('SN', '2026-T1', 1590818.0)] |
| WO-009 | simple | wo | exacte | approchee | issue attendue exacte, obtenu approchee |
| WO-020 | approchee | wo | approchee | aucune | issue attendue approchee, obtenu aucune |
| WO-024 | approchee | wo | approchee | aucune | issue attendue approchee, obtenu aucune |
