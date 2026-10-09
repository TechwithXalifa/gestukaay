# Rapport de Benchmark — Gëstukaay (llm-gemini-2.5-flash)

- **Date** : 2026-10-09 00:48:45 UTC
- **Mode** : `llm-gemini-2.5-flash`
- **Jeu de test** : 113 questions officielles

## 1. Cibles du cahier des charges (§12)

| Mesure | Cible | Obtenu | Statut |
|---|---|---|---|
| **Chiffres faux affichés** (confiance) | 0 | **1** | NON CONFORME |
| **Exactitude** (sourcée, sur 84 questions) | ≥ 85 % | **95.2 %** (80/84) | CONFORME |
| **Refus pertinent** (sur 19 refus) | ≥ 95 % | **100.0 %** (19/19) | CONFORME |
| Hors sujet : réponse de conversation (0033) | — | **10/10** | indicatif |
| **Invariant « zéro chiffre inventé »** | Tolérance 0 | **6 violation(s)** | **VIOLATION** |
| **Latence médiane** | < 3,0 s | **1501.5 ms** (P95: 5029.3 ms) | CONFORME |

## 2. Sous-scores par type de question

| Type | Réussite | Pourcentage |
|---|---|---|
| Correspondance approchée (choix vivants) | 11/11 | 100.0 % |
| Classement (14 régions ou 16 académies) | 10/10 | 100.0 % |
| Comparaison spatiale (multi-zones) | 10/10 | 100.0 % |
| Comparaison temporelle (deux périodes) | 5/5 | 100.0 % |
| Hors sujet (réponse de conversation, 0033) | 10/10 | 100.0 % |
| Refus officiel (hors socle, projection, inintelligible) | 19/19 | 100.0 % |
| Simple (valeur exacte directe) | 39/43 | 90.7 % |
| Suivi contextuel (suite_de) | 5/5 | 100.0 % |

## 3. Sous-scores par langue

| Langue | Réussite | Pourcentage |
|---|---|---|
| Français | 76/78 | 97.4 % |
| Wolof | 33/35 | 94.3 % |

## 4. Invariant « zéro chiffre inventé »

> **ALERTE : 6 violation(s) de l'invariant constatée(s) !**

| Question | Volet | Détail |
|---|---|---|
| WO-009 | b | point barre Matam (SN-MT) y=3419.0 absent du socle pour l'indicateur wrqfsxb.quantite |
| WO-009 | b | point barre Sédhiou (SN-SE) y=1772.0 absent du socle pour l'indicateur wrqfsxb.quantite |
| WO-009 | b | point barre Kédougou (SN-KE) y=1309.0 absent du socle pour l'indicateur wrqfsxb.quantite |
| WO-009 | b | point barre Tambacounda (SN-TC) y=900.0 absent du socle pour l'indicateur wrqfsxb.quantite |
| WO-009 | b | point barre Kolda (SN-KD) y=804.0 absent du socle pour l'indicateur wrqfsxb.quantite |
| WO-009 | b | point barre Kaffrine (SN-KA) y=53.0 absent du socle pour l'indicateur wrqfsxb.quantite |

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
| FR-051 | 2026-10-07 | 0030 | Choix attendus changés : département de Mbacké devient région de Diourbel ou Sénégal. | La population (RGPH-5) n'est publiée que par région, le Tableau 1.1 (projection de 2013) n'est pas utilisé (choix de KBD, 0030). Changé après la passe LLM du 7/10. |
| FR-020 | 2026-10-08 | 0035 | Attendu changé : 17,9 % (xsitdae, EDS 2019) devient 17,5 % (pagfmnc, EDS 2023). | La question ne cite pas d'année : la dernière valeur publiée est attendue (US-06). pagfmnc est la même série que xsitdae (17,9 % en 2019 dans les deux) et publie 2023. Changé après la passe LLM du 8/10, où la réponse 17,5 % comptait comme seul chiffre faux : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| WO-028 | 2026-10-08 | 0033 | Motif attendu élargi : incomprehension devient incomprehension ou conversation. | Bavardage sans question statistique : depuis la 0033, un message hors sujet reçoit une réponse de conversation (« je réponds seulement aux statistiques… », avec un exemple), comme FR-059 et WO-025. Les règles répondent « je n'ai pas compris », le LLM la conversation : les deux refusent sans deviner d'indicateur. Changé après la passe LLM du 8/10 (KBD) : signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |
| FR-059|FR-060|FR-063|WO-025|WO-026|WO-028 | 2026-10-08 | 0033 | Type changé : refus devient conversation (mesuré à part). | KBD : un refus est une demande de chiffre que l'ANSD ne publie pas (cahier : « refus explicite en l'absence de donnée officielle »), un message qui ne demande pas de chiffre (président, météo, poème, bavardage) est un hors-sujet, qui reçoit une réponse de conversation. « Refus pertinents » ne compte plus que les vrais refus, et non les conversations comme avant. |
| FR-074|WO-032|WO-033|WO-034|WO-035 | 2026-10-08 | 0033 | Questions ajoutées : cinq vrais refus « donnée absente » (iPhone, plages, bâtiments brûlés, noyade, 5G). | Écrites par KBD (wolof d'usage) pour remplacer les hors-sujet sortis des refus. Données absentes vérifiées dans le référentiel. Avant ajout, en règles : plages et noyade donnaient un chiffre voisin (fécondité, mortalité des enfants), le LLM refusait bien. |
| FR-075|FR-076|FR-077|FR-078 | 2026-10-08 | 0033 | Questions ajoutées : quatre hors-sujet (points cardinaux, capitale de la Zambie, champion de football, maire de Saint-Louis). | Écrites par KBD. Avant ajout, en règles : points cardinaux -> points d'eau (approchée), football et maire -> « donnée absente », le LLM répondait bien en conversation. |
| FR-018 | 2026-10-08 | 0035 | Attendu changé : 1 011 269 t (ovothxc, 2017) devient 991 551 t (dwehszb, 2023). | La question ne cite pas d'année : la dernière valeur publiée est attendue (US-06). dwehszb (BADIS) est la même série que ovothxc (1 011 269 t en 2017 dans les deux) et publie 2023. Signalé dans #162 (recette du 8/10), validé par KBD le 8/10 (dwehszb vérifié) : changé après la mesure, signalé ici pour qu'on ne lise pas un examen ajusté au moteur. |

## 6. Détail des écarts (4 questions non conformes)

| Id | Type | Langue | Attendu | Obtenu | Détail |
|---|---|---|---|---|---|
| FR-015 | simple | fr | exacte | approchee | issue attendue exacte, obtenu approchee |
| FR-049 | simple | fr | exacte | aucune | issue attendue exacte, obtenu aucune |
| WO-009 | simple | wo | exacte | exacte | attendu [('SN', '2024', 361077.455)] != obtenu [('SN-DK', '2024', 59467.792), ('SN-FK', '2024', 25457.869), ('SN-KA', '2024', 53.0), ('SN-KD', '2024', 804.0), ('SN-KE', '2024', 1309.0), ('SN-KL', '2024', 243.056), ('SN-LG', '2024', 456.61), ('SN-MT', '2024', 3419.0), ('SN-SE', '2024', 1772.0), ('SN-SL', '2024', 108982.837), ('SN-TC', '2024', 900.0), ('SN-TH', '2024', 98893.9), ('SN-ZG', '2024', 67575.391)] |
| WO-021 | simple | wo | exacte | aucune | issue attendue exacte, obtenu aucune |
