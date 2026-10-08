"""Compréhension (#10). LLM simulé (httpx.MockTransport) : aucun appel réseau."""

import json

import httpx
from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_engine.candidats import index, periodes_citees, zones_citees
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.llm import ClientLLM, Maillon

MAILLON = Maillon(nom="principal", fournisseur="openai_compatible", modele="x/modele", cle="k")


def client(sortie: dict | None = None, statut: int = 200, messages: list | None = None) -> ClientLLM:
    """LLM simulé qui renvoie `sortie` ; garde les messages reçus dans `messages`."""
    def gerer(request: httpx.Request):
        if messages is not None:
            messages.append(json.loads(request.content)["messages"])
        if statut != 200:
            return httpx.Response(statut, json={"error": {"message": "panne"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(sortie)},
                                                      "finish_reason": "stop"}], "usage": {}})
    return ClientLLM([MAILLON], transport=httpx.MockTransport(gerer))


def sortie(**kw) -> dict:
    return {"intention": "valeur", "candidat": 1, "periode_type": "derniere", "periode_valeur": None,
            "sexe": None, "milieu": None, "age": None, "cycle": None, "produit": None, "confiance": 0.9} | kw


# --- sans LLM ---------------------------------------------------------------

def test_zones_citees():
    assert zones_citees("Combien d'habitants à Thiès ?") == ["SN-TH"]
    assert zones_citees("Ñata nit ñoo dëkk Cees ?") == ["SN-TH"]
    assert zones_citees("Limu askanu Ndakaaru ak Kaolack") == ["SN-DK", "SN-KL"]
    assert zones_citees("Taux brut : académies de Kolda et de Ziguinchor") == ["SN-IA-KOLDA", "SN-IA-ZIGUINCHOR"]
    assert zones_citees("dans l'académie de Kolda") == ["SN-IA-KOLDA"]
    assert zones_citees("Mortalité à Kolda comparée à la moyenne nationale") == ["SN-KD", "SN"]
    assert zones_citees("Quel temps fera-t-il ?") == []


def test_periodes_citees():
    assert periodes_citees("entre mars 2025 et mars 2026") == ["2025-03", "2026-03"]
    assert periodes_citees("Chômage en 2024") == ["2024"]
    assert periodes_citees("au T2 2024") == ["2024-T2"]
    assert periodes_citees("Combien d'habitants ?") == []


def test_candidats_trouves_sans_llm():
    def premiers(q, n=3):
        return [c.indicateur.code for c in index().chercher(q)[:n]]
    assert "pvswjnd" in premiers("Combien d'habitants à Thiès ?")
    assert "dwibrlf" in premiers("Ñi amul ligéey ci Senegaal ?")
    assert "feujxob.riz-brise-ordinaire-au-detail" in premiers("Ñata la kilo thieb bou dagg détail di diar ?")
    # niveau cité : l'indicateur publié par académie passe devant le national
    tbs = index().chercher("taux brut de scolarisation", niveaux={"academie"})
    assert tbs[0].indicateur.code == "ervtjfc.taux-brut-de-scolarisation"


def test_milieu_departage_sans_chercher():
    """#116 : le national sans milieu cité, le rural s'il l'est ; « rurale » seul ne fait pas
    remonter l'électrification rurale pour « population rurale »."""
    def tete(q):
        return index().chercher(q)[0].indicateur.code
    assert tete("Quel est le taux d'électrification au Sénégal ?") == "vlaobkb"
    assert tete("Quel est le taux d'électrification rurale ?") == "vcvtdsf"
    assert "vcvtdsf" not in [c.indicateur.code for c in index().chercher("Population rurale")]


# --- avec LLM simulé ----------------------------------------------------------

def test_le_llm_choisit_un_numero_jamais_un_code():
    recus = []
    c = Comprehension(client(sortie(candidat=1), messages=recus)).comprendre("Combien d'habitants à Thiès ?")
    assert c.source == "llm"
    assert c.requete.indicateur == c.candidats[0].indicateur.code
    assert c.requete.zones == ["SN-TH"] and c.requete.periode == Periode(type="derniere")
    message = recus[0][1]["content"]
    assert "1. " in message and "Zones repérées : SN-TH" in message


def test_numero_hors_liste_donne_hors_perimetre():
    r = Comprehension(client(sortie(candidat=99))).comprendre("Combien d'habitants à Thiès ?").requete
    assert r.intention == "hors_perimetre" and r.indicateur is None


def test_aucun_candidat_donne_hors_perimetre():
    r = Comprehension(client(sortie(candidat=None))).comprendre("Quel temps fera-t-il demain à Dakar ?").requete
    assert r.intention == "hors_perimetre"


def test_periode_du_texte_prime_et_desagregation_canonique():
    s = sortie(periode_type="annee", periode_valeur="2019", sexe="femmes", age="15-24")
    r = Comprehension(client(s)).comprendre("Taux de chômage des jeunes femmes en 2025").requete
    assert r.periode == Periode(type="annee", valeur="2025")
    assert r.desagregation == {"sexe": "femmes", "age": "15-24"}


def test_periode_mal_formee_ignoree():
    r = Comprehension(client(sortie(periode_type="annee", periode_valeur="l'an dernier"))).comprendre(
        "Taux de chômage").requete
    assert r.periode == Periode(type="derniere")


def test_panne_du_llm_bascule_sur_les_regles():
    c = Comprehension(client(statut=500)).comprendre("Combien d'habitants à Thiès ?")
    assert c.source == "regles" and c.appel.tentatives[0].statut == "http"
    assert c.requete.indicateur == "pvswjnd" and c.requete.zones == ["SN-TH"]


def test_suivi_reprend_l_indicateur_et_les_zones():
    avant = RequeteStructuree(intention="valeur", indicateur="pvswjnd", zones=["SN-TH"], confiance=0.9)
    c = Comprehension(None).comprendre("Et pour Kaolack ?", [avant])
    assert c.requete.indicateur == "pvswjnd" and c.requete.zones == ["SN-KL"]
    # proposé au LLM en premier
    c = Comprehension(client(sortie(candidat=1))).comprendre("Kaolack nak ?", [avant])
    assert c.candidats[0].indicateur.code == "pvswjnd" and c.requete.indicateur == "pvswjnd"


def test_regles_sans_reseau():
    comp = Comprehension(None)
    assert comp.comprendre("Quelle est la région la plus peuplée ?").requete.intention == "classement"
    r = comp.comprendre("Population de Dakar et de Thiès en 2023").requete
    assert r.intention == "comparaison" and r.zones == ["SN-DK", "SN-TH"]


def test_ponctuation_collee_au_nom_de_lieu():
    """« Thiès? » (messagerie, transcription) : la zone est reconnue. Avant, le moteur répondait pour
    le Sénégal entier, comme si aucune zone n'avait été citée."""
    assert zones_citees("Combien d'habitants à Thiès?") == ["SN-TH"]
    assert zones_citees("Population de Kaolack!") == ["SN-KL"]
    assert zones_citees("Chômage à Dakar et Thiès?") == ["SN-DK", "SN-TH"]
    assert zones_citees('Ziguinchor; "Matam": Louga?') == ["SN-ZG", "SN-MT", "SN-LG"]


def test_candidat_sans_unite_signale_au_llm():
    # #132 : à sujet égal, le LLM doit pouvoir préférer l'indicateur qui a une unité
    from gestukaay_engine.candidats import index
    from gestukaay_engine.comprehension import SYSTEME, Comprehension
    candidats = index().chercher("Taux d'accès des ménages à l'électricité")
    message = Comprehension._message("électricité", [], [], candidats, None)
    assert "(unité non précisée)" in message or all(c.indicateur.unite or c.indicateur.unite_affichee for c in candidats)
    assert "dont l'unité est indiquée" in SYSTEME
