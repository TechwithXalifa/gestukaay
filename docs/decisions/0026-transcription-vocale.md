# 0026 — Transcription des notes vocales : M-Kiriku

**Date** : 2026-10-05 · **Statut** : accepté (KBD) · **Issues** : #27, #28 · **Exigences** : EF-11, EF-15, US-07, US-09, 10.2, 14.2

## Contexte

Le parcours P1 (Awa, note vocale en wolof sur WhatsApp) demande une transcription du wolof et du
français, jusqu'à 60 s, en moins de 2 s (réponse vocale complète en moins de 8 s en médiane). Le
cahier vise un modèle de la famille Whisper adapté au wolof, choisi sur des enregistrements réels.

## Mesures (`mesure/rapports/transcription.md`)

62 notes WhatsApp réelles (KBD et Aziz, les 31 questions wolof du jeu de test), critère principal
la **bonne réponse** du moteur (choix KBD), puis le taux d'erreur par mot et la latence. Huit
modèles comparés ; trois bancs d'essai concordants :

- avec la compréhension LLM : **M-Kiriku 35/62** et Kiriku-Wolof 35/62, pour un plafond de 51/62
  (texte tapé) ; WER médian 37 % et 50 % ;
- en règles : M-Kiriku 32, Kiriku-Wolof 31, Whosper 21, ADIA (API) 13/31 sur les notes de KBD ;
- WaxalNLP, six voix inconnues des modèles : M-Kiriku meilleur sur 21 extraits sur 27 ;
- 1,9 s par note sur Mac M3 (demi-précision) ; **30 s sur processeur seul**.

L'essentiel de l'écart avec le plafond vient de la compréhension, pas de la transcription :
noms de lieux en wolof (seeju, maatam, kawlak), graphies (ceeb, poore, taux scolaire), nombres.

## Décisions

1. **Modèle : M-Kiriku** (`AIHubSN/M-Kiriku-ASR`, IA Hub Sénégal : wolof, pulaar, sérère), avec
   **Kiriku-Wolof** (`AIHubSN/Kiriku-Wolof-ASR`) en secours. Langue de la note non imposée : le
   modèle gère le wolof, le français et leur mélange (3/5 sur des questions en français).
2. **Un service de transcription à part**, appelé par une adresse (`TRANSCRIPTION_URL`), au format
   standard des API compatibles OpenAI (`POST /v1/audio/transcriptions`). Il tourne, dans l'ordre :
   sur une **carte graphique louée** si le budget le permet ; sinon sur le **Mac M3 de KBD** ; sinon
   sur le **PC d'Aziz** (RTX 3050, 4 Go de mémoire vidéo : à tester, version compressée int8 au besoin).
   Changer de machine revient à changer `TRANSCRIPTION_URL`.
3. **Repli automatique sur ADIA** (API payante, ~1,6 FCFA par note) si le service ne répond pas ;
   en dernier recours, « écrivez votre question ». ADIA envoie la voix chez un tiers : à mentionner
   sur la page Confidentialité ; pendant les essais, seulement des voix dont le locuteur a accepté.
4. **Après la transcription** : les nombres dits en lettres sont convertis en chiffres (« deux mille
   vingt quatre » -> 2024) avant d'aller au moteur ; « J'ai compris : … » est renvoyé (EF-15).
   **Remplacé par la 0027 (point 4)** : pas de « J'ai compris » écrit pour une note vocale.
5. **Écartés** : Whisper standard (traduit le wolof en phrases françaises inventées), dofbi/wolof-asr
   et whisper-small-wolof (boucles sur de vraies voix), Wolof-HuBERT-CTC (écrit les sons, licence
   AGPL-3.0), ADIA en principal (inventions, mots français mal transcrits).

## Conséquences

- #28 : service de transcription, branchement dans `MoteurReel.transcrire`, conversion des nombres,
  repli ADIA.
- Le plus gros gain pour la voix comme pour l'écrit est le vocabulaire wolof (#22, #23) : noms wolof
  des lieux et variantes de graphie, relevés dans ces transcriptions, à valider par KBD.
- Les notes vocales de test restent hors Git (`../voix_test/`, ce sont des voix).
