# 0036 — Design system v2 « Terre et baobab » et nouvelle structure du site

**Date** : 2026-10-07 · **Statut** : proposé (SAN), à valider par KBD · **Touche** : `web/` seulement
(aucun changement de contrat, de moteur ni de canal) · **Écart au cahier** : §9.3 et §9.4

## Contexte

La charte v1.1 (cahier §9 : Baobab, Feuille, Sable, Poppins et Lora) donnait un site propre mais
peu marquant pour la démonstration au jury. SAN a demandé une refonte visuelle complète, en
s'inspirant du soin de wurus.app (sections sombres et crème, or, trio typographique, mouvements
courts), sans toucher aux fonctionnalités ni aux adresses.

## Décisions (choix de SAN)

1. **Palette hybride « Terre et baobab »** : le vert baobab du logo reste la couleur de marque ;
   fond crème, sections brun-noir (en-tête, héros, pied, écoute vocale), or pour l'action (un seul
   bouton or plein par écran). Issues : exacte en vert feuille, approchée en ocre, projection en
   violet, erreur en latérite (jamais pour un refus). Contrastes vérifiés (axe, WCAG 2.1 AA).
2. **Typographie** : Unbounded (titres, chiffre de la réponse), Bricolage Grotesque (texte),
   Space Mono (sur-titres, lignes source, valeurs des graphiques). Gratuites (OFL), auto-hébergées
   par next/font, sous-ensembles latins.
3. **Signature** : la frise statistique (tuiles tirées des marques de graphique et du nœud du
   baobab), en bas du héros, en haut de la carte réponse et du pied de page.
4. **Mouvement** : chiffre qui défile jusqu'à sa valeur, barres qui poussent, apparitions, micro
   qui pulse ; tout en CSS (sauf le compteur), coupé par `prefers-reduced-motion`. Pas de vidéo ni
   de particules : budget 7.6 tenu (JavaScript initial 123 à 125 Ko).
5. **Structure** : trois espaces et la confiance (Demander, Données, Où je me situe, Méthode) ;
   Indicateurs, Domaines et Explorer réunis par des onglets ; sur mobile, une barre d'onglets en
   bas (Demander, Données, Me situer, Plus) remplace le bouton menu, « Plus » ouvre la barre
   latérale. Toutes les adresses sont inchangées (`/r/…`, tests, liens WhatsApp).
6. **Icônes** : Phosphor Icons, graisse duotone (licence MIT), choisies le 08/10 parmi Phosphor,
   Hugeicons, Tabler et Solar ; tracés recopiés dans `web/components/icones.tsx`, sans dépendance.
   Pas de sur-titre à point au-dessus des titres, ni de numéro de version du socle dans les pages
   publiques (retours de SAN du 08/10).
7. **Logo** : l'icône baobab n'est pas recolorée (vert, blanc sur sombre, noir) ; dans
   l'interface, le mot « Gëstukaay » s'écrit en Unbounded.

## Conséquences

- Référence : design system publié (artifact « Gëstukaay », section Structure) ; jetons dans
  `web/app/tokens.css`, composants dans `web/app/globals.css` (mêmes noms de classes qu'avant).
- Accueil recomposé : héros sombre, socle en chiffres (`web/lib/socle.ts`, recopié des décisions
  0002, 0003, 0005, 0008), domaines, trois façons d'obtenir un chiffre, résultats de la mesure
  (`web/lib/mesure.ts`).
- Tests de bout en bout : seul le test du menu mobile change (le bouton s'appelle « Plus »).
- **Reste à faire** : le PDF exporté garde Poppins, Lora et l'ancienne palette (polices TTF à
  embarquer dans `backend/src/gestukaay_backend/polices`) ; les maquettes du cahier (§9) sont à
  mettre à jour pour la v1.2 du document.
