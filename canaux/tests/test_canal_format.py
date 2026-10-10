"""Mise en forme d'une réponse pour WhatsApp et Telegram (#33, #34)."""

from pathlib import Path

from gestukaay_canaux.format import CHIFFRES, _commun, formater
from gestukaay_contracts.models import AskResponse

EXEMPLES = Path(__file__).parents[2] / "contracts" / "examples"


def rep(nom: str) -> AskResponse:
    return AskResponse.model_validate_json((EXEMPLES / f"{nom}.json").read_text(encoding="utf-8"))


def test_reponse_exacte_chiffre_explication_source_lien_mention():
    r = rep("exacte_valeur")
    lignes = formater(r).texte.split("\n")
    x = r.reponse.resultats[0]
    assert lignes[0] == f"*{x.valeur_affichee} {x.unite}*"
    assert lignes[1] == r.reponse.explication
    assert f"Source : {x.source.libelle}" in lignes and r.reponse.url in lignes
    assert lignes[-1] == "— gestukaay"
    assert not formater(r, gras=False).texte.startswith("*")  # Telegram : texte brut


def test_comparaison_sans_ligne_de_chiffre_isolee():
    r = rep("exacte_comparaison")
    assert formater(r).texte.split("\n")[0] == r.reponse.explication


def test_approchee_choix_numerotes_et_proposes():
    r = rep("approchee")
    s = formater(r)
    for c in s.choix:  # #214 : numéros emoji, choix courts (le contexte commun est dit une fois en tête)
        assert f"{CHIFFRES[c.id]} {c.libelle}" in s.texte
    assert [c.id for c in s.choix] == [c.id for c in r.reponse.choix]
    assert "Tontul ak lim (numéro) bi nga tànn." in s.texte  # « choisir », wolof de KBD


def test_choix_courts_contexte_une_fois():  # #214
    tete, courts = _commun(["Taux de pauvreté - Région de Kolda en 2011", "Taux de pauvreté - Région de Kolda en 2019"])
    assert tete == "Taux de pauvreté - Région de Kolda" and courts == ["en 2011", "en 2019"]
    assert _commun(["Pêche artisanale, par région", "Pêche continentale, par région"])[0] == ""
    libelles = ["Taux brut de scolarisation", "Taux net de scolarisation"]  # différents dès le 2e mot (revue de SAN)
    assert _commun(libelles) == ("", libelles)
    assert _commun(["Population (2023) - Région de Thiès (2023)", "Population (2023) - Sénégal (2023)"])[1] == [
        "Région de Thiès (2023)", "Sénégal (2023)"]


def test_refus_message_suggestions_mention():
    r = rep("aucune_hors_socle")
    s = formater(r)
    assert s.texte.startswith(r.reponse.message) and s.texte.endswith("— gestukaay") and not s.choix
    for x in r.reponse.suggestions:
        assert f"• {x.question_suggeree}" in s.texte


def test_pas_de_lien_vers_localhost():  # #228 : sur un téléphone, http://localhost:3000/r/… n'ouvre rien
    r = rep("exacte_valeur")
    public = formater(r).texte
    assert r.reponse.url in public
    local = r.model_copy(update={"reponse": r.reponse.model_copy(update={"url": "http://localhost:3000/r/abc"})})
    texte = formater(local).texte
    assert "localhost" not in texte and texte.endswith("— gestukaay")
