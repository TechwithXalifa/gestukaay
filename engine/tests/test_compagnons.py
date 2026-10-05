"""Un nombre accompagné de son taux (décision 0024). Socle synthétique : tourne en CI, sans réseau.

Valeurs du socle 2026.10.0 (muhgux, 1er trimestre 2026 : 1 590 818 personnes au chômage, 22,9 %),
sauf celles marquées « fictive ».
"""

from datetime import date

from gestukaay_contracts.models import Periode, RequeteStructuree
from gestukaay_engine.compagnons import compagnons
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.socle import Observation, Socle, SourceJeu


def obs(ind, periode, valeur, zone="SN"):
    return Observation(id=f"{ind}-{zone}-{periode}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=(), valeur=valeur, unite="", echelle="1",
                       source_id="muhgux", nature="observee", base_projection="")


NOMBRE, TAUX = "muhgux.population-au-chomage", "muhgux.taux-de-chomage"
SOURCES = {"muhgux": SourceJeu("muhgux", "ANSD", "ANSD", "Marché du travail", date(2026, 5, 1), "", "https://x")}
SOCLE = Socle([
    obs(NOMBRE, "2026-T1", 1590818), obs(TAUX, "2026-T1", 22.9),
    obs(NOMBRE, "2025-T4", 1500000),  # fictive : un trimestre où le taux n'est pas publié
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def demander(indicateur, periode=None):
    p = Periode(type="derniere") if periode is None else Periode(type="trimestre", valeur=periode)
    req = RequeteStructuree(intention="valeur", indicateur=indicateur, periode=p, confiance=0.9)
    return MOTEUR.executer(req, "Ñi amul ligéey ci Senegaal ?", "wo").reponse


def test_le_nombre_vient_avec_son_taux_au_meme_trimestre():
    r = demander(NOMBRE)
    assert [(x.indicateur.code, x.periode.valeur, x.valeur) for x in r.resultats] == \
        [(NOMBRE, "2026-T1", 1590818), (TAUX, "2026-T1", 22.9)]
    assert r.explication == (
        "Le Sénégal compte 1 590 818 personnes au chômage au 1er trimestre 2026, dernière donnée "
        "publiée. Le taux de chômage est de 22,9 % des personnes actives (celles qui travaillent ou "
        "cherchent un emploi).")


def test_pas_de_taux_d_une_autre_periode():
    r = demander(NOMBRE, "2025-T4")
    assert [x.indicateur.code for x in r.resultats] == [NOMBRE]
    assert "taux" not in r.explication


def test_le_taux_seul_n_appelle_pas_de_compagnon():
    r = demander(TAUX)
    assert [x.indicateur.code for x in r.resultats] == [TAUX]


def test_paires_declarees_dans_le_meme_jeu():
    for code, c in compagnons().items():
        assert code.split(".")[0] == c.code.split(".")[0], f"{code} -> {c.code} : jeux différents"
        assert "{nombre}" in c.phrase or "{valeur}" in c.phrase
