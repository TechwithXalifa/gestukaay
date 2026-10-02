"""Contrôles et corrections (#6, décision 0008). Observations synthétiques : tourne en CI."""

import json

from gestukaay_socle.controles import (
    ACTIONS,
    CONDITIONS,
    Correction,
    appliquer,
    controle_population,
    controler,
    corrections,
)
from gestukaay_socle.indicateurs import indicateurs


def obs(code, zone, periode, valeur, ds=None, desag=None, unite="%", ligne=2):
    return ("id", code, zone, "", periode, json.dumps(desag or {}, ensure_ascii=False), valeur, unite, "1",
            ds or code.split(".")[0], "observee", "", ligne)


def corr(**kw):
    base = {"id": "C99", "action": "exclure", "dataset_id": "x", "indicateur": "", "zones": (), "periode_debut": "",
                "periode_fin": "", "condition": "", "valeur": "", "motif": "m", "preuve": "p"}
    return Correction(**(base | kw))


def test_exclusion_ciblee_par_zone_et_periode():
    c = corr(dataset_id="rnumqzf", zones=("SN-KD", "SN-KE"), periode_debut="2016", periode_fin="2022")
    garde, rejets, compte = appliquer([
        obs("rnumqzf", "SN-KD", "2016", "174298"),  # exclue
        obs("rnumqzf", "SN-KD", "2023", "914798"),  # hors période
        obs("rnumqzf", "SN-TH", "2016", "1966117"),  # autre zone
    ], [c])
    assert [o[2] + o[4] for o in garde] == ["SN-KD2023", "SN-TH2016"]
    assert rejets[0][3] == "correction C99" and compte["C99"] == 1


def test_conditions():
    assert corr(dataset_id="q", indicateur="q.gini", condition="valeur=0").vise(obs("q.gini", "SN", "2005", "0.0"))
    assert not corr(dataset_id="q", condition="valeur=0").vise(obs("q.gini", "SN", "2010", "0.3"))
    assert corr(dataset_id="i", condition="journalier").vise(obs("i.x", "SN", "0016-02-01", "5"))
    assert not corr(dataset_id="i", condition="journalier").vise(obs("i.x", "SN", "2016", "5"))
    assert corr(dataset_id="u", indicateur="unite:*prix constants de*").cible("u.total", "En milliards aux prix constants de 2003")


def test_referentiel_des_corrections():
    cs = corrections()
    assert len({c.id for c in cs}) == len(cs)
    for c in cs:
        assert c.action in ACTIONS and c.condition in CONDITIONS and c.motif and c.preuve, c.id
        assert (c.action == "unite_affichee") == bool(c.valeur), c.id
    # les unités affichées corrigées sont bien reportées dans le référentiel des indicateurs
    for c in cs:
        if c.action == "unite_affichee":
            vises = [x for x in indicateurs().values() if x.dataset_id == c.dataset_id and c.cible(x.code, x.unite)]
            assert vises and all(x.unite_affichee == c.valeur for x in vises), c.id


def test_controles_signalent():
    o = [obs("a.taux", "SN", "2020", "120"), obs("q.gini", "SN", "2020", "0.0", unite=""),
         obs("b", "SN", "2020", "100", unite="t"), obs("b", "SN", "2021", "1000", unite="t")]
    s = controler(o, {})
    assert len(s["Gini hors de ]0, 1["]) == 1
    assert len(s["rupture (×3 d'une année sur l'autre)"]) == 1


def test_population_comparee_au_rgph5():
    tot = {"groupe-d-âge": "Ensemble", "sexe": "TOTALE"}
    o = [obs("pvswjnd", "SN-KD", "2023", "914798", desag={"sexe": "Total", "age": "Total"}),
         obs("rnumqzf.x", "SN-KD", "2022", "231217", desag=tot)]
    assert controle_population(o) == ["SN-KD : rnumqzf 2022 = 231 217 ; RGPH-5 2023 = 914 798"]
