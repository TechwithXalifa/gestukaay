/**
 * Textes de l'interface en français : la référence. Toute nouvelle phrase
 * visible s'ajoute ici, puis se traduit dans wo.ts. Les variables s'écrivent
 * {nom} et sont remplacées par t("cle", { nom }).
 * Ton (7.4) : clair, chaleureux, sobre ; vouvoiement ; 20 mots au plus.
 */
export const fr = {
  // En-tête et pied
  "nav.poser": "Poser une question",
  "nav.evitement": "Aller au contenu",
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
  "reponse.projection": "Projection",
  "reponse.estimation": "Estimation",
  "reponse.base": "Ce n'est pas une valeur observée. Base : {base}.",
  "reponse.sansEstimation": "Gëstukaay ne remplace jamais un chiffre manquant par une estimation. Aucune valeur n'est affichée avant votre choix.",
  "reponse.horsligne": "Hors ligne · réponse enregistrée sur cet appareil.",

  // Graphique (EF-26 à EF-28)
  "graphique.voirTableau": "Voir les {n} valeurs en tableau",
  "graphique.voirGraphique": "Voir le graphique",
  "graphique.serie": "Série",
  "graphique.libelle": "Libellé",
  "graphique.valeur": "Valeur ({unite})",

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

  // Où je me situe (EF-37 à EF-40, décision 0004 §2)
  "nav.situer": "Où je me situe",
  "situer.eyebrow": "Où je me situe",
  "situer.titre": "Comparez votre ménage aux moyennes officielles",
  "situer.intro": "Trois questions, une par écran. Vous verrez comment les dépenses de votre ménage se comparent à celles publiées pour votre région et pour le pays.",
  "situer.garantie": "Rien n'est enregistré : vos réponses servent au calcul, puis disparaissent.",
  "situer.commencer": "Commencer",
  "situer.etape": "Étape {n} sur {total}",
  "situer.retour": "Question précédente",
  "situer.progression": "Progression du questionnaire",
  "situer.continuer": "Continuer",
  "situer.voir": "Voir mon résultat",
  "situer.q.region": "Dans quelle région vit votre ménage ?",
  "situer.q.taille": "Combien de personnes vivent dans votre ménage ?",
  "situer.q.tailleAide": "Toutes les personnes qui partagent les repas, vous compris.",
  "situer.moins": "Une personne de moins",
  "situer.plus": "Une personne de plus",
  "situer.personnes": "personnes",
  "situer.q.depenses": "Combien votre ménage dépense-t-il par mois, à peu près ?",
  "situer.q.depensesAide": "Nourriture, loyer, transport, factures, école… pour tout le ménage.",
  "situer.d.moins_50k": "Moins de 50 000 FCFA",
  "situer.d.50k_100k": "De 50 000 à 100 000 FCFA",
  "situer.d.100k_200k": "De 100 000 à 200 000 FCFA",
  "situer.d.200k_350k": "De 200 000 à 350 000 FCFA",
  "situer.d.350k_500k": "De 350 000 à 500 000 FCFA",
  "situer.d.plus_500k": "Plus de 500 000 FCFA",
  "situer.resultat": "Votre résultat",
  "situer.estimation": "Votre estimation, d'après vos réponses",
  "situer.comparaison": "Comparée aux moyennes publiées",
  "situer.pos.en_dessous": "Votre ménage dépense moins",
  "situer.pos.autour": "Votre ménage est dans la moyenne",
  "situer.pos.au_dessus": "Votre ménage dépense plus",
  "situer.contexte": "Repères pour votre région",
  "situer.moyenne": "C'est quoi une moyenne ?",
  "situer.moyenneTexte": "On additionne ce que consomment tous les ménages, puis on divise par le nombre de personnes. Quelques ménages très aisés suffisent à tirer la moyenne vers le haut : beaucoup de ménages sont donc en dessous.",
  "situer.recommencer": "Recommencer",
  "accueil.situer": "Où je me situe : comparez votre ménage aux moyennes officielles",
  "situer.question": "Poser une question",

  // Domaines (décision 0005)
  "domaines.accueil": "Parcourir par domaine",
  "domaines.tous": "Tous les domaines",
  "domaines.eyebrow": "Domaines",
  "domaines.titre": "{n} domaines de données officielles",
  "domaines.intro": "Posez votre question sur l'un de ces sujets, en français ou en wolof. Le catalogue détaillé des indicateurs arrive bientôt.",

  // Interface wolof incomplète
  "wo.enCours": "L'interface en wolof est en cours de validation par un linguiste : les textes pas encore validés restent en français.",
} as const;

export type Cle = keyof typeof fr;
