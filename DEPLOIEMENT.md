# Déployer Gëstukaay

Ce guide installe toute la solution sur une machine, depuis zéro, avec Docker Compose : le site, l'API, la base
de données, et la voix en wolof (comprendre une note vocale, répondre par la voix) sur le GPU.

Durée : environ 30 minutes, dont 20 de téléchargement au premier lancement (images et modèles de voix).

## 1. Machine

| | Minimum |
|---|---|
| Système | Ubuntu 22.04 ou 24.04 (Linux x86_64) |
| CPU | 4 vCPU |
| RAM | 16 Go |
| Disque | 60 Go libres |
| GPU | **NVIDIA, 16 Go de VRAM** (T4, L4, A10, RTX 4080 ou supérieur), pilote 535 ou plus récent |

Le GPU sert à la voix en wolof. Les deux modèles tournent chez vous : aucun enregistrement ne part chez un tiers.

## 2. Logiciels

1. Git.
2. Docker Engine 24 ou plus récent, avec Docker Compose v2 : https://docs.docker.com/engine/install/ubuntu/
3. Le pilote NVIDIA et le NVIDIA Container Toolkit :
   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

   Vérification : cette commande doit afficher votre GPU.

   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
   ```

## 3. Comptes et clés (gratuits)

- **Hugging Face**, pour télécharger le modèle de transcription.
  1. Créer un compte sur https://huggingface.co.
  2. Ouvrir https://huggingface.co/AIHubSN/M-Kiriku-ASR et accepter les conditions d'utilisation (accès immédiat).
  3. Créer un jeton de lecture sur https://huggingface.co/settings/tokens.
- **Google AI Studio**, pour la compréhension des questions : créer une clé Gemini sur
  https://aistudio.google.com/apikey.

  Sans clé Gemini, l'application fonctionne avec ses règles locales. La mesure publiée (98,8 % de bonnes
  réponses) est faite avec Gemini 2.5 Flash.

## 4. Installation

```bash
# 1. Le code
git clone https://github.com/TechwithXalifa/gestukaay.git
cd gestukaay

# 2. La configuration
cp .env.example .env
```

Dans `.env`, remplir ces lignes :

```
HF_TOKEN=<votre jeton Hugging Face>
LLM_PRINCIPAL_CLE=<votre clé Gemini>
LLM_REPLI_CLE=<la même clé Gemini>
GESTUKAAY_SEL=<une chaîne aléatoire, par exemple la sortie de : openssl rand -hex 16>
POSTGRES_PASSWORD=<un mot de passe pour la base>
```

`GESTUKAAY_SEL` sert à pseudonymiser les numéros de téléphone dans le journal : gardé hors de la base, il
empêche de les retrouver à partir d'une copie de la base.

Le reste a déjà ses valeurs : moteur réel (`GESTUKAAY_MOTEUR=reel`), voix sur le GPU (`COMPOSE_PROFILES=voix`).

```bash
# 3. Le socle de données officiel (15 Mo, empreintes vérifiées)
./scripts/recuperer_socle.sh

# 4. Les modèles de voix (environ 15 Go, une seule fois, dans le volume Docker « modeles »)
docker compose run --rm modeles

# 5. Construire et démarrer les 5 services : site, API, base, transcription, synthèse
docker compose up -d --build

# 6. Attendre que tout soit « healthy » (chargement des modèles sur le GPU : 1 à 2 minutes)
docker compose ps

# 7. Créer un compte pour le back-office (le mot de passe est demandé)
docker compose exec api python -m gestukaay_backend.comptes creer evaluateur

# 8. Vérifier le déploiement de bout en bout
./scripts/verifier_deploiement.sh
```

L'étape 8 vérifie l'API, le site, une question écrite (« Combien d'habitants à Thiès en 2023 ? » : 2 463 677)
et la voix. Pour la voix, une réponse en wolof est dite par Oolel, puis retranscrite par M-Kiriku.

## 5. Utilisation

| | Adresse |
|---|---|
| Site | http://localhost:3000 |
| API et sa documentation (OpenAPI) | http://localhost:8000/docs |
| Back-office (journal, tableau de bord, jeu de test) | http://localhost:3000/admin/journal |

Questions à essayer sur le site :
- « Combien coûte le riz à Thiès ? »
- « Ñata nit ñoo dëkk Cees ? »
- « Quelle région a le taux de chômage le plus élevé ? »
- « Combien d'habitants à Touba ? » (réponse approchée : choisir la zone)
- « Combien de personnes parlent sérère ? » (refus : la donnée n'est pas publiée)

Le bouton micro du site pose la question à voix haute, en français ou en wolof.

## 6. Commandes utiles

| Action | Commande |
|---|---|
| Arrêter | `docker compose down` |
| Arrêter et effacer la base | `docker compose down -v` (garde les modèles : volume `modeles`) |
| Redémarrer | `docker compose up -d` |
| Journaux | `docker compose logs -f api` (ou `web`, `transcription`, `synthese`) |
| Reproduire la mesure, sans réseau | `docker compose exec api python mesure/scripts/benchmark.py --regles` |

## 7. Telegram et WhatsApp (facultatif)

Les deux canaux reçoivent les messages par webhook : il faut une adresse publique en HTTPS.

1. Faire pointer un nom de domaine vers la machine, ports 80 et 443 ouverts.
2. Dans `.env` :
   - `DOMAINE=<votre domaine>` et `COMPOSE_PROFILES=voix,https` (le service Caddy obtient le certificat) ;
   - `GESTUKAAY_URL_PUBLIQUE=https://<votre domaine>` ;
   - `NEXT_PUBLIC_API_URL=https://<votre domaine>` ;
   - `GESTUKAAY_PROXY_DE_CONFIANCE=1`.
3. Telegram : créer un bot avec @BotFather, puis mettre `TELEGRAM_BOT_TOKEN` et `TELEGRAM_SECRET_TOKEN`
   (une chaîne de votre choix) dans `.env`. Brancher ensuite le webhook :

   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -d url=https://<votre domaine>/webhooks/telegram -d secret_token=<TELEGRAM_SECRET_TOKEN>
   ```
4. WhatsApp : une application Meta (WhatsApp Cloud API) et ses quatre variables `WHATSAPP_*` dans `.env`. L'URL du
   webhook est `https://<votre domaine>/webhooks/whatsapp`.
5. `docker compose up -d --build` (le site est reconstruit avec la nouvelle adresse).

## 8. Problèmes connus

- **`could not select device driver "nvidia"`** : le NVIDIA Container Toolkit n'est pas installé (section 2).
  Pour démarrer sans la voix : `COMPOSE_PROFILES=` dans `.env`. Une note vocale reçoit alors une réponse écrite.
- **`Accès refusé à AIHubSN/M-Kiriku-ASR`** à l'étape 4 : accepter les conditions du modèle sur Hugging Face, et
  vérifier `HF_TOKEN` (section 3).
- **Les services de voix restent « starting »** plusieurs minutes : premier chargement des modèles sur le GPU, ou
  téléchargement si l'étape 4 n'a pas été faite (`docker compose logs transcription`).
- **Quota de la clé Gemini** : une clé gratuite accepte quelques requêtes par minute seulement. Si une salle
  pose beaucoup de questions en même temps, le moteur passe à Flash-Lite, puis à ses règles locales, sans
  erreur pour l'usager. Pour une démonstration devant beaucoup de monde, une clé avec facturation activée évite
  cette baisse.
- **Le LLM ne répond pas toujours exactement pareil** : une même question peut recevoir la valeur, ou une réponse
  approchée à confirmer. Aucun chiffre faux ne passe : chaque valeur affichée est contrôlée dans le socle.
- **Interface en wolof** : les parcours principaux sont traduits ; les autres pages
  restent en français.
