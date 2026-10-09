"""Ce qu'on fait d'un message reçu, avec des services et un envoyeur simulés (décision 0025)."""

from pathlib import Path

import pytest
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_canaux.conversation import Contenu, traiter
from gestukaay_canaux.media import NoteTropGrosse
from gestukaay_canaux.textes import texte
from gestukaay_contracts.models import AskResponse, TranscriptionResponse
from gestukaay_engine import NonDisponible, NoteVocale

EXEMPLES = Path(__file__).parents[2] / "contracts" / "examples"


def rep(nom: str) -> AskResponse:
    return AskResponse.model_validate_json((EXEMPLES / f"{nom}.json").read_text(encoding="utf-8"))


class Envoyeur:
    gras = True

    def __init__(self):
        self.envois: list[tuple[str, object]] = []

    def accuser(self, destinataire, contenu):
        self.envois.append(("accuse", contenu.accuse))

    def texte(self, destinataire, message):
        self.envois.append(("texte", message))

    def choix(self, destinataire, choix):
        self.envois.append(("choix", [c.id for c in choix]))

    def media(self, contenu):
        return b"OggS..."

    def preparer_vocal(self, destinataire):
        self.envois.append(("preparer_vocal", destinataire))

    def vocal(self, destinataire, opus):
        self.envois.append(("vocal", opus))

    def textes(self):
        return [x for k, x in self.envois if k == "texte"]


def services(derniere=None, transcrire=None, demander=None, parler=None):
    appels = []

    def demander_(question, **kw):
        appels.append(("demander", question, kw))
        if demander:
            return demander(question)
        return rep("approchee") if "ville" in question else rep("exacte_valeur")

    def confirmer(rid, choix_id):
        appels.append(("confirmer", rid, choix_id))
        return rep("exacte_valeur")

    def transcrire_(audio, fmt):
        if transcrire is None:
            raise NonDisponible("pas encore")
        return transcrire

    s = Services("whatsapp:221700000001", demander_, confirmer, lambda: derniere, transcrire_,
                 parler or (lambda r: NoteVocale(b"OggS-note", 4.0, "oolel")))
    return s, appels


def entrant(**kw):
    return Entrant("wamid.X", "221700000001", Contenu(accuse="wamid.X", **kw))


def test_premier_message_accueil_puis_reponse():
    e, (s, appels) = Envoyeur(), services(derniere=None)
    traiter(entrant(type="texte", texte="Combien d'habitants à Thiès ?"), s, e)
    assert e.envois[0] == ("accuse", "wamid.X")
    assert e.textes()[0] == texte("accueil") and "2 463 677" in e.textes()[1]
    assert appels == [("demander", "Combien d'habitants à Thiès ?", {})]


def test_conversation_en_cours_pas_d_accueil():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="texte", texte="Combien d'habitants à Thiès ?"), s, e)
    assert texte("accueil") not in e.textes()


@pytest.mark.parametrize("message, cle", [("ndimbal", "aide"), ("stop", "stop"), ("Làkk", "langue"),
                                          ("ok", "aide"), ("déet", "reformuler"), ("Non", "reformuler"),
                                          ("waxuma loolu deh", "reformuler"), ("laaju loolu deh", "reformuler")])
def test_commandes_et_message_trop_court(message, cle):
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="texte", texte=message), s, e)
    assert e.textes() == [texte(cle)] and appels == []


def test_approchee_puis_benn_confirme_le_choix_1():
    approchee = rep("approchee")
    e, (s, appels) = Envoyeur(), services(derniere=approchee)
    traiter(entrant(type="texte", texte="Benn"), s, e)
    assert appels == [("confirmer", approchee.reponse.id, "1")]
    e2, (s2, appels2) = Envoyeur(), services(derniere=approchee)
    traiter(entrant(type="choix", choix_id="2"), s2, e2)  # toucher dans la liste
    assert appels2 == [("confirmer", approchee.reponse.id, "2")]


def test_choix_sans_approchee_en_attente():
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="texte", texte="2"), s, e)
    assert e.textes() == [texte("choix_invalide")] and appels == []


def test_approchee_envoie_le_texte_puis_la_liste():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="texte", texte="Population de la ville de Thiès"), s, e)
    assert e.envois[-1] == ("choix", [c.id for c in rep("approchee").reponse.choix])


def test_vocal_avant_la_transcription():
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert e.textes() == [texte("vocal_pas_encore")] and appels == []


def test_vocal_transcrit_puis_repondu():
    tr = TranscriptionResponse(transcription="Ñaata nit ñoo dëkk Tiés ?", langue="wo", duree_s=3.0)
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=tr)
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert appels == [("demander", tr.transcription, {"source": "voix", "transcription_brute": tr.transcription,
                                                       "audio_retour": True})]
    # EF-15, US-07 : la transcription comprise part d'abord, pour pouvoir répondre « non » (audit du 09/10)
    assert e.textes()[0] == f"{texte('compris')} « Ñaata nit ñoo dëkk Tiés ? »"


def test_vocal_trop_gros_invite_a_reformuler():
    class Gros(Envoyeur):
        def media(self, contenu):
            raise NoteTropGrosse
    e, (s, appels) = Gros(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert e.textes() == [texte("reformuler")] and appels == []


def test_erreur_le_dit_a_l_utilisateur_puis_remonte():
    def panne(question):
        raise RuntimeError("panne")
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), demander=panne)
    with pytest.raises(RuntimeError):
        traiter(entrant(type="texte", texte="Combien d'habitants à Thiès ?"), s, e)
    assert e.textes()[-1] == texte("erreur")


def test_image_ou_autre_aide():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="autre"), s, e)
    assert e.textes() == [texte("aide")]


@pytest.mark.parametrize("message", ["/start", "Salam Naka leu"])
def test_salutation_seule_l_accueil_sans_question(message):
    # Essai Telegram du 07/10 : « /start » partait au moteur (« Cette donnée n'existe pas… »)
    for derniere in (None, rep("exacte_valeur")):
        e, (s, appels) = Envoyeur(), services(derniere=derniere)
        traiter(entrant(type="texte", texte=message), s, e)
        assert e.textes() == [texte("accueil")] and appels == []


def test_salutation_puis_question_part_au_moteur():
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"))
    traiter(entrant(type="texte", texte="Salam, ñaata nit ñoo dëkk Tiés ?"), s, e)
    assert appels and appels[0][1] == "Salam, ñaata nit ñoo dëkk Tiés ?"


# --- Voix de réponse (EF-20, décision 0029) ------------------------------------


def avec_question(question: str, transcription: str | None = None, langue: str = "wo") -> AskResponse:
    r = rep("exacte_valeur")
    return r.model_copy(update={"reponse": r.reponse.model_copy(
        update={"question": question, "transcription": transcription, "langue": langue})})


def test_question_vocale_la_voix_puis_une_fiche():
    # choix de KBD (07/10) : plus d'empilement texte + voix ; la voix, puis une ligne (chiffre exact, source)
    tr = TranscriptionResponse(transcription="Ñaata nit ñoo dëkk Tiés ?", langue="wo", duree_s=3.0)
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=tr,
                                      demander=lambda q: avec_question(q, transcription=q))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert [k for k, _ in e.envois] == ["accuse", "texte", "preparer_vocal", "vocal", "texte"]  # « J'ai compris »
    assert e.envois[3] == ("vocal", b"OggS-note")
    ligne, lien, mention = e.textes()[-1].split("\n")  # revue de SAN : se suffit si on la transfère
    assert "2\u202f463\u202f677" in ligne and "Source" in ligne and " · " in ligne
    assert lien.startswith("http") and mention == "— gestukaay"


def test_question_vocale_en_francais_le_texte_complet_en_francais():
    # KBD, 08/10 : une question dite en français recevait une note en wolof (seule voix du projet)
    tr = TranscriptionResponse(transcription="Combien d'habitants à Thiès ?", langue="fr", duree_s=3.0)
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=tr,
                                      demander=lambda q: avec_question(q, transcription=q, langue="fr"))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert [k for k, _ in e.envois] == ["accuse", "texte", "texte"]  # « J'ai compris », puis le texte ; ni note wolof
    assert "2\u202f463\u202f677" in e.textes()[-1]


def test_question_ecrite_en_wolof_texte_seul():
    # choix de KBD (07/10) : question écrite -> texte seul, même en wolof (la réponse écrite est en wolof)
    e, (s, appels) = Envoyeur(), services(derniere=rep("exacte_valeur"), demander=lambda q: avec_question(q))
    traiter(entrant(type="texte", texte="Ñaata nit ñoo dëkk Tiés ?"), s, e)
    assert "vocal" not in [k for k, _ in e.envois] and appels[0][2] == {}


def test_question_ecrite_en_francais_texte_seul():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), demander=lambda q: avec_question(q))
    traiter(entrant(type="texte", texte="Combien d'habitants à Thiès ?"), s, e)
    assert "vocal" not in [k for k, _ in e.envois]


def _vocale():
    return TranscriptionResponse(transcription="Ñaata nit ñoo dëkk Tiés ?", langue="wo", duree_s=3.0)


def test_panne_de_la_voix_le_texte_complet_part():
    def panne(r):
        raise RuntimeError("Oolel tombé")
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=_vocale(), parler=panne,
                                      demander=lambda q: avec_question(q, transcription=q))
    traiter(entrant(type="audio", media="300000000000001"), s, e)  # ne remonte pas
    assert "vocal" not in [k for k, _ in e.envois]
    assert "2\u202f463\u202f677" in e.textes()[-1] and "gestukaay" in e.textes()[-1]  # le texte complet
    assert texte("erreur") not in e.textes()


def test_pas_de_voix_le_texte_complet_part():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=_vocale(), parler=lambda r: None,
                                      demander=lambda q: avec_question(q, transcription=q))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert "vocal" not in [k for k, _ in e.envois] and "Source" in e.textes()[-1]


def test_approchee_vocale_la_voix_puis_les_choix():
    e, (s, _) = Envoyeur(), services(derniere=rep("exacte_valeur"), transcrire=_vocale(),
                                      demander=lambda q: rep("approchee").model_copy(update={"reponse": rep(
                                          "approchee").reponse.model_copy(update={"transcription": q, "langue": "wo"})}))
    traiter(entrant(type="audio", media="300000000000001"), s, e)
    assert [k for k, _ in e.envois] == ["accuse", "texte", "preparer_vocal", "vocal", "choix"]  # « J'ai compris »


def test_envoi_de_la_note_en_panne_le_texte_complet_part():
    # revue de SAN sur #146 : l'envoi de la note (dépôt chez Meta, sendVoice) peut échouer aussi
    class EnvoyeurSansVoix(Envoyeur):
        def vocal(self, destinataire, opus):
            raise RuntimeError("dépôt du média refusé")

    e, (s, _) = EnvoyeurSansVoix(), services(derniere=rep("exacte_valeur"), transcrire=_vocale(),
                                             demander=lambda q: avec_question(q, transcription=q))
    traiter(entrant(type="audio", media="300000000000001"), s, e)  # ne remonte pas
    assert texte("erreur") not in e.textes()
    assert "2\u202f463\u202f677" in e.textes()[-1] and "— gestukaay" in e.textes()[-1]  # le texte complet



def test_accuse_en_panne_la_reponse_part_quand_meme(caplog):
    # essais du 09/10 : « lu » refusé par Meta (400), « en train d'écrire » injoignable (Telegram) -> aucune réponse
    class SansAccuse(Envoyeur):
        def accuser(self, destinataire, contenu):
            raise RuntimeError("Telegram sendChatAction : ConnectTimeout")

    e, (s, _) = SansAccuse(), services(derniere=rep("exacte_valeur"))
    with caplog.at_level("WARNING"):
        traiter(entrant(type="texte", texte="Combien d'habitants à Thiès ?"), s, e)  # ne remonte pas
    assert texte("erreur") not in e.textes() and "2\u202f463\u202f677" in e.textes()[-1]
    assert "accusé non envoyé" in caplog.text and "221700000001" not in caplog.text
