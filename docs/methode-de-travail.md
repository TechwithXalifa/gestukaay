# Méthode de travail — KBD × SAN à distance

Ce document fixe **comment on travaille ensemble** : où vit le code, comment on se le passe,
comment nos deux moitiés se rejoignent, et comment on se parle. Il est court exprès : chaque
règle ici existe pour éviter un problème précis, et on l'applique dès le premier jour.

---

## 1. Le principe : se mettre d'accord sur la frontière, puis travailler sans s'attendre

Le piège classique à deux, c'est : « je t'attends pour avancer ». Serigne attend le moteur pour
faire la page réponse ; Khalifa attend l'API pour tester WhatsApp. Résultat : on intègre tout
la dernière nuit, et rien ne marche.

On l'évite avec trois outils :

1. **Un contrat** ([`docs/api/contrat-v1.md`](api/contrat-v1.md)) : le format exact des données
   échangées, écrit **avant** le code, dans le code (`contracts/`), testé automatiquement.
2. **Un faux moteur** (`GESTUKAAY_MOTEUR=fake`) : il renvoie des réponses conformes au contrat.
   Serigne construit le backend et le web dessus **dès le jour 1**, sans attendre le vrai.
3. **Une intégration continue** : on fusionne dans `main` **au moins une fois par jour**. Le jour
   où le vrai moteur est prêt, on change une variable d'environnement — pas une ligne de code.

> Règle d'or : **on intègre tôt et souvent.** Une petite fusion par jour coûte 10 minutes.
> Une grosse fusion en fin de semaine coûte une nuit.

---

## 2. Un seul dépôt (monorepo), des zones de responsabilité claires

```
gestukaay/
├── contracts/   ← COMMUN : le contrat. Modifié seulement avec l'accord des deux.
├── engine/      ← KBD : compréhension (LLM), résolution, gabarits FR/WO
├── socle/       ← KBD : construction et contrôles du socle de données
├── canaux/      ← KBD : logique WhatsApp / Telegram, voix (STT / TTS)
├── backend/     ← SAN : FastAPI, base, exports PDF/CSV, graphiques
├── web/         ← SAN : Next.js
├── docs/        ← COMMUN : contrat, décisions, méthode
└── .github/     ← COMMUN : CI, modèles de PR, CODEOWNERS
```

**Pourquoi un seul dépôt et pas deux ?** Parce qu'un changement de contrat touche les deux côtés :
dans un seul dépôt, il se fait en **une seule PR** que la CI vérifie en entier. Avec deux dépôts,
on synchronise des versions à la main, et on se trompe.

**Chacun est propriétaire de ses dossiers** (fichier [`.github/CODEOWNERS`](../.github/CODEOWNERS)) :
GitHub demande automatiquement l'avis du propriétaire quand quelqu'un d'autre y touche.
On peut toucher au dossier de l'autre, mais c'est lui qui approuve.

---

## 3. Git : le flux de travail au quotidien

### 3.1 La branche `main` est sacrée

- `main` **fonctionne toujours** : tests verts, démontrable à tout moment.
- **Personne ne pousse directement sur `main`**, même pas pour « une petite correction ».
  Tout passe par une **Pull Request (PR)**. GitHub l'impose (protection de branche, voir §8).

### 3.2 Une tâche = une branche courte

```bash
git switch main && git pull                  # toujours partir d'un main à jour
git switch -c kbd/moteur-resolution-exacte   # préfixe = qui ; puis le sujet
# ... travailler, committer souvent ...
git push -u origin kbd/moteur-resolution-exacte
gh pr create --fill                          # ouvre la PR
```

- Préfixes : `kbd/…`, `san/…`, `contrat/…` (changement du contrat, les deux approuvent).
- **Une branche vit moins d'une journée.** Si c'est plus long, la tâche est trop grosse : on la
  découpe (une PR « squelette de la page réponse », puis « graphique », puis « exports »…).
- Si `main` a avancé pendant que tu travailles :
  ```bash
  git fetch origin && git rebase origin/main   # rejoue tes commits par-dessus main
  git push --force-with-lease                  # jamais --force tout court
  ```

### 3.3 Messages de commit

Format court et lisible (« Conventional Commits ») :

```
feat(engine): résolution exacte sur (indicateur, zone, période)
fix(web): la citation n'était pas copiée sur Safari
test(contracts): vérifie qu'une réponse approchée n'a pas de valeur
docs: méthode de travail
```

Types utiles : `feat`, `fix`, `test`, `docs`, `refactor`, `chore`. Le sujet entre parenthèses
est le dossier. Ça rend l'historique lisible et le rapport final facile à écrire.

### 3.4 La Pull Request

Une PR, c'est **une unité de relecture**. Le modèle ([`.github/pull_request_template.md`](../.github/pull_request_template.md))
se remplit en 2 minutes : quoi, pourquoi, comment tester, lien vers l'exigence (EF-xx / US-xx).

- **Petite** : moins de ~400 lignes modifiées. Une PR de 2 000 lignes n'est pas relue, elle est subie.
- **La CI doit être verte** avant fusion (tests, lint, contrat à jour).
- **Relecture par l'autre** : on relit dans les **2 heures** en journée. C'est la règle qui
  fait tenir tout le reste : une PR qui attend bloque son auteur.
- **Fusion** : « Squash and merge » (un commit propre par PR dans `main`), puis on supprime la branche.

Pendant le hackathon, pour ne pas se bloquer : une PR qui ne touche **que** ses propres dossiers
peut être fusionnée par son auteur si la CI est verte et que l'autre n'a pas répondu en 2 h —
en le prévenant. Les PR `contrat/…` attendent **toujours** les deux approbations.

### 3.5 Relire le code de l'autre : quoi regarder

Pas le style (la CI s'en charge). On regarde :
1. Est-ce que ça respecte le contrat et les engagements (aucune valeur sans source, rien d'inventé) ?
2. Est-ce que ça casse quelque chose de mon côté ?
3. Est-ce que je comprends ce que ça fait ? Sinon, une question en commentaire.

Formuler : « Bloquant : … » (à corriger avant fusion) ou « Suggestion : … » (libre).

---

## 4. Comment nos deux parties se rejoignent

| Étape | Quand | Ce qui se passe |
|---|---|---|
| **1. Contrat figé** | J0 | Ce dépôt. Les exemples de `contracts/examples/` sont les réponses de référence. |
| **2. Squelette qui marche de bout en bout** | J0–J1 | Web → `/v1/ask` → faux moteur → réponse affichée. Moche, mais **complet**. Déployé sur une URL de préproduction. |
| **3. Chacun remplit sa moitié** | J1–J3 | SAN : pages, graphiques, exports, sur le faux moteur. KBD : socle et vrai moteur, testés contre les **mêmes** exemples. |
| **4. Bascule** | dès que le moteur répond à 1 question | En préproduction : `GESTUKAAY_MOTEUR=reel`. Le faux reste disponible pour les tests du web. |
| **5. Benchmark quotidien** | chaque jour | Le jeu de test tourne en CI sur le vrai moteur. Le score est affiché dans la PR. |

Le « squelette qui marche de bout en bout » (étape 2) est **la** priorité du premier jour, avant
toute page jolie ou tout moteur intelligent. Tant qu'il n'existe pas, on ne sait pas si nos
morceaux s'emboîtent.

---

## 5. Se parler : le minimum qui suffit

| Quoi | Où | Quand |
|---|---|---|
| **Point quotidien** (15 min, visio) | Google Meet | chaque matin, même heure. Trois questions : fait hier ? fait aujourd'hui ? qu'est-ce qui me bloque ? |
| **Tâches** | GitHub Projects (tableau : À faire / En cours / En relecture / Fait) | toujours à jour : une tâche = une issue |
| **Discussions techniques** | commentaires de l'issue ou de la PR | elles restent attachées au code |
| **Décisions** | `docs/decisions/NNNN-titre.md` (5 lignes : contexte, décision, conséquences) | dès qu'on tranche quelque chose qui engage l'autre |
| **Urgences** | groupe WhatsApp | « la préprod est cassée », « je suis bloqué » — pas pour décider |

> Une décision prise au téléphone et non écrite n'existe pas. Elle sera oubliée ou comprise
> différemment. On l'écrit dans `docs/decisions/` le jour même.

**Signaler un blocage tout de suite**, pas au point du lendemain. « Je bloque sur X depuis 30 min »
est un message normal, pas un aveu.

---

## 6. Secrets et configuration

- **Jamais de clé dans le code ni dans Git** (OpenRouter, Meta, Telegram…). Un secret poussé sur
  GitHub est considéré comme compromis : on le révoque immédiatement.
- Chaque variable est déclarée dans [`.env.example`](../.env.example) avec un commentaire, **sans
  valeur**. Chacun copie en `.env` (ignoré par Git) et remplit.
- Les secrets partagés s'échangent **hors Git** (gestionnaire de mots de passe partagé, ou message
  éphémère), et vont en production dans les « Secrets » de GitHub / de l'hébergeur.

---

## 7. Définition de « fini »

Une tâche est finie quand :
- [ ] le code est fusionné dans `main` (pas « ça marche sur ma machine ») ;
- [ ] les tests couvrent le cas nominal et au moins un cas limite ;
- [ ] la CI est verte ;
- [ ] c'est visible en préproduction (pour ce qui se voit) ;
- [ ] l'issue est fermée et reliée à l'exigence (EF-xx / US-xx).

---

## 8. Mise en place (une fois, ~30 minutes)

**Khalifa :**
1. Créer le dépôt GitHub **privé** `gestukaay` (il deviendra public pour la livraison, ENF-16) et pousser ce dépôt.
2. Inviter Serigne comme collaborateur avec le rôle **Maintain**.
3. Protéger `main` : *Settings → Branches → Add rule* : PR obligatoire, 1 approbation,
   CI verte obligatoire (`contrat-et-tests`), pas de push direct, historique linéaire.
4. Remplacer `@SERIGNE_GITHUB` dans `.github/CODEOWNERS` par son identifiant GitHub.
5. Créer le tableau GitHub Projects et les issues de la semaine (voir §9).

**Serigne :**
1. `git clone`, puis `brew install uv` et `uv sync`, puis `uv run pytest` (tout doit être vert).
2. Lire [`docs/api/contrat-v1.md`](api/contrat-v1.md) et les fichiers de `contracts/examples/`.
3. Créer `backend/` et `web/` dans une première PR `san/squelette`, branchés sur le faux moteur.

**Les deux :** premier point quotidien pour valider ce document et le contrat.

---

## 9. Découpage de la semaine

Le cahier des charges (13.1) prévoit 72 h. Le hackathon étant **mixte**, on fait avant
l'événement tout ce qui est long ou risqué, et on garde les 72 h pour intégrer, fiabiliser et
présenter.

| Jour | KBD — données, IA, wolof, WhatsApp | SAN — backend, web, déploiement | Ensemble |
|---|---|---|---|
| **J0** | Contrat, dépôt, méthode *(ce document)* | Lecture du contrat, squelette backend + web sur faux moteur | Point de lancement, protection de `main` |
| **J1** | Socle curé : zones SN-xx, ~200 indicateurs, contrôles | `/v1/ask` + page réponse (3 issues) ; préproduction en ligne | **Squelette de bout en bout déployé** |
| **J2** | Moteur : compréhension multi-fournisseur + résolution ; jeu de 100 questions | Graphiques SVG, citation, exports CSV/PDF | Bascule préprod sur le vrai moteur |
| **J3** | Wolof (normalisation, lexique) ; webhook WhatsApp + Telegram | Accueil, micro web, bascule FR/WO, états (7.3) | Benchmark quotidien en CI |
| **J4** | Voix : transcription + audio de réponse ; corrections du benchmark | Où je me situe, journal (back-office minimal), finitions mobile | Recette des parcours P1–P4 |
| **72 h** | Fiabilisation, rapport de mesure | Fiabilisation, performance (7.6) | **Gel à H+54**, vidéo de secours à H+66 |
