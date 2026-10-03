# 0019 — Moteur réel branché dans l'API

**Date** : 2026-10-03 · **Statut** : accepté (KBD) · **Issues** : #17, #95 · **Exigences** : EF-05, EF-06, methode-de-travail §4

## Contexte

Les briques du moteur existaient séparément : compréhension (#10, 0010), résolution (#11, 0011),
réponse approchée (#12, 0015), refus (#13, 0017), gabarits (#16, 0014), comparaison et classement
(#14, 0018). Le backend n'utilisait que le faux moteur. Il fallait décider dans quel ordre les
enchaîner, quelle langue déclarer tant que le wolof n'est pas prêt, et quoi faire des fonctions pas
encore construites.

## Décisions

1. **Ordre de la chaîne** (`engine/src/gestukaay_engine/moteur.py`, `MoteurReel.repondre`) :
   - question inintelligible -> refus `incomprehension` ;
   - valeur trouvée par la résolution -> réponse exacte (gabarits, graphique de la résolution) ;
   - type de question que la résolution ne traite pas (`non_traite`) -> « Ce type de question n'est
     pas encore disponible. » **Jamais** le refus `hors_socle` (« Cette donnée n'existe pas… ») : la
     donnée existe peut-être. Depuis #14, plus aucun code ne produit `non_traite` : c'est un garde-fou ;
   - projection, ou lieu inconnu non déclaré dans `rattachements.csv` -> refus (#13) ;
   - sinon réponse approchée (#12) ; un seul choix vérifié -> refus avec ce choix en suggestion ;
     aucun -> refus avec des indicateurs proches.
2. **Confirmation d'un choix** (`executer`) : résolution seule, sans LLM ; un échec donne un refus,
   jamais une nouvelle réponse approchée (pas de boucle).
3. **Langue** : tant que la détection (#24) et les gabarits wolof (#25) manquent, `auto` vaut `fr`, et
   une question forcée en `wo` est comprise mais la réponse est rédigée en français et déclarée `fr`.
   Pas de faux wolof (0009).
4. **Fonctions pas encore construites** : `transcrire` (#28) et `situer` (#95) lèvent `NonDisponible`,
   que le backend rend en **503**. Le faux moteur n'est pas repris : `situer` y renvoie les chiffres
   fixes de Kolda quelle que soit la saisie, ce serait un chiffre inventé.
5. **Motif « pas encore disponible »** : le motif `non_disponible` est demandé pour le contrat 1.3.0
   (SAN). En attendant, `incomprehension`, le seul motif du contrat 1.2.0 qui ne prétend pas que la
   donnée est absente (constante `MOTIF_NON_DISPONIBLE`, à changer après la 1.3.0).
6. **Chargement** : socle et client LLM chargés une fois au démarrage du backend ; sans `LLM_CHAINE`,
   compréhension par règles locales (signalé sur la sortie d'erreur). L'identifiant de réponse est
   donné par le moteur ; l'URL stable et la latence restent au backend.
7. **Sens du classement** : `ordre_effectif()` (résolution) est partagé par le tri et la phrase, pour
   qu'un repli lexical (« le plus faible ») ne donne jamais un tri croissant sous une phrase « la plus
   élevée ».

## Conséquences

- `GESTUKAAY_MOTEUR=reel` fonctionne dans le backend : vérifié sur le socle `2026.10.0` (valeur,
  classement, comparaison, évolution, approchée puis confirmation, projection, lieu inconnu).
- **SAN** : traduire `NonDisponible` (exporté par `gestukaay_engine`) en 503 sur `/v1/transcrire` et
  `/v1/situate` ; d'ici là, ces routes rendent 500 avec le vrai moteur.
- Le faux moteur reste le défaut (`GESTUKAAY_MOTEUR=fake`) pour les tests du web.
