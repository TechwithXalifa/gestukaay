"""« Où je me situe » : le ménage comparé aux moyennes publiées (issue #95, décisions 0004 §2, 0012, 0022).

Rien n'est conservé de ce qui est saisi (EF-40) : le moteur est sans état.

  1. dépense par personne et par an : calculée sur les SEULES données saisies (tranche mensuelle × 12 /
     taille du ménage), arrondie à l'unité ; une tranche ouverte n'a pas de maximum ;
  2. moyennes : consommation moyenne par tête publiée (`jcvcajc.total`) pour la région et le pays,
     milieu « Ensemble » (on ne demande pas ville ou campagne) ;
  3. position : `au_dessus` / `en_dessous` si tout l'intervalle est d'un côté de la moyenne, sinon
     `autour` ; une tranche ouverte n'est `au_dessus` que si sa borne basse dépasse la moyenne (0012) ;
  4. repères publiés, chacun lu dans le socle : pauvreté des ménages de même taille (national ; aucun
     repère pour 20 ou 21 personnes, qu'aucune tranche publiée ne couvre), part de la région dans le
     quintile le plus bas, ménages éclairés à l'électricité. L'accès à l'eau n'est publié qu'au niveau
     national : pas de repère (0022).
Le niveau d'instruction du chef de ménage est accepté mais ignoré : aucune donnée publiée ne le croise.

v1.6.0 (décision 0039), tout lu dans le socle, jamais calculé :
  5. milieu déclaré (facultatif) : consommation moyenne par tête des ménages urbains ou ruraux du Sénégal
     (le milieu n'est publié qu'au niveau national) ;
  6. seuil de pauvreté officiel (EHCVM, #59), même règle de position ;
  7. répartition de la population de la région entre les cinq groupes de bien-être (`sfxudug`) : le
     ménage n'y est pas placé, les seuils des groupes ne sont pas publiés ;
  8. consommation moyenne des 14 régions, même période que celle de la région (carte du site).
"""

from __future__ import annotations

import re

from gestukaay_contracts.models import (
    Intervalle,
    Position,
    Resultat,
    SituateRequest,
    SituateResponse,
)
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import zones

from .gabarits import formater, zone_en_lettres
from .interface import NonDisponible, SaisieInvalide
from .resolution import est_total, periode_par_defaut, resultat
from .socle import Observation, Socle

# Bornes mensuelles (FCFA) de chaque tranche du contrat 1.3.0 ; None : tranche ouverte
TRANCHES: dict[str, tuple[int, int | None]] = {
    "moins_50k": (0, 50_000), "50k_100k": (50_000, 100_000), "100k_200k": (100_000, 200_000),
    "200k_350k": (200_000, 350_000), "350k_500k": (350_000, 500_000), "500k_750k": (500_000, 750_000),
    "750k_1m": (750_000, 1_000_000), "plus_1m": (1_000_000, None),
    "plus_500k": (500_000, None),  # dépréciée (1.3.0) mais encore acceptée : même règle que plus_1m
}

MOYENNE = "jcvcajc.total"
MILIEU = "milieu-de-résidence"
SEUIL = "ahjjzgc.seuil-de-pauvrete"
BIEN_ETRE, GROUPE = "sfxudug", "quintile"
# Groupes de bien-être, du plus bas au plus élevé, avec le libellé affiché (le site n'affiche pas la désagrégation)
GROUPES = {"Le plus bas": "Groupe de bien-être le plus bas", "Second": "Deuxième groupe de bien-être",
           "Moyen": "Groupe de bien-être du milieu", "Quatrième": "Quatrième groupe de bien-être",
           "Le plus élevé": "Groupe de bien-être le plus élevé"}
PAUVRETE, TAILLE = "jcvcajc.taux-de-pauvrete", "taille-du-ménage"
# Repères régionaux : code -> libellé affiché (celui de l'exemple du contrat, plus clair que le référentiel)
REPERES_REGION = {"qjyrtof.le-plus-bas": "Population dans le quintile de bien-être le plus bas",
                  "asongtc": "Ménages éclairés à l'électricité"}

EXPLICATION_MOYENNE = (
    "Une moyenne additionne les dépenses de tous les ménages puis divise par le nombre de personnes : "
    "elle ne dit pas où se situe la majorité.")
PRECAUTIONS = (
    "Deux précautions : ces moyennes ont été mesurées en {annee}, en FCFA de {annee}, alors que vos "
    "dépenses sont celles d'aujourd'hui ; et la consommation mesurée par l'enquête compte aussi ce que "
    "le ménage produit lui-même et la valeur du logement occupé, que l'on oublie souvent dans ses "
    "dépenses. La comparaison donne donc un ordre de grandeur, pas un classement.")


def intervalle(tranche: str, taille: int) -> Intervalle:
    bas, haut = TRANCHES[tranche]
    minimum = round(bas * 12 / taille)
    maximum = None if haut is None else round(haut * 12 / taille)
    if maximum is None:
        libelle = f"au moins {_fcfa(minimum)} par personne et par an"
    elif minimum == 0:
        libelle = f"moins de {_fcfa(maximum)} par personne et par an"
    else:
        libelle = f"entre {_nombre(minimum)} et {_fcfa(maximum)} par personne et par an"
    return Intervalle(minimum=minimum, maximum=maximum, libelle=libelle)


def position(iv: Intervalle, moyenne: float) -> Position:
    if iv.maximum is not None and iv.maximum < moyenne:
        return "en_dessous"
    if iv.minimum > moyenne:
        return "au_dessus"
    return "autour"


def situer(socle: Socle, req: SituateRequest) -> SituateResponse:
    z = zones().get(req.region)
    if z is None or z.niveau != "region":
        raise SaisieInvalide(f"région inconnue : {req.region!r}")
    region, pays = _lire(socle, MOYENNE, req.region), _lire(socle, MOYENNE, "SN")
    if region is None or pays is None:
        raise NonDisponible(f"consommation moyenne par tête non publiée pour {req.region}")
    iv = intervalle(req.depenses_mensuelles, req.taille_menage)
    pos_r, pos_p = position(iv, region.valeur), position(iv, pays.valeur)
    milieu = _lire(socle, MOYENNE, "SN", {MILIEU: req.milieu.capitalize()}) if req.milieu else None
    milieu = _libelle(milieu, f"Consommation moyenne par tête des ménages {_MILIEUX[req.milieu]}") if milieu else None
    seuil = _lire(socle, SEUIL, "SN")
    pos_m = position(iv, milieu.valeur) if milieu else None
    pos_s = position(iv, seuil.valeur) if seuil else None
    texte = explication(iv, region, pays, pos_r, pos_p)
    ajouts = [f"Par rapport aux ménages {_MILIEUX[req.milieu]} du Sénégal ({_fcfa(milieu.valeur)}), c'est "
              f"{_RELATIF[pos_m]} leur consommation moyenne." if milieu else "",
              f"Le seuil de pauvreté officiel est de {_fcfa(seuil.valeur)} par personne et par an "
              f"(enquête de {seuil.periode.valeur}) : votre estimation est {_RELATIF_SEUIL[pos_s]}." if seuil else ""]
    texte = _avant_precautions(texte, " ".join(a for a in ajouts if a))
    return SituateResponse(
        depense_par_personne_an=iv, moyenne_region=region, moyenne_pays=pays,
        position_region=pos_r, position_pays=pos_p,
        contexte=reperes(socle, req.region, req.taille_menage),
        explication=texte,
        moyenne_milieu=milieu, position_milieu=pos_m, seuil_pauvrete=seuil, position_seuil=pos_s,
        repartition_bien_etre=repartition(socle, req.region),
        moyennes_regions=moyennes_regions(socle, region.periode.valeur))


_MILIEUX = {"urbain": "urbains", "rural": "ruraux"}
_RELATIF_SEUIL = {"en_dessous": "en dessous de ce seuil", "au_dessus": "au-dessus de ce seuil", "autour": "autour de ce seuil"}


def _avant_precautions(texte: str, ajout: str) -> str:
    """Les phrases nouvelles viennent après la comparaison, avant l'encadré et les précautions."""
    if not ajout:
        return texte
    return texte.replace(EXPLICATION_MOYENNE, f"{ajout} {EXPLICATION_MOYENNE}", 1)


def repartition(socle: Socle, region: str) -> list[Resultat]:
    """Part de la population de la région dans chaque groupe de bien-être, même période pour les cinq."""
    lus = {g: _lire(socle, BIEN_ETRE, region, {MILIEU: "Total", GROUPE: g}) for g in GROUPES}
    if any(r is None for r in lus.values()) or len({r.periode.valeur for r in lus.values()}) != 1:
        return []  # cinq groupes de la même enquête, ou rien : une répartition incomplète tromperait
    return [_libelle(lus[g], libelle) for g, libelle in GROUPES.items()]


def moyennes_regions(socle: Socle, periode: str) -> list[Resultat]:
    """Consommation moyenne par tête des 14 régions pour la période de la région du ménage."""
    out = []
    for z in sorted(z.code for z in zones().values() if z.niveau == "region"):
        r = _lire(socle, MOYENNE, z)
        if r and r.periode.valeur == periode:
            out.append(r)
    return out


def reperes(socle: Socle, region: str, taille: int) -> list[Resultat]:
    out = []
    if (bande := _bande(socle, taille)) and (r := _lire(socle, PAUVRETE, "SN", {TAILLE: bande})):
        out.append(_libelle(r, f"Taux de pauvreté des ménages {_de_taille(bande)}"))
    for code, libelle in REPERES_REGION.items():
        if r := _lire(socle, code, region):
            out.append(_libelle(r, libelle))
    return out


def explication(iv: Intervalle, region: Resultat, pays: Resultat, pos_r: Position, pos_p: Position) -> str:
    zr = zone_en_lettres(region.zone.code)["sujet"]
    zr = zr[0].lower() + zr[1:]  # « la région de Kolda »
    vr, vp = _fcfa(region.valeur), _fcfa(pays.valeur)
    debut = f"Votre ménage dépense {iv.libelle}."
    if pos_r == pos_p:
        comparaison = (f"{_COMPARER[pos_r]} la consommation moyenne par tête publiée pour {zr} ({vr}) "
                       f"et pour le Sénégal ({vp}).")
    else:
        comparaison = (f"Par rapport à la consommation moyenne par tête publiée, c'est "
                       f"{_RELATIF[pos_r]} celle de {zr} ({vr}) et {_RELATIF[pos_p]} celle du Sénégal ({vp}).")
    annee = region.periode.valeur
    return " ".join([debut, comparaison, EXPLICATION_MOYENNE, PRECAUTIONS.format(annee=annee)])


_COMPARER = {"en_dessous": "C'est moins que", "au_dessus": "C'est plus que", "autour": "C'est autour de"}
_RELATIF = {"en_dessous": "moins que", "au_dessus": "plus que", "autour": "autour de"}


# --------------------------------------------------------------------------
# Lecture du socle : jamais de calcul, chaque repère est une ligne publiée
# --------------------------------------------------------------------------

def _lire(socle: Socle, code: str, zone: str, fixe: dict[str, str] | None = None) -> Resultat | None:
    """La dernière valeur publiée pour la zone : dimensions fixées, total pour les autres (une dimension
    à une seule modalité, « catégorie : Indices de pauvreté », ne compte pas)."""
    fixe = fixe or {}
    lignes = socle.observations(code)
    uniques = frozenset(k for k in {k for o in lignes for k, _ in o.desagregation}
                        if len({o.dims().get(k) for o in lignes} - {None}) == 1)
    retenues = [o for o in lignes if o.zone == zone and _convient(o, fixe, uniques)]
    if not retenues:
        return None
    p, _ = periode_par_defaut(retenues)  # dernière valeur observée (#116)
    o = next(o for o in retenues if o.periode == p)
    return resultat(socle, o, indicateurs()[code], "fr", uniques)


def _convient(o: Observation, fixe: dict[str, str], uniques: frozenset[str]) -> bool:
    dims = o.dims()
    return all(dims.get(k) == v for k, v in fixe.items()) and all(
        est_total(v) for k, v in dims.items() if k not in fixe and k not in uniques)


def _bande(socle: Socle, taille: int) -> str | None:
    """La tranche de taille publiée qui contient `taille` (« 5-9 personnes », « 22 personnes ou plus »)."""
    for b in {o.dims().get(TAILLE) for o in socle.observations(PAUVRETE)} - {None}:
        n = [int(x) for x in re.findall(r"\d+", b)]
        if len(n) == 2 and n[0] <= taille <= n[1] or len(n) == 1 and "plus" in b and taille >= n[0]:
            return b
    return None


def _de_taille(bande: str) -> str:
    n = re.findall(r"\d+", bande)
    return f"de {n[0]} à {n[1]} personnes" if len(n) == 2 else f"de {bande}"


def _libelle(r: Resultat, libelle: str) -> Resultat:
    return r.model_copy(update={"indicateur": r.indicateur.model_copy(update={"libelle": libelle})})


def _nombre(v: float) -> str:
    return formater(v, "FCFA")[0]


def _fcfa(v: float) -> str:
    return f"{_nombre(v)} FCFA"
