# 0023 · Catalogue, fiche indicateur et séries pour Explorer

**Date** : 2026-10-04 · **Statut** : accepté (SAN, KBD le 04/10) · **Exigences** : 5.5 (Explorer,
Catalogue, Fiche indicateur), US-18, US-19, EF-29, EF-34 · **Touche** : contrat (v1.4.0, additif)

## Contexte

Le cahier classe trois écrans en « Doit V1.0 » : Explorer / comparer, le catalogue d'indicateurs et la
fiche indicateur. Les maquettes existent (Explorer, Catalogue, Fiche), mais le contrat n'avait aucune
route pour les servir : `/v1/ask` répond à une question, pas à une navigation. Le référentiel des
indicateurs (0005), les fiches des jeux (#7) et le socle extrait (0013) contiennent déjà tout ce qu'il faut.

## Décision

Trois routes en lecture seule, sans LLM, ajoutées au contrat 1.4.0. Rien ne casse : ce sont des
modèles et des routes en plus.

1. **`GET /v1/indicators`** → `CatalogueResponse` : filtres `domaine`, `q` (libellé), `niveau`,
   pagination `limite` / `decalage` ; seuls les indicateurs qui ont des valeurs dans le socle servi ;
   les vérifiés d'abord, puis par libellé.
2. **`GET /v1/indicators/{code}`** → `FicheIndicateur` : libellé, domaine, unité, producteur, opération,
   définition **citée mot pour mot du portail** (`None` s'il n'en publie pas, 0005), méthode, désagrégations,
   couverture par niveau (nombre de zones, périodes publiées), note de périmètre, source du jeu, citation
   EF-35, jusqu'à 6 indicateurs liés. 404 si le code est inconnu.
3. **`GET /v1/series?indicateur=&zones=&debut=&fin=`** → `SeriesResponse` : une série par zone (6 au plus,
   422 au-delà), les **seules périodes publiées** (jamais d'interpolation, maquette Explorer), chaque point
   avec `valeur_affichee`, `observation_id` et sa nature ; les zones sans aucune valeur publiée dans
   `absents` ; un graphique prêt à dessiner (courbe, ou barres pour une seule période). Total par défaut
   pour les désagrégations, comme la résolution (0011).

Le code d'indicateur sert aux adresses (`/indicateurs/{code}`, `/explorer?indicateur=…&zones=…`,
EF-29) mais n'est jamais affiché comme texte au public (7.1 principe 5).

## Priorité

Le cahier v1.1 place les trois écrans en V1.0 (tableau des versions §2.3, écrans §5.5, US-18 et US-19
« Doit · V1.0 ») ; la V1.1 prévoit leur consolidation à partir des retours des testeurs (§13.2, S3).
Côté moteur, les trois méthodes passent **après** les priorités V1.0 de KBD (WhatsApp, wolof, voix).
En attendant, `MoteurReel` lève `NonDisponible` et les trois routes répondent **503** avec
`GESTUKAAY_MOTEUR=reel` (0019), comme la voix aujourd'hui ; les pages se construisent sur le faux moteur.
Si le moteur n'est pas prêt avant le gel (H+54), les écrans restent hors de la démo et l'écart au cahier
est noté.

## Qui fait quoi

- **KBD (moteur)** : trois méthodes sur le Protocol `Moteur`, par exemple `catalogue(filtre)`,
  `fiche(code)`, `series(indicateur, zones, debut, fin)`, qui lisent le référentiel et le socle (formatage
  des valeurs avec `gabarits.formater`, sources avec `resolution.source`). Le nom exact des méthodes et
  la façon de les écrire sont à son choix.
- **SAN (backend et site)** : les trois routes, le faux moteur sur les exemples
  (`catalogue.json`, `fiche_indicateur.json`, `series.json`), puis les pages `/indicateurs`,
  `/indicateurs/[code]` et `/explorer` d'après les maquettes, avec l'export CSV de la série (schéma EF-34).

## Conséquences

- Les exemples reprennent des valeurs réelles du socle `2026.10.0` (taux de pauvreté de l'EHCVM pour le
  Sénégal, Dakar et Kolda en 2011, 2019 et 2022), avec leur `observation_id`.
- Le site peut avancer sur le faux moteur dès la fusion, sans attendre l'implémentation réelle.
- Hors V1.0 : sélection fine des désagrégations dans Explorer (sexe, milieu…), export PNG (EF-36).

## Mise en œuvre (08/10)

Écrite par SAN à la demande de KBD (#156), à relire par KBD : `engine/src/gestukaay_engine/donnees.py`. Les
valeurs d'Explorer passent par `resoudre_un()` : total par défaut, défauts déclarés du jeu, académie
équivalente, comme une question ; une période sans valeur sûre est absente, jamais interpolée. Le catalogue
(4 247 indicateurs avec des valeurs dans le socle 2026.10.0) est calculé une fois, en 0,7 s ; la recherche
porte sur le libellé, l'opération, le producteur et le domaine. Les trois routes ne répondent plus 503.
