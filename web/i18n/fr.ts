/**
 * Textes de l'interface en français : la référence. Toute nouvelle phrase
 * visible s'ajoute ici, puis se traduit dans wo.ts. Les variables s'écrivent
 * {nom} et sont remplacées par t("cle", { nom }).
 * Ton (7.4) : clair, chaleureux, sobre ; vouvoiement ; 20 mots au plus.
 */
export const fr = {
  // En-tête et pied
  "nav.poser": "Poser une question",
  "nav.principale": "Navigation principale",
  "langue.groupe": "Langue de l'interface",
  "pied.adresse": "{adresse} · adresse stable et partageable",
  "pied.methode": "Méthode et transparence",
  "pied.apropos": "À propos",
  "pied.confidentialite": "Confidentialité",
  "pied.nav": "Pied de page",

  // Accueil
  "accueil.eyebrow": "Données officielles du Sénégal",
  "accueil.titre1": "Posez votre question.",
  "accueil.titre2": "Recevez le chiffre officiel.",
  "accueil.chapeau": "En français ou en wolof. Parlez ou écrivez.",

  // Champ de question
  "champ.libelle": "Votre question",
  "champ.exemple": "Combien d'habitants à Thiès ?",
  "champ.horsligne": "Question indisponible hors ligne",
  "champ.micro": "Poser la question à voix haute",
  "champ.envoyer": "Envoyer la question",

  // Réponse
  "reponse.exacte": "Correspondance exacte",
  "reponse.approchee": "Correspondance approchée",
  "reponse.derniere": "dernière donnée publiée",
  "reponse.source": "Source officielle",
  "reponse.perimetre": "Périmètre : {note}",
  "reponse.publication": "Voir la publication",
  "reponse.graphique": "Graphique : {titre}",
  "reponse.sansEstimation": "Gëstukaay ne remplace jamais un chiffre manquant par une estimation. Aucune valeur n'est affichée avant votre choix.",
  "reponse.horsligne": "Hors ligne · réponse enregistrée sur cet appareil.",

  // Actions
  "actions.pdf": "Exporter PDF",
  "actions.csv": "Exporter CSV",
  "actions.citer": "Copier la citation",
  "actions.partager": "Partager",
  "actions.citationCopiee": "Citation copiée",
  "actions.lienCopie": "Lien copié",
  "actions.copieImpossible": "Copie impossible : sélectionnez le texte à la main.",

  // Retours
  "retour.question": "Cette réponse vous a-t-elle été utile ?",
  "retour.oui": "Oui",
  "retour.non": "Non",
  "retour.signaler": "Signaler une erreur",
  "retour.merci": "Merci, votre retour a été transmis à l'équipe.",
  "retour.echec": "L'envoi a échoué, réessayez.",
  "retour.quoi": "Qu'est-ce qui ne va pas ?",
  "retour.chiffre_faux": "Le chiffre me semble faux",
  "retour.mauvaise_zone": "Ce n'est pas la bonne zone",
  "retour.mauvaise_comprehension": "Ma question a été mal comprise",
  "retour.autre": "Autre chose",
  "retour.preciser": "Précisez (facultatif)",
  "retour.envoyer": "Envoyer le signalement",
  "retour.annuler": "Annuler",

  // États (7.3)
  "etat.recue": "Question reçue",
  "etat.recherche": "Recherche du chiffre officiel…",
  "etat.introuvable": "Cette réponse n'existe plus.",
  "etat.introuvableAide": "Posez à nouveau votre question : la réponse sera recalculée sur les données officielles.",
  "etat.service": "Le service ne répond pas pour le moment.",
  "etat.serviceAide": "Votre question est conservée. Réessayez dans un instant.",
  "etat.reessayer": "Réessayer",
  "etat.incident": "Code d'incident : {code} · à indiquer si vous nous contactez",
  "horsligne.titre": "Vous êtes hors ligne.",
  "horsligne.texte": "Vos dernières réponses restent lisibles. Les nouvelles questions demandent une connexion.",
  "horsligne.aide": "Vérifiez votre connexion, puis réessayez.",
  "horsligne.recentes": "Consultées récemment · disponibles sans connexion",
  "horsligne.aHeure": "consultée à {heure}",
  "horsligne.hier": "consultée hier",
  "horsligne.le": "consultée le {date}",
  "micro.titre": "Le micro est bloqué pour {site}",
  "micro.intro": "Pour parler à Gëstukaay, autorisez le micro en deux étapes :",
  "micro.etape1": "Touchez le cadenas à gauche de l'adresse, en haut de l'écran.",
  "micro.etape2": "Ouvrez Autorisations, puis réglez Micro sur « Autoriser ».",
  "micro.reessayer": "J'ai autorisé, réessayer",
  "micro.texte": "Vous pouvez aussi écrire votre question dans le champ ci-dessus. Gëstukaay n'écoute que lorsque vous appuyez sur le micro.",

  // Écoute (7.3, décision 0004 §1)
  "ecoute.titre": "Je vous écoute…",
  "ecoute.arret": "arrêt automatique après 2 s de silence",
  "ecoute.annuler": "Annuler",
  "ecoute.terminer": "Terminer",
  "ecoute.transcription": "Transcription en cours…",
  "ecoute.verifier": "Vérifiez votre question",
  "ecoute.corriger": "Corrigez le texte si besoin, puis envoyez.",
  "ecoute.reenregistrer": "Réenregistrer",
  "ecoute.envoyer": "Envoyer",
  "ecoute.vide": "Je n'ai pas bien compris.",
  "ecoute.videAide": "Parlez près du téléphone, par exemple : « Combien d'habitants à Thiès ? »",
  "ecoute.format": "Votre navigateur ne sait pas enregistrer la voix.",
  "ecoute.ecrire": "Vous pouvez écrire votre question à la place.",
  "ecoute.ecrireBouton": "Écrire ma question",
  "ecoute.confidentialite": "L'audio sert seulement à la transcription, puis il est effacé.",

  // Interface wolof incomplète
  "wo.enCours": "L'interface en wolof est en cours de validation par un linguiste : les textes pas encore validés restent en français.",
} as const;

export type Cle = keyof typeof fr;
