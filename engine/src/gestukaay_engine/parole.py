"""Texte wolof lu par la voix de réponse (#29, décision 0029) : jamais généré, toujours composé.

Tout le wolof vient de KBD (décision 0009) : les phrases à trous de `gabarits_wo.csv` et les mots de
`parole_wo.csv` (zones, périodes, sources, unités), écrits avec lui le 5 et le 6 octobre 2026. Ce
module ne fait que remplir les trous :

- `{chiffre}` : la valeur **affichée** (jamais recalculée), dite selon les règles de KBD : « ak »
  entre les groupes, « fanweer » pour 30, « benn milyoŋ », « wirgil » pour la virgule, « … ci
  téeméer » pour un pourcentage ; l'argent se compte en dërëm (5 FCFA) sous le million, le mot
  « dërëm » n'étant dit que sous 100 FCFA ; un montant qui n'est pas un multiple de 5 se dit en
  CFA suivi de « sefaa » ; au-delà du million, en CFA ; devant un nom, le dernier mot du nombre
  prend -i (« juróom-ñaari nit », « junniy ton ») ;
- `{periode}` : les années se disent en français (« ci atum deux mille vingt-trois ») ;
- `{zone}` porte sa préposition (« ci diiwaanu Cees »), `{nom_zone}` non (« diiwaanu Cees ») ;
- `{source}` : les sigles s'épellent à la française (« A-EN-ES-DE »).

Une note fait 20 s au plus (#30) : on prend la variante la plus courte, puis on retire la source
(elle reste dans le texte écrit), « dernière donnée publiée », enfin la comparaison au national.
"""

from __future__ import annotations

import csv
import re
import unicodedata
import zlib
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path

from gestukaay_contracts.models import (
    AskResponse,
    ReponseApprochee,
    ReponseAucune,
    ReponseExacte,
    Resultat,
)
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import zones

from .compagnons import compagnons
from .gabarits import avec_unite, formater
from .gabarits import gabarit as gabarit_fr
from .resolution import national
from .socle import Socle

ICI = Path(__file__).resolve().parent
DUREE_MAX_S = 20.0  # #30 : une note de réponse dure 20 s au plus
CARACTERES_PAR_S = 16.0  # débit d'Oolel mesuré sur les phrases de KBD (13 à 18 caractères par seconde)
PAUSE_DEUX_POINTS_S, PAUSE_PHRASE_S = 0.6, 0.3  # silences insérés à la synthèse (choix KBD)

# ---------------------------------------------------------------------------
# Données de KBD
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GabaritWo:
    cle: str
    indicateurs: tuple[str, ...]
    chiffre: str  # « nombre » : le gabarit écrit le nom après {chiffre} ; « avec_unite » sinon
    selon_unite: bool  # 2 variantes : la 1re pour les taux, prix, indices ; la 2e pour les effectifs
    variantes: tuple[str, ...]


@cache
def gabarits_wo() -> dict[str, GabaritWo]:
    with (ICI / "gabarits_wo.csv").open(encoding="utf-8") as f:
        return {r["cle"]: GabaritWo(r["cle"], tuple(x for x in r["indicateurs"].split("|") if x), r["chiffre"],
                                    r["variantes"] == "selon_unite", tuple(r["wolof"].split("|")))
                for r in csv.DictReader(f, delimiter=";")}


@cache
def _parole() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with (ICI / "parole_wo.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out.setdefault(r["type"], {})[r["cle"]] = r["wolof"]
    return out


def _sans_accent(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


# ---------------------------------------------------------------------------
# Nombres (règles de KBD, lexique_wolof/1_nombres.csv et voix_wolof/2_nombres_argent_unites.csv)
# ---------------------------------------------------------------------------

UNITES = {1: "benn", 2: "ñaar", 3: "ñett", 4: "ñeent", 5: "juróom", 6: "juróom-benn", 7: "juróom-ñaar",
          8: "juróom-ñett", 9: "juróom-ñeent"}


def suffixe(t: str) -> str:
    """-i sur le dernier mot (-y après un i) : devant un nom ou devant téeméer, junni, milyoŋ."""
    return t + ("y" if t.endswith("i") else "i")


def _dizaine(d: int) -> str:
    return "fukk" if d == 1 else "fanweer" if d == 3 else f"{UNITES[d]}-fukk"


def _moins_de_mille(n: int) -> str:
    c, d, u = n // 100, (n // 10) % 10, n % 10
    morceaux = []
    if c:
        morceaux.append("téeméer" if c == 1 else f"{suffixe(UNITES[c])} téeméer")
    if d:
        morceaux.append(_dizaine(d))
    if u:
        morceaux.append(UNITES[u])
    return " ak ".join(morceaux)


def _groupe(n: int, nom: str) -> str:
    if n == 1:
        return "junni" if nom == "junni" else f"benn {nom}"  # « junni », mais « benn milyoŋ »
    # 21 295 milliards : le nombre de milliards dépasse 999, il se dit lui-même en entier
    return f"{suffixe(_moins_de_mille(n) if n < 1000 else entier_wo(n))} {nom}"


def entier_wo(n: int) -> str:
    """2463677 -> « ñaari milyoŋ ak ñeenti téeméer ak juróom-benn-fukk ak ñetti junni ak … »."""
    if n == 0:
        return "tus"
    morceaux = []
    for taille, nom in ((10**9, "milyaar"), (10**6, "milyoŋ"), (1000, "junni")):
        if n >= taille:
            morceaux.append(_groupe(n // taille, nom))
            n %= taille
    if n:
        morceaux.append(_moins_de_mille(n))
    return " ak ".join(morceaux)


def nombre_wo(entier: int, decimales: str = "") -> str:
    """« 13 », « 2 » -> « fukk ak ñett wirgil ñaar » ; les zéros de tête après la virgule sont dits."""
    if not decimales or not int(decimales):
        return entier_wo(entier)
    zeros = len(decimales) - len(decimales.lstrip("0"))
    apres = " ".join(["tus"] * zeros + [entier_wo(int(decimales))])
    return f"{entier_wo(entier)} wirgil {apres}"


def argent_wo(n: int) -> str:
    """Montant en FCFA (règle de KBD) : dërëm sous le million, CFA au-delà."""
    if n >= 10**6:
        return entier_wo(n)  # « benn milyoŋ », « ñaari milyoŋ ak … » (sans « sefaa »)
    if n % 5:
        return f"{suffixe(entier_wo(n))} sefaa"  # 1 234 -> « … ñeenti sefaa »
    d = n // 5
    if n < 100:  # « dërëm » n'est dit que sous 100 FCFA
        return "dërëm" if d == 1 else f"{suffixe(entier_wo(d))} dërëm"
    return entier_wo(d)


_FR = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze",
       "treize", "quatorze", "quinze", "seize"]
_FR_DIZ = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"}


def _fr_moins_de_cent(n: int) -> str:
    if n < 17:
        return _FR[n]
    if n < 20:
        return f"dix-{_FR[n - 10]}"
    d, u = n // 10, n % 10
    if d in (7, 9):
        base = "soixante" if d == 7 else "quatre-vingt"
        return f"{base}-{_fr_moins_de_cent(10 + u)}" if not (d == 7 and u == 1) else "soixante et onze"
    if d == 8:
        return "quatre-vingts" if u == 0 else f"quatre-vingt-{_FR[u]}"
    if u == 0:
        return _FR_DIZ[d]
    return f"{_FR_DIZ[d]} et un" if u == 1 else f"{_FR_DIZ[d]}-{_FR[u]}"


def fr_entier(n: int) -> str:
    """Français, jusqu'à 9 999 : les années et les chiffres d'un sigle (« RGPH-5 »)."""
    if n < 100:
        return _fr_moins_de_cent(n)
    if n < 1000:
        c, r = divmod(n, 100)
        tete = "cent" if c == 1 else f"{_FR[c]} cent{'s' if r == 0 else ''}"
        return tete if r == 0 else f"{tete} {_fr_moins_de_cent(r)}"
    m, r = divmod(n, 1000)
    tete = "mille" if m == 1 else f"{_FR[m]} mille"
    return tete if r == 0 else f"{tete} {fr_entier(r)}"


# ---------------------------------------------------------------------------
# Chiffre, zone, période, source
# ---------------------------------------------------------------------------


def _affichee(r: Resultat) -> tuple[int, str]:
    """La valeur affichée (« 2 463 677 », « 13,2 ») : c'est elle qu'on dit, jamais r.valeur."""
    t = re.sub(r"[\s  ]", "", r.valeur_affichee).replace("−", "-")
    entier, _, dec = t.partition(",")
    return int(entier.lstrip("-") or 0), dec


def est_effectif(unite: str) -> bool:
    """Personnes, choses, montants totaux : « réy » / « néew » plutôt que « kawe » / « suufe »."""
    u = _sans_accent(unite)
    return any(m in u for m in ("habitant", "personne", "tonne", "vehicule", "arrivee", "nombre", "million",
                                "milliard", "menage", "individu", "tete", "visiteur"))


def _nom_unite(u: str) -> str | None:
    return next((wo for motif, wo in _parole()["unite_nom"].items() if re.search(rf"\b{motif}", u)), None)


# Réponse écrite en wolof (option B de KBD, 07/10) : les mêmes phrases que la voix, mais le chiffre et
# l'année tels qu'affichés, les sigles tels qu'écrits, sans limite de 20 s. Posé par `texte_ecrit`.
_ECRIT: ContextVar[bool] = ContextVar("ecrit", default=False)


def _chiffre_ecrit(r: Resultat, devant_nom: bool) -> str:
    """À l'écrit : le chiffre exact du site, du PDF et du CSV (7.4), avec les mots d'unité de KBD
    (« 2 463 677 nit », « 309 FCFA ci kilo bi ») ; sinon l'unité telle que publiée (« % », « tonnes »)."""
    v, u = r.valeur_affichee, _sans_accent(r.unite or "").strip()
    if devant_nom:
        return v
    if "%" in u or u in ("pour cent", "pourcent"):
        return avec_unite(v, "%")
    if re.search(r"fcfa|\bcfa\b|franc", u):
        monnaie = "milliards de FCFA" if "milliard" in u else "millions de FCFA" if "million" in u else "FCFA"
        par = next((wo for motif, wo in _parole()["argent_par"].items() if re.search(rf"\b{motif}", u)), None)
        return f"{v} {monnaie} {par}" if par else avec_unite(v, r.unite)
    nom = _nom_unite(u)
    return f"{v} {nom}" if nom else avec_unite(v, r.unite)


def chiffre_wo(r: Resultat, devant_nom: bool = False) -> str:
    """{chiffre} : la valeur affichée et son unité. `devant_nom` : le gabarit écrit lui-même le nom."""
    if _ECRIT.get():
        return _chiffre_ecrit(r, devant_nom)
    entier, dec = _affichee(r)
    u = _sans_accent(r.unite or "").strip()
    nombre = nombre_wo(entier, dec)
    if "%" in u or "pour cent" in u or "pourcent" in u:
        return f"{nombre} {_parole()['unite']['pourcent']}"
    if "‰" in (r.unite or "") or re.search(r"pour 1 ?000", u):
        return f"{nombre} {_parole()['unite']['pour_mille']}"
    if "$" in u or "dollar" in u or re.search(r"\bus\b", u):
        return f"{nombre} {r.unite}"  # devises étrangères : unité dite en français
    if re.search(r"fcfa|\bcfa\b|franc", u):
        # « millions de FCFA » : le vrai montant est dit, pas « … milyoŋ milyoŋ » (#130, option B de KBD)
        mult = 10**9 if "milliard" in u else 10**6 if "million" in u else \
            1000 if "millier" in u or re.search(r"\b1 ?000 ?fcfa", u) else 1
        total = Decimal(f"{entier}.{dec}" if dec else entier) * mult
        if total != total.to_integral_value():
            montant = f"{suffixe(nombre)} sefaa"  # centimes : en CFA, comme publié
        else:
            montant = argent_wo(int(total))
            if total >= 10**6:
                montant = f"{suffixe(montant)} CFA"  # au-delà du million, en CFA (0029) : dit à l'oral
        par = next((wo for motif, wo in _parole()["argent_par"].items() if re.search(rf"\b{motif}", u)), None)
        if par is None and "/" in (r.unite or ""):  # FCFA/Pièce… : pas de mot de KBD, dit en français
            par = "par " + r.unite.split("/", 1)[1].strip().lower()
        return f"{montant} {par}" if par else montant
    if devant_nom:
        return suffixe(nombre)
    nom = _nom_unite(u)
    if nom:
        return f"{suffixe(nombre)} {nom}"
    return f"{nombre} {r.unite}" if r.unite else nombre  # unité sans mot wolof : dite en français (Q1)


def nom_zone_wo(code: str) -> str:
    z = zones().get(code)
    if z is None:
        return code
    return z.libelle_wo if z.libelle_wo and z.statut_wo == "valide" else z.libelle_fr


def zone_wo(code: str, avec_ci: bool = True) -> str:
    z = zones().get(code)
    niveau = z.niveau if z else "region"
    forme = _parole()["zone"].get(niveau, "ci {nom}").format(nom=nom_zone_wo(code))
    return forme if avec_ci else forme.removeprefix("ci ")


def periode_wo(p: str) -> str:
    """« 2023 » -> « ci atum deux mille vingt-trois » ; « 2026-03 » ; « 2026-T1 »."""
    P = _parole()["periode"]
    annee = p[:4] if _ECRIT.get() else fr_entier(int(p[:4]))  # à l'écrit : « ci atum 2023 »
    if re.fullmatch(r"\d{4}-T[1-4]", p):
        return P[f"T{p[-1]}"].format(annee=annee)
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return P["mois"].format(mois=_parole()["mois"][p[5:7]], annee=annee)
    return P["annee"].format(annee=annee)


def epeler(sigle: str) -> str:
    """« ANSD » -> « A-EN-ES-DE », « RGPH-5 » -> « ER-JÉ-PÉ-ACH cinq » (KBD : comme en français)."""
    lettres, _, chiffres = sigle.partition("-")
    t = "-".join(_parole()["lettre"][c] for c in lettres.upper() if c in _parole()["lettre"])
    return f"{t} {fr_entier(int(chiffres))}" if chiffres.isdigit() else t


def _sigles(texte: str) -> str:
    """Épelle les sigles connus (`parole_wo.csv`, type sigle) ; les autres mots en majuscules
    (« PRODUIT INTERIEUR BRUT ») sont lus comme des mots, en minuscules. BADIS, MITTA : tels quels."""
    sigles, mots = _parole()["sigle"], _parole()["sigle_mot"]

    def un(m: re.Match) -> str:
        base = m[0].partition("-")[0]
        if m[0] in mots or base in mots:
            return m[0]
        return epeler(m[0]) if base in sigles else m[0].lower()

    # pas un morceau déjà épelé : « EN » dans « A-EN-ES-DE » n'est pas un sigle
    return re.sub(r"(?<![-\w])[A-ZÀ-Ý]{2,}(?:-\d+)?(?![-\w])", un, texte)


def source_wo(r: Resultat) -> str:
    S = _parole()["source"]
    prod, op = r.source.producteur, r.source.operation
    dit = S.get(prod) or next((v for k, v in S.items() if _sans_accent(prod.replace("-", " ")).startswith(
        _sans_accent(k))), prod.replace("-", " "))
    if prod == "ANSD" and op and op != prod:
        dit = f"{dit}, {S.get(op, op)}"
    return dit


def _precisions_wo(r: Resultat) -> str:
    """Modalités non totales (Féminin, 15-24 ans…) : mots de KBD, sinon le français (Q1)."""
    P = _parole()["precision"]
    out = []
    for v in (r.desagregation or {}).values():
        if _sans_accent(v) in ("total", "ensemble", "tous", "toutes"):
            continue
        if m := re.fullmatch(r"(\d+)\s*-\s*(\d+)\s*ans", v.strip()):
            out.append(f"diggante {entier_wo(int(m[1]))} ba {suffixe(entier_wo(int(m[2])))} at")
        else:
            out.append(P.get(v.strip(), v.strip()))
    return ", ".join(out)


def indicateur_wo(r: Resultat) -> str:
    ind = indicateurs().get(r.indicateur.code)
    nom = (ind.libelle_wo if ind and ind.libelle_wo and ind.statut_wo == "valide"
           else ind.libelle_fr if ind else r.indicateur.libelle)
    if r.zone.code != "SN":  # KBD : « Limu woto yi ci réew mi » ne dit « dans le pays » que pour le Sénégal
        nom = nom.removesuffix(" ci réew mi")
    precisions = _precisions_wo(r)
    return f"{nom}, {precisions}" if precisions else nom


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

_NOMS_APRES_NOMBRE = ("at", "weer", "nit", "kër", "ton", "jur", "ektaar", "woto", "gan")


def _nettoyer(texte: str) -> str:
    """Parenthèses lues (KBD) : « (X) » -> « , X, » ; nombres restés en chiffres -> mots."""
    def nombre(m: re.Match) -> str:
        n, apres = int(m[1]), m[2]
        if 1900 <= n <= 2100 and len(m[1]) == 4:
            return fr_entier(n) + apres  # une année : en français
        dit = entier_wo(n)
        return (suffixe(dit) if apres.strip() in _NOMS_APRES_NOMBRE else dit) + apres

    t = re.sub(r"\s*\(([^)]*)\)", r", \1,", texte)
    t = _sigles(t)
    t = re.sub(r"(\d+)(\s+\w+|)", nombre, t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.:?!])", r"\1", t)
    t = re.sub(r",\s*([.,:?!])", r"\1", t).strip()
    return re.sub(r"(^|[.?!]\s+)(\w)", lambda m: m[1] + m[2].upper(), t)  # majuscule en début de phrase


def duree_estimee(texte: str) -> float:
    return (len(texte) / CARACTERES_PAR_S + PAUSE_DEUX_POINTS_S * texte.count(":")
            + PAUSE_PHRASE_S * len(re.findall(r"[.?!](?:\s|$)", texte)))


class _Choix:
    """Variante d'une phrase : fixe pour une même réponse ; la plus courte quand il faut gagner du temps."""

    def __init__(self, ident: str, court: bool = False):
        self.ident, self.court = ident, court

    def __call__(self, g: GabaritWo, effectif: bool = False, **trous: str) -> str:
        if g.selon_unite:
            v = g.variantes[min(int(effectif), len(g.variantes) - 1)]
        elif self.court:
            v = min(g.variantes, key=lambda x: len(x.format_map(_Trous(trous))))
        else:
            v = g.variantes[zlib.crc32(f"{self.ident}{g.cle}".encode()) % len(g.variantes)]
        return v.format_map(_Trous(trous))


class _Trous(dict):
    def __missing__(self, cle: str) -> str:
        return ""


def _gabarit_valeur(r: Resultat) -> GabaritWo:
    G = gabarits_wo()
    if not _precisions_wo(r):  # une modalité à dire (Féminin…) : la phrase passe-partout la nomme
        for g in G.values():
            if r.indicateur.code in g.indicateurs:
                return g
    return G["valeur.neutre"]


def _valeur(rep: ReponseExacte, socle: Socle, choix: _Choix) -> list[tuple[int, str]]:
    """(priorité, phrase) : 0 = toujours dit ; plus le nombre est grand, plus tôt on l'enlève."""
    G, r = gabarits_wo(), rep.resultats[0]
    g = _gabarit_valeur(r)
    blocs = [(0, choix(g, zone=zone_wo(r.zone.code), nom_zone=zone_wo(r.zone.code, False),
                       chiffre=chiffre_wo(r, g.chiffre == "nombre"), periode=periode_wo(r.periode.valeur),
                       indicateur=indicateur_wo(r)))]
    if len(rep.resultats) > 1 and (c := compagnons().get(r.indicateur.code)) and \
            rep.resultats[1].indicateur.code == c.code:
        blocs.append((0, choix(G["compagnon.taux-chomage"], chiffre=chiffre_wo(rep.resultats[1]))))
    ind = indicateurs().get(r.indicateur.code)
    if ind and gabarit_fr(ind).comparer_au_national and r.zone.code != "SN":
        n = national(socle, r, "fr")
        if n is not None and n.periode.valeur == r.periode.valeur:
            cle = "national.plus" if r.valeur > n.valeur else "national.moins" if r.valeur < n.valeur \
                else "national.autant"
            blocs.append((1, choix(G[cle], effectif=est_effectif(r.unite), chiffre=chiffre_wo(n),
                                   periode=periode_wo(n.periode.valeur))))
    if rep.periode_par_defaut:
        blocs.append((2, choix(G["derniere-donnee"])))
    return blocs


def _comparaison(rep: ReponseExacte, choix: _Choix) -> list[tuple[int, str]]:
    G, res = gabarits_wo(), rep.resultats
    r0 = res[0]
    if len({r.zone.code for r in res}) == 1:  # évolution : même zone, deux périodes
        r1, r2 = sorted((res[0], res[-1]), key=lambda r: r.periode.valeur)
        base = G["evolution.baisse"].variantes[0]
        fin = ", muy wàññiku."
        if not base.endswith(fin):
            raise ValueError("evolution.baisse doit finir par la tendance")
        tendance = {1: G["evolution.hausse"], -1: G["evolution.baisse"], 0: G["evolution.stable"]}[
            (r2.valeur > r1.valeur) - (r2.valeur < r1.valeur)]
        fin_dite = fin if tendance.cle == "evolution.baisse" else tendance.variantes[0]
        phrase = base[: -len(fin)].format_map(_Trous(
            indicateur=indicateur_wo(r1), zone=zone_wo(r1.zone.code), chiffre1=chiffre_wo(r1),
            periode1=periode_wo(r1.periode.valeur), chiffre2=chiffre_wo(r2), periode2=periode_wo(r2.periode.valeur)))
        return [(0, phrase + fin_dite)]
    memes = len({r.periode.valeur for r in res}) == 1
    morceaux = [f"{chiffre_wo(r)} {zone_wo(r.zone.code)}" + ("" if memes else f" {periode_wo(r.periode.valeur)}")
                for r in res]
    liste = f"{', '.join(morceaux[:-1])}, ak {morceaux[-1]}"  # KBD : « …, {c2} {z2}, ak {c3} {z3} »
    modele = G["comparaison.deux-zones"].variantes[0]
    phrase = modele.replace("{chiffre1} {zone1}, ak {chiffre2} {zone2}", liste).format_map(_Trous(
        indicateur=indicateur_wo(r0), periode=periode_wo(r0.periode.valeur) if memes else ""))
    blocs = [(0, phrase)]
    haut = max(res, key=lambda r: r.valeur)
    if sum(r.valeur == haut.valeur for r in res) == 1:
        blocs.append((1, choix(G["comparaison.plus-eleve"], effectif=est_effectif(r0.unite),
                               zone=zone_wo(haut.zone.code))))
    return blocs


def _classement(rep: ReponseExacte, choix: _Choix, n: int = 3) -> list[tuple[int, str]]:
    G, res = gabarits_wo(), rep.resultats[:n]
    croissant = len(rep.resultats) > 1 and rep.resultats[0].valeur < rep.resultats[-1].valeur
    g = G["classement.plus-bas" if croissant else "classement.plus-eleve"]
    v = g.variantes[min(int(est_effectif(res[0].unite)), len(g.variantes) - 1)]
    if len(res) < 3:  # KBD : on raccourcit la phrase
        v = v[: v.index(", ak {nom_zone3}")] + "." if len(res) == 2 else v[: v.index(", teg ci")] + "."
    trous = {"periode": periode_wo(res[0].periode.valeur), "zone1": zone_wo(res[0].zone.code)}
    for i, r in enumerate(res, 1):
        trous[f"chiffre{i}"] = chiffre_wo(r)
        trous[f"nom_zone{i}"] = zone_wo(r.zone.code, avec_ci=False)
    return [(0, v.format_map(_Trous(trous)))]


def _approchee(rep: ReponseApprochee, choix: _Choix) -> list[tuple[int, str]] | None:
    G, t = gabarits_wo(), rep.reformulation
    if rep.langue == "wo" and not _ECRIT.get():  # déjà écrite en wolof (0032) : la voix la lit telle quelle
        intro = t
    elif m := re.search(r"n'est pas publié pour (.+?)\s*[;.]", t):
        intro = choix(G["approchee.lieu"], lieu=m[1])
    elif m := re.search(r"pour l'année (\d{4})", t):
        intro = choix(G["approchee.annee"], periode=periode_wo(m[1]))
    elif "catégorie" in t:
        intro = choix(G["approchee.categorie"])
    elif g := _ecrit("approchee.generique"):  # académies de Dakar… : les choix sont lus quand même (EF-21)
        intro = choix(g)
    else:
        return None  # pas de phrase wolof pour ce cas : le texte seul part
    if _ECRIT.get():  # à l'écrit, les choix s'affichent à part (boutons, liste numérotée)
        return [(0, intro)]
    choixs = " ".join(f"{entier_wo(int(c.id)) if c.id.isdigit() else c.id} : {c.libelle}." for c in rep.choix)
    return [(0, f"{intro} {choixs}")]


def _ecrit(cle: str) -> GabaritWo | None:
    """Le gabarit, seulement si KBD en a écrit le wolof (une ligne vide ne dit rien)."""
    g = gabarits_wo().get(cle)
    return g if g and any(v.strip() for v in g.variantes) else None


def _nature(rep: ReponseExacte, choix: _Choix) -> list[tuple[int, str]]:
    """Projection ou estimation : toujours dite, jamais coupée (0002 ; à l'oral, c'est la seule étiquette)."""
    for nature in ("projection", "estimation"):
        r = next((x for x in rep.resultats if x.nature == nature), None)
        if r and (g := _ecrit(f"nature.{nature}")):
            prod = r.source.producteur
            return [(0, choix(g, source=_parole()["source"].get(prod, prod), base=r.base_projection or ""))]
    return []


def _aucune(rep: ReponseAucune, choix: _Choix) -> list[tuple[int, str]] | None:
    cle = {"hors_socle": "refus.hors-socle", "projection": "refus.prevision",
           "incomprehension": "refus.incomprehension"}.get(rep.motif)
    return [(0, choix(gabarits_wo()[cle]))] if cle else None  # non_disponible : pas de wolof écrit


def _assembler(blocs: list[tuple[int, str]]) -> str:
    return _nettoyer(" ".join(p for _, p in blocs))


def texte_parle(rep: AskResponse, socle: Socle) -> str | None:
    """Le texte wolof de la note vocale, ou None (le texte écrit part seul). 20 s au plus."""
    r = rep.reponse
    blocs = _blocs(r, socle, _Choix(r.id))
    if blocs is None:
        return None
    for n in (3, 2, 1):  # classement : 3 zones, puis 2, puis 1 (KBD : la phrase se raccourcit)
        if duree_estimee(_assembler(blocs)) <= DUREE_MAX_S:
            break
        blocs = _blocs(r, socle, _Choix(r.id, court=True), n)  # 1. les variantes les plus courtes
        while duree_estimee(_assembler(blocs)) > DUREE_MAX_S and max(p for p, _ in blocs) > 0:
            pire = max(p for p, _ in blocs)  # 2. la source, puis « dernière donnée », puis le national
            blocs = [b for b in blocs if b[0] != pire]
        if not (isinstance(r, ReponseExacte) and r.intention == "classement"):
            break
    return _assembler(blocs)  # encore trop long : la synthèse mesurera la vraie durée (#30)


def _blocs(r, socle: Socle, choix: _Choix, n: int = 3) -> list[tuple[int, str]] | None:
    if isinstance(r, ReponseExacte):
        if r.intention == "classement":
            blocs = _classement(r, choix, n)
        elif r.intention == "comparaison" or (len(r.resultats) > 1 and not (
                (c := compagnons().get(r.resultats[0].indicateur.code))
                and r.resultats[1].indicateur.code == c.code)):
            blocs = _comparaison(r, choix)
        else:
            blocs = _valeur(r, socle, choix)
        return [*blocs, *_nature(r, choix), (3, choix(gabarits_wo()["source"], source=source_wo(r.resultats[0])))]
    if isinstance(r, ReponseApprochee):
        return _approchee(r, choix)
    return _aucune(r, choix)


# ---------------------------------------------------------------------------
# Réponse écrite en wolof (option B de KBD, 07/10)
# ---------------------------------------------------------------------------


@cache
def _formes_ecrites() -> tuple[tuple[str, str], ...]:
    """Ce que la voix épelle, remis tel qu'écrit : « A-EN-ES-DE » -> « ANSD » (sigles de `parole_wo.csv`)."""
    formes = {epeler(sigle): sigle for sigle in _parole()["sigle"]}
    formes["we we we poñ A-EN-ES-DE poñ sn"] = "www.ansd.sn"
    return tuple(sorted(formes.items(), key=lambda kv: len(kv[0]), reverse=True))


def _ecrire(texte: str) -> str:
    for dit, ecrit in _formes_ecrites():
        texte = texte.replace(dit, ecrit)
    t = re.sub(r"\s+", " ", texte)
    t = re.sub(r"\s+([,.:?!])", r"\1", t).strip()
    return re.sub(r"(^|[.?!]\s+)(\w)", lambda m: m[1] + m[2].upper(), t)


def _notes_fr(r: Resultat) -> str:
    """Les notes qui n'ont pas encore de wolof restent en français (choix de KBD) ; la projection a le sien."""
    morceaux = []
    if formater(r.valeur, r.unite)[1]:
        morceaux.append("Valeur arrondie à l'affichage, la valeur exacte figure dans les exports.")
    if not (r.unite or "").strip():
        morceaux.append("Unité non précisée par la source.")
    return " ".join(morceaux)


def texte_ecrit(rep: AskResponse, socle: Socle) -> str | None:
    """Le texte wolof de la réponse écrite, ou None (pas de phrase wolof : la réponse reste en français)."""
    r = rep.reponse
    jeton = _ECRIT.set(True)
    try:
        blocs = _blocs(r, socle, _Choix(r.id))
    finally:
        _ECRIT.reset(jeton)
    if blocs is None:
        return None
    texte = _ecrire(" ".join(p for _, p in blocs))
    if isinstance(r, ReponseExacte) and (notes := _notes_fr(r.resultats[0])):
        texte = f"{texte} {notes}"
    return texte


def en_wolof(rep: AskResponse, socle: Socle) -> AskResponse:
    """La réponse française, réécrite en wolof quand KBD a écrit les phrases ; sinon inchangée (« fr »)."""
    texte = texte_ecrit(rep, socle)
    if texte is None:
        return rep
    r = rep.reponse
    champ = "explication" if isinstance(r, ReponseExacte) else \
        "reformulation" if isinstance(r, ReponseApprochee) else "message"
    return rep.model_copy(update={"reponse": r.model_copy(update={champ: texte, "langue": "wo"})})

