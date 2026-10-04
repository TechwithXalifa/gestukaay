# 0021 — Suivi sur trois échanges

**Date** : 2026-10-04 · **Statut** : accepté (KBD) · **Issue** : #15 · **Exigences** : EF-09, US-05

## Contexte

Le moteur recevait déjà `contexte` (les requêtes des échanges précédents), mais une question de
suivi ne reprenait que l'indicateur et les zones : « Et Thiès ? » après « Chômage à Dakar en 2019 »
répondait pour la dernière année publiée, alors qu'EF-09 demande la même période. Le backend ne
transmettait pas encore le contexte, et le site n'envoie pas de `conversation_id`.

## Décisions

1. **Ce que le suivi reprend** : tout ce que la question ne précise pas est repris de l'échange
   précédent (zones, période, intention comparaison ou classement avec son sens) ; ce qu'elle cite
   remplace. La désagrégation n'est reprise que pour le **même indicateur** : les dimensions d'un
   autre jeu peuvent ne pas exister (« cycle » n'a pas de sens pour le chômage). Une question qui
   parle du temps sans année (« et aujourd'hui ? ») ne reprend pas la période.
2. **Les 3 échanges** : on repart du **dernier échange compris** (avec un indicateur) parmi les 3
   derniers ; sa requête porte déjà ce qui a été repris avant. Un refus ou une incompréhension
   intercalés ne coupent pas le fil ; au-delà de 3 échanges, il est perdu.
3. **Expiration** (backend, SAN) : contexte oublié après **30 minutes** sans échange. Le site crée un
   `conversation_id` par onglet ; sur WhatsApp, c'est le numéro haché.
4. **Marqueurs** d'une question courte (5 mots au plus) : en tête « et », « pour », « ak » ;
   n'importe où « aussi », « nak », « tamit » ; « même chose ». Les marqueurs wolof sont écrits par
   KBD (0009). « ak » ne compte qu'en tête : « Chômage Dakar ak Thiès » est une comparaison.
5. L'héritage est appliqué **après** la compréhension, sans changer le message envoyé au LLM
   (mesuré en 0010) : il est le même sur le chemin LLM et sur les règles.

## Conséquences

- **SAN** : garder pour chaque conversation les requêtes des 3 derniers échanges (celle du choix
  confirmé pour une approchée, `None` pour une incompréhension), les passer à `moteur.repondre(req,
  contexte)`, appliquer l'expiration de 30 minutes ; le site envoie un `conversation_id` par onglet.
  Cette PR fermera #15 et cochera la 2.7.
- **Point ouvert (SAN, relecture de #101)** : après une comparaison Dakar et Thiès, « et pour Kolda ? »
  répond pour Kolda seul (la zone citée remplace). La maquette de la réponse comparative propose
  « Ajouter Kolda à la comparaison » : les deux lectures se défendent ; on garde ce comportement et
  on tranchera avec les tests utilisateurs.
- Le jeu de test ne contient aucun suivi après une période explicite : le cas est couvert par les
  tests unitaires (`engine/tests/test_suivi.py`), à ajouter au jeu de test lors de son extension.
