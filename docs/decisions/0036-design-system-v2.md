# 0036 — Design system v2 « Terre et baobab » et nouvelle structure du site

**Date** : 2026-10-07 · **Statut** : proposé (SAN), à valider par KBD · **Touche** : `web/` seulement
(aucun changement de contrat, de moteur ni de canal) · **Écart au cahier** : §9.3, §9.4 et §12.1

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
4. **Mouvement** : barres qui poussent, apparitions, micro qui pulse ; tout en CSS, coupé par
   `prefers-reduced-motion`. Sur l'accueil seulement, les chiffres du socle et le taux de bonnes
   réponses défilent jusqu'à leur valeur (`Compteur`) : effet visuel, le texte exact reste lu par
   les lecteurs d'écran et copié tel quel. Le chiffre d'une réponse ne défile jamais : il s'affiche
   d'emblée. Pas de vidéo ni de particules : budget 7.6 tenu (JavaScript initial de 118 à
   128 Ko selon la page).
5. **Structure** : trois espaces et la confiance (Demander, Données, Où je me situe, Méthode) ;
   Indicateurs, Domaines et Explorer réunis par des onglets ; sur mobile, une barre d'onglets en
   bas (Demander, Données, Me situer, Plus) remplace le bouton menu, « Plus » ouvre la barre
   latérale. Toutes les adresses sont inchangées (`/r/…`, tests, liens WhatsApp).
   Tant que catalogue, fiche et séries ne sont pas écrits dans le moteur réel (#156), « Données »
   (en-tête, menu, pied de page) et la troisième façon de l'accueil ouvrent Domaines, la seule
   page de l'espace qui répond sans eux.
   L'en-tête flotte en pilule arrondie au-dessus de la page (inspiré d'adafrik.com) : il glisse
   hors de l'écran quand on descend et revient dès qu'on remonte, ou quand le focus clavier y
   entre ; il reste en place si moins d'animations est demandé.
6. **Icônes** : Phosphor Icons, graisse duotone (licence MIT), choisies le 08/10 parmi Phosphor,
   Hugeicons, Tabler et Solar ; tracés recopiés dans `web/components/icones.tsx`, sans dépendance.
   Pas de sur-titre à point au-dessus des titres, ni de numéro de version du socle dans les pages
   publiques (retours de SAN du 08/10).
7. **Logo** : l'icône baobab n'est pas recolorée (vert, blanc sur sombre, noir) ; dans
   l'interface, le mot « Gëstukaay » s'écrit en Unbounded.
8. **Résultats publiés** : l'accueil et la page Méthode ne donnent qu'un chiffre, le taux de bonnes
   réponses aux tests (`web/lib/mesure.ts`). Ni temps de réponse, ni refus, ni liste d'erreurs
   (choix de SAN du 08/10 : le temps médian de 1,4 s du 04/10 ne correspondait plus à la recette
   du 08/10, #156). Écart au cahier §12.1 (« nous publions nos erreurs avec nos réussites ») : le
   détail reste dans les rapports de `mesure/rapports/`.

## Conséquences

- Référence : jetons dans `web/app/tokens.css`, composants dans `web/app/globals.css` (mêmes noms
  de classes qu'avant).
- Accueil recomposé : héros sombre, socle en chiffres (`web/lib/socle.ts`, recopié des décisions
  0002, 0003, 0005, 0008), domaines, trois façons d'obtenir un chiffre, taux de bonnes réponses
  (`web/lib/mesure.ts`). Ces deux fichiers ne se synchronisent pas : à mettre à jour à chaque
  version du socle et à chaque mesure.
- Tests de bout en bout : le bouton du menu mobile s'appelle « Plus » ; `e2e/outils.ts` attend la
  fin des animations (sauf celles sans fin) avant axe, pour mesurer les contrastes sur l'état final ;
  le test de la page Méthode suit le point 8 ; un test mobile vérifie que « Continuer » (Où je me
  situe) n'est jamais recouvert par la barre d'onglets ; un autre, que l'en-tête se cache en
  descendant et revient en remontant ou au clavier.
- **Reste à faire** : le PDF exporté garde Poppins, Lora et l'ancienne palette (polices TTF à
  embarquer dans `backend/src/gestukaay_backend/polices`) ; les maquettes du cahier (§9) sont à
  mettre à jour pour la v1.2 du document.
