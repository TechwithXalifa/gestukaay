"""Gabarits de réponse en français : explication, note de périmètre, citation (issue #16, décision 0014).

Aucun LLM : des phrases à trous, remplies avec des valeurs du socle. Rien n'est calculé, sauf
la mise en forme (arrondi d'affichage, signalé) et la comparaison de deux valeurs publiées.

  - phrase principale : naturelle pour les indicateurs P1 (`gabarits_fr.csv`, écrits à la main),
    neutre pour les autres (« Taux d'urbanisation dans la région de Dakar en 2023 : 97,2 %. ») ;
  - position relative (§5.4) : une valeur régionale est comparée à la valeur nationale publiée
    pour la même période (seulement pour les taux, prix, moyennes : pas pour les effectifs) ;
  - notes : projection ou estimation (avec sa base), arrondi d'affichage.
  1 à 3 phrases au total. Nombres : espace fine insécable, virgule décimale (§7.4).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

from gestukaay_contracts.models import Resultat
from gestukaay_socle.indicateurs import Indicateur, indicateurs
from gestukaay_socle.zones import normaliser, zones

FICHIER_GABARITS = Path(__file__).with_name("gabarits_fr.csv")
FINE = " "  # espace fine insécable : séparateur de milliers, avant % et ‰
INSECABLE = " "  # entre un nombre et son unité en toutes lettres
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]


# --------------------------------------------------------------------------
# Nombres
# --------------------------------------------------------------------------

def decimales_max(unite: str, valeur: float) -> int:
    """Décimales affichées au plus, selon l'unité (décision 0014)."""
    u = normaliser(unite)
    if abs(valeur) < 1 and valeur != 0:
        return 2  # Gini 0,35 ; ratios
    if any(m in u for m in ("fcfa", "tonne", "habitant", "personne", "vehicule", "arrivee", "nombre",
                            "million", "milliard", "menage", "eleve")):
        return 0
    return 1  # %, ‰, pour 1 000, ans, enfants par femme, indices…


def _decimales(valeur: float) -> int:
    texte = repr(float(valeur))
    return 0 if texte.endswith(".0") or "e" in texte else len(texte.split(".")[1])


def formater(valeur: float, unite: str = "") -> tuple[str, bool]:
    """(« 2 463 677 », arrondi ?) : jamais plus de décimales que publiées, jamais plus que la règle."""
    d = min(_decimales(valeur), decimales_max(unite, valeur))
    texte = f"{valeur:,.{d}f}".replace(",", FINE).replace(".", ",")
    return texte, _decimales(valeur) > d


def avec_unite(nombre: str, unite: str) -> str:
    if not unite:
        return nombre
    if unite in ("%", "‰"):
        return f"{nombre}{FINE}{unite}"
    return f"{nombre}{INSECABLE}{unite}"


# --------------------------------------------------------------------------
# Zones et périodes en toutes lettres
# --------------------------------------------------------------------------

def _de(nom: str) -> str:
    return f"d'{nom}" if normaliser(nom)[:1] in "aeiouy" else f"de {nom}"


def zone_en_lettres(code: str) -> dict[str, str]:
    """{dans, sujet, de} : « dans la région de Thiès », « La région de Thiès », « de la région de Thiès »."""
    z = zones()[code]
    nom = z.libelle_fr
    if z.niveau == "pays":
        return {"dans": f"au {nom}", "sujet": f"Le {nom}", "de": f"du {nom}"}
    groupe = {"region": "la région", "departement": "le département", "academie": "l'académie"}.get(
        z.niveau, "la zone")
    base = f"{groupe} {_de(nom)}"
    de = f"de {base}" if not base.startswith("le ") else f"du {base[3:]}"
    return {"dans": f"dans {base}", "sujet": base[0].upper() + base[1:], "de": de}


def periode_en_lettres(p: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return f"en {MOIS[int(p[5:7]) - 1]} {p[:4]}"
    if re.fullmatch(r"\d{4}-T[1-4]", p):
        return f"au {p[-1]}{'er' if p[-1] == '1' else 'e'} trimestre {p[:4]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
        return f"le {int(p[8:])} {MOIS[int(p[5:7]) - 1]} {p[:4]}"
    return f"en {p}"


def date_en_lettres(d: date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


# --------------------------------------------------------------------------
# Gabarits
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Gabarit:
    phrase: str  # trous : {valeur} {nombre} {zone_dans} {zone_sujet} {zone_de} {periode} {precisions} {d[dimension]}
    comparer_au_national: bool


NEUTRE = "{libelle}{precisions} {zone_dans} {periode} : {valeur}."
_EFFECTIFS = ("habitant", "personne", "tonne", "vehicule", "arrivee", "nombre", "million", "milliard")


@cache
def gabarits() -> dict[str, Gabarit]:
    with FICHIER_GABARITS.open(encoding="utf-8") as f:
        return {r["code"]: Gabarit(r["gabarit"], r["comparer_au_national"] == "oui")
                for r in csv.DictReader(f, delimiter=";")}


def gabarit(ind: Indicateur) -> Gabarit:
    """Le gabarit P1 écrit à la main, sinon la forme neutre. Pour la forme neutre, on ne compare au
    national que les taux, prix et moyennes : un effectif régional est toujours plus petit."""
    if ind.code in gabarits():
        return gabarits()[ind.code]
    unite = normaliser(ind.unite_affichee or ind.unite)
    return Gabarit(NEUTRE, bool(unite) and not any(m in unite for m in _EFFECTIFS))


class _Modalites(dict):
    def __missing__(self, cle):  # {d[prix-pib]} absent : rien plutôt qu'une erreur
        return ""


def precisions(r: Resultat, sauf: set[str] = frozenset()) -> str:
    """« (Féminin ; 15-24 ans) » : modalités non totales, sauf celles que le gabarit nomme déjà."""
    valeurs = [v for k, v in (r.desagregation or {}).items() if k not in sauf]
    return f" ({' ; '.join(valeurs)})" if valeurs else ""


def phrase_principale(r: Resultat, ind: Indicateur, derniere: bool) -> tuple[str, bool]:
    nombre, arrondi = formater(r.valeur, r.unite)
    z = zone_en_lettres(r.zone.code)
    periode = periode_en_lettres(r.periode.valeur) + (", dernière donnée publiée" if derniere else "")
    phrase = gabarit(ind).phrase
    nommees = set(re.findall(r"\{d\[([^\]]+)\]\}", phrase))  # {d[prix-pib]} : modalité citée par le gabarit
    texte = phrase.format(
        valeur=avec_unite(nombre, r.unite), nombre=nombre, libelle=ind.libelle_fr,
        precisions=precisions(r, nommees), d=_Modalites(r.desagregation or {}),
        zone_dans=z["dans"], zone_sujet=z["sujet"], zone_de=z["de"], periode=periode)
    return texte[0].upper() + texte[1:], arrondi


def position_relative(r: Resultat, national: Resultat | None) -> str | None:
    """« C'est moins que la valeur nationale (20,4 % en 2025). » — deux valeurs publiées comparées."""
    if national is None or r.zone.code == "SN" or national.periode.valeur != r.periode.valeur:
        return None
    nombre, _ = formater(national.valeur, national.unite)
    rapport = "plus que" if r.valeur > national.valeur else "moins que" if r.valeur < national.valeur \
        else "autant que"
    return (f"C'est {rapport} la valeur nationale ({avec_unite(nombre, national.unite)} "
            f"{periode_en_lettres(national.periode.valeur)}).")


def notes(r: Resultat, arrondi: bool) -> str | None:
    morceaux = []
    if r.nature == "projection":
        morceaux.append(f"il s'agit d'une projection officielle ({r.source.producteur}"
                        + (f", {r.base_projection})" if r.base_projection else ")"))
    elif r.nature == "estimation":
        morceaux.append("il s'agit d'une estimation" + (f" ({r.base_projection})" if r.base_projection else ""))
    if arrondi:
        morceaux.append("valeur arrondie à l'affichage, la valeur exacte figure dans les exports")
    if not morceaux:
        return None
    texte = " ; ".join(morceaux)
    return texte[0].upper() + texte[1:] + "."


def explication(resultats: list[Resultat], derniere: bool = False,
                nationaux: dict[str, Resultat] | None = None) -> str:
    """1 à 3 phrases. `nationaux` : valeur nationale publiée de chaque indicateur, même période."""
    nationaux = nationaux or {}
    r = resultats[0]
    ind = indicateurs()[r.indicateur.code]
    if len(resultats) == 1:
        principale, arrondi = phrase_principale(r, ind, derniere)
        phrases = [principale]
        if gabarit(ind).comparer_au_national:
            phrases.append(position_relative(r, nationaux.get(ind.code)))
        phrases.append(notes(r, arrondi))
        return " ".join(p for p in phrases if p)
    return comparaison(resultats, ind)


def comparaison(resultats: list[Resultat], ind: Indicateur) -> str:
    """« Taux de chômage en 2025 : 13,2 % dans la région de Dakar, 22,7 % dans la région de Thiès. »"""
    arrondi = False
    morceaux = []
    memes_periodes = len({r.periode.valeur for r in resultats}) == 1
    for r in resultats:
        nombre, a = formater(r.valeur, r.unite)
        arrondi |= a
        morceau = f"{avec_unite(nombre, r.unite)} {zone_en_lettres(r.zone.code)['dans']}"
        morceaux.append(morceau if memes_periodes else f"{morceau} {periode_en_lettres(r.periode.valeur)}")
    tete = ind.libelle_fr + precisions(resultats[0])
    if memes_periodes:
        tete += " " + periode_en_lettres(resultats[0].periode.valeur)
    phrases = [f"{tete} : {', '.join(morceaux[:-1])} et {morceaux[-1]}."]
    haut = max(resultats, key=lambda r: r.valeur)
    if sum(r.valeur == haut.valeur for r in resultats) == 1:
        phrases.append(f"La valeur la plus élevée est celle {zone_en_lettres(haut.zone.code)['de']}.")
    phrases.append(notes(resultats[0], arrondi))
    return " ".join(p for p in phrases if p)


# --------------------------------------------------------------------------
# Note de périmètre et citation
# --------------------------------------------------------------------------

@cache
def _notes_de_jeux() -> dict[str, str]:
    """Jeux dont la zone est déclarée (prix relevés à Dakar…) : leur note devient la note de périmètre."""
    from gestukaay_socle.extraction import FICHIER_ZONES_PAR_JEU
    with FICHIER_ZONES_PAR_JEU.open(encoding="utf-8") as f:
        return {r["dataset_id"]: r["note"] for r in csv.DictReader(f, delimiter=";")
                if r["zone"] != "SN" and r["note"]}


def note_perimetre(r: Resultat) -> str | None:
    ind = indicateurs()[r.indicateur.code]
    if note := _notes_de_jeux().get(ind.dataset_id):
        return note.split(" (")[0] + "."
    return {"region": "Région administrative, pas la ville.",
            "departement": "Département, pas la commune.",
            "academie": "Inspection d'académie, pas la région administrative."}.get(r.zone.niveau)


def citation(r: Resultat, consulte_le: date, url: str) -> str:
    """EF-35 : Source : ANSD, [opération] ([année]), publié le [date]. Consulté via Gëstukaay le [date], [URL].
    L'URL est provisoire : le backend la remplace par l'adresse stable de la réponse (/r/…)."""
    s = r.source
    operation = s.operation or s.titre
    return (f"Source : {s.producteur}, {operation} ({r.periode.valeur[:4]}), publié le "
            f"{date_en_lettres(s.date_publication)}. Consulté via Gëstukaay le {date_en_lettres(consulte_le)}, {url}.")
