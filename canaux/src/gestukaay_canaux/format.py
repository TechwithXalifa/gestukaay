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
