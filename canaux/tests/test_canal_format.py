"""Mise en forme d'une réponse pour WhatsApp et Telegram (#33, #34)."""

from pathlib import Path

from gestukaay_canaux.format import formater
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
    for c in r.reponse.choix:
        assert f"{c.id}) {c.libelle}" in s.texte
    assert [c.id for c in s.choix] == [c.id for c in r.reponse.choix]
    assert "Tontul ak lim (numéro) bi nga tànn." in s.texte  # « choisir », wolof de KBD


def test_refus_message_suggestions_mention():
    r = rep("aucune_hors_socle")
    s = formater(r)
    assert s.texte.startswith(r.reponse.message) and s.texte.endswith("— gestukaay") and not s.choix
    for x in r.reponse.suggestions:
        assert f"• {x.question_suggeree}" in s.texte
