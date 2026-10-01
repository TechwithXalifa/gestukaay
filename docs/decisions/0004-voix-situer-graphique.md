# 0004 — Voix sur le web, « Où je me situe », graphique d'une valeur unique

**Date** : 2026-10-01 · **Statut** : accepté par KBD, **à valider par SAN** · **Origine** : retours de SAN
sur les écarts maquettes / cahier / contrat · **Mise en œuvre** : contrat v1.1.0 (#45)

## 1. Écoute vocale sur le web

**Constat (SAN).** La maquette montre une transcription corrigeable avant l'envoi (US-09, EF-15 :
« éditable avant l'envoi définitif »). Le contrat v1.0.0 envoie l'audio à `/v1/ask/audio` et répond
directement : aucune correction possible.

**Décision.**
- Nouvelle route **`POST /v1/transcrire`** : audio (WebM/OGG Opus, 60 s max) → transcription, langue
  détectée, durée. Rien n'est conservé (audio supprimé après transcription, 10.7).
- Parcours web : enregistrer → `/v1/transcrire` → texte affiché et **corrigeable** → `/v1/ask`.
- `/v1/ask/audio` (transcription + réponse en un appel) reste pour **WhatsApp et Telegram**, où la
  correction se fait en répondant « non » / « déet » (US-09).
- La transcription s'affiche **dès l'arrêt de l'enregistrement** (2 s de silence, 7.3), pas pendant
  que l'on parle : aucun modèle de transcription wolof ne fonctionne en continu aujourd'hui.
  **Maquette à ajuster** (« transcription en direct » → « transcription à l'arrêt »).

## 2. Module « Où je me situe »

**Constat (SAN, vérifié dans le socle).** Les maquettes et le cahier (EF-38, US-20) parlent de
**déciles**. Or le socle ne publie **aucun seuil** (bornes en FCFA) de déciles ni de quintiles de
dépenses : impossible de placer un ménage dans une tranche sans calculer nous-mêmes des seuils, ce
que l'engagement 02 interdit. Le seul jeu « quintile » (`qjyrtof`) donne la répartition de la
population d'une région entre quintiles nationaux d'un indice de bien-être (ex. Kolda 2023 : 63 %
dans le quintile le plus bas), pas des bornes de dépenses.

**Décision : comparer le ménage aux moyennes publiées, sans tranches.**
- Entrées (inchangées, EF-37) : région, taille du ménage, niveau d'instruction du chef, dépenses
  mensuelles par tranches.
- Résultat :
  - dépense annuelle par personne du ménage (calcul sur **les seules données saisies**) comparée à la
    **consommation moyenne par tête** publiée pour la région et pour le pays (`jcvcajc`, FCFA) ;
  - **taux de pauvreté** publié des ménages de même taille dans la région (`jcvcajc`) ;
  - **contexte** : part de la population de la région dans le quintile le plus bas (`qjyrtof`), accès
    à l'eau et à l'électricité de la région ;
  - chaque valeur avec sa source ; encadré pédagogique « C'est quoi une moyenne ? » à la place de
    « C'est quoi un décile ? » (EF-39) ; aucune donnée saisie conservée (EF-40, US-21).
- **Maquettes à refaire** (plus de barre de déciles). Écart au cahier à acter (EF-38, US-20).
- Si des seuils officiels sont un jour publiés (rapports EHCVM), le module pourra y revenir.

## 3. Graphique d'une valeur unique

**Constat (SAN).** Le tableau 5.4 dit « valeur unique → chiffre seul, un graphique d'un seul point
n'apporte rien » ; la maquette 8.2 montre pourtant un graphique pour une valeur unique ; le contrat
documente `graphique: null`.

**Décision.** Les deux textes sont compatibles : la maquette montre un **graphique de contexte**, pas
un point seul. Pour une valeur unique, le moteur fournit, si les données existent :
1. le **classement des régions** sur le même indicateur et la même période, zone demandée mise en
   évidence (`mise_en_evidence: true`, 9.8) ;
2. à défaut, l'**évolution dans le temps** de la zone demandée ;
3. sinon, pas de graphique.

Le contrat ne change pas (`graphique` est déjà optionnel et porte la mise en évidence) : seule sa
documentation est corrigée.

## Conséquences

- **Contrat v1.1.0 (#45)**, à faire approuver par SAN, regroupe : `nature` de la valeur (0002),
  niveau `academie` (0003), route `/v1/transcrire`, contrat de `/v1/situate`, documentation du graphique.
- **Maquettes** : écoute vocale (§1) et « Où je me situe » (§2) à ajuster côté SAN.
- **Cahier des charges** : écarts à noter pour la v1.2 du document (EF-38, US-20, tableau 5.4).
