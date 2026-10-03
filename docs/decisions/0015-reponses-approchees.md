# 0015 — Réponses approchées : 2 à 3 choix vérifiés et repli vers le refus

**Date** : 2026-10-03 · **Statut** : accepté (KBD) · **Issue** : #12

## Contexte

Quand une demande ne peut pas être servie de façon exacte (zone plus fine que publiée, période absente,
modalité ambiguë, lieu non administratif), le système propose une réponse `approchee` avec des `Choix`
([EF-06, EF-21]). Le cahier impose strictement 2 à 3 choix (`min_length=2, max_length=3`), et **aucune
valeur numérique** n'est affichée dans la réponse approchée.

## Décisions

1. **Zéro chiffre inventé & Choix vérifiés à l'avance** :
   Chaque `Choix` proposé est obligatoirement testé et validé par `resolution.resoudre(socle, req)` à
   l'avance. S'il ne donne aucune valeur officielle réelle dans le socle, il est éliminé.
2. **Référentiel déclaratif `socle/referentiels/rattachements.csv`** :
   Contient les types `lieu` (Touba, villes de Thiès et Kaolack) et `modalite` (voitures $\rightarrow$ TOTAL / VPP),
   avec une colonne `preuve` obligatoire. Les zones parentes se déduisent de `zones.csv` (`parent`),
   et les académies couvrantes de `zones.csv` (`couvre` et `parent`).
3. **Plafond à 3 choix sur dimension ambiguë** :
   Critère déterministe : modalités nommées dans la question d'abord, puis les plus fréquentes dans le jeu ;
   `Total` / `Ensemble` exclu ; existence vérifiée dans le socle pour la zone et la période.
4. **Reformulations** :
   Sans jargon (« les zones pour lesquelles l'ANSD publie ce chiffre »), vouvoiement, une seule phrase,
   et se terminant obligatoirement par « Est-ce ce que vous cherchez ? » en français (cahier §7.4) et
   « Ndax lii nga bëgg ? » en wolof.
5. **Ordre de repli pour atteindre 2 à 3 choix** :
   - (a) zone parente, puis niveau au-dessus (département $\rightarrow$ région $\rightarrow$ Sénégal) ;
   - (b) sinon la même zone à une autre période publiée (période la plus proche) ;
   - (c) s'il ne reste qu'une seule option réelle vérifiée : repli sur `ReponseAucune` (`motif="hors_socle"`)
     avec cette option unique en `suggestions`. Exemple : « ville de Thiès » sur `pvswjnd` (régions seulement,
     2023 seulement) bascule en refus avec la région de Thiès en suggestion.

## Conséquences

- Module `engine/src/gestukaay_engine/approchee.py` et référentiel `socle/referentiels/rattachements.csv`.
- Tests unitaires complets dans `engine/tests/test_approchee.py`.
- Tâche 2.4 pointée dans `docs/suivi-kbd.md`.
