# 0027 — Notes vocales dans la conversation

**Date** : 2026-10-05 · **Statut** : accepté (KBD) · **Issues** : #28 · **Exigences** : EF-11, EF-15, US-07, US-09 ; décision 0026

## Contexte

M-Kiriku est choisi (0026). Il restait à brancher la transcription : où elle tourne, que faire si
elle ne répond pas, et comment se passe la conversation quand Awa envoie une note vocale.

## Décisions

1. **Service à part** (`transcription/serveur.py`, format des API compatibles OpenAI), appelé par le
   moteur à `TRANSCRIPTION_URL` avec `TRANSCRIPTION_CLE`. Il décode tout format (OGG de WhatsApp,
   WebM du site) en mémoire, sans rien garder ; ses dépendances (torch…) ne sont pas dans l'image de
   l'API. Machines : carte graphique louée si le budget le permet, sinon le Mac de KBD, sinon le PC
   d'Aziz. Sans `TRANSCRIPTION_CLE`, il n'écoute que sur la machine elle-même (127.0.0.1).
2. **5 s d'attente de la transcription** (plus 1 s pour se connecter et 1 s pour envoyer la note),
   puis **repli sur ADIA** (`ADIA_API_KEY`) ; si rien ne répond, `NonDisponible` : le canal invite à
   écrire la question. Une note de plus de 2 Mo n'est pas téléchargée (« reformuler »).
3. **Nombres dits en lettres -> chiffres** après la transcription (« deux mille vingt-quatre » ->
   2024, « treize virgule deux » -> 13,2), en français et en wolof (mots et règles de KBD : « ak »
   additionne, « fukk » après des unités multiplie, suffixe « -i » devant téeméer, junni, milyoŋ,
   fanweer = 30, wirgil ; « ñaari junni ak ñaar-fukk ak ñeent » -> 2024). Un mot seul qui a un autre
   sens n'est jamais converti : « un », « benn » (article), « dara » (rien), « fanweer » (mois) ;
   « pour cent » et « ci téeméer » restent tels quels. Deux nombres reliés par « et » ou « ak »
   restent deux nombres (« entre deux mille onze et deux mille vingt-deux » -> « entre 2011 et 2022 ») :
   « et » ne lie que devant un, une, onze ; « ak » coupe quand un nouveau junni ou milyoŋ commence.
   **Langue** : si l'appelant ne l'impose pas (le site envoie « auto »), elle est déduite du texte
   transcrit (`langue.detecter`, choix KBD) : un mot interrogatif wolof (ñaata, ndax, ban…) suffit,
   sinon on compte les petits mots de chaque langue. Une question faite seulement de mots français
   (« Taux chomage en 2030 ») part en français. Premier pas de #24.
4. **Pas de « J'ai compris : … » écrit** pour une note vocale. **Écart au cahier (EF-15)**, décidé
   par KBD : une personne qui ne lit pas ne peut pas vérifier un texte. La réponse dit elle-même ce
   qu'elle a compris (« La région de Thiès compte… ») ; avec l'audio de réponse (#29), elle sera
   entendue, et un « J'ai compris » parlé pourra s'y ajouter.
5. **Correction (US-09)** : « non », « déet », « laaju loolu deh », « waxuma loolu deh » (wolof de
   KBD) -> « Xéyna dégguma la bu baax. Mën nga baamtuwaat laaj bi wala nga bind ko. » (et le
   français) ; toute nouvelle question est traitée normalement. Une transcription vide reçoit le
   même message.

## Conséquences

- Le site (`/v1/transcrire`) et WhatsApp passent par le même `MoteurReel.transcrire`.
- Page Confidentialité : en repli, la voix part chez ADIA (Concree).
- Les nombres wolof de KBD serviront aussi, dans l'autre sens, à l'audio de réponse (#29).
