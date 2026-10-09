# Rapport de mesure — Gëstukaay

**Date** : 9 octobre 2026 · **Issue** : #21 · **Exigences** : cahier des charges §12.1, §13.3
**Version mesurée** : `main` du 9/10 (après #180) et la correction du moteur de cette PR, socle `2026.10.0`
(644 827 valeurs)

## 1. En bref

Sur les 113 questions du jeu de test, posées telles qu'un utilisateur les écrirait (78 en français, 35 en wolof),
avec la chaîne de production (Gemini 2.5 Flash en direct, puis Flash-Lite, puis les règles locales) :

| Mesure (cahier §12) | Cible | Mesuré le 9/10 | Statut |
|---|---|---|---|
| Invariant « zéro chiffre inventé » | 0 violation | **0** | conforme |
| Exactitude (84 questions à chiffre) | ≥ 85 % | **98,8 %** (83/84) | conforme |
| Refus pertinents (19 demandes de chiffre sans réponse officielle) | ≥ 95 % | **100 %** (19/19) | conforme |
| Hors sujet : réponse de conversation (10 questions, 0033) | — | **10/10** | conforme |
| Chiffres faux affichés | 0 | **0** | conforme |
| Latence médiane / P95 (texte) | < 3 s | **1,38 s** / 2,86 s | conforme |

Le seul écart (WO-009) est une réponse approchée là où une valeur était attendue : aucun chiffre n'est affiché,
l'utilisateur choisit la catégorie (§4).

**Erreurs trouvées le jour même.** Une première passe du 9/10, sur `main` avant correction, donnait 80/84,
1 chiffre faux (WO-009) et **6 alertes de l'invariant** sur cette même réponse. Aucun chiffre n'était inventé : les 6 valeurs existent dans le
socle, mais dans une autre catégorie que celle affichée (§4). Le défaut est corrigé dans le moteur, avec un
test, et la passe a été refaite sur le code corrigé. Les deux passes sont publiées.

## 2. Méthode

- **Jeu de test** (`mesure/jeu_de_test/questions.csv`) : 113 questions, écrites avant le développement pour la plupart (les ajouts sont déclarés, voir
  Transparence), à partir des besoins et du socle. Chaque valeur attendue est prouvée dans le fichier brut du portail
  (`mesure/scripts/verifier_attendus.py` : 73 questions, 219 valeurs, 0 échec). Les questions en wolof sont
  écrites par un locuteur natif (KBD, décision 0009), en orthographe officielle ou d'usage (« gnata »,
  « thieb »).
- **Types** : valeur simple (43), réponse approchée (11), classement (10), comparaison de zones (10), comparaison
  de périodes (5), suivi de conversation (5), refus (19 : donnée absente, prévision, incompréhension), hors sujet
  (10, réponse de conversation).
- **Juge** : `mesure/scripts/benchmark.py`, déterministe. Une réponse « exacte » est juste si la zone, la période
  et la valeur servies sont celles attendues. Une réponse approchée doit proposer des choix vérifiés. Un refus
  doit avoir le bon motif.
- **Invariant**, vérifié sur chaque réponse : (a) chaque valeur servie est une observation du socle ; (b) chaque
  point de graphique aussi ; (c) chaque nombre du texte figure sur la liste blanche des valeurs affichées ;
  (d) aucune valeur n'apparaît dans une réponse approchée ou un refus.
- **Transparence** : tout attendu modifié après le début des mesures est listé dans
  `mesure/jeu_de_test/changements.csv`, avec sa raison et la mention « changé après la passe… », pour que le
  jeu de test ne soit pas lu comme un examen ajusté au moteur. On en compte 14 à ce jour.

## 3. Résultats détaillés (passe LLM du 9/10, code corrigé)

| Type | Réussite |
|---|---|
| Valeur simple | 42/43 (97,7 %) |
| Réponse approchée | 11/11 (100 %) |
| Classement | 10/10 (100 %) |
| Comparaison de zones | 10/10 (100 %) |
| Comparaison de périodes | 5/5 (100 %) |
| Suivi de conversation | 5/5 (100 %) |
| Refus (donnée absente, prévision, incompréhension) | 19/19 (100 %) |
| Hors sujet (conversation, 0033) | 10/10 (100 %) |

| Langue | Réussite |
|---|---|
| Français | 78/78 (100 %) |
| Wolof | 34/35 (97,1 %) |

Rapports bruts : `benchmark_llm-gemini-2.5-flash.md` (code corrigé) et
`benchmark_llm-gemini-2.5-flash_avant_correction_0910.md` (première passe). Coût : environ 0,07 $ par passe.

## 4. Analyse des écarts

| Question | Passe avant correction | Analyse | Suite |
|---|---|---|---|
| **WO-009** « Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? » | Classement par région : la pêche artisanale de la côte et la **pêche continentale** de Matam, Sédhiou, Kédougou… dans le même graphique ; Saint-Louis absente | **Défaut du moteur.** Chaque région fixait seule sa catégorie : là où une seule est publiée (Matam : pêche continentale), elle était prise d'office. Les valeurs existent dans le socle, mais pas dans la catégorie affichée : l'invariant l'a détecté (volet b, 6 alertes). | Corrigé : un classement ou une comparaison de zones compare la même catégorie partout, sinon le choix est proposé (« Pêche artisanale, par région » / « Pêche continentale, par région »). Après correction : réponse approchée, aucun chiffre affiché. |
| **FR-049** « Combien coûte le riz à Thiès ? », **WO-021** « Ñata lay diar thieb kaolack ? » | « Donnée absente » | **Refus à tort.** La série « riz brisé » choisie n'est publiée que pour Dakar, alors que le prix de détail du riz est publié par région (CSA). | Corrigé : avant un refus, un indicateur de la même notion et de la même unité qui publie la zone est servi. Jamais une autre mesure (un taux n'est pas remplacé par un effectif). |
| **FR-015** « Quelle quantité de produits la pêche artisanale a-t-elle débarquée en 2024 ? » | Réponse approchée | Choix variable du LLM : la même question rejouée donne la valeur attendue (379 286 t). | Juste dans la passe corrigée. |

## 5. Évolution

| Passe LLM | Questions | Exactitude | Chiffres faux | Refus | Latence médiane |
|---|---|---|---|---|---|
| 4/10 | 103 | 89,2 % (74/83) | 2 | 20/20 | 1,39 s |
| 7/10 | 104 | 92,9 % (78/84) | 1 | 19/20 | 1,88 s |
| 8/10 | 104 | 97,6 % (82/84) | 1 (attendu dépassé) | 19/20 | 1,81 s |
| 9/10, avant correction | 113 | 95,2 % (80/84) | 1 (WO-009, 6 alertes de l'invariant) | 19/19 | 1,50 s |
| **9/10, code corrigé** | 113 | **98,8 % (83/84)** | **0** | **19/19** | **1,38 s** |

Depuis le 8/10, les refus ne comptent que les demandes de chiffre sans réponse officielle. Les messages sans
demande de chiffre (président, météo, poème, bavardage) sont mesurés à part, en conversation (0033), et
5 vrais refus écrits par KBD les remplacent (`changements.csv`).

Principaux apports entre le 4/10 et le 9/10 :
- le choix du LLM est encadré (0034, #159) : doublons, précisions inventées, indicateur hors sujet ;
- la période par défaut n'est jamais une projection future (0035) ;
- les réponses approchées sont vérifiées et passent de 6/11 à 11/11 ;
- le vocabulaire wolof, les dates en wolof et les formes d'usage ont été complétés (0028, #153, #157, #168) ;
- un classement ne mélange plus les catégories ; une zone non publiée est servie par la même notion (9/10).

## 6. Mode de secours (règles locales, sans LLM)

Si le LLM ne répond pas, le moteur continue avec des règles locales, gratuites et hors réseau. Mesure du 9/10 :
**84/84**, **0 chiffre faux**, invariant respecté, hors sujet 10/10, latence médiane 2 ms. Refus 17/19 :
deux refus en wolof (WO-032, plages ; WO-033, bâtiments brûlés) reçoivent une réponse approchée au lieu d'un
refus. Aucun chiffre n'y est affiché, l'utilisateur doit choisir.

## 7. Voix

- **Transcription** (`transcription.md`, 5/10) : M-Kiriku retenu (0026). Sur 62 notes vocales réelles, il donne
  35 bonnes réponses, pour un plafond de 51/62 avec le texte tapé. WER médian 37,4 %, latence médiane 1,9 s.
- **Voix de réponse** : Oolel-Voices retenu (0029), préféré à l'écoute (KBD, 8/10). Mesuré sur le Mac de
  l'équipe : une réponse chiffrée d'environ 18 s d'audio demande environ 22 s de calcul, soit environ 30 s
  d'attente en tout. L'objectif de moins de 8 s (#35) suppose une carte graphique (#38).

## 8. Limites connues

- **Un seul locuteur valide le wolof** (0009). Une relecture par un linguiste est prévue en V1.1.
- **Le LLM ne répond pas toujours pareil** : une même question peut donner la valeur ou une réponse approchée
  d'une passe à l'autre (FR-015). L'invariant et les garde-fous rendent ces écarts sûrs (jamais un chiffre faux),
  pas réguliers.
- **Production agricole par culture** : « production de mil » tombe sur le prix du mil en mode règles (le mot
  « mil » pèse plus que « production »).
- **Réponse approchée limitée à 3 choix** : pour les écoles, le 4e cycle (« Moyen général ») n'est pas proposé.
- **FR-048** (scolarisation à Dakar) : le jeu de test attend les trois académies, mais le portail ne publie le
  taux brut de scolarisation que pour l'IA de Dakar (Pikine et Rufisque sont vides). Attendu à revoir avec SAN.
