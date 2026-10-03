# Suivi des chantiers — Khalifa (KBD)

Fichier de synthèse de mes tâches. Le détail de chaque tâche (critère de fin, dépendances) est dans son issue GitHub.

**Hackathon** : 72 h du **07 au 10 octobre 2026**. Gel des fonctionnalités à H+54, vidéo de secours à H+66 (cahier 13.1).

## Tableau de bord

| Chantier | Fait | Total | Jalon principal |
|---|---|---|---|
| 0 · Fondations | 4 | 4 | ✅ terminé |
| 1 · Socle | 7 | 8 | Préparation |
| 2 · Moteur | 4 | 10 | Préparation |
| 3 · Jeu de test et mesure | 1 | 4 | Préparation |
| 4 · Wolof | 1 | 5 | Préparation |
| 5 · Voix | 0 | 4 | Hackathon |
| 6 · WhatsApp et Telegram | 0 | 6 | Préparation |
| 7 · Intégration et démo | 0 | 5 | Hackathon |
| **Total** | **17** | **46** | |

## Comment je mets à jour ce fichier

1. Je termine une tâche → ma PR contient `Closes #N` dans sa description : l'issue se ferme toute seule à la fusion.
2. Dans la même PR, je coche la case ici et j'incrémente la colonne « Fait » du tableau de bord.
3. Une tâche nouvelle → d'abord une issue (étiquettes `kbd` + chantier), puis une ligne ici.

Légende : ⚖️ décision à trancher ensemble avant de coder · ⏳ jalon Hackathon 72 h (sinon : Préparation, avant le 06/10).

## Planning jour par jour (proposé)

| Jour | Tâches |
|---|---|
| 01/10 | 1.1 · 1.2 · 2.1 · 3.1 · 4.5 · 6.1 · 7.1 |
| 02/10 | 1.3 · 1.4 · 1.5 |
| 03/10 | 1.6 · 1.7 · 1.8 · 2.2 · 2.10 |
| 04/10 | 2.3 · 2.4 · 2.5 · 2.6 · 2.8 · 3.2 |
| 05/10 | 2.7 · 2.9 · 3.3 · 4.1 · 4.2 · 4.3 · 6.2 · 6.3 |
| 06/10 | 4.4 · 5.1 · 6.4 · 6.6 · 7.2 |
| 07/10 | 5.2 |
| 08/10 | 5.3 · 5.4 · 6.5 · 7.3 |
| 09/10 | 3.4 · 7.4 |
| 10/10 | 7.5 |

## 0 · Fondations ✅

- [x] Contrat d'API v1.0.0 et faux moteur
- [x] Dépôt GitHub, CI, CODEOWNERS, protection de `main`
- [x] Méthode de travail avec Aziz (`docs/methode-de-travail.md`)
- [x] Socle brut complet avec les thèmes du portail (`socle_opendata_par_themes/`, hors Git)

## 1 · Socle

- [x] **1.1** Décider le périmètre du socle : sources, 6 domaines, projections ⚖️ — [#1](https://github.com/TechwithXalifa/gestukaay/issues/1) · échéance 01/10
- [x] **1.2** Référentiel des zones : 14 régions, 46 départements ⚖️ — [#2](https://github.com/TechwithXalifa/gestukaay/issues/2) · échéance 01/10 · après 1.1
- [x] **1.3** Choisir les ~200 indicateurs V1 à partir du jeu de test — [#3](https://github.com/TechwithXalifa/gestukaay/issues/3) · échéance 02/10 · après 3.1
- [x] **1.4** Extraction vers le schéma indicateur | zone | période | valeur | source — [#4](https://github.com/TechwithXalifa/gestukaay/issues/4) · échéance 02/10 · après 1.2, 1.3
- [x] **1.5** Étiqueter chaque valeur : observée, estimation ou projection — [#5](https://github.com/TechwithXalifa/gestukaay/issues/5) · échéance 02/10 · après 1.4
- [x] **1.6** Contrôles et rapport d'anomalies — [#6](https://github.com/TechwithXalifa/gestukaay/issues/6) · échéance 03/10 · après 1.4
- [x] **1.7** Fiches indicateurs (libellés FR/WO, définition, unité, périmètre) — [#7](https://github.com/TechwithXalifa/gestukaay/issues/7) · échéance 03/10 · après 1.3
- [ ] **1.8** Figer la version du socle et le format de chargement avec Aziz ⚖️ — [#8](https://github.com/TechwithXalifa/gestukaay/issues/8) · échéance 03/10 · après 1.5, 1.6

## 2 · Moteur

- [x] **2.1** Client LLM multi-fournisseur (OpenRouter, repli, délai 2 s) — [#9](https://github.com/TechwithXalifa/gestukaay/issues/9) · échéance 01/10
- [x] **2.2** Compréhension : question → requête structurée validée — [#10](https://github.com/TechwithXalifa/gestukaay/issues/10) · échéance 03/10 · après 2.1, 1.3
- [x] **2.3** Résolution exacte + valeurs par défaut — [#11](https://github.com/TechwithXalifa/gestukaay/issues/11) · échéance 04/10 · après 1.8
- [ ] **2.4** Correspondance approchée (zone parente/enfant, période voisine) — [#12](https://github.com/TechwithXalifa/gestukaay/issues/12) · échéance 04/10 · après 2.3
- [ ] **2.5** Refus + 3 indicateurs proches ; refus des projections — [#13](https://github.com/TechwithXalifa/gestukaay/issues/13) · échéance 04/10 · après 2.3
- [ ] **2.6** Comparaison et classement — [#14](https://github.com/TechwithXalifa/gestukaay/issues/14) · échéance 04/10 · après 2.3
- [ ] **2.7** Contexte de suivi sur 3 échanges — [#15](https://github.com/TechwithXalifa/gestukaay/issues/15) · échéance 05/10 · après 2.2
- [ ] **2.8** Gabarits d'explication FR, formatage des nombres, citation — [#16](https://github.com/TechwithXalifa/gestukaay/issues/16) · échéance 04/10 · après 2.3
- [ ] **2.9** Basculer du faux moteur au vrai — [#17](https://github.com/TechwithXalifa/gestukaay/issues/17) · échéance 05/10 · après 2.3, 2.4, 2.5
- [x] **2.10** Contrat v1.1.0 : nature, académie, /v1/transcrire, /v1/situate, graphique de contexte — [#45](https://github.com/TechwithXalifa/gestukaay/issues/45) · échéance 03/10 · après décisions 0002 et 0003

## 3 · Jeu de test et mesure

- [x] **3.1** Rédiger les 100 questions de référence — [#18](https://github.com/TechwithXalifa/gestukaay/issues/18) · échéance 01/10
- [ ] **3.2** Script de benchmark + invariant « zéro chiffre inventé » — [#19](https://github.com/TechwithXalifa/gestukaay/issues/19) · échéance 04/10 · après 3.1, 2.3
- [ ] **3.3** Benchmark exécuté par la CI — [#20](https://github.com/TechwithXalifa/gestukaay/issues/20) · échéance 05/10 · après 3.2
- [ ] **3.4** Rapport de mesure ⏳ — [#21](https://github.com/TechwithXalifa/gestukaay/issues/21) · échéance 09/10 · après 3.2

## 4 · Wolof

- [ ] **4.1** Table de normalisation wolof — [#22](https://github.com/TechwithXalifa/gestukaay/issues/22) · échéance 05/10 · après 1.2
- [ ] **4.2** Lexique métier bilingue — [#23](https://github.com/TechwithXalifa/gestukaay/issues/23) · échéance 05/10 · après 1.3
- [ ] **4.3** Détection automatique de la langue — [#24](https://github.com/TechwithXalifa/gestukaay/issues/24) · échéance 05/10
- [ ] **4.4** Gabarits de réponse en wolof — [#25](https://github.com/TechwithXalifa/gestukaay/issues/25) · échéance 06/10 · après 2.8
- [x] **4.5** ~~Trouver 2 locuteurs natifs dont un linguiste~~ → validation par KBD, décision 0009 — [#26](https://github.com/TechwithXalifa/gestukaay/issues/26) · échéance 01/10

## 5 · Voix

- [ ] **5.1** Évaluer la transcription wolof et choisir ⚖️ — [#27](https://github.com/TechwithXalifa/gestukaay/issues/27) · échéance 06/10
- [ ] **5.2** Transcription des vocaux (OGG/WebM ≤ 60 s) ⏳ — [#28](https://github.com/TechwithXalifa/gestukaay/issues/28) · échéance 07/10 · après 5.1
- [ ] **5.3** Audio de réponse : lecture des nombres en wolof ⏳ — [#29](https://github.com/TechwithXalifa/gestukaay/issues/29) · échéance 08/10 · après 4.4
- [ ] **5.4** Audio ≤ 60 Ko ⏳ — [#30](https://github.com/TechwithXalifa/gestukaay/issues/30) · échéance 08/10 · après 5.3

## 6 · WhatsApp et Telegram

- [ ] **6.1** Vérifier le compte de test Meta — [#31](https://github.com/TechwithXalifa/gestukaay/issues/31) · échéance 01/10
- [ ] **6.2** Webhook : idempotence, accusé de lecture, fenêtre 24 h — [#32](https://github.com/TechwithXalifa/gestukaay/issues/32) · échéance 05/10 · après 6.1
- [ ] **6.3** Message de réponse WhatsApp — [#33](https://github.com/TechwithXalifa/gestukaay/issues/33) · échéance 05/10 · après 2.9
- [ ] **6.4** Accueil, choix numérotés, commandes — [#34](https://github.com/TechwithXalifa/gestukaay/issues/34) · échéance 06/10 · après 6.3
- [ ] **6.5** Envoi de l'audio WhatsApp ⏳ — [#35](https://github.com/TechwithXalifa/gestukaay/issues/35) · échéance 08/10 · après 5.3, 6.3
- [ ] **6.6** Bot Telegram de secours — [#36](https://github.com/TechwithXalifa/gestukaay/issues/36) · échéance 06/10 · après 6.3

## 7 · Intégration et démo

- [ ] **7.1** Squelette de bout en bout avec Aziz — [#37](https://github.com/TechwithXalifa/gestukaay/issues/37) · échéance 01/10
- [ ] **7.2** Préproduction branchée sur le vrai moteur — [#38](https://github.com/TechwithXalifa/gestukaay/issues/38) · échéance 06/10 · après 2.9
- [ ] **7.3** Recette des parcours P1 à P4 ⏳ — [#39](https://github.com/TechwithXalifa/gestukaay/issues/39) · échéance 08/10 · après 7.2
- [ ] **7.4** Gel H+54, vidéo de secours H+66, captures ⏳ — [#40](https://github.com/TechwithXalifa/gestukaay/issues/40) · échéance 09/10 · après 7.3
- [ ] **7.5** Présentation au jury ⏳ — [#41](https://github.com/TechwithXalifa/gestukaay/issues/41) · échéance 10/10 · après 7.4
