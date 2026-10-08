# Rapport de mesure — Gëstukaay

**Date** : 8 octobre 2026 · **Issue** : #21 · **Exigences** : cahier des charges §12.1, §13.3
**Version mesurée** : `main` du 8/10 (après #159), socle `2026.10.0` (644 827 valeurs)

## 1. En bref

Sur les 104 questions du jeu de test, posées telles qu'un utilisateur les écrirait (73 en français, 31 en wolof),
avec la chaîne de production (Gemini 2.5 Flash, puis Flash-Lite, puis les règles locales) :

| Mesure (cahier §12) | Cible | Mesuré le 8/10 | Statut |
|---|---|---|---|
| Invariant « zéro chiffre inventé » | 0 violation | **0** | conforme |
| Exactitude (84 questions à chiffre) | ≥ 85 % | **97,6 %** (82/84) | conforme |
| Refus pertinents (20 questions sans réponse) | ≥ 95 % | **95,0 %** (19/20) | conforme |
| Chiffres faux affichés | 0 | **1** (FR-020, voir §4) | voir §4 |
| Latence médiane / P95 (texte) | < 3 s | **1,81 s** / 2,81 s | conforme |

Les trois écarts sont analysés au §4. Deux viennent d'attendus dépassés, qui ont été corrigés et **déclarés**. Un
venait d'un mot wolof inconnu, qui est corrigé dans le code. Après ces corrections, les réponses du 8/10
donnent **83/84, 0 chiffre faux et 20/20 refus**, sans nouvel appel au LLM. La correction de WO-009 reste à
confirmer par une prochaine passe LLM.

## 2. Méthode

- **Jeu de test** (`mesure/jeu_de_test/questions.csv`) : 104 questions écrites avant le développement, à
  partir des besoins et du socle. Chaque valeur attendue est prouvée dans le fichier brut du portail
  (`mesure/scripts/verifier_attendus.py` : 73 questions, 219 valeurs, 0 échec). Les questions en wolof sont
  écrites par un locuteur natif (KBD, décision 0009), en orthographe officielle ou d'usage (« gnata »,
  « thieb »).
- **Types** : valeur simple (43), réponse approchée (11), classement (10), comparaison de zones (10), comparaison
  de périodes (5), suivi de conversation (5), refus (20 : donnée absente, prévision, incompréhension, hors sujet).
- **Juge** : `mesure/scripts/benchmark.py`, déterministe. Une réponse « exacte » est juste si la zone, la période
  et la valeur servies sont celles attendues. Une réponse approchée doit proposer des choix vérifiés. Un refus
  doit avoir le bon motif.
- **Invariant**, vérifié sur chaque réponse : (a) chaque valeur servie est une observation du socle ; (b) chaque
  point de graphique aussi ; (c) chaque nombre du texte figure sur la liste blanche des valeurs affichées ;
  (d) aucune valeur n'apparaît dans une réponse approchée ou un refus.
- **Transparence** : tout attendu modifié après le début des mesures est listé dans
  `mesure/jeu_de_test/changements.csv`, avec sa raison et la mention « changé après la passe… », pour que le
  jeu de test ne soit pas lu comme un examen ajusté au moteur. On en compte 10 à ce jour.

## 3. Résultats détaillés (passe LLM du 8/10)

| Type | Réussite |
|---|---|
| Valeur simple | 41/43 (95,3 %) |
| Réponse approchée | 11/11 (100 %) |
| Classement | 10/10 (100 %) |
| Comparaison de zones | 10/10 (100 %) |
| Comparaison de périodes | 5/5 (100 %) |
| Suivi de conversation | 5/5 (100 %) |
| Refus | 19/20 (95 %) |

| Langue | Réussite |
|---|---|
| Français | 72/73 (98,6 %) |
| Wolof | 29/31 (93,5 %) |

Rapport brut de la passe : `benchmark_llm-google-gemini-2.5-flash.md`. Coût : environ 0,07 $.

## 4. Analyse des écarts

| Question | Obtenu | Analyse | Suite |
|---|---|---|---|
| **FR-020** « Quel pourcentage d'enfants souffrent d'un retard de croissance au Sénégal ? » | 17,5 % (2023) au lieu de 17,9 % (2019) | **Attendu dépassé.** Le moteur sert l'EDS-Continue 2023 (`pagfmnc`), la dernière valeur publiée. `pagfmnc` est la même série que `xsitdae` : il donne aussi 17,9 % pour 2019. Sans année demandée, la dernière valeur est la bonne réponse (US-06, 0035). | Attendu changé et déclaré. `pagfmnc` vérifié (KBD) |
| **WO-028** « waa man tay dama xiif… » (bavardage) | conversation au lieu d'incompréhension | **Attendu antérieur à la 0033.** Depuis cette décision, un message hors sujet reçoit une réponse de conversation qui propose un exemple. Les deux réponses refusent sans deviner d'indicateur. | Motif élargi à `incomprehension\|conversation`, déclaré |
| **WO-009** « Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? » | approchée (choix du type de pêche) au lieu de la valeur | **Vocabulaire manquant.** « nappkat yu ndaw » (les petits pêcheurs) n'était pas reconnu comme la pêche artisanale, ni « yàpp géej » comme les poissons. | Formes de KBD ajoutées. En français, « tonnes de poisson » sélectionnait aussi le total au lieu des poissons (singulier et pluriel) : corrigé |

## 5. Évolution

| Passe LLM | Questions | Exactitude | Chiffres faux | Refus | Latence médiane |
|---|---|---|---|---|---|
| 4/10 | 103 | 89,2 % (74/83) | 2 | 20/20 | 1,39 s |
| 7/10 | 104 | 92,9 % (78/84) | 1 | 19/20 | 1,88 s ¹ |
| **8/10** | 104 | **97,6 % (82/84)** | 1 (attendu dépassé) | 19/20 | **1,81 s** |

¹ Mesurée sur 20 questions après le passage du délai de Flash à 3 s (0034).

Principaux apports entre le 4/10 et le 8/10 :
- le choix du LLM est encadré (0034, #159) : doublons, précisions inventées, indicateur hors sujet ;
- la période par défaut n'est jamais une projection future (0035) ;
- les réponses approchées sont vérifiées et passent de 6/11 à 11/11 ;
- le vocabulaire wolof et les formes d'usage ont été complétés (0028, #153, #157).

## 6. Mode de secours (règles locales, sans LLM)

Si le LLM ne répond pas, le moteur continue avec des règles locales, gratuites et hors réseau. Mesure du 8/10
après corrections : **77/84 (91,7 %)**, refus 17/20, **5 chiffres faux**, invariant respecté, latence médiane
2 ms. Les chiffres faux en règles sont des choix d'indicateur voisins (chômage : le taux au lieu du nombre de
chômeurs, FR-073 et WO-002 ; scolarisation des filles à Louga, WO-005 ; deux hors-sujet pris pour des
questions, FR-062 et WO-031). C'est pour cette raison que le LLM reste le premier maillon.

## 7. Voix

- **Transcription** (`transcription.md`, 5/10) : M-Kiriku retenu (0026). Sur 62 notes vocales réelles, il donne
  35 bonnes réponses, pour un plafond de 51/62 avec le texte tapé. WER médian 37,4 %, latence médiane 1,9 s.
- **Voix de réponse** : Oolel-Voices retenu (0029), préféré à l'écoute (KBD, 8/10). Mesuré sur le Mac de
  l'équipe : une réponse chiffrée d'environ 18 s d'audio demande environ 22 s de calcul, soit environ 30 s
  d'attente en tout. L'objectif de moins de 8 s (#35) suppose une carte graphique (#38).

## 8. Limites connues

- **Un seul locuteur valide le wolof** (0009). Une relecture par un linguiste est prévue en V1.1.
- **Production agricole par culture** : « production de mil » tombe sur le prix du mil en mode règles (le mot
  « mil » pèse plus que « production »). Le LLM est à mesurer sur ces questions.
- **Réponse approchée limitée à 3 choix** : pour les écoles, le 4e cycle (« Moyen général ») n'est pas proposé.
- **FR-048** (scolarisation à Dakar) : le jeu de test attend les trois académies, mais le portail ne publie le
  taux brut de scolarisation que pour l'IA de Dakar (Pikine et Rufisque sont vides). Attendu à revoir avec SAN.
- **Refus** : 5 questions hors sujet sont passées en « conversation » (0033). Il faut écrire 5 nouveaux refus
  « donnée absente » pour revenir à 20.
