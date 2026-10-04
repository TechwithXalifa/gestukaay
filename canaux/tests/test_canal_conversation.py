"""Ce qu'on fait d'un message reçu, avec des services et un envoyeur simulés (décision 0025)."""

from pathlib import Path

import pytest
from gestukaay_backend.canaux import Entrant, Services
from gestukaay_canaux.conversation import Contenu, traiter
from gestukaay_canaux.textes import texte
from gestukaay_contracts.models import AskResponse, TranscriptionResponse
from gestukaay_engine import NonDisponible

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

    def textes(self):
        return [x for k, x in self.envois if k == "texte"]


def services(derniere=None, transcrire=None, demander=None):
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

    s = Services("whatsapp:221700000001", demander_, confirmer, lambda: derniere, transcrire_)
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
                                          ("ok", "aide")])
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
    assert appels == [("demander", tr.transcription, {"source": "voix", "transcription_brute": tr.transcription})]


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
