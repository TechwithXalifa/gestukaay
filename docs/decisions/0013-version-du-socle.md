# 0013 — Version figée du socle et format de chargement

**Date** : 2026-10-03 · **Statut** : accepté (KBD, SAN) · **Issue** : #8 · **Proposé par** : SAN

## Contexte

Le socle extrait (0006) est un dossier de CSV hors Git, produit par `socle/scripts/extraire.py` avec
les référentiels du dépôt (indicateurs, zones, natures, corrections). Il faut savoir quelle version
sert chaque réponse, la reproduire sur une autre machine, et décider qui la charge où.

## Décisions (proposition de SAN, précisions de KBD)

1. **Le moteur lit les CSV en mémoire** (V1.0) : 645 000 valeurs, 2,3 s au démarrage, 190 Mo ; aucune
   base pour répondre aux questions.
2. **PostgreSQL sert seulement le backend** : réponses (liens `/r/…`), journal des requêtes, retours
   des utilisateurs (SAN). Le socle n'y est chargé que si un besoin apparaît (Explorer, V1.1) : pas de
   deuxième copie à synchroniser pendant le hackathon.
3. **Version figée et numérotée** (`2026.10.0`) : un dossier par version dans `../socle_gestukaay/`,
   avec `VERSION` ; le moteur la renvoie dans `version_socle`, citée dans chaque réponse. **Nouvelle
   version = nouveau dossier** ; `extraire.py --version` refuse de réécrire une version publiée.
   Les extractions de travail vont dans `brouillon/`.
4. **Docker** : le dossier est monté en lecture seule dans l'API (`GESTUKAAY_SOCLE_EXTRAIT`, #67).
   Le moteur accepte un dossier de version ou le dossier qui les contient (il prend alors la version
   publiée la plus récente).
5. *(KBD)* **Manifeste** `MANIFEST.json` : date, commit Git, référentiels modifiés non commités, comptes,
   **empreintes sha256** des fichiers du socle et des référentiels utilisés.
6. *(KBD)* **Vérification au démarrage** : tout indicateur du socle doit exister dans le référentiel du
   dépôt, sinon le moteur **refuse de démarrer** ; un référentiel modifié depuis l'extraction est signalé.
7. *(KBD)* **Reproduction** : SAN régénère la version sur sa machine depuis le socle brut ; l'extraction
   est déterministe (vérifié : deux passes, mêmes empreintes), le manifeste prouve l'identité.

## Conséquences

- **2026.10.0** sera coupée après la fusion de #5 (nature) et #6 (corrections), sur `main` :
  `uv run python socle/scripts/extraire.py --version 2026.10.0`.
- **Écart au cahier 10.3** : la table `version_socle` (brouillon / validé / publié, score du benchmark)
  est remplacée en V1.0 par le dossier figé et son manifeste ; la table viendra avec le back-office (V1.1).
