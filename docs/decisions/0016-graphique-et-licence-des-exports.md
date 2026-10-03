# 0016 · Graphiques dessinés par le navigateur, licence dans les exports

**Date** : 2026-10-03 · **Statut** : proposé par SAN, **à valider par KBD** · **Exigences** : EF-26, EF-33

## Contexte

En repassant le cahier exigence par exigence, deux écarts V1.0 n'étaient écrits nulle part.

- **EF-26** demande des graphiques « générés côté serveur (Plotly) en SVG pour le web ». Le site les
  dessine dans le navigateur à partir de `graphique.series` (#71) ; le PDF les dessine côté serveur (#76).
  `Graphique.svg_url` existe dans le contrat mais reste vide.
- **EF-33** demande dans le PDF la « mention de licence CC BY 4.0 ». Le PDF affichait la licence lue
  dans les sources. Or ce champ est vide sur les 376 jeux du portail (point ouvert de 0012) : avec le
  vrai socle, le PDF aurait affiché « Licence » suivi de rien.

## Décisions

1. **Graphiques web dessinés par le navigateur** (écart assumé à EF-26). Mêmes données, même pied
   (EF-27), même règle (8 barres, zone demandée en vert) que le PDF. Raisons :
   - pas de Plotly ni de rendu SVG côté serveur : rien de plus à installer, à mettre en cache ou à servir ;
   - la réponse reste lisible hors ligne, graphique compris (le SVG serveur serait une ressource de plus) ;
   - budgets 7.6 tenus (JavaScript ≤ 150 Ko, LCP 2,1 s sur la page réponse, `docs/performance.md`) ;
   - le tableau de données (EF-28) vient des mêmes points, il ne peut pas diverger du dessin.
   `svg_url` reste dans le contrat, `null`, pour un éventuel usage futur (partage d'image, EF-36 en V1.1).
2. **Licence dans les exports** (EF-33) : deux mentions distinctes, aucune supposée.
   - Pied du PDF : « Export Gëstukaay sous licence CC BY 4.0 », pour la mise en forme (texte, graphique,
     PDF) produite par Gëstukaay : c'est la mention CC BY 4.0 du cahier.
   - Bloc source : « Licence des données : … » avec la licence publiée par l'ANSD ; si le portail ne la
     donne pas : « non précisée par le portail ; voir la publication de l'ANSD ». On n'écrit jamais
     qu'un jeu de l'ANSD est sous CC BY sans preuve.

## Conséquences

- `backend/src/gestukaay_backend/exports.py` : `mention_licence_donnees`, pied du PDF ; test associé.
- Les exemples du contrat (`licence: "CC BY 4.0"`) restent des exemples ; le moteur renvoie la licence
  réelle des sources (vide aujourd'hui).
- À revoir si l'ANSD précise la licence de ses jeux : la mention se mettra à jour toute seule.
