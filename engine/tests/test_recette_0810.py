"""Recette du 08/10 (237 questions au vrai moteur) : chiffres faux et refus à tort, avec le LLM ou sans.
Référentiels du dépôt, socle synthétique : tourne en CI, sans réseau ni socle extrait."""

from datetime import date

from gestukaay_contracts.models import AskRequest, RequeteStructuree
from gestukaay_engine.approchee import Approchee, proposer_approchee, rattachements
from gestukaay_engine.candidats import (
    Candidat,
    desagregation_citee,
    lieux_inconnus,
    ratio_non_publie,
    zones_citees,
)
from gestukaay_engine.comprehension import Comprehension, Comprise, _verifie_en_tete
from gestukaay_engine.gabarits import NOTE_MENAGES_AGRICOLES, note_perimetre
from gestukaay_engine.moteur import MoteurReel
from gestukaay_engine.refus import obtenir_suggestions
from gestukaay_engine.resolution import Introuvable, resoudre
from gestukaay_engine.socle import Observation, Socle, SourceJeu
from gestukaay_socle.indicateurs import indicateurs


def obs(ind, zone, periode, valeur, **dims):
    return Observation(id=f"{ind}-{zone}-{periode}-{valeur}-{dims}", indicateur=ind, zone=zone, zone_presumee=False,
                       periode=periode, desagregation=tuple(sorted(dims.items())), valeur=valeur, unite="",
                       echelle="1", source_id=ind.split(".")[0].split("~")[0], nature="observee", base_projection="")


SOURCES = {d: SourceJeu(d, "ANSD", "Agence nationale", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
           for d in ("pvswjnd", "jcvcajc", "muhgux", "deuqmkd", "dwibrlf", "hfhored")}
SOCLE = Socle([
    obs("pvswjnd", "SN", "2023", 18126390, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-DK", "2023", 4004426, sexe="Total", age="Total"),
    obs("pvswjnd", "SN-SL", "2023", 1202441, sexe="Total", age="Total"),
    obs("jcvcajc.taux-de-pauvrete", "SN", "2022", 37.5, **{"milieu-de-résidence": "Ensemble"}),
    obs("jcvcajc.taux-de-pauvrete", "SN", "2022", 53.3, **{"milieu-de-résidence": "Rural"}),
    obs("jcvcajc.taux-de-pauvrete", "SN-KA", "2022", 58.2, **{"milieu-de-résidence": "Ensemble"}),
    obs("muhgux.salaire-moyen-mensuel", "SN", "2026-T1", 126642),
    obs("muhgux.salaire-moyen-mensuel-du-secteur-prive", "SN", "2026-T1", 150000),
    obs("hfhored.medecin-generaliste", "SN", "2022", 624),
], SOURCES, "test")
MOTEUR = MoteurReel(SOCLE, Comprehension(None))


def demander(question):
    return MOTEUR.repondre(AskRequest(question=question)).reponse


# --- le choix du LLM nommé par la question n'est plus remplacé par la tête vérifiée (A2) ------------------

def test_le_llm_garde_un_choix_que_la_question_nomme():
    i = indicateurs()
    tete, choisi = i["ioxbglg.nombre-de-personnes-emprisonnees"], i["ioxbglg.nombre-de-personnes-condamnees"]
    cands = [Candidat(tete, 15.2), Candidat(choisi, 14.9)]
    q = "Quel est le nombre de personnes condamnées en 2025 ?"
    assert _verifie_en_tete(choisi.code, cands, [], ["2025"], q) == choisi.code  # avant : les emprisonnées
    tete, choisi = i["qjyrtof.gini"], i["sfxudug"]
    assert _verifie_en_tete(choisi.code, [Candidat(tete, 24.6), Candidat(choisi, 22.6)], ["SN-SE"], [],
                            "Indice de bien-être à Sédhiou") == choisi.code  # avant : l'indice de Gini


def test_morbidite_libelles_par_maladie():
    i = indicateurs()
    assert "tuberculose" in i["dipofde~detectes"].libelle_fr.lower()  # avant : « Paludisme, Tuberculose et VIH »
    assert "paludisme" in i["dipofde~enregistres"].libelle_fr.lower()
    assert "vih" in i["dipofde~depistes"].libelle_fr.lower()


# --- ratios, suggestions, périmètre --------------------------------------------------------------------

def test_un_ratio_n_est_jamais_calcule_ni_remplace_par_le_brut():
    assert ratio_non_publie("hfhored.medecin-generaliste", "Combien de médecins pour 10 000 habitants ?")
    assert ratio_non_publie("rgohtcc", "Quel est le PIB par habitant ?")
    assert not ratio_non_publie("smcofug.quotient-de-mortalite-infanto-juvenile",
                                "Mortalité des enfants pour 1 000 naissances")
    assert not ratio_non_publie("hfhored.medecin-generaliste", "Combien de médecins généralistes ?")
    r = demander("Combien de médecins pour 10 000 habitants ?")
    assert r.issue == "aucune" and r.motif == "hors_socle"


def test_suggestions_sans_phrase_en_double(monkeypatch):
    """Trois codes du salaire moyen donnaient trois fois « Quel est le salaire moyen au Sénégal ? »."""
    from gestukaay_contracts.models import RefIndicateur, Suggestion
    from gestukaay_engine import refus

    def meme_phrase(socle, code, zone):
        return Suggestion(indicateur=RefIndicateur(code=code, libelle="Salaire moyen"),
                          question_suggeree="Quel est le salaire moyen au Sénégal ?")
    monkeypatch.setattr(refus, "verifier_suggestion", meme_phrase)
    i = indicateurs()
    c = Comprise(RequeteStructuree(intention="hors_perimetre", confiance=0.3), [], "regles",
                 proches=[Candidat(i["muhgux.salaire-moyen-mensuel"], 9), Candidat(i["muhgux.taux-de-chomage"], 8)])
    textes = [s.question_suggeree for s in obtenir_suggestions(SOCLE, c, "SN")]
    assert textes == ["Quel est le salaire moyen au Sénégal ?"]


def test_note_menages_agricoles():
    from gestukaay_contracts.models import PeriodeResolue, RefIndicateur, RefZone, Resultat, Source
    r = Resultat(indicateur=RefIndicateur(code="deuqmkd.taux-dalphabetisation-des-membres-%", libelle="x"),
                 zone=RefZone(code="SN", libelle="Sénégal", niveau="pays"),
                 periode=PeriodeResolue(valeur="2024", libelle="2024"), valeur=45.3, valeur_affichee="45,3",
                 unite="%", source=Source(producteur="DAPSA", operation="EAA", titre="t", date_publication=date(2023, 12, 5),
                                          licence="", url="", libelle="l"), observation_id="x")
    assert note_perimetre(r) == NOTE_MENAGES_AGRICOLES


# --- wolof, lieux, approchées ---------------------------------------------------------------------------

def test_jigeen_ju_est_une_femme_pas_une_desagregation():
    assert "sexe" not in desagregation_citee("Ñaata doom la jigéen ju nekk ci Senegaal di am ?")
    assert desagregation_citee("Ñaata jigéen ñoo amul ligéey ?") == {"sexe": "femmes"}


def test_ville_de_dakar_rattachee_au_departement_puis_a_la_region():
    assert rattachements()["ville de dakar"].propositions == ("SN-DK-DAKAR", "SN-DK")
    assert rattachements()["ville de thies"].propositions[-1] == "SN-TH"  # la ligne déclarée prime
    r = demander("Population de la ville de Dakar")
    assert r.issue == "approchee" and r.choix[0].requete.zones == ["SN-DK"]


def test_graphies_de_saint_louis():
    for q in ("Combien d'habitants à Sant Louis ?", "Population de St-Louis"):
        assert zones_citees(q) == ["SN-SL"] and lieux_inconnus(q) == [], q
    assert demander("Combien d'habitants à Sant Louis ?").issue == "exacte"


def test_precision_non_publiee_pour_la_zone_donne_une_approchee():
    req = RequeteStructuree(intention="valeur", indicateur="jcvcajc.taux-de-pauvrete", zones=["SN-KA"],
                            desagregation={"milieu": "rural"}, confiance=0.9)
    r = resoudre(SOCLE, req, "fr")
    assert isinstance(r, Introuvable) and r.raison == "desagregation_absente"
    a = proposer_approchee(SOCLE, req, r, "taux de pauvreté rural à Kaffrine")
    assert isinstance(a, Approchee)
    assert [(c.requete.zones, c.requete.desagregation) for c in a.choix] == [(["SN-KA"], None),
                                                                           (["SN"], {"milieu": "rural"})]


# --- finitions --------------------------------------------------------------------------------------------

def test_unites_lisibles_dans_la_phrase():
    from gestukaay_engine.gabarits import avec_unite
    assert avec_unite("1 398", "En millions (U)") == "1 398 millions"
    assert avec_unite("445 313", "Individu") == "445 313"  # un simple compte
    assert avec_unite("26 990", "tonne") == "26 990 tonnes"
    assert avec_unite("1", "tonne") == "1 tonne"
    assert avec_unite("20,4", "%").endswith("%")


def test_evolution_sans_annee_de_la_premiere_a_la_derniere_periode():
    socle = Socle([obs("jcvcajc.taux-de-pauvrete", "SN", p, v, **{"milieu-de-résidence": "Ensemble"})
                   for p, v in (("2011", 46.7), ("2018", 37.8), ("2022", 37.5))], SOURCES, "test")
    req = RequeteStructuree(intention="comparaison", indicateur="jcvcajc.taux-de-pauvrete", zones=[], confiance=0.9)
    r = resoudre(socle, req, "fr", "Évolution du taux de pauvreté")
    assert [x.periode.valeur for x in r.resultats] == ["2011", "2022"]


def test_zone_non_publiee_servie_par_la_meme_notion(monkeypatch):
    """Benchmark LLM du 09/10 (FR-049, WO-021) : « riz brisé » n'est publié que pour Dakar ; le riz à Thiès
    finissait en « donnée absente » alors que le prix de détail du riz est publié par région."""
    i = indicateurs()
    socle_riz = Socle([
        obs("feujxob.riz-brise-ordinaire-au-detail", "SN-DK", "2026-03", 309.0),
        obs("sbsryhc", "SN-TH", "2023", 391.1, **{"type-de-céréales": "Riz"}),
        obs("sbsryhc", "SN-TH", "2023", 300.0, **{"type-de-céréales": "Mil"}),
    ], {d: SourceJeu(d, "ANSD", "Agence", f"Jeu {d}", date(2023, 10, 31), "", f"https://x/{d}")
        for d in ("feujxob", "sbsryhc")}, "test")
    moteur = MoteurReel(socle_riz, Comprehension(None))
    choisi = RequeteStructuree(intention="valeur", indicateur="feujxob.riz-brise-ordinaire-au-detail",
                               zones=["SN-TH"], periode={"type": "derniere"}, desagregation={"produit": "riz"},
                               confiance=0.4)
    cands = [Candidat(i["feujxob.riz-brise-ordinaire-au-detail"], 9), Candidat(i["sbsryhc"], 8)]
    monkeypatch.setattr(moteur.comprehension, "comprendre", lambda q, ctx=None: Comprise(choisi, cands, "regles"))
    r = moteur.repondre(AskRequest(question="Combien coûte le riz à Thiès ?")).reponse
    assert r.issue == "exacte" and r.resultats[0].valeur == 391.1
