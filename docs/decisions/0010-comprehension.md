# 0010 — Compréhension : le LLM choisit un numéro, jamais un code

**Date** : 2026-10-02 · **Statut** : accepté (KBD) · **Issue** : #10

## Contexte

Le cahier exige « aucun chiffre inventé » et des codes validés contre le socle (10.4). Le socle compte
4 282 indicateurs (0005) : impossible de tous les donner au LLM dans un délai de 2 s.

## Décisions

1. **Le LLM n'écrit jamais un code.** Zones et périodes citées sont trouvées **sans LLM** (référentiel
   des zones du socle, expressions régulières). Une recherche lexicale (BM25, sans dépendance ni réseau)
   retient **15 indicateurs candidats**, numérotés ; le LLM renvoie le **numéro**, l'intention, la
   période et la désagrégation. Un numéro hors liste devient `hors_perimetre`. Le LLM ne voit aucune
   valeur [EF-04].
2. **Désagrégation en vocabulaire fixe** : `sexe` (femmes, hommes, total), `milieu` (urbain, rural,
   total), `age`, `cycle`, `produit`. La résolution (#11) les fait correspondre aux libellés de chaque
   jeu (« Féminin », « FEMMES », « Femme »).
3. **Recherche des candidats** : libellés FR / WO et nom du jeu ; noms de zones retirés de la requête ;
   vocabulaire FR / WO d'amorce (`candidats.SYNONYMES`, à reprendre dans le lexique #23) ; avantage aux
   indicateurs vérifiés et à ceux publiés au niveau de zone cité.
4. **Secours sans réseau** : si aucun fournisseur ne répond, des règles locales (meilleur candidat,
   mots du classement et de la comparaison) produisent la requête, avec une confiance de 0,4.
5. **Suivi minimal** (#15 affinera) : une question courte qui prolonge (« Et pour Kaolack ? »,
   « Kaolack nak ? ») reprend l'indicateur et, sans zone citée, les zones de l'échange précédent.

## Conséquences

- Règles seules, sans LLM, sur les 103 questions : **85 justes (83 %)**, zones et périodes 100 %,
  indicateurs 91 % (`mesure/rapports/comprehension_regles.md`). Le LLM doit surtout apporter les refus
  hors sujet (météo, Paris) et les indicateurs proches (production de riz contre prix du riz).
- **Limite du contrat** : `Periode` ne porte qu'une période ; « entre 2015 et 2025 » (5 questions)
  garde la première. Évolution du contrat (v1.2.0) à proposer à SAN.
