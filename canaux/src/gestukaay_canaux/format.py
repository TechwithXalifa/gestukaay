"""Mise en forme d'une réponse du moteur pour une messagerie (#33, #34, décision 0025).

Texte seul, aucun fichier (EF-20) : le chiffre, l'explication (libellé, zone, période), la source et
sa date, la note de périmètre, le lien de la réponse et la mention gestukaay (EF-23, EF-25). Rien
n'est recalculé : chaque nombre vient de la réponse du moteur.

`gras` : WhatsApp met en gras entre astérisques ; Telegram reçoit du texte brut.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gestukaay_contracts.models import (
    AskResponse,
    Choix,
    ReponseApprochee,
    ReponseAucune,
    ReponseExacte,
)
from gestukaay_engine.gabarits import avec_unite

from .textes import texte

MENTION = "— gestukaay"


@dataclass
class Sortant:
    texte: str
    choix: list[Choix] = field(default_factory=list)  # approchée : à proposer en liste / boutons


def formater(rep: AskResponse, gras: bool = True) -> Sortant:
    r = rep.reponse
    if isinstance(r, ReponseExacte):
        return Sortant(_exacte(r, gras))
    if isinstance(r, ReponseApprochee):
        lignes = [r.reformulation, "", *(f"{c.id}) {c.libelle}" for c in r.choix), "", texte("choisir")]
        return Sortant("\n".join(lignes), list(r.choix))
    return Sortant(_aucune(r))


def _exacte(r: ReponseExacte, gras: bool) -> str:
    lignes = []
    if r.intention == "valeur":  # le chiffre d'abord ; un taux compagnon (0024) est dans l'explication
        x = r.resultats[0]
        chiffre = avec_unite(x.valeur_affichee, x.unite)
        lignes.append(f"*{chiffre}*" if gras else chiffre)
    lignes.append(r.explication)
    if r.note_perimetre:
        lignes.append(r.note_perimetre)
    lignes += [f"Source : {r.resultats[0].source.libelle}", r.url, MENTION]
    return "\n".join(lignes)


def _aucune(r: ReponseAucune) -> str:
    lignes = [r.message, *(f"• {s.question_suggeree}" for s in r.suggestions)]
    return "\n".join([*lignes, MENTION])


def fiche(rep: AskResponse, gras: bool = True) -> str | None:
    """Ce qui accompagne une note vocale (choix de KBD, 07/10) : le chiffre exact, l'indicateur, la zone, la
    période et la source sur une ligne, puis le lien de la réponse et la mention gestukaay. C'est souvent ce
    message qu'on transfère : il doit se suffire (P1 étape 5, US-14, revue de SAN sur #146).
    Approchée : rien (les choix suivent) ; refus : les suggestions s'il y en a."""
    r = rep.reponse
    if isinstance(r, ReponseExacte):
        res = r.resultats
        if r.intention == "valeur":
            x = res[0]
            chiffre = avec_unite(x.valeur_affichee, x.unite)
            corps = (f"{f'*{chiffre}*' if gras else chiffre} · {x.indicateur.libelle} · {x.zone.libelle}"
                     f" · {x.periode.libelle}")
        else:  # comparaison, classement : l'indicateur, les trois premiers, la période commune
            corps = f"{res[0].indicateur.libelle} : " + " · ".join(
                f"{x.zone.libelle} {avec_unite(x.valeur_affichee, x.unite)}" for x in res[:3])
            corps += f" ({res[0].periode.libelle})"
        return "\n".join([f"{corps} — Source : {res[0].source.libelle}", r.url, MENTION])
    if isinstance(r, ReponseAucune) and r.suggestions:
        return "\n".join([*(f"• {s.question_suggeree}" for s in r.suggestions), MENTION])
    return None
