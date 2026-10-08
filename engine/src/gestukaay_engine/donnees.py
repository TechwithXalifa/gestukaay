"""Espace Données : catalogue, fiche indicateur et séries d'Explorer (décision 0023, #156).

Lecture seule, sans LLM : tout vient du référentiel des indicateurs (0005), des fiches des jeux (#7) et
du socle extrait déjà en mémoire. Les choix de la résolution s'appliquent tels quels (0011) : une valeur
d'Explorer est celle que donnerait la question « indicateur, zone, période » (total par défaut, défauts
déclarés du jeu, académie équivalente) ; une période sans valeur sûre est absente, jamais interpolée.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import cache

from gestukaay_contracts.models import (
    CatalogueResponse,
    Couverture,
    FicheIndicateur,
    Graphique,
    IndicateurResume,
    PointGraphique,
    PointSerie,
    RefIndicateur,
    Serie,
    SerieGraphique,
    SeriesResponse,
)
from gestukaay_socle.fiches import jeux
from gestukaay_socle.indicateurs import Indicateur, indicateurs
from gestukaay_socle.zones import normaliser, zones

from .gabarits import citation, note_perimetre
from .graphique import pied_graphique
from .interface import IndicateurInconnu
from .resolution import Introuvable, producteur_et_operation, ref_zone, resoudre_un, resultat
from .socle import Socle

NIVEAUX = ("pays", "region", "departement", "academie")  # ceux du contrat (NiveauZone), dans cet ordre
LIES_MAX = 6
# Adresse provisoire de la fiche, comme URL_PROVISOIRE des réponses : le backend met l'adresse publique
URL_FICHE = "https://app.gestukaay.test/indicateurs/{code}"


@dataclass(frozen=True)
class _Ligne:
    resume: IndicateurResume
    texte: str  # libellé, opération, producteur et domaine normalisés : la recherche « q »


def _niveaux(codes_zone: set[str]) -> list[str]:
    connus = {zones()[z].niveau for z in codes_zone if z in zones()}
    return [n for n in NIVEAUX if n in connus]


def _resume(socle: Socle, ind: Indicateur) -> IndicateurResume | None:
    lignes = socle.observations(ind.code)
    if not lignes:
        return None
    periodes = sorted({o.periode for o in lignes})
    producteur, operation = producteur_et_operation(lignes[0].source_id, socle.sources.get(lignes[0].source_id), ind)
    return IndicateurResume(
        code=ind.code, libelle=ind.libelle_fr, domaine=ind.domaine, unite=ind.unite_affichee or ind.unite,
        producteur=producteur, operation=operation, niveaux=_niveaux({o.zone for o in lignes}),
        periode_debut=periodes[0], periode_fin=periodes[-1], verifie=ind.verification == "verifie",
    )


@cache
def _catalogue(socle: Socle) -> tuple[_Ligne, ...]:
    """Les indicateurs qui ont des valeurs, vérifiés d'abord puis par libellé ; calculé une fois par socle."""
    lignes = []
    for ind in indicateurs().values():
        if r := _resume(socle, ind):
            lignes.append(_Ligne(r, normaliser(f"{r.libelle} {r.operation} {r.producteur} {r.domaine}")))
    return tuple(sorted(lignes, key=lambda x: (not x.resume.verifie, normaliser(x.resume.libelle), x.resume.code)))


def catalogue(socle: Socle, domaine: str | None = None, q: str | None = None, niveau: str | None = None,
              limite: int = 50, decalage: int = 0) -> CatalogueResponse:
    mots = normaliser(q).split() if q else []
    garder = [x.resume for x in _catalogue(socle)
              if (not domaine or normaliser(x.resume.domaine) == normaliser(domaine))
              and all(m in x.texte for m in mots)
              and (not niveau or niveau in x.resume.niveaux)]
    return CatalogueResponse(version_socle=socle.version, total=len(garder),
                             indicateurs=garder[decalage:decalage + limite])


def _indicateur(socle: Socle, code: str) -> Indicateur:
    ind = indicateurs().get(code)
    if ind is None or not socle.observations(code):
        raise IndicateurInconnu(code)
    return ind


def _lies(socle: Socle, ind: Indicateur) -> list[RefIndicateur]:
    """Jusqu'à 6 indicateurs proches : ceux du même jeu, puis les vérifiés du même domaine."""
    autres = [x.resume for x in _catalogue(socle) if x.resume.code != ind.code]
    meme_jeu = [r for r in autres if indicateurs()[r.code].dataset_id == ind.dataset_id]
    meme_domaine = [r for r in autres if r.verifie and r.domaine == ind.domaine and r not in meme_jeu]
    return [RefIndicateur(code=r.code, libelle=r.libelle) for r in [*meme_jeu, *meme_domaine][:LIES_MAX]]


def fiche(socle: Socle, code: str, consulte_le: date | None = None) -> FicheIndicateur:
    ind = _indicateur(socle, code)
    lignes = socle.observations(code)
    jeu = jeux().get(ind.dataset_id)
    couverture = []
    for niveau in NIVEAUX:
        ici = [o for o in lignes if o.zone in zones() and zones()[o.zone].niveau == niveau]
        if ici:
            couverture.append(Couverture(niveau=niveau, zones=len({o.zone for o in ici}),
                                         periodes=sorted({o.periode for o in ici})))
    # La valeur que servirait une question sans zone ni période : elle porte la source, la note et la citation
    servie = resoudre_un(socle, ind, None, None, {})
    r = servie[0] if not isinstance(servie, Introuvable) else resultat(socle, max(lignes, key=lambda o: o.periode), ind)
    return FicheIndicateur(
        version_socle=socle.version, indicateur=_catalogue_par_code(socle)[code],
        # Citée du portail, jamais rédigée ; None s'il n'en publie pas (0005)
        definition=ind.definition or (jeu.definition if jeu else "") or None,
        methode=(jeu.methode if jeu else "") or None,
        desagregations=list(ind.desagregations), couverture=couverture, note_perimetre=note_perimetre(r),
        source=r.source, citation=citation(r, consulte_le or datetime.now(UTC).date(), URL_FICHE.format(code=code)),
        indicateurs_lies=_lies(socle, ind),
    )


@cache
def _catalogue_par_code(socle: Socle) -> dict[str, IndicateurResume]:
    return {x.resume.code: x.resume for x in _catalogue(socle)}


def series(socle: Socle, code: str, codes_zone: list[str], debut: str | None = None,
           fin: str | None = None) -> SeriesResponse:
    ind = _indicateur(socle, code)
    lignes = socle.observations(code)
    unite = ind.unite_affichee or ind.unite or lignes[0].unite
    retenues: list[Serie] = []
    absents: list[str] = []
    desagregation = None
    for z in codes_zone:
        periodes = sorted({o.periode for o in lignes if o.zone == z}) if z in zones() else []
        if not periodes and z in zones():  # région servie par son académie (Kolda, Sédhiou…), comme la résolution
            servie = resoudre_un(socle, ind, z, None, {})
            if not isinstance(servie, Introuvable):
                periodes = sorted({o.periode for o in lignes if o.zone == servie[0].zone.code})
        periodes = [p for p in periodes if (not debut or p >= debut) and (not fin or p <= fin)]
        points, derniere = [], None
        for p in periodes:
            servie = resoudre_un(socle, ind, z, p, {})
            if isinstance(servie, Introuvable):  # aucune valeur sûre cette période-là (pas de total) : absente
                continue
            derniere = servie[0]
            desagregation = desagregation or derniere.desagregation
            points.append(PointSerie(periode=p, libelle=derniere.periode.libelle, valeur=derniere.valeur,
                                     valeur_affichee=derniere.valeur_affichee, observation_id=derniere.observation_id,
                                     nature=derniere.nature, base_projection=derniere.base_projection))
        if derniere is None:
            absents.append(z)
        else:
            retenues.append(Serie(zone=ref_zone(derniere.zone.code), points=points, source=derniere.source))
    return SeriesResponse(
        version_socle=socle.version, indicateur=RefIndicateur(code=ind.code, libelle=ind.libelle_fr), unite=unite,
        desagregation=desagregation, series=retenues, absents=absents,
        graphique=_graphique(ind, unite, retenues),
    )


def _graphique(ind: Indicateur, unite: str, series_: list[Serie]) -> Graphique | None:
    """Courbe pour plusieurs périodes, barres (de la plus grande à la plus petite) pour une seule."""
    if not series_:
        return None
    periodes = sorted({p.periode for s in series_ for p in s.points})
    courbe = len(periodes) > 1
    quand = f"de {periodes[0]} à {periodes[-1]}" if courbe else f"en {periodes[0]}"
    if courbe:
        traces = [SerieGraphique(nom=s.zone.libelle, points=[PointGraphique(x=p.periode, y=p.valeur) for p in s.points])
                  for s in series_]
    else:
        traces = [SerieGraphique(nom=ind.libelle_fr, points=sorted(
            (PointGraphique(x=s.zone.libelle, y=s.points[0].valeur) for s in series_), key=lambda p: -p.y))]
    return Graphique(type="courbe" if courbe else "barres_horizontales",
                     titre=f"{ind.libelle_fr} {quand}" + (f" ({unite})" if unite else ""), unite=unite,
                     series=traces, pied=pied_graphique(series_[0].source))
