"""Mise en forme d'une réponse du moteur pour une messagerie (#33, #34, décision 0025).

Texte seul, aucun fichier (EF-20) : le chiffre, l'explication (libellé, zone, période), la source et
sa date, la note de périmètre, le lien de la réponse et la mention gestukaay (EF-23, EF-25). Rien
n'est recalculé : chaque nombre vient de la réponse du moteur.

`gras` : WhatsApp met en gras entre astérisques ; Telegram reçoit du texte brut.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

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
_LOCALES = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _lien(url: str) -> list[str]:
    """Le lien de la réponse, sauf s'il pointe vers la machine elle-même (#228 : GESTUKAAY_URL_PUBLIQUE par défaut,
    « http://localhost:3000/r/… » n'ouvre rien sur un téléphone, ou ouvre un autre site)."""
    return [] if not url or urlsplit(url).hostname in _LOCALES else [url]


@dataclass
class Sortant:
    texte: str
    choix: list[Choix] = field(default_factory=list)  # approchée : à proposer en liste / boutons


def formater(rep: AskResponse, gras: bool = True) -> Sortant:
    r = rep.reponse
    if isinstance(r, ReponseExacte):
        return Sortant(_exacte(r, gras))
    if isinstance(r, ReponseApprochee):
        return _approchee(r, gras)
    return Sortant(_aucune(r))


CHIFFRES = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣"}


def _commun(libelles: list[str]) -> tuple[str, list[str]]:
    """Le contexte commun à tous les choix, dit une fois en tête, et ce qui les distingue (#214 :
    « Taux de pauvreté - Région de Kolda en 2011 / 2019 / 2022 » -> « 2011 », « 2019 », « 2022 »)."""
    if len(libelles) < 2:
        return "", libelles
    mots_ = [x.split() for x in libelles]
    n = 0
    while all(len(m) > n + 1 for m in mots_) and len({m[n] for m in mots_}) == 1:
        n += 1
    while n and mots_[0][n - 1].lower() in _LIENS:  # « … d'académie de » : « de Dakar » reste dans le choix
        n -= 1
    if n < 2:  # rien de commun qui vaille d'être sorti
        return "", libelles
    tete = " ".join(mots_[0][:n]).rstrip(" -–:(").strip()
    return tete, [" ".join(m[n:]).lstrip(" -–:").strip() or " ".join(m) for m in mots_]


_LIENS = {"de", "du", "des", "d'", "en", "à", "a", "la", "le", "les", "l'", "au", "aux", "-", "–", "par"}


def _approchee(r: ReponseApprochee, gras: bool) -> Sortant:
    """Un seul message (#213, #214) : la reformulation, le contexte commun une fois, des choix courts
    numérotés, puis la consigne ; les boutons ou la liste reprennent les mêmes choix courts."""
    tete, courts = _commun([c.libelle for c in r.choix])
    choix = [c.model_copy(update={"libelle": court}) for c, court in zip(r.choix, courts, strict=True)]
    lignes = [f"🔎 {r.reformulation}"]
    if tete:
        lignes.append(f"*{tete}*" if gras else tete)
    lignes += ["", *(f"{CHIFFRES.get(c.id, c.id + ')')} {c.libelle}" for c in choix), "", f"👉 {texte('choisir', r.langue)}"]
    return Sortant("\n".join(lignes), choix)


def _exacte(r: ReponseExacte, gras: bool) -> str:
    lignes = []
    if r.intention == "valeur":  # le chiffre d'abord ; un taux compagnon (0024) est dans l'explication
        x = r.resultats[0]
        chiffre = avec_unite(x.valeur_affichee, x.unite)
        lignes.append(f"*{chiffre}*" if gras else chiffre)
    lignes.append(r.explication)
    if r.note_perimetre:
        lignes.append(r.note_perimetre)
    lignes += [f"Source : {r.resultats[0].source.libelle}", *_lien(r.url), MENTION]
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
        return "\n".join([f"{corps} — Source : {res[0].source.libelle}", *_lien(r.url), MENTION])
    if isinstance(r, ReponseAucune) and r.suggestions:
        return "\n".join([*(f"• {s.question_suggeree}" for s in r.suggestions), MENTION])
    return None
