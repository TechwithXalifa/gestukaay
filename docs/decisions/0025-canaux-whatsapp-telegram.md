# 0025 — Canaux WhatsApp et Telegram

**Date** : 2026-10-04 · **Statut** : accepté (KBD, SAN) · **Issues** : #31 à #34, #36 · **Exigences** : EF-06, EF-19 à EF-25, US-07, US-12, US-13, 10.7

## Contexte

Sans canal de messagerie, le parcours P1 (Awa, WhatsApp) n'est pas démontrable. Il fallait décider
qui reçoit les messages de Meta, qui les interprète et répond, et sous quelle forme.

## Décisions

1. **Répartition** (proposée par KBD, mise en œuvre par SAN en #119) :
   - **SAN, backend** : routes `/webhooks/whatsapp` et `/webhooks/telegram`, vérification de Meta,
     **signature `X-Hub-Signature-256`** (et jeton secret Telegram) en temps constant, 200 immédiat
     et traitement en tâche de fond, **unicité par identifiant de message** (table `messages_recus`,
     purge à 48 h), numéro haché et suivi sur trois échanges comme pour le web ;
   - **KBD, paquet `canaux/` (`gestukaay_canaux`)** : lire le payload, interpréter, formater et
     **envoyer** (accusé de lecture et « en train d'écrire », réponse, liste de choix, téléchargement
     des notes vocales en mémoire seulement). Interface : `lire(payload)` et `traiter(entrant, services)`.
2. **Message de réponse** (#33), texte seul, aucun fichier : le chiffre (gras sur WhatsApp), l'explication,
   la note de périmètre, la source et sa date, le lien `/r/{id}`, « — gestukaay ». Telegram : texte brut.
3. **Choix d'une approchée** (#34) : numérotés dans le texte (lisibles partout) **et** proposés en liste
   WhatsApp (bouton « Tànnal / Choisir ») ou en boutons Telegram ; « 1 », « benn », « ñaar »… tapés
   marchent aussi. Les boutons de réponse WhatsApp (20 caractères) sont écartés : trop courts.
4. **Notes vocales** : tant que la transcription (#28) manque, réponse polie « je ne sais pas encore
   écouter les notes vocales » ; dès qu'elle existe, le vocal est traité (`source = voix`).
5. **Textes fixes** (accueil, aide, exemples, langue, stop, choix, erreur) et **mots de commande** :
   wolof écrit par KBD (0009), dans `canaux/src/gestukaay_canaux/textes.csv` et `commandes.csv`.
   Tant que la détection de la langue (#24) manque, un texte fixe part en wolof puis en français ;
   l'accueil, bilingue, part tel quel. Une commande n'est reconnue que si le message ne contient
   qu'elle. Premier message d'une conversation : l'accueil d'abord.
6. **Secrets** : `WHATSAPP_TOKEN` (utilisateur système, sans expiration) en en-tête, jamais dans une
   adresse ; le jeton du bot Telegram fait partie de l'adresse de l'API : toute erreur réseau est
   relancée **sans** son adresse, pour qu'il n'arrive jamais dans les journaux.

## Conséquences

- La réponse n'est envoyée qu'en retour d'un message reçu : toujours dans la fenêtre de 24 h de Meta.
- Reste pour #31 : l'essai réel (jeton permanent et App Secret réinitialisé dans `.env`, URL publique
  du webhook déclarée chez Meta). Pour #36 : créer le bot et déclarer son webhook (`secret_token`).
- Les réponses du moteur restent en français tant que les gabarits wolof (#25) manquent.
