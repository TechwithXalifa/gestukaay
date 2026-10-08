"""Résolution exacte (#11). Socle synthétique : tourne en CI, sans le socle extrait."""

from datetime import date

from gestukaay_contracts.models import Periode, RequeteStructuree, Resultat
from gestukaay_engine.resolution import Introuvable, Resolution, libelle_periode, resoudre
from gestukaay_engine.socle import Observation, Socle, SourceJeu, charger


def obs(ind, zone, periode, valeur, nature="observee", base="", **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature=nature, base_projection=base)


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "dwibrlf", "rgohtcc", "whkisxc", "feujxob", "pexioke", "vcvtdsf")}
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
    obs("vcvtdsf", "SN", "2023", 65.6),
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
    # accord en genre : « rural » est porté par « Taux d'électrification rurale » (#116)
    x = une(resoudre(SOCLE, req("vcvtdsf", milieu="rural")))
    assert (x.periode.valeur, x.valeur) == ("2023", 65.6)


def test_lieu_hors_referentiel_jamais_national():
    r = resoudre(SOCLE, req("pvswjnd"), lieux_inconnus=["Touba"])
    assert isinstance(r, Introuvable) and r.raison == "zone_non_couverte" and "Touba" in r.detail


def test_comparaison_et_projection():
    r = resoudre(SOCLE, req("pvswjnd", ["SN-DK", "SN-TH"], intention="comparaison"))
    assert [x.zone.code for x in r.resultats] == ["SN-DK", "SN-TH"]
    x = une(resoudre(SOCLE, req("pexioke.esperance-de-vie-a-la-naissance", periode="2035")))
    assert x.nature == "projection" and x.base_projection == "Projections démographiques RGPHAE 2013"


def test_sans_annee_jamais_une_annee_future():
    """#116, 0035 : « l'espérance de vie » sans année répondait 2035, « dernière donnée publiée »."""
    vie, isf = "pexioke.esperance-de-vie-a-la-naissance", "elwxsmc.indice-synthetique-de-fecondite"
    contra, naiss = "hltemyf.utilisation-actuelle-de-la-contraception", "pexioke.naissances"
    socle = Socle([
        *[obs(vie, "SN", p, v, nature="projection", sexe="Total") for p, v in (("2013", 64.8), ("2026", 70.2),
                                                                                ("2035", 74.6))],
        obs(isf, "SN", "2023", 3.9), obs(isf, "SN", "2025", 3.7, nature="projection"),
        obs(contra, "SN", "2024", 25.1, nature="estimation"), obs(contra, "SN", "2025", 26.0, nature="estimation"),
        obs(naiss, "SN", "2030", 700000, nature="projection"), obs(naiss, "SN", "2035", 720000, nature="projection"),
        obs("pvswjnd", "SN", "2023", 18126390), obs("pvswjnd", "SN", "2030", 21000000, nature="projection"),
    ], {d: SOURCES["pexioke"] for d in ("pexioke", "elwxsmc", "hltemyf", "pvswjnd")})

    # observée puis projetée jusqu'à une année passée (FR-009) : la projection 2025, badge projection
    r = resoudre(socle, req(isf))
    assert (une(r).periode.valeur, une(r).nature, r.defauts["periode"]) == ("2025", "projection", True)
    # observée puis projetée dans le futur : la dernière observée, « dernière donnée publiée »
    r = resoudre(socle, req("pvswjnd"))
    assert (une(r).periode.valeur, une(r).nature, r.defauts["periode"]) == ("2023", "observee", True)
    # projection seule : l'année en cours, sans « dernière donnée publiée »
    r = resoudre(socle, req(vie))
    assert (une(r).periode.valeur, une(r).nature, r.defauts["periode"]) == ("2026", "projection", False)
    # estimation seule qui s'arrête avant l'année en cours : c'est bien la dernière publiée
    r = resoudre(socle, req(contra))
    assert (une(r).periode.valeur, r.defauts["periode"]) == ("2025", True)
    # projection qui ne commence qu'après l'année en cours : la plus proche
    assert une(resoudre(socle, req(naiss))).periode.valeur == "2030"
    # l'année demandée reste servie
    assert une(resoudre(socle, req(vie, periode="2035"))).valeur == 74.6


def test_formats():
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


def test_region_servie_par_son_academie_equivalente():  # Sédhiou : une seule académie, même territoire
    tbs = "ervtjfc.taux-brut-de-scolarisation"
    socle = Socle([obs(tbs, "SN-IA-SEDHIOU", "2025", 100.1), obs(tbs, "SN-IA-DAKAR", "2025", 101.2)],
                  {"ervtjfc": SOURCES["pvswjnd"]})
    x = une(resoudre(socle, req(tbs, ["SN-SE"])))
    assert (x.zone.code, x.valeur) == ("SN-IA-SEDHIOU", 100.1)
    assert resoudre(socle, req(tbs, ["SN-DK"])).raison == "zone_non_couverte"  # Dakar : trois académies
