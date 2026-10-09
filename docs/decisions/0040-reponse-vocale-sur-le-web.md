# 0040 — Réponse vocale sur le site web

**Date** : 2026-10-09 · **Statut** : proposé (KBD), à valider par SAN (contrat 1.7.0, route, site) ·
**Exigences** : EF-16, EF-20, US-10 · **Complète** : 0026, 0027, 0029

## Contexte

Sur WhatsApp et Telegram, une question posée à la voix en wolof reçoit une note vocale (Oolel, repli
ADIA, décision 0029). Sur le site, la question vocale existe (transcription, 0026 et 0027) et le site
envoie déjà `audio_retour: true`, mais l'API ne remplissait jamais `audio_url` et n'avait aucune route
pour l'audio : le lecteur de la réponse n'apparaissait jamais. Le contrat ne prévoyait l'audio que pour
une réponse exacte.

## Décisions (KBD, 09/10)

1. **Wolof seulement**, comme sur WhatsApp : le projet n'a pas de voix française. Une question vocale
   dont la réponse est en wolof reçoit `audio_url` ; en français, le texte seul.
2. **À la demande** : `/v1/ask` ne calcule pas la voix (plusieurs secondes) ; il renvoie l'adresse
   `GET /v1/answers/{id}/audio.ogg`, qui compose la note (`parole.py`, jamais générée librement) et la
   dit au premier appel. Les notes sont gardées **en mémoire** quelques minutes pour une réécoute, jamais
   écrites sur disque ni journalisées (0029). Limite de requêtes : groupe « voix ».
3. **Les trois issues** : exacte, approchée (la reformulation) et refus (le message) peuvent être dites :
   contrat **1.7.0**, `audio_url` ajouté à `ReponseApprochee` et `ReponseAucune`.
4. **Lecture** : sur un téléphone (écran tactile), la note démarre seule après une question posée à la
   voix ; sur un ordinateur, un bouton « Écouter ». Si le navigateur bloque la lecture automatique, le
   bouton reste. Une réponse ouverte plus tard par son lien (`/r/…`) ne démarre jamais seule.

## Conséquences

- La voix ne retarde jamais le texte : le texte s'affiche d'abord ; le lecteur demande aussitôt la durée de
  la note, ce qui lance son calcul pendant la lecture du texte. Mesuré le 09/10 avec le vrai moteur, Oolel
  éteint : repli ADIA, note de 47 Ko en 31 s au premier appel, 10 ms ensuite (mémoire).
- Coût : une note ADIA (payante, environ 7 FCFA) seulement quand Oolel ne répond pas, et seulement pour
  une question vocale en wolof.
