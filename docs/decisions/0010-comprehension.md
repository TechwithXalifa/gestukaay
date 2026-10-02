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

- **Mesures sur les 103 questions** (`mesure/rapports/comprehension_*.md`, délai 2 s) :

  | | Juste | Intention | Indicateur | Médiane | Coût / question |
  |---|---|---|---|---|---|
  | Règles seules | 86 (83 %) | 91 % | 92 % | — | 0 |
  | **Gemini 2.5 Flash** (OpenRouter) | **99 (96 %)** | 100 % | 96 % | 1,1 s | ~0,0006 $ |
  | Gemini 2.5 Flash-Lite | 84 (82 %) | 96 % | 84 % | 0,8 s | ~0,0002 $ |
  | Qwen3-32B | — | — | — | 3,4 s : au-delà du délai | — |

  **Chaîne retenue** (`.env.example`) : Gemini 2.5 Flash, puis Flash-Lite, puis les règles.
- Ce qui a fait progresser le LLM : candidats publiés au niveau de zone cité placés en tête, couverture
  [zones ; années] affichée, indicateurs vérifiés marqués ★, consigne « choisis même si la zone n'est
  pas couverte (réponse approchée) », période du LLM prise seulement si la question parle du temps.
- La compréhension a trouvé une donnée que le jeu de test ignorait : le prix du riz par région (CSA,
  `sbsryhc`) ; FR-049 et WO-021 deviennent exactes.
- Restent 4 confusions entre indicateurs équivalents de jeux différents (chômage national `muhgux`
  contre régional `dwibrlf`…) : la résolution (#11) devra préférer, à concept égal, le jeu qui couvre
  la zone et la période demandées.
- **Limite du contrat** : `Periode` ne porte qu'une période ; « entre 2015 et 2025 » (5 questions)
  garde la première. Évolution du contrat (v1.2.0) à proposer à SAN.
