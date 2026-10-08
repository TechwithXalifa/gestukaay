# 0037 — Connexion au back-office : comptes nominatifs, identifiant et mot de passe

**Date** : 2026-10-08 · **Statut** : accepté (SAN) · **Remplace** : le jeton `GESTUKAAY_ADMIN_JETON`

## Contexte

Le back-office (journal, tableau de bord, jeu de test) s'ouvrait avec un seul jeton partagé,
`GESTUKAAY_ADMIN_JETON`, défini dans `.env`, collé dans un champ puis gardé dans `sessionStorage` (lisible
par tout script de la page) et envoyé en `Authorization: Bearer`. Rien ne disait qui s'était connecté, et
retirer l'accès d'une personne obligeait à changer le jeton de tout le monde.

## Décision

- **Un compte par personne** (SAN, KBD), avec un identifiant et un mot de passe de 12 caractères au moins.
  Les comptes se créent **en ligne de commande seulement**, sans inscription ni page d'administration des
  comptes : `python -m gestukaay_backend.comptes creer|changer|desactiver|lister`.
- Mots de passe hachés par **scrypt** (bibliothèque standard), avec un sel par compte.
- `POST /admin/connexion` ouvre une **session côté serveur** portée par le cookie `gestukaay_admin`
  (`HttpOnly`, `SameSite=Strict`, `Path=/admin`, `Secure` si `GESTUKAAY_URL_PUBLIQUE` est en https).
  La base ne garde que le hachage du jeton. La session expire après 8 h sans activité, et 12 h au plus.
  `POST /admin/deconnexion` la ferme et `GET /admin/moi` renvoie l'identifiant connecté.
- **Une seule réponse en cas de refus** (identifiant inconnu, mot de passe faux, compte désactivé ou
  bloqué), avec le même temps de calcul. Le compte est bloqué 15 min après 5 essais manqués, en plus de
  la limite de 20 requêtes par minute et par adresse.
- **Protection CSRF** : un `POST /admin/*` dont l'en-tête `Origin` n'est pas le site est refusé (403).
- Sans compte actif, le back-office n'existe pas (404), comme avant sans jeton.

## Conséquences

- `GESTUKAAY_ADMIN_JETON` disparaît. Après déploiement, chacun crée son compte sur la machine de l'API :
  `docker compose exec api python -m gestukaay_backend.comptes creer SAN`.
- CORS autorise les cookies (`allow_credentials`). Le cookie n'est envoyé que si le site et l'API sont
  sur le même site (même domaine racine, ports ignorés) : c'est le cas en local (`localhost:3000` →
  `localhost:8000`). En préproduction, si l'API est sur un autre domaine, il faudra faire passer `/admin/*`
  par le serveur web (réécriture Next.js) pour que le cookie reste celui du site.
- Les autres jetons `Bearer` (services de transcription et de synthèse, clés du LLM, webhooks) relient des
  machines entre elles : ils ne changent pas.
