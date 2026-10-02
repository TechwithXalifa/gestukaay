# 0011 — Résolution exacte : valeurs par défaut, désagrégations, strict sinon

**Date** : 2026-10-02 · **Statut** : accepté (KBD) · **Issue** : #11

## Contexte

La compréhension (0010) produit une requête structurée. Il faut en tirer la valeur officielle, sourcée,
sans recalcul, et savoir dire quand elle n'existe pas.

## Décisions

1. **Socle en mémoire** : `../socle_gestukaay/observations.csv` chargé au démarrage du moteur (2,3 s,
   190 Mo), indexé par indicateur ; une résolution prend moins d'une milliseconde. Seule
   `socle.charger()` connaît le format : passer à PostgreSQL (#8, avec SAN) ne change qu'elle.
2. **Valeurs par défaut** : sans zone, le national (ou l'unique zone du jeu : prix relevés à Dakar) ;
   sans période, la dernière publiée, signalée (`Resolution.defauts`) ; sans désagrégation, le total.
3. **Désagrégation**, dans l'ordre : demandée (vocabulaire fixe de 0010 traduit vers les libellés du
   jeu : femmes -> « Féminin », « FEMMES »…) ; nommée dans la question (« Pêche artisanale »,
   « Français ») ; unique ; total ; **défaut déclaré du jeu** (`socle/referentiels/defauts_desagregation.csv`,
   avec son motif : PIB en base 2021, prix courants, approche production…). Une précision déjà portée
   par l'indicateur (« riz » pour « Prix du riz brisé ») est ignorée. La période est fixée avant les
   dimensions.
4. **Strict sinon** : zone non couverte, période absente, désagrégation absente ou ambiguë -> `Introuvable`
   avec la raison et ce qui est disponible (zones, périodes, modalités). Les propositions relèvent de
   #12 ; le classement de #14.
5. **Un lieu hors référentiel n'est jamais remplacé par le national** : « à Touba », « à Paris », « la
   ville de Thiès » -> `Introuvable` (approchée ou refus en #12).

## Conséquences

- Bout en bout (compréhension + résolution) sur le jeu de test, **règles seules, sans réseau** :
  48/57 questions exactes justes au chiffre près ; 9 chiffres faux, tous dus aux limites de la
  compréhension par règles (refus hors sujet non détectés, indicateur voisin) — à mesurer avec le LLM
  (`engine/scripts/evaluer_bout_en_bout.py`, `mesure/rapports/bout_en_bout_*.md`).
- « Nombre de voitures à Kolda » sert le TOTAL du parc (9 317) : la nuance « voitures » ≠ toutes
  catégories relève de #12 (proposer TOTAL ou VPP).
- `valeur_affichee` et les libellés de période sont provisoires : les gabarits (#16) les reprennent.
