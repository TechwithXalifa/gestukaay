# 0029 — Voix de réponse en wolof

**Date** : 2026-10-06 · **Statut** : accepté (KBD) · **Issues** : #29, #30, #25 · **Exigences** : EF-16, EF-20, US-10, 7.6 ; décisions 0009, 0026, 0027

## Contexte

Le cahier demande une réponse audio en wolof, composée à partir d'un gabarit de phrase contraint,
avec des nombres dits par un module dédié et jamais par génération libre (EF-16), en 20 s et 60 Ko
au plus (7.6). Trois voix ont été comparées le 5 octobre sur les mêmes phrases, puis écoutées par KBD
(`voix_test/tts/`, hors Git) : Kiriku-Wolof-TTS (IA Hub Sénégal), ADIA (Concree, API payante) et
Oolel-Voices (Soynade). Kiriku n'a pas de chiffres dans son alphabet ; ADIA est payant ; Oolel a la
voix la plus claire et la plus naturelle.

## Décisions

1. **Oolel-Voices**, utilisé **sans aucune modification** de son code (licence AGPL-3.0 : on cite la
   licence et le lien vers son code), dans un service à part, comme la transcription (0027).
   Réglage prudent : température 0,3, exagération 0,2, cfg 0,5. Mesuré sur 220 puis 60 notes :
   avec une orthographe soignée, 1 note ratée sur 30 et aucune boucle ; les réglages d'origine
   ajoutaient des mots parasites. Voix de référence : celle de la démo d'Oolel, en attendant une
   voix professionnelle (enregistrement de 10 à 20 s, accord écrit de la personne).
2. **Repli** : si Oolel ne répond pas ou si la note est rejetée, un 2e tirage, puis ADIA, puis le
   texte seul. **Contrôle** : M-Kiriku retranscrit la note ; la comparaison porte sur les mots, pas
   sur les nombres (M-Kiriku relit mal les grands nombres qu'Oolel dit bien, constaté à l'écoute).
3. **Le texte lu est composé, jamais généré** (`engine/…/parole.py`) : phrases à trous écrites par
   KBD avec Gemini puis validées à l'écoute (`gabarits_wo.csv`, 24 phrases), mots de KBD
   (`parole_wo.csv` : zones, périodes, sources, unités), noms wolof des académies, départements et
   27 indicateurs (`zones.csv`, `indicateurs.csv`, statut `valide`). Plusieurs tournures sont
   gardées (formelle | orale) : une par réponse, toujours la même pour une même réponse.
4. **Les nombres** (règles de KBD) : le nombre dit est la valeur **affichée** ; « ak » entre les
   groupes ; 30 = « fanweer » ; « benn milyoŋ » mais « junni » ; « wirgil » pour la virgule ;
   « … ci téeméer » (%), « … ci junni » (‰) ; devant un nom, le dernier mot prend -i (« juróom-ñaari
   nit », « junniy ton »). **L'argent se compte en dërëm** (5 FCFA) sous le million : 1 000 F =
   « ñaari téeméer », 150 000 F = « fanweeri junni » ; le mot « dërëm » n'est dit que sous 100 F ;
   un montant qui n'est pas un multiple de 5 se dit en CFA suivi de « sefaa » ; au-delà du million,
   en CFA, sans « sefaa ». **Les années se disent en français** (« ci atum deux mille vingt-trois ») :
   « aucun natif ne dit une année en wolof » (KBD). Les sigles s'épellent à la française
   (« A-EN-ES-DE »), les parenthèses sont lues.
5. **Indicateurs sans nom wolof** (plus de 4 000 sur 4 282) : phrase passe-partout wolof avec le
   nom français de l'indicateur, comme on parle couramment (choix KBD). Refus et réponses approchées
   ont aussi leur phrase.
6. **20 s au plus** (#30) : la variante la plus courte, puis on retire la source (elle reste dans le
   texte écrit), « dernière donnée publiée », la comparaison au national ; un classement passe de 3 à
   2 puis 1 zone. Sur les 104 questions du jeu de test : 102 textes, médiane estimée 16 s ; 4
   dépassent encore 20 s (plusieurs très grands nombres : PIB, populations comparées). **Écart au
   cahier (7.6, 20 s), décidé par KBD** : ces notes partent quand même, en une seule note ; le débit
   Opus baisse alors pour rester sous 60 Ko (une personne qui ne lit pas doit tout entendre).
7. **Pauses** : Oolel change « : » en virgule ; on découpe le texte et on insère un silence (0,6 s
   après « : », plus court entre les phrases), préféré à l'écoute par KBD. Opus à 20 kbps : 20 s =
   50 Ko au plus.
8. **Où** : un GPU loué si le budget le permet, sinon la machine de l'équipe (Mac M3 : le calcul
   dure à peu près la durée de la note). WhatsApp et Telegram : le texte part d'abord, la note
   suit. Site : la note est fabriquée dès la réponse servie, et servie par le backend.

## Conséquences

- La conversion inverse des nombres (#28) comprend aussi « milyaar », les formes en -i (« fukki
  junni », « téeméeri junni », « junniy ») et « tus wirgil juróom » (0,5) : vérifié par 5 000 allers
  et retours (nombre -> wolof -> chiffres).
- Tout nouveau mot wolof passe par KBD ; les fiches de travail sont dans `voix_wolof/` (hors Git).
- « … ci réew mi » à la fin d'un nom d'indicateur n'est dit que pour le Sénégal (KBD).
- Reste : la voix professionnelle.
