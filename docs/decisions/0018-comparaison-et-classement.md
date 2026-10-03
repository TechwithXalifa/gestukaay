# 0018 — Comparaison géographique et temporelle, classement des régions et académies

**Date** : 2026-10-03 · **Statut** : accepté (KBD, Khalifa) · **Issues** : #14, #45 · **Exigences** : EF-07, US-04, EF-20, EF-26, EF-27

## Contexte

Le moteur traitait jusqu'ici les réponses exactes à valeur unique (#11), les réponses approchées (#12) et les refus (#13).
Les deux intentions `classement` et `comparaison` (spatiale et temporelle) devaient être résolues sans jamais inventer de chiffre, avec un objet `Graphique` exploitable par le web et les exports PDF, et une explication textuelle sans accord à deviner ni recalcul non autorisé.

## Décisions

1. **Évolution additive du contrat (v1.2.0)** :
   - `Periode.fin : str | None = None` : borne de fin d'une comparaison temporelle (« entre 2011 et 2022 ») pour éviter de devoir relire la question dans `executer()`, le journal ou le web ;
   - `RequeteStructuree.ordre : Literal["desc", "asc"] = "desc"` : sens du tri pour les classements.
   - En cas d'appel avec un contrat antérieur, un repli déterministe par analyse lexicale dans la résolution garantit la compatibilité.

2. **Périmètre du classement (Choix 2 : A)** :
   - Pour les indicateurs régionaux : les **14 régions** administratives (hors Sénégal national).
   - Pour les indicateurs scolaires (ex. `ervtjfc`, FR-040) : les **16 académies** d'enseignement (Dakar étant découpée en 3 académies, décision 0003).
   - Tous les points sont inclus dans l'objet `Graphique` ; le composant web et l'export PDF appliquent le plafonnement d'affichage à 8 barres (décision 0016).

3. **Mise en évidence (`mise_en_evidence : bool`)** :
   - Dans un classement général (« Quelle région a le plus/le moins… ») : la zone en tête du classement reçoit `mise_en_evidence = True` (colorée en vert sur le web et le PDF).
   - Si la question cite une zone spécifique (ex. « Où se situe Thiès pour le chômage ? ») : la zone citée reçoit la mise en évidence pour être toujours visible parmi les barres affichées.
   - Dans une comparaison spatiale : toutes les zones demandées sont en évidence.
   - Dans une comparaison temporelle : seules les deux bornes demandées sont en évidence, les points intermédiaires restent neutres.

4. **Comparaison temporelle et tracé en courbe** :
   - `resultats` ne contient **strictement que les périodes demandées** (les deux bornes) ;
   - `graphique` (type `courbe`) intègre **toutes les années publiées entre les deux bornes**, permettant au visiteur de visualiser la trajectoire continue ;
   - `explication` : indique **uniquement le sens** de l'évolution (hausse, baisse ou stabilité), sans **jamais calculer d'écart numérique** ni de pourcentage d'évolution (respect strict de l'invariant « aucun chiffre inventé ni recalculé »).

5. **Gabarit de classement sans accord à deviner (Choix 4)** :
   - Forme : *« En {période}, la valeur la plus élevée [ou la plus faible] est celle de {zone 1} ({v1}), devant celles de {zone 2} ({v2}) et de {zone 3} ({v3}). »*
   - Pour les académies : formulation explicite *« celle de l'académie de {nom} »*.
   - Séparateur avant `%` et `‰` : espace fine insécable U+202F.

6. **Graphiques conformes aux décisions 0004 et 0016** :
   - `svg_url = None` : le tracé SVG est généré côté client par le composant web à partir de `g.series` ;
   - Pied normalisé EF-27 conforme aux exemples du contrat : `Source : ANSD, RGPH-5, publié le 31 octobre 2023 · gestukaay`.
