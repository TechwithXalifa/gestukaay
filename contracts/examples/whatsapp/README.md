# Payloads d'exemple des webhooks (à valider avec KBD)

Au format réel de Meta (WhatsApp Cloud API) et de Telegram (Bot API), avec des numéros et identifiants
fictifs. Ils servent à tester les routes `/webhooks/whatsapp` et `/webhooks/telegram` et le module de
canal sans appeler Meta ni Telegram.

| Fichier | Ce qu'il contient | Ce qui doit se passer |
|---|---|---|
| `whatsapp/texte.json` | une question écrite | une réponse texte (EF-20) |
| `whatsapp/audio.json` | une note vocale (média à télécharger) | « J'ai compris : … » puis texte et audio (US-07) |
| `whatsapp/reponse_choix.json` | un choix dans une liste, après une réponse approchée | la valeur du choix confirmé (US-13) |
| `whatsapp/statut.json` | un accusé de lecture | rien : aucun message à traiter |
| `../telegram/texte.json` | une question écrite (bot de secours) | une réponse texte (EF-24) |
| `../telegram/voix.json` | une note vocale | comme WhatsApp |

Le numéro (`from`, `wa_id`) et le `chat.id` de Telegram ne sont jamais journalisés : ils deviennent
`conversation_id`, haché par le backend.
