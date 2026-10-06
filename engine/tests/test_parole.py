"""Texte wolof de la voix de réponse (#29, décision 0029). Les attendus sont les exemples écrits par
KBD (voix_wolof/2_nombres_argent_unites.csv, 3_noms.csv, 5 et 6 octobre 2026), mot pour mot."""

import random
import re
from datetime import date

import pytest
from gestukaay_contracts.models import AskRequest, Periode, RequeteStructuree
from gestukaay_engine.comprehension import Comprehension
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.nombres import en_chiffres
from gestukaay_engine.parole import (
    DUREE_MAX_S,
    argent_wo,
    duree_estimee,
    entier_wo,
    epeler,
    fr_entier,
    nombre_wo,
    periode_wo,
    suffixe,
    texte_parle,
    zone_wo,
)
from gestukaay_engine.socle import Observation, Socle, SourceJeu

# --- Nombres ---------------------------------------------------------------


@pytest.mark.parametrize("n, dit", [  # fiche 2 (KBD)
    (2463677, ("ñaari milyoŋ ak ñeenti téeméer ak juróom-benn-fukk ak ñetti junni ak juróom-benni téeméer ak "
               "juróom-ñaar-fukk ak juróom-ñaar")),
    (1590818, ("benn milyoŋ ak juróomi téeméer ak juróom-ñeent-fukki junni ak juróom-ñetti téeméer ak fukk ak "
               "juróom-ñett")),
    (3450, "ñetti junni ak ñeenti téeméer ak juróom-fukk"), (1200, "junni ak ñaari téeméer"),
    (30, "fanweer"), (37, "fanweer ak juróom-ñaar"), (24, "ñaar-fukk ak ñeent"),
])
def test_nombres_de_kbd(n, dit):
    assert entier_wo(n) == dit


@pytest.mark.parametrize("devant, dit", [  # le dernier mot prend -i (ou -y) devant un nom
    (2463677, "… juróom-ñaari"), (12000, "fukk ak ñaari junniy"), (40000, "ñeent-fukki junniy"),
    (30, "fanweeri"), (5, "juróomi"),
])
def test_suffixe_devant_un_nom(devant, dit):
    assert suffixe(entier_wo(devant)).endswith(dit.removeprefix("… "))


@pytest.mark.parametrize("fcfa, dit", [  # fiche 2 : l'argent se compte en dërëm (5 FCFA)
    (5, "dërëm"), (10, "ñaari dërëm"), (25, "juróomi dërëm"), (50, "fukki dërëm"), (100, "ñaar-fukk"),
    (200, "ñeent-fukk"), (250, "juróom-fukk"), (500, "téeméer"), (750, "téeméer ak juróom-fukk"),
    (1000, "ñaari téeméer"), (1250, "ñaari téeméer ak juróom-fukk"), (2000, "ñeenti téeméer"),
    (2500, "juróomi téeméer"), (5000, "junni"), (10000, "ñaari junni"), (25000, "juróomi junni"),
    (50000, "fukki junni"), (75000, "fukk ak juróomi junni"), (100000, "ñaar-fukki junni"),
    (150000, "fanweeri junni"), (152500, "fanweeri junni ak juróomi téeméer"), (500000, "téeméeri junni"),
    (150, "fanweer"), (1000000, "benn milyoŋ"), (2500000, "ñaari milyoŋ ak juróomi téeméeri junni"),
    (1234, "junni ak ñaari téeméer ak fanweer ak ñeenti sefaa"),  # pas un multiple de 5 : en CFA
    (450, "juróom-ñeent-fukk"), (700, "téeméer ak ñeent-fukk"), (350000, "juróom-ñaar-fukki junni"),
])
def test_argent_de_kbd(fcfa, dit):
    assert argent_wo(fcfa) == dit


def test_milliards_du_pib():
    assert f"{suffixe(entier_wo(18500))} milyaar" == \
        "fukk ak juróom-ñetti junni ak juróomi téeméeri milyaar"  # 18 500 milliards (fiche 2)
    assert entier_wo(10**9) == "benn milyaar"


@pytest.mark.parametrize("entier, dec, dit", [
    (13, "2", "fukk ak ñett wirgil ñaar"), (20, "4", "ñaar-fukk wirgil ñeent"), (0, "5", "tus wirgil juróom"),
    (68, "4", "juróom-benn-fukk ak juróom-ñett wirgil ñeent"), (0, "35", "tus wirgil fanweer ak juróom"),
    (112, "3", "téeméer ak fukk ak ñaar wirgil ñett"), (4, "0", "ñeent"), (0, "05", "tus wirgil tus juróom"),
])
def test_decimales(entier, dec, dit):
    assert nombre_wo(entier, dec) == dit


def test_nombre_dit_egal_au_nombre_affiche():
    """#29 : le nombre prononcé est le nombre affiché. Contrôle indépendant : la conversion inverse
    (nombres dits -> chiffres, #28) retrouve le même nombre sur 5 000 tirages."""
    hasard = random.Random(29)
    for n in [2, 31, 1000, 1001, 10**6, 999999999] + [hasard.randrange(2, 10**12) for _ in range(5000)]:
        assert en_chiffres(entier_wo(n)) == str(n), n
    for _ in range(500):
        e, d = hasard.randrange(1000), str(hasard.randrange(1, 100))
        assert en_chiffres(nombre_wo(e, d)) == f"{e},{d}"
    # « tus » (0), « benn » (1), « fanweer » (30, aussi « le mois ») dits seuls ne sont jamais convertis
    assert (entier_wo(0), entier_wo(1), entier_wo(30)) == ("tus", "benn", "fanweer")


@pytest.mark.parametrize("n, fr", [
    (2011, "deux mille onze"), (2019, "deux mille dix-neuf"), (2021, "deux mille vingt et un"),
    (2023, "deux mille vingt-trois"), (1999, "mille neuf cent quatre-vingt-dix-neuf"), (2080, "deux mille quatre-vingts"),
    (2071, "deux mille soixante et onze"), (2200, "deux mille deux cents"), (5, "cinq"),
])
def test_annees_en_francais(n, fr):
    """KBD : « j'ai jamais entendu un natif parler d'une année en wolof »."""
    assert fr_entier(n) == fr


# --- Zones, périodes, sources ------------------------------------------------


def test_zones_et_periodes_de_kbd():
    assert zone_wo("SN-TH") == "ci diiwaanu Cees" and zone_wo("SN-TH", avec_ci=False) == "diiwaanu Cees"
    assert zone_wo("SN") == "ci Senegaal" and zone_wo("SN-IA-RUFISQUE") == "ci akaademiyu Tëngéej"
    assert zone_wo("SN-FK-FOUNDIOUGNE") == "ci tunduw Fundiyuñ"
    assert periode_wo("2023") == "ci atum deux mille vingt-trois"
    assert periode_wo("2026-03") == "ci weeru Mars atum deux mille vingt-six"
    assert periode_wo("2026-T1") == "ci trimestre bu njëkk bu deux mille vingt-six"
    assert periode_wo("2026-T4") == "ci ñenteelu trimestre bu deux mille vingt-six"


@pytest.mark.parametrize("sigle, dit", [  # KBD (fiche 3) : épelés comme en français
    ("ANSD", "A-EN-ES-DE"), ("EHCVM", "E-ACH-CÉ-VÉ-EM"), ("ENES", "E-EN-E-ES"), ("EDS", "E-DE-ES"),
    ("IHPC", "I-ACH-PÉ-CÉ"), ("CSA", "CÉ-ES-A"), ("ARTP", "A-ER-TÉ-PÉ"), ("RGPH-5", "ER-JÉ-PÉ-ACH cinq"),
])
def test_sigles_epeles_comme_kbd(sigle, dit):
    assert epeler(sigle) == dit


# --- Réponses complètes (socle synthétique) ----------------------------------


def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0], nature="observee", base_projection="")


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "dwibrlf")}
SOCLE = Socle([
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-TH", "2023", 2463677, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DB", "2023", 2080333, sexe="Total", age="Total"),
    obs("dwibrlf", "SN", "2025", 20.4, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN-DK", "2025", 13.2, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN-TH", "2025", 22.7, sexe="TOTAL", âge="TOTAL"),
    obs("dwibrlf", "SN-TH", "2024", 23.1, sexe="TOTAL", âge="TOTAL"),
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def parle(question: str) -> str | None:
    return texte_parle(MOTEUR.repondre(AskRequest(question=question)), SOCLE)


def req(indicateur, zones=(), intention="valeur", ordre="desc"):
    return RequeteStructuree(intention=intention, indicateur=indicateur, zones=list(zones),
                             periode=Periode(type="derniere"), ordre=ordre, confiance=0.9)


def test_population_de_thies():
    t = parle("Combien d'habitants à Thiès ?")
    nombre = ("ñaari milyoŋ ak ñeenti téeméer ak juróom-benn-fukk ak ñetti junni ak juróom-benni téeméer ak "
              "juróom-ñaar-fukk ak juróom-ñaari nit")  # -i devant « nit »
    periode = "ci atum deux mille vingt-trois"
    assert t.startswith((  # l'une des deux tournures validées par KBD (formelle | orale)
        f"Limu askan wi ci diiwaanu Cees mi ngi tollu ci {nombre} {periode}.",
        f"Am na {nombre} ci diiwaanu Cees {periode}."))
    assert "Lii mooy lim bi mujj bi ñu génne." in t  # pas d'année demandée
    assert not re.search(r"\d", t) and duree_estimee(t) <= DUREE_MAX_S


def test_taux_regional_compare_au_national_avec_la_source():
    t = parle("Quel est le taux de chômage à Thiès en 2025 ?")
    assert t.startswith("Tolluwaayu ñàkk liggéey bi ci diiwaanu Cees mi ngi tollu ci ñaar-fukk ak ñaar "
                        "wirgil juróom-ñaar ci téeméer ci atum deux mille vingt-cinq.")
    assert "Loolu dafa ëpp limu réew mi gépp, di ñaar-fukk wirgil ñeent ci téeméer" in t
    assert "A-EN-ES-DE" in t and not re.search(r"\d", t)


def test_comparaison_de_deux_regions():
    r = MOTEUR.executer(req("dwibrlf", ["SN-DK", "SN-TH"], "comparaison"), "Chômage à Dakar et Thiès", "fr")
    t = texte_parle(r, SOCLE)
    assert ("mi ngi tollu ci fukk ak ñett wirgil ñaar ci téeméer ci diiwaanu Ndakaaru, ak ñaar-fukk ak ñaar "
            "wirgil juróom-ñaar ci téeméer ci diiwaanu Cees.") in t
    assert "Lim bi moo gën a kawe ci diiwaanu Cees." in t  # un taux : « kawe »


def test_evolution_en_baisse():
    r = MOTEUR.executer(RequeteStructuree(intention="comparaison", indicateur="dwibrlf", zones=["SN-TH"],
                                          periode=Periode(type="annee", valeur="2024", fin="2025"),
                                          confiance=0.9), "Chômage à Thiès entre 2024 et 2025", "fr")
    t = texte_parle(r, SOCLE)
    assert "ci atum deux mille vingt-quatre, ak ñaar-fukk ak ñaar wirgil juróom-ñaar ci téeméer ci atum " \
           "deux mille vingt-cinq, muy wàññiku." in t


def test_classement_population_dit_rey_et_pas_ci_ci():
    r = MOTEUR.executer(req("pvswjnd", intention="classement"), "Quelle région a le plus d'habitants ?", "fr")
    t = texte_parle(r, SOCLE)
    assert t.startswith("Ci atum deux mille vingt-trois, lim bi moo gën a réy ci diiwaanu Ndakaaru ak ")
    assert "teg ci diiwaanu Cees ak" in t and "ci ci" not in t


@pytest.mark.parametrize("question, debut", [
    ("Combien d'habitants à Thiès en 2045 ?", "Gëstukaay du xeyma lu jëm ci ëlëg."),
    ("Combien d'habitants à Paris ?", "Lim bii amul ci xibaari A-EN-ES-DE yi ñu yor."),
    ("azerty qsdf", "Xéyna dégguma la bu baax."),
])
def test_refus(question, debut):
    assert parle(question).startswith(debut)


def test_une_note_ne_depasse_pas_20_s():
    """Variante la plus courte, puis on retire la source, « dernière donnée », le national."""
    for q in ("Combien d'habitants à Thiès ?", "Quel est le taux de chômage à Thiès ?",
              "Combien d'habitants au Sénégal ?"):
        assert duree_estimee(parle(q)) <= DUREE_MAX_S, q


def test_majuscules_et_sigles():
    from gestukaay_engine.parole import _nettoyer
    assert _nettoyer("ci atum. lim bi (PIB), PRODUIT INTERIEUR BRUT, A-EN-ES-DE, MITTA") == \
        "Ci atum. Lim bi, PÉ-I-BÉ, produit interieur brut, A-EN-ES-DE, MITTA"


def test_ci_reew_mi_seulement_pour_le_senegal():
    """KBD : « Limu woto yi ci réew mi » (dans le pays) ne se dit pas pour une région."""
    from types import SimpleNamespace

    from gestukaay_engine.parole import indicateur_wo
    r = SimpleNamespace(indicateur=SimpleNamespace(code="qbvttzc", libelle=""), desagregation=None,
                        zone=SimpleNamespace(code="SN-KD"))
    assert indicateur_wo(r) == "Limu woto yi"
    r.zone.code = "SN"
    assert indicateur_wo(r) == "Limu woto yi ci réew mi"
