"""Construction des graphiques de réponse (issue #14, EF-20, EF-26, décision 0016).

Graphiques dessinés côté client par le navigateur Next.js (svg_url = None, décision 0016).
Données structurées servant d'alternative textuelle (EF-28). Pied normalisé citant la source (EF-27).
Types de graphiques :
  - barres_horizontales : classement des régions/académies et comparaison géographique multi-zones ;
  - courbe : comparaison temporelle (évolution dans le temps d'un indicateur sur une zone).
"""

from __future__ import annotations

from datetime import date

from gestukaay_contracts.models import Graphique, PointGraphique, Resultat, SerieGraphique, Source
from gestukaay_socle.indicateurs import Indicateur
from gestukaay_socle.zones import zones

from .gabarits import date_en_lettres
from .socle import Socle


def pied_graphique(s: Source) -> str:
    """Format de pied EF-27 conforme aux exemples du contrat (ex. exacte_valeur.json) :
    « Source : ANSD, RGPH-5, publié le 31 octobre 2023 · gestukaay »."""
    operation = s.operation or s.titre
    date_pub = date_en_lettres(s.date_publication) if isinstance(s.date_publication, date) else str(s.date_publication)
    return f"Source : {s.producteur}, {operation}, publié le {date_pub} · gestukaay"


def _nom_zone_court(code: str, repli: str) -> str:
    z = zones().get(code)
    return z.libelle_fr if z else repli


def graphique_classement(resultats: list[Resultat], ind: Indicateur) -> Graphique:
    """Graphique en barres horizontales pour un classement (14 régions ou 16 académies)."""
    r0 = resultats[0]
    niveau = r0.zone.niveau
    groupe = "par académie" if niveau == "academie" else "par région"
    unite = r0.unite
    unite_parenth = f" ({unite})" if unite else ""
    titre = f"{ind.libelle_fr} {groupe} en {r0.periode.valeur}{unite_parenth}"

    points = [
        PointGraphique(
            x=_nom_zone_court(r.zone.code, r.zone.libelle),
            y=r.valeur,
            mise_en_evidence=r.mise_en_evidence,
        )
        for r in resultats
    ]
    return Graphique(
        type="barres_horizontales",
        titre=titre,
        unite=unite,
        series=[SerieGraphique(nom=ind.libelle_fr, points=points)],
        pied=pied_graphique(r0.source),
        svg_url=None,
    )


def graphique_comparaison_zones(resultats: list[Resultat], ind: Indicateur) -> Graphique:
    """Graphique en barres horizontales pour comparer 2 ou plusieurs zones à la même période."""
    r0 = resultats[0]
    unite = r0.unite
    unite_parenth = f" ({unite})" if unite else ""
    titre = f"{ind.libelle_fr} en {r0.periode.valeur}{unite_parenth}"
    points = [
        PointGraphique(
            x=_nom_zone_court(r.zone.code, r.zone.libelle),
            y=r.valeur,
            mise_en_evidence=True,
        )
        for r in resultats
    ]
    return Graphique(
        type="barres_horizontales",
        titre=titre,
        unite=unite,
        series=[SerieGraphique(nom=ind.libelle_fr, points=points)],
        pied=pied_graphique(r0.source),
        svg_url=None,
    )


def graphique_evolution(socle: Socle, resultats: list[Resultat], ind: Indicateur) -> Graphique:
    """Graphique en courbe pour une comparaison temporelle.
    resultats = les bornes demandées.
    points = toutes les années publiées entre les deux bornes, bornes en évidence.
    """
    r_debut, r_fin = resultats[0], resultats[-1]
    if r_debut.periode.valeur > r_fin.periode.valeur:
        r_debut, r_fin = r_fin, r_debut
    p_debut, p_fin = r_debut.periode.valeur, r_fin.periode.valeur

    lignes = socle.observations(ind.code)
    o_cible = next((o for o in lignes if o.id == r_debut.observation_id), None)
    desag_cible = o_cible.desagregation if o_cible else ()

    intermediaires = [
        o for o in lignes
        if o.zone == r_debut.zone.code
        and o.desagregation == desag_cible
        and p_debut <= o.periode <= p_fin
    ]
    intermediaires.sort(key=lambda o: o.periode)

    if not intermediaires:
        intermediaires = [
            next((o for o in lignes if o.id == r_debut.observation_id), None),
            next((o for o in lignes if o.id == r_fin.observation_id), None),
        ]
        intermediaires = [o for o in intermediaires if o is not None]

    points = [
        PointGraphique(
            x=o.periode,
            y=o.valeur,
            mise_en_evidence=(o.periode in (p_debut, p_fin)),
        )
        for o in intermediaires
    ]

    unite = r_debut.unite
    unite_parenth = f" ({unite})" if unite else ""
    titre = f"Évolution de : {ind.libelle_fr}{unite_parenth}"

    return Graphique(
        type="courbe",
        titre=titre,
        unite=unite,
        series=[SerieGraphique(nom=ind.libelle_fr, points=points)],
        pied=pied_graphique(r_debut.source),
        svg_url=None,
    )


def graphique_contexte_valeur(socle: Socle, r: Resultat, ind: Indicateur) -> Graphique | None:
    """Graphique de contexte pour une valeur unique régionale (14 régions, zone demandée en évidence).
    Seules les zones du même niveau que la zone demandée : certains jeux publient régions et
    départements pour la même période (aykimoe, zctvxac, ekihmme, pykrorg…)."""
    if r.zone.niveau not in ("region", "academie"):
        return None
    lignes = socle.observations(ind.code)
    o_cible = next((o for o in lignes if o.id == r.observation_id), None)
    if o_cible is None:
        return None
    desag_cible = o_cible.desagregation
    ref = zones()
    meme_periode = [
        o for o in lignes
        if o.periode == r.periode.valeur
        and o.desagregation == desag_cible
        and (z := ref.get(o.zone)) is not None and z.niveau == r.zone.niveau
    ]
    if len(meme_periode) <= 1:
        return None
    meme_periode.sort(key=lambda o: o.valeur, reverse=True)
    points = [
        PointGraphique(
            x=_nom_zone_court(o.zone, o.zone),
            y=o.valeur,
            mise_en_evidence=(o.zone == r.zone.code),
        )
        for o in meme_periode
    ]
    unite = r.unite
    unite_parenth = f" ({unite})" if unite else ""
    groupe = "par académie" if r.zone.niveau == "academie" else "par région"
    titre = f"{ind.libelle_fr} {groupe} en {r.periode.valeur}{unite_parenth}"
    return Graphique(
        type="barres_horizontales",
        titre=titre,
        unite=unite,
        series=[SerieGraphique(nom=ind.libelle_fr, points=points)],
        pied=pied_graphique(r.source),
        svg_url=None,
    )
