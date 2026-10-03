"""Résolution exacte (#11). Socle synthétique : tourne en CI, sans le socle extrait."""

from datetime import date

from gestukaay_contracts.models import Periode, RequeteStructuree, Resultat
from gestukaay_engine.resolution import Introuvable, Resolution, formater, libelle_periode, resoudre
from gestukaay_engine.socle import Observation, Socle, SourceJeu, charger


def obs(ind, zone, periode, valeur, nature="observee", base="", **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature=nature, base_projection=base)


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "dwibrlf", "rgohtcc", "whkisxc", "feujxob", "pexioke")}
SOCLE = Socle([
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 1240000, sexe="Féminin", age="Total"),
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("dwibrlf", "SN", "2024", 19.5, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 20.4, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN", "2025", 25.7, sexe="TOTAL", âge="15-24 ans"),
    *[obs("rgohtcc", "SN", "2024", v, composantes="PRODUIT INTERIEUR BRUT", **{"base-pib": b, "prix-pib": p,
                                                                               "approche": "PIB approche production"})
      for v, b, p in ((22745900, "Base 2021", "Prix courant"), (17000000, "Base 2021", "Prix constant (référence de 2021)"),
                      (21000000, "Base 2014", "Prix courant"))],
    obs("whkisxc", "SN", "2018-12", 55538, nationalité="Français"),
    obs("whkisxc", "SN", "2018-12", 9000, nationalité="Algériens"),
    obs("feujxob.riz-brise-ordinaire-au-detail", "SN-DK", "2026-03", 309.026438943514),
    obs("pexioke.esperance-de-vie-a-la-naissance", "SN", "2035", 74.6, nature="projection",
        base="Projections démographiques RGPHAE 2013", sexe="Total"),
], SOURCES)


def req(indicateur, zones=(), periode=None, intention="valeur", **desag):
    p = Periode(type="derniere") if periode is None else Periode(type="mois" if "-" in periode else "annee",
                                                                  valeur=periode)
    return RequeteStructuree(intention=intention, indicateur=indicateur, zones=list(zones), periode=p,
                             desagregation=desag or None, confiance=0.9)


def une(r) -> Resultat:
    assert isinstance(r, Resolution), r
    assert len(r.resultats) == 1
    return r.resultats[0]


def test_valeurs_par_defaut_national_derniere_periode_total():
    r = resoudre(SOCLE, req("dwibrlf"))
    x = une(r)
    assert (x.zone.code, x.periode.valeur, x.valeur) == ("SN", "2025", 20.4)
    assert r.defauts == {"zone": True, "periode": True} and x.desagregation is None


def test_zone_et_periode_demandees():
    x = une(resoudre(SOCLE, req("pvswjnd", ["SN-TH"], "2023")))
    assert x.valeur == 2463677 and x.valeur_affichee == "2 463 677"
    assert x.zone.libelle == "Thiès" and x.source.url == "https://x/pvswjnd"
    Resultat.model_validate(x.model_dump())  # conforme au contrat


def test_desagregation_canonique_vers_libelles_du_jeu():
    assert une(resoudre(SOCLE, req("pvswjnd", ["SN-TH"], sexe="femmes"))).desagregation == {"sexe": "Féminin"}
    x = une(resoudre(SOCLE, req("dwibrlf", periode="2025", age="15-24")))
    assert x.valeur == 25.7 and x.desagregation == {"âge": "15-24 ans"}


def test_strict_periode_ou_zone_absente():
    r = resoudre(SOCLE, req("dwibrlf", ["SN-KL"]))
    assert isinstance(r, Introuvable) and r.raison == "zone_non_couverte" and "SN" in r.disponibles
    r = resoudre(SOCLE, req("dwibrlf", periode="2026"))
    assert r.raison == "periode_absente" and r.disponibles == ["2024", "2025"]


def test_defaut_declare_du_jeu_pour_le_pib():
    x = une(resoudre(SOCLE, req("rgohtcc", periode="2024")))
    assert x.valeur == 22745900  # base 2021, prix courants, approche production


def test_modalite_nommee_dans_la_question_sinon_choix():
    q = "Combien de touristes français sont arrivés au Sénégal en décembre 2018 ?"
    assert une(resoudre(SOCLE, req("whkisxc", periode="2018-12"), question=q)).valeur == 55538
    r = resoudre(SOCLE, req("whkisxc", periode="2018-12"), question="Combien de touristes ?")
    assert r.raison == "desagregation_ambigue" and r.choix == {"nationalité": ["Algériens", "Français"]}


def test_precision_deja_portee_par_l_indicateur():
    x = une(resoudre(SOCLE, req("feujxob.riz-brise-ordinaire-au-detail", produit="riz")))
    assert (x.zone.code, x.periode.libelle, x.valeur_affichee) == ("SN-DK", "mars 2026", "309")


def test_lieu_hors_referentiel_jamais_national():
    r = resoudre(SOCLE, req("pvswjnd"), lieux_inconnus=["Touba"])
    assert isinstance(r, Introuvable) and r.raison == "zone_non_couverte" and "Touba" in r.detail


def test_comparaison_et_projection():
    r = resoudre(SOCLE, req("pvswjnd", ["SN-DK", "SN-TH"], intention="comparaison"))
    assert [x.zone.code for x in r.resultats] == ["SN-DK", "SN-TH"]
    x = une(resoudre(SOCLE, req("pexioke.esperance-de-vie-a-la-naissance", periode="2035")))
    assert x.nature == "projection" and x.base_projection == "Projections démographiques RGPHAE 2013"


def test_formats():
    assert formater(25.7) == "25,7" and formater(0.3) == "0,3" and formater(391.145833) == "391"
    assert libelle_periode("2026-03") == "mars 2026" and libelle_periode("2024-T2") == "2e trimestre 2024"


def test_charger_lit_le_format_extrait(tmp_path):
    (tmp_path / "observations.csv").write_text(
        "observation_id;indicateur;zone;zone_presumee;periode;desagregation;valeur;unite;echelle;source_id;"
        "nature;base_projection;ligne_origine\n"
        'a1;pvswjnd;SN-TH;;2023;"{""sexe"": ""Total""}";2463677.0;;1;pvswjnd;observee;;12\n', encoding="utf-8")
    (tmp_path / "sources.csv").write_text(
        "source_id;producteur;organisme;titre;date_publication;derniere_maj;licence;url;url_producteur\n"
        "pvswjnd;ANSD;ANSD;RGPH-5;2023-10-31;2024-01-01;;https://x;\n", encoding="utf-8")
    s = charger(tmp_path)
    assert len(s) == 1 and s.observations("pvswjnd")[0].dims() == {"sexe": "Total"}
    assert s.sources["pvswjnd"].date_publication == date(2023, 10, 31)


def test_demandes_du_llm_tolerees():
    """Cas réels de la passe Gemini (#11) : sexe = total sans dimension sexe ; « français » rangé dans
    produit ; « primaire » pour « Elémentaire » ; la céréale demandée avant la dernière période."""
    s = Socle([
        obs("whkisxc", "SN", "2018-12", 55538, nationalité="Français"),
        obs("whkisxc", "SN", "2018-12", 9000, nationalité="Algériens"),
        obs("ervtjfc.taux-brut-de-scolarisation", "SN-IA-LOUGA", "2025", 86.7, sexe="Féminin", cycle="Elémentaire"),
        obs("ervtjfc.taux-brut-de-scolarisation", "SN-IA-LOUGA", "2025", 70.1, sexe="Féminin", cycle="Moyen général"),
        obs("sbsryhc", "SN-KL", "2016", 273.5, **{"type-de-céréales": "Riz"}),
        obs("sbsryhc", "SN-KL", "2023", 300.0, **{"type-de-céréales": "mil"}),
    ], SOURCES)
    assert une(resoudre(s, req("whkisxc", periode="2018-12", produit="français"))).valeur == 55538
    assert une(resoudre(s, req("whkisxc", periode="2018-12", sexe="total"),
                        question="touristes français")).valeur == 55538
    assert une(resoudre(s, req("ervtjfc.taux-brut-de-scolarisation", ["SN-IA-LOUGA"], sexe="femmes",
                               cycle="primaire"))).valeur == 86.7
    x = une(resoudre(s, req("sbsryhc", ["SN-KL"], produit="riz")))
    assert (x.valeur, x.periode.valeur) == (273.5, "2016")


def test_socle_incoherent_refuse():
    """Décision 0013 : un indicateur du socle inconnu du référentiel -> le moteur ne démarre pas."""
    import pytest
    from gestukaay_engine.socle import SocleIncoherent, verifier
    verifier(SOCLE)  # tous connus
    with pytest.raises(SocleIncoherent, match="code-disparu"):
        verifier(Socle([obs("code-disparu", "SN", "2023", 1)], SOURCES, "2026.10.0"))
