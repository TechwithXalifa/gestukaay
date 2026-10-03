# 0014 — Gabarits de réponse en français

**Date** : 2026-10-03 · **Statut** : accepté (KBD) · **Issue** : #16

## Contexte

Une réponse exacte porte une `explication` (1 à 3 phrases par gabarit, §5.4), une `citation` (EF-35) et une
`note_perimetre`. Le cahier impose les nombres à espace fine insécable et virgule décimale, les unités
toujours affichées (§7.4), et un arrondi d'affichage signalé (§1). Aucun LLM pour rédiger.

## Décisions

1. **Phrase principale** : naturelle pour les **P1**, écrite à la main par gabarit
   (`engine/src/gestukaay_engine/gabarits_fr.csv` : « {zone_sujet} compte {valeur} {periode}. ») ;
   **neutre** pour les autres indicateurs (« Taux d'urbanisation dans la région de Dakar en 2023 : 97,2 %. »),
   sans article ni accord à deviner.
2. **Montants tels que publiés** : « 22 745 886 millions de FCFA », pas de conversion d'échelle.
3. **Arrondi par type d'unité** : %, ‰, années, indices : 1 décimale ; effectifs, FCFA, tonnes : entier ;
   valeurs < 1 : 2 décimales ; jamais plus de décimales que publiées. Quand l'arrondi modifie la valeur
   publiée, l'explication le dit une fois ; la valeur exacte reste dans les exports.
4. **Position relative** : une valeur régionale (ou départementale, académique) est comparée à la valeur
   nationale **publiée** pour la même période et les mêmes modalités (« C'est plus que la valeur nationale
   (20,4 % en 2025). »). Seulement pour les taux, prix et moyennes ; jamais pour un effectif.
5. **Phrases complémentaires** : « dernière donnée publiée » quand la période n'est pas demandée ;
   projection ou estimation avec sa base. Au plus 3 phrases.
6. **Citation EF-35** : « Source : ANSD, RGPH-5 (2023), publié le 31 octobre 2023. Consulté via Gëstukaay
   le 3 octobre 2026, [URL]. » Producteur et opération courts, **déclarés avec leur preuve** dans
   `socle/referentiels/sources_citees.csv` (les 25 jeux P1) ; sinon producteur du portail et opération
   courte du portail, ou titre du jeu. L'URL est provisoire : le backend la remplace par l'adresse stable.
7. **Note de périmètre** : note déclarée du jeu (prix relevés à Dakar) ; sinon « Région administrative,
   pas la ville. », « Département, pas la commune. », « Inspection d'académie, pas la région administrative. »

## Conséquences

- Réponses rédigées du jeu de test : `mesure/rapports/reponses_fr_*.md` (relecture KBD).
- Le wolof (#25) reprendra la même structure ; le classement (#14) aura son gabarit.
- `valeur_affichee` suit les mêmes règles que le texte.
