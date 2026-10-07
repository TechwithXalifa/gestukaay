# 0032 — Réponse écrite en wolof pour une question en wolof (option B)

**Date** : 2026-10-07 · **Statut** : accepté (KBD) · **Issues** : #24, #25 · **Modifie** : 0017, 0019

## Contexte

Jusqu'ici, toute réponse écrite était en français et déclarée « fr » (0019), même pour une question en wolof ;
le wolof n'existait qu'à l'oral (0029). Le tableau de bord comptait donc le wolof comme du français (0,7 %).
Essai Telegram du 07/10 : « Tu peux pas répondre en wolof ? ».

## Décisions (choix de KBD)

1. **Option B** : une question en wolof reçoit sa réponse écrite **en wolof seul**, déclarée « wo ».
2. **Langue** : celle choisie par l'utilisateur (`AskRequest.langue`) prime ; sinon celle détectée dans la
   question (`langue.detecter`, 100/104 sur le jeu de test ; les 4 écarts sont du charabia ou du wolof écrit
   avec des mots français, sans conséquence).
3. **Mêmes phrases que la voix** (gabarits de KBD, `gabarits_wo.csv`), rien de généré, avec un mode écrit :
   chiffre exactement tel qu'affiché (7.4), années en chiffres (« ci atum 2023 »), sigles écrits (« ANSD »,
   « www.ansd.sn » au lieu de leur épellation), mots d'unité de KBD (« nit », « ci kilo bi »), pas de limite
   de 20 s.
4. **Morceaux sans wolof : en français pour l'instant** (valeur arrondie, unité non précisée, citation EF-35,
   libellés des choix et des suggestions, « pas encore disponible ») ; ils seront remplacés dès que KBD les
   écrit. Sans phrase wolof pour un cas, la réponse reste en français et déclarée « fr ».

## Conséquences

- `parole.texte_ecrit`, `parole.en_wolof` ; `MoteurReel.repondre/executer` réécrivent la réponse si « wo ».
- Le journal, le tableau de bord, le site, le PDF et les canaux reçoivent le wolof sans changement de contrat.
