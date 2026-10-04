# 0020 — Benchmark de bout en bout et invariant « zéro chiffre inventé »

**Date** : 2026-10-04 · **Statut** : accepté (KBD) · **Issues** : #19, #20 · **Exigences** : EF-04, EF-05, EF-06, EF-27, EF-35, cahier §12.1

## Contexte

Le moteur réel (`MoteurReel`, décision 0019, PR #96) est branché dans l'API. Il fallait mesurer
ses performances de bout en bout sur l'ensemble du jeu de test officiel (103 questions dans
`mesure/jeu_de_test/questions.csv`) au regard des 4 cibles fixées par le cahier des charges (§12) :
exactitude ≥ 85 %, refus pertinent ≥ 95 %, latence médiane < 3 s, et l'invariant non négociable
« zéro chiffre inventé ».

## Décisions

1. **Définition de l'exactitude (§12.1)** :
   Calculée sur les **83 questions qui appellent une réponse** (72 exactes + 11 approchées).
   Une réponse compte comme juste si elle est **correcte et correctement sourcée** :
   - `source` est remplie (`producteur`, `date_publication`, `libelle`) et `citation` est présente ;
   - pour une question exacte simple : les triplets `(zone, période, valeur)` correspondent au jeu de test ;
   - pour un classement : toute la liste ordonnée `(zone, valeur)` correspond à `valeurs_attendues`
     (14 régions ou 16 académies), le tri asc/desc est respecté, et le graphique en barres
     horizontales est présent ;
   - pour une comparaison temporelle (5 questions sur deux périodes, dont WO-014) : les bornes
     demandées sont exactes, le graphique en courbe continue couvre les années intermédiaires,
     et l'explication indique le sens d'évolution sans écart calculé ;
   - pour une comparaison spatiale (10 questions entre zones) : valeurs exactes et graphique en barres ;
   - pour une réponse approchée : `resultats` absent, 2 à 3 choix vivants (exécutables via `moteur.executer()`
     vers une observation non vide du socle) couvrant les zones et périodes attendues quand le jeu les donne.

2. **Définition du refus pertinent (§12.1)** :
   Calculé séparément sur les **20 questions de refus** (14 FR + 6 WO).
   Une réponse compte comme juste si l'issue est `aucune` avec le `motif` attendu
   (`hors_socle`, `projection`, `incomprehension`), les messages officiels conformes, et au plus
   3 suggestions vérifiées pour `hors_socle`.

3. **Invariant « zéro chiffre inventé » (tolérance zéro)** :
   Tout manquement fait échouer le benchmark avec un **code de sortie 1** :
   - *(a) Chaque `Resultat` servi* : `observation_id` existe dans le socle chargé et `valeur` est
     rigoureusement égale à la valeur du socle (`r.valeur == o.valeur`).
   - *(b) Chaque point de graphique* : chaque point `PointGraphique(x, y)` correspond à une observation
     réelle du socle pour l'indicateur.
   - *(c) Chiffres de l'explication* : tous les nombres figurant dans le texte de l'explication sont
     vérifiés contre une liste blanche des textes affichés (et non des valeurs brutes) :
     `valeur_affichee` des résultats et de la valeur nationale publiée, libellés des périodes,
     modalités de désagrégation (ex. « 15-24 ans »), `base_projection`, unité, ordinaux et nombres
     statiques du gabarit officiel (`gabarits_fr.csv`).
   - *(d) Approchée et refus* : aucune valeur numérique statistique n'est autorisée dans la reformulation,
     les libellés des choix ou les messages de refus (seules les années sont admises).

4. **Modes d'évaluation** :
   - `--regles` (par défaut) : local, gratuit, sans réseau. Utilise la compréhension par règles.
   - `--llm` (payant) : chaîne configurée (Gemini 2.5 Flash via OpenRouter). Affiche le coût estimé
     (~0,07 $ pour 103 questions) et exige une confirmation explicite (`--oui` / `-y`).
     Aucun appel payant sans l'accord préalable de Khalifa.

5. **Stratégie CI pour la tâche #20 (Option B)** :
   Le socle extrait n'est pas versionné dans Git (103 Mo). Pour la CI :
   - téléchargement automatique de `2026.10.0.zip` depuis une GitHub Release officielle ;
   - mise en cache dans GitHub Actions selon la version du socle ;
   - vérification de l'empreinte sha256 de chaque fichier par rapport au `MANIFEST.json` avant exécution ;
   - publication du rapport synthétique dans `$GITHUB_STEP_SUMMARY`.

6. **Sorties et rapports** :
   - Un seul rapport Markdown par mode : `mesure/rapports/benchmark_<mode>.md`, sans nom de fichier daté.
   - Code de sortie 1 uniquement en cas de violation de l'invariant, 0 sinon (un score sous la cible
     est consigné dans le rapport sans bloquer la commande).

## Conséquences

- `uv run python mesure/scripts/benchmark.py --regles` s'exécute en local en ~2,5 s.
- 495 tests unitaires et d'intégration automatisés dans la suite pytest (`mesure/tests/test_benchmark.py`).
- Les violations de l'invariant sont détectées dès le premier faux chiffre injecté.
