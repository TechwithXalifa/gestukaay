"""Moteur réel (#17). Socle synthétique et règles locales : tourne en CI, sans réseau ni socle extrait."""

from datetime import date

import pytest
from gestukaay_contracts.models import AskRequest, Periode, RequeteStructuree, SituateRequest
from gestukaay_engine import NonDisponible, charger_moteur
from gestukaay_engine import moteur as module_moteur
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.moteur import MESSAGE_NON_DISPONIBLE, MoteurReel
from gestukaay_engine.resolution import Introuvable
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature="observee", base_projection="")


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "dwibrlf", "qbvttzc")}
SOCLE = Socle([
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DB", "2023", 2080333, sexe="Total", age="Total"),
    obs("dwibrlf", "SN-DK", "2025", 13.2, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN-TH", "2025", 22.7, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN-TC", "2025", 5.0, sexe="TOTAL", âge="TOTAL"),
    obs("qbvttzc", "SN-KD", "2021", 9317, catégories="TOTAL"),
    obs("qbvttzc", "SN-KD", "2021", 5000, catégories="VPP"),
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def demander(question, **kw):
    return MOTEUR.repondre(AskRequest(question=question, **kw)).reponse


def req(indicateur, zones=(), intention="valeur", ordre="desc"):
    return RequeteStructuree(intention=intention, indicateur=indicateur, zones=list(zones),
                             periode=Periode(type="derniere"), ordre=ordre, confiance=0.9)


def test_reponse_exacte_complete():
    r = demander("Combien d'habitants à Thiès ?")
    assert r.issue == "exacte" and r.intention == "valeur"
    assert [(x.zone.code, x.valeur) for x in r.resultats] == [("SN-TH", 2463677)]
    assert "2 463 677" in r.explication and r.periode_par_defaut  # espace fine insécable (§7.4)
    assert r.version_socle == "test" and r.langue == "fr" and r.requete.indicateur == "pvswjnd"
    # URL provisoire dans la citation : le backend la remplace par l'adresse stable /r/<id>
    assert r.url.endswith(f"/r/{r.id}") and r.citation.endswith(f"/r/{r.id}.")


def test_annee_tapee_en_lettres():
    """#22 : un nombre écrit en lettres est converti comme dans une note vocale (0027) ; la question affichée
    reste celle posée."""
    for q in ("Ñaata nit ñoo dëkk Thiès ci ñaari junni ak ñaar-fukk ak ñett ?",
              "Combien d'habitants à Thiès en deux mille vingt-trois ?"):
        rep = MOTEUR.repondre(AskRequest(question=q)).reponse
        assert rep.resultats[0].valeur == 2463677 and not rep.periode_par_defaut and rep.question == q


def test_refus_projection():
    r = demander("Combien d'habitants à Thiès en 2045 ?")
    assert (r.issue, r.motif) == ("aucune", "projection")


def test_refus_lieu_inconnu_non_rattache():
    r = demander("Combien d'habitants à Paris ?")
    assert (r.issue, r.motif) == ("aucune", "hors_socle")


def test_refus_incomprehension():
    r = demander("azerty qsdf")
    assert (r.issue, r.motif, r.requete) == ("aucune", "incomprehension", None)


def test_non_traite_jamais_hors_socle(monkeypatch):
    """Un type de question non traité par la résolution : « pas encore disponible », jamais
    « cette donnée n'existe pas » (la donnée existe peut-être)."""
    monkeypatch.setattr(module_moteur, "resoudre", lambda *a, **k: Introuvable("non_traite", "essai"))
    for r in (demander("Combien d'habitants à Thiès ?"),
              MOTEUR.executer(req("pvswjnd", ["SN-TH"]), "Combien d'habitants à Thiès ?", "fr").reponse):
        assert (r.issue, r.motif, r.message) == ("aucune", "non_disponible", MESSAGE_NON_DISPONIBLE)
        assert r.motif != "hors_socle" and "n'existe pas" not in r.message and not r.suggestions


def test_classement_le_plus_faible_phrase_et_tri_concordent():
    r = MOTEUR.executer(req("dwibrlf", intention="classement"),
                        "Quelle région a le taux de chômage le plus faible ?", "fr").reponse
    assert [x.zone.code for x in r.resultats] == ["SN-TC", "SN-DK", "SN-TH"]
    assert "la plus faible" in r.explication and r.graphique.type == "barres_horizontales"


def test_executer_echec_donne_un_refus_pas_une_approchee():
    r = MOTEUR.executer(req("pvswjnd", ["SN-KL"]), "Combien d'habitants à Kaolack ?", "fr").reponse
    assert r.issue == "aucune"


def test_langue_wolof_forcee_reponse_ecrite_en_wolof():
    # option B de KBD (0032) : la langue choisie prime ; phrases de KBD, chiffres et année tels qu'affichés
    r = demander("Combien d'habitants à Thiès ?", langue="wo")
    assert r.langue == "wo" and "2 463 677" in r.explication and "2023" in r.explication
    assert "Cees" in r.explication and "A-EN-ES-DE" not in r.explication


def test_langue_detectee_sans_choix():
    assert demander("Ñaata nit ñoo dëkk Tiés ?").langue == "wo"
    assert demander("Combien d'habitants à Thiès ?").langue == "fr"
    assert demander("Ñaata nit ñoo dëkk Tiés ?", langue="fr").langue == "fr"  # le choix forcé prime


def test_question_vocale_garde_la_transcription():
    r = demander("Combien d'habitants à Thiès ?", source="voix", transcription_brute="combien d habitants a thies")
    assert r.transcription == "Combien d'habitants à Thiès ?"


def test_voix_sans_service_ni_repli_non_disponible():
    from gestukaay_engine.transcription import Transcripteur
    m = MoteurReel(SOCLE, Comprehension(None), Transcripteur(env={}))
    with pytest.raises(NonDisponible):
        m.transcrire(b"\x00", "webm")


def test_situer_sans_moyenne_publiee_pas_disponible():
    """Le mini-socle n'a pas de consommation moyenne : jamais de chiffre de remplacement."""
    with pytest.raises(NonDisponible):
        MOTEUR.situer(SituateRequest(region="SN-KD", taille_menage=5, depenses_mensuelles="100k_200k"))


def test_charger_moteur_reel(monkeypatch):
    monkeypatch.setattr(module_moteur, "socle", lambda: SOCLE)
    monkeypatch.delenv("LLM_CHAINE", raising=False)
    monkeypatch.setenv("GESTUKAAY_MOTEUR", "reel")
    m = charger_moteur()
    assert isinstance(m, MoteurReel) and m.version_socle() == "test" and m.comprehension.client is None


def test_question_avec_point_d_interrogation_colle():
    r = demander("Combien d'habitants à Thiès?")
    assert [(x.zone.code, x.valeur) for x in r.resultats] == [("SN-TH", 2463677)]


def test_voitures_toujours_approchee_meme_si_le_total_existe():
    # « voitures » n'est pas le parc total : on fait choisir TOTAL ou VPP, aucune valeur (#116, choix KBD)
    r = demander("Nombre de voitures à Kolda")
    assert r.issue == "approchee"
    assert [c.requete.desagregation for c in r.choix] == [{"catégories": "TOTAL"}, {"catégories": "VPP"}]


def test_touba_approchee_region_puis_senegal():
    r = demander("Combien d'habitants à Touba ?")
    assert r.issue == "approchee"
    assert [c.requete.zones for c in r.choix] == [["SN-DB"], ["SN"]]
