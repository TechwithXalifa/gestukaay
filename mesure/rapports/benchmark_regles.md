# Rapport de Benchmark — Gëstukaay (regles)

- **Date** : 2026-10-04 04:06:55 UTC
- **Mode** : `regles`
- **Jeu de test** : 103 questions officielles

## 1. Cibles du cahier des charges (§12)

| Mesure | Cible | Obtenu | Statut |
|---|---|---|---|
| **Chiffres faux affichés** (confiance) | 0 | **9** | indicatif |
| **Exactitude** (sourcée, sur 83 questions) | ≥ 85 % | **81.9 %** (68/83) | indicatif |
| **Refus pertinent** (sur 20 refus) | ≥ 95 % | **80.0 %** (16/20) | indicatif |
| **Invariant « zéro chiffre inventé »** | Tolérance 0 | **0 violation(s)** | **CONFORME** |
| **Latence médiane** (indicatif) | < 3,0 s | **3.7 ms** (P95: 19.1 ms) | indicatif |

## 2. Sous-scores par type de question

| Type | Réussite | Pourcentage |
|---|---|---|
| Correspondance approchée (choix vivants) | 6/11 | 54.5 % |
| Classement (14 régions ou 16 académies) | 8/10 | 80.0 % |
| Comparaison spatiale (multi-zones) | 10/10 | 100.0 % |
| Comparaison temporelle (deux périodes) | 5/5 | 100.0 % |
| Refus officiel (hors socle, projection, inintelligible) | 16/20 | 80.0 % |
| Simple (valeur exacte directe) | 35/42 | 83.3 % |
| Suivi contextuel (suite_de) | 4/5 | 80.0 % |

## 3. Sous-scores par langue

| Langue | Réussite | Pourcentage |
|---|---|---|
| Français | 63/72 | 87.5 % |
| Wolof | 21/31 | 67.7 % |

## 4. Invariant « zéro chiffre inventé »

> **Invariant strictement vérifié** : aucune violation détectée sur les 103 questions.
- Volet (a) : 100 % des `Resultat` servis proviennent d'une observation du socle avec la valeur exacte.
- Volet (b) : 100 % des points de graphiques correspondent à des observations du socle.
- Volet (c) : tous les chiffres figurant dans les explications appartiennent à la liste blanche des données officielles affichées.
- Volet (d) : aucune valeur numérique statistique n'apparaît dans une réponse approchée ou un refus.

## 5. Défauts constatés du moteur (signalements sans modification de engine/src)

- FR-045 (classement mortalité) : le motif `_ORDRE_ASC` du moteur capture à tort « moins de » dans « moins de 5 ans » (comprehension.py et resolution.py), produisant un tri croissant au lieu du tri décroissant attendu. Défaut moteur à corriger côté engine.

## 6. Détail des écarts (19 questions non conformes)

| Id | Type | Langue | Attendu | Obtenu | Détail |
|---|---|---|---|---|---|
| FR-018 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-025 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-045 | classement | fr | exacte | exacte | classement: attendu SN-SL=77.0, obtenu SN-LG=20.0 |
| FR-047 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-049 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| FR-051 | approchee | fr | approchee | aucune | issue attendue approchee, obtenu aucune |
| FR-054 | approchee | fr | approchee | exacte | issue attendue approchee, obtenu exacte |
| FR-062 | refus | fr | aucune | exacte | issue attendue aucune, obtenu exacte |
| FR-066 | refus | fr | aucune | approchee | issue attendue aucune, obtenu approchee |
| WO-001 | simple | wo | exacte | exacte | attendu [('SN-TH', '2023', 2463677.0)] != obtenu [('SN-TH', '2023', 57.5)] |
| WO-005 | simple | wo | exacte | exacte | attendu [('SN-IA-LOUGA', '2025', 86.6806)] != obtenu [('SN-IA-LOUGA', '2025', 56.3)] |
| WO-009 | simple | wo | exacte | approchee | issue attendue exacte, obtenu approchee |
| WO-017 | classement | wo | exacte | exacte | classement: attendu SN-DK=4004426.0, obtenu SN-DK=5958.0 |
| WO-020 | approchee | wo | approchee | aucune | issue attendue approchee, obtenu aucune |
| WO-021 | simple | wo | exacte | aucune | issue attendue exacte, obtenu aucune |
| WO-024 | approchee | wo | approchee | exacte | issue attendue approchee, obtenu exacte |
| WO-026 | refus | wo | aucune | aucune | motif attendu 'hors_socle', obtenu 'incomprehension' |
| WO-031 | refus | wo | aucune | exacte | issue attendue aucune, obtenu exacte |
| WO-029 | suivi | wo | exacte | exacte | attendu [('SN-KL', '2023', 1336720.0)] != obtenu [('SN-KL', '2023', 38.2)] |
