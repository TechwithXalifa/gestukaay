"""Alertes de nouvelle publication : un flux Atom par indicateur et par zone.

« Prévenez-moi quand le chômage est mis à jour » : l'usager ajoute l'adresse du flux à un lecteur de flux
(Feedly, Inoreader, Thunderbird…) ou à un service qui envoie les flux par e-mail. Chaque valeur publiée est une
entrée ; une nouvelle période, ou une valeur révisée, fait une entrée nouvelle, et le lecteur prévient.

Aucune donnée personnelle : Gëstukaay ne garde ni adresse e-mail ni numéro, il publie seulement le flux. Les
valeurs sont celles d'Explorer (moteur.series), jamais une projection au-delà de l'année en cours (décision 0035).
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import quote, urlencode
from xml.sax.saxutils import escape

ENTREES = 10  # les dix dernières périodes publiées


def _date(d) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def flux_atom(serie_rep, code: str, zone: str, site: str) -> str:
    """Le flux Atom d'une série (SeriesResponse) ; sans valeur publiée pour la zone, un flux vide mais valide."""
    serie = serie_rep.series[0] if serie_rep.series else None
    annee = datetime.now(UTC).year
    points = [p for p in (serie.points if serie else []) if int(p.periode[:4]) <= annee][-ENTREES:]
    indicateur = serie_rep.indicateur.libelle
    lieu = serie.zone.libelle if serie else zone
    explorer = f"{site}/explorer?" + urlencode({"indicateur": code, "zones": "SN" if zone == "SN" else f"SN,{zone}"})
    fiche = f"{site}/indicateurs/{quote(code, safe='')}"
    publie = _date(serie.source.date_publication) if serie else _date(datetime.now(UTC).date())
    entrees = []
    for p in reversed(points):
        nature = " (projection officielle)" if p.nature == "projection" else " (estimation officielle)" \
            if p.nature == "estimation" else ""
        titre = f"{indicateur} · {lieu} · {p.libelle} : {p.valeur_affichee} {serie_rep.unite}".strip() + nature
        # Une valeur révisée garde sa période mais change d'identifiant : le lecteur la signale comme nouvelle
        ident = f"tag:gestukaay,2026:{quote(code, safe='')}:{zone}:{p.periode}:{p.valeur}"
        entrees.append(
            "  <entry>\n"
            f"    <id>{escape(ident)}</id>\n"
            f"    <title>{escape(titre)}</title>\n"
            f"    <updated>{publie}</updated>\n"
            f'    <link rel="alternate" href="{escape(explorer)}"/>\n'
            f"    <summary>{escape(titre)}. Source : {escape(serie.source.libelle)}.</summary>\n"
            "  </entry>\n"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="fr">\n'
        f"  <id>tag:gestukaay,2026:{escape(quote(code, safe=''))}:{escape(zone)}</id>\n"
        f"  <title>{escape(indicateur)} · {escape(lieu)} · Gëstukaay</title>\n"
        f"  <subtitle>Chaque nouvelle valeur officielle publiée, avec sa source.</subtitle>\n"
        f"  <updated>{publie}</updated>\n"
        f'  <link rel="alternate" href="{escape(fiche)}"/>\n'
        "  <author><name>Gëstukaay</name></author>\n"
        + "".join(entrees)
        + "</feed>\n"
    )
