"""Exports d'une réponse exacte : CSV (EF-34) et PDF A4 d'une page (EF-33).

Les valeurs ne sont jamais recalculées ni reformatées : le CSV donne `valeur`
(brute) et le PDF affiche `valeur_affichee` (formatée par le moteur, 7.4).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from gestukaay_contracts.models import ReponseExacte, SeriesResponse
from gestukaay_socle.zones import zones

# Schéma imposé par EF-34, dans cet ordre
COLONNES = [
    "indicateur", "zone", "code_zone", "periode", "valeur", "unite", "desagregation",
    "source", "date_publication", "note_methodologique", "url_gestukaay",
]


def vers_csv(rep: ReponseExacte, virgule_decimale: bool = False) -> bytes:
    """UTF-8 avec BOM (ouverture correcte dans Excel FR), séparateur « ; »."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";", lineterminator="\r\n")
    w.writerow(COLONNES)
    for r in rep.resultats:
        valeur = repr(r.valeur) if r.valeur != int(r.valeur) else str(int(r.valeur))
        w.writerow([
            r.indicateur.libelle,
            r.zone.libelle,
            r.zone.code,
            r.periode.valeur,
            valeur.replace(".", ",") if virgule_decimale else valeur,
            r.unite,
            "|".join(f"{k}={v}" for k, v in (r.desagregation or {}).items()),
            r.source.libelle,
            r.source.date_publication.isoformat(),
            rep.note_perimetre or "",
            rep.url,
        ])
    # Les autres zones du graphique (les 14 régions autour de Thiès…) : ce que la page montre
    # dans « Voir les valeurs en tableau », le CSV le donne aussi.
    for zone, code, valeur in _comparaisons(rep):
        r0 = rep.resultats[0]
        texte = repr(valeur) if valeur != int(valeur) else str(int(valeur))
        w.writerow([
            r0.indicateur.libelle, zone, code, r0.periode.valeur,
            texte.replace(".", ",") if virgule_decimale else texte,
            r0.unite,
            "|".join(f"{k}={v}" for k, v in (r0.desagregation or {}).items()),
            r0.source.libelle, r0.source.date_publication.isoformat(),
            NOTE_COMPARAISON, rep.url,
        ])
    return ("﻿" + sortie.getvalue()).encode("utf-8")


NOTE_COMPARAISON = "Valeur de comparaison, affichée dans le graphique de la réponse."


def _comparaisons(rep: ReponseExacte) -> list[tuple[str, str, float]]:
    """Zones du graphique en barres absentes des résultats : même indicateur, même période, même
    publication que la réponse (graphique de contexte ou de classement du moteur). Pas les années
    intermédiaires d'une courbe : elles peuvent venir d'une autre enquête, donc d'une autre source."""
    g = rep.graphique
    if (g is None or g.type != "barres_horizontales" or not rep.resultats
            or len({(r.indicateur.code, r.periode.valeur) for r in rep.resultats}) != 1):
        return []
    # Par code : la réponse dit « académie de Kolda », le graphique « Kolda » (relecture KBD, #129)
    deja = {r.zone.code for r in rep.resultats}
    z0 = rep.resultats[0].zone
    ref = zones()
    codes = {z.libelle_fr: z.code for z in ref.values() if z.niveau == z0.niveau}
    # Même façon d'écrire que la réponse : « académie de Kolda » -> « académie de Kédougou »
    court = ref[z0.code].libelle_fr if z0.code in ref else z0.libelle
    prefixe = z0.libelle[: -len(court)] if court and z0.libelle.endswith(court) else ""
    return [(prefixe + p.x, codes.get(p.x, ""), p.y) for s in g.series for p in s.points
            if codes.get(p.x, p.x) not in deja]


def vers_csv_series(rep: SeriesResponse, url: str, virgule_decimale: bool = False) -> bytes:
    """Séries d'Explorer au même schéma EF-34 que les réponses : une ligne par zone et par période."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";", lineterminator="\r\n")
    w.writerow(COLONNES)
    desag = "|".join(f"{k}={v}" for k, v in (rep.desagregation or {}).items())
    for serie in rep.series:
        for p in serie.points:
            valeur = repr(p.valeur) if p.valeur != int(p.valeur) else str(int(p.valeur))
            w.writerow([rep.indicateur.libelle, serie.zone.libelle, serie.zone.code, p.periode,
                        valeur.replace(".", ",") if virgule_decimale else valeur, rep.unite, desag,
                        serie.source.libelle, serie.source.date_publication.isoformat(), "", url])
    return ("﻿" + sortie.getvalue()).encode("utf-8")


# ---- PDF -------------------------------------------------------------------

BAOBAB, FEUILLE, ARDOISE, ENCRE, LIN, COTON = (
    (29, 68, 72), (15, 110, 86), (92, 104, 103), (26, 26, 24), (228, 223, 213), (246, 242, 234),
)
DATA_NEUTRE, TRAIT, BAOBAB_50 = (185, 207, 203), (169, 183, 181), (230, 238, 237)
BARRES_MAX = 8  # comme la page réponse (maquettes Reponse et ExportPDF)


POLICES = Path(__file__).parent / "polices"  # Poppins et Lora, licence OFL (charte 9.4)


def _texte(t: str) -> str:
    """Polices Unicode : tout caractère passe (’, «, ñ, ë). Seule l'espace fine
    insécable (U+202F) est remplacée par l'insécable ordinaire, visuellement
    identique, au cas où une police ne la dessinerait pas."""
    return t.replace(" ", " ")


def _polices(pdf) -> None:
    pdf.add_font("Poppins", "", POLICES / "Poppins-Regular.ttf")
    pdf.add_font("Poppins", "B", POLICES / "Poppins-Bold.ttf")
    pdf.add_font("PoppinsSB", "", POLICES / "Poppins-SemiBold.ttf")
    pdf.add_font("Lora", "", POLICES / "Lora.ttf")
    pdf.add_font("Lora", "I", POLICES / "Lora-Italic.ttf")


# Logo baobab : même tracé que le SVG de la charte (viewBox 33 × 43)
_TRONC = [((16, 20.7), (16, 36.4)), ((16, 36.4), (10.8, 40.8)), ((16, 36.4), (21.3, 40.8))]
_BRANCHES = [(2.9, 12), (10.5, 4.2), (18.2, 2.1), (25.8, 5.3), (30.2, 14.1)]


def _baobab(pdf, x: float, y: float, hauteur: float) -> None:
    k = hauteur / 43
    pdf.set_draw_color(*BAOBAB)
    pdf.set_fill_color(*BAOBAB)
    pdf.set_line_width(2.2 * k)
    traits = _TRONC + [((16, 20.7), b) for b in _BRANCHES]
    for (x1, y1), (x2, y2) in traits:
        pdf.line(x + x1 * k, y + y1 * k, x + x2 * k, y + y2 * k)
    for bx, by in _BRANCHES:
        r = 2.3 * k
        pdf.ellipse(x + bx * k - r, y + by * k - r, 2 * r, 2 * r, style="F")


# Décision 0016 §2 (EF-33) : la mise en forme Gëstukaay (texte, graphique, PDF) est sous CC BY 4.0 ;
# la licence des données est celle que publie l'ANSD, jamais supposée quand le portail ne la dit pas.
LICENCE_EXPORT = "sous licence CC BY 4.0"


def mention_licence_donnees(sources) -> str:
    licences = sorted({s.licence for s in sources if s.licence.strip()})
    if licences:
        return f"Licence des données : {', '.join(licences)}"
    return "Licence des données : non précisée par le portail ; voir la publication de l'ANSD"


def _nombre(v: float) -> str:
    """4004426 -> « 4 004 426 » ; 25.7 -> « 25,7 » (comme le graphique du site)."""
    texte = f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"
    return texte.replace(",", " ").replace(".", ",")


def _barres(pdf, g, y: float, largeur: float, n: int) -> float:
    """Graphique en barres horizontales (une série), n barres au plus. Rend le y de fin."""
    points = list(g.series[0].points)  # ordre du moteur (classement croissant possible, #14)
    visibles = points[:n]
    for p in points[n:]:
        if p.mise_en_evidence:  # la zone demandée reste toujours visible
            visibles[-1] = p
    maxi = max((p.y for p in points), default=0) or 1
    pdf.set_y(y)
    pdf.set_font("PoppinsSB", "", 10)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 5, _texte(g.titre), new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 2
    x_axe, piste = 20 + 32, largeur - 32 - 24  # libellés à gauche, valeurs à droite des barres
    pdf.set_draw_color(*TRAIT)
    pdf.set_line_width(0.3)
    pdf.line(x_axe, y, x_axe, y + len(visibles) * 6)
    for i, p in enumerate(visibles):
        yb = y + i * 6
        fort = p.mise_en_evidence
        pdf.set_font("PoppinsSB" if fort else "Poppins", "", 8.5)
        pdf.set_text_color(*(ENCRE if fort else ARDOISE))
        pdf.set_xy(20, yb)
        pdf.cell(29, 6, _texte(p.x), align="R")
        w = max(p.y / maxi * piste, 0.5)
        pdf.set_fill_color(*(FEUILLE if fort else DATA_NEUTRE))
        pdf.rect(x_axe, yb + 1.25, w, 3.5, style="F")
        pdf.set_xy(x_axe + w + 2, yb)
        pdf.cell(24, 6, _texte(_nombre(p.y)))
    y += len(visibles) * 6 + 2
    _baobab(pdf, 20, y + 0.6, 3.4)
    pdf.set_xy(23.5, y)
    pdf.set_font("Poppins", "", 7.5)
    pdf.set_text_color(*ARDOISE)
    pdf.cell(largeur - 4, 4.5, _texte(g.pied))
    return y + 4.5


def vers_pdf(rep: ReponseExacte, genere_le: datetime | None = None) -> bytes:
    from fpdf import FPDF  # chargé à la demande : seul le PDF en a besoin

    genere_le = genere_le or datetime.now(UTC)  # heure du Sénégal = UTC
    pdf = FPDF(format="A4", unit="mm")
    _polices(pdf)
    pdf.set_auto_page_break(False)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()
    largeur = pdf.w - 40

    # En-tête
    _baobab(pdf, 20, 19, 10)
    pdf.set_x(29)
    pdf.set_font("Poppins", "B", 18)
    pdf.set_text_color(*BAOBAB)
    pdf.cell(largeur / 2 - 9, 10, _texte("Gëstukaay"))
    pdf.set_font("Poppins", "", 9)
    pdf.set_text_color(*ARDOISE)
    pdf.multi_cell(largeur / 2, 4.5, _texte(f"Réponse officielle\ngénérée le {genere_le:%d/%m/%Y à %H:%M}"), align="R")
    pdf.set_draw_color(*BAOBAB)
    pdf.set_line_width(0.6)
    pdf.line(20, 32, pdf.w - 20, 32)

    # Question
    pdf.set_y(38)
    pdf.set_font("PoppinsSB", "", 8)
    pdf.set_text_color(*FEUILLE)
    pdf.cell(0, 5, _texte("QUESTION POSÉE"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Lora", "I", 13)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 6.5, _texte(f"« {rep.question} »"), new_x="LMARGIN", new_y="NEXT")

    # Badge
    pdf.ln(4)
    pdf.set_font("PoppinsSB", "", 9)
    pdf.set_text_color(*FEUILLE)
    pdf.cell(0, 5, _texte("Correspondance exacte"), new_x="LMARGIN", new_y="NEXT")
    # Décision 0002 : une projection ou une estimation est toujours étiquetée, jusque dans l'export
    autre = next((r for r in rep.resultats if r.nature in ("projection", "estimation")), None)
    if autre:
        etiquette = "Projection" if autre.nature == "projection" else "Estimation"
        base = f" · ce n'est pas une valeur observée. Base : {autre.base_projection}" if autre.base_projection             else " · ce n'est pas une valeur observée"
        pdf.set_font("PoppinsSB", "", 9)
        pdf.set_fill_color(*BAOBAB_50)
        pdf.set_text_color(*BAOBAB)
        pdf.multi_cell(largeur, 5.5, _texte(etiquette + base), fill=True, new_x="LMARGIN", new_y="NEXT")

    # Valeurs
    for r in rep.resultats:
        pdf.ln(2)
        pdf.set_font("Poppins", "", 10.5)
        pdf.set_text_color(*ARDOISE)
        libelle = f"{r.indicateur.libelle} · {r.zone.libelle} · {r.periode.libelle}"
        if rep.periode_par_defaut:
            libelle += " · dernière donnée publiée"
        pdf.multi_cell(largeur, 5.5, _texte(libelle), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Poppins", "B", 30)
        pdf.set_text_color(*BAOBAB)
        pdf.cell(pdf.get_string_width(_texte(r.valeur_affichee)) + 3, 13, _texte(r.valeur_affichee))
        pdf.set_font("Poppins", "", 12)
        pdf.set_text_color(*ARDOISE)
        pdf.cell(0, 15, _texte(r.unite), new_x="LMARGIN", new_y="NEXT")

    # Explication
    pdf.ln(2)
    pdf.set_font("Lora", "", 12)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 6, _texte(rep.explication), new_x="LMARGIN", new_y="NEXT")

    # Bloc source complet (obligatoire dans les exports, 5.4)
    sources = list({r.source.url: r.source for r in rep.resultats}.values())
    lignes = []
    for s in sources:
        lignes += [s.titre, s.libelle, s.url]
    if rep.note_perimetre:
        lignes.append(f"Périmètre : {rep.note_perimetre}")
    lignes.append(mention_licence_donnees(sources))
    # Hauteurs mesurées d'abord : fond Coton sous le texte, et place restante pour le graphique
    pdf.set_font("Poppins", "", 9.5)
    nb = sum(len(pdf.multi_cell(largeur - 12, 5, _texte(t), dry_run=True, output="LINES")) for t in lignes)
    h_source = 5 + 5 + nb * 5 + 4
    h_citation = 5 + 5 * len(pdf.multi_cell(largeur, 5, _texte(rep.citation), dry_run=True, output="LINES"))

    # Graphique (EF-26) : autant de barres que la page A4 unique le permet (8 au plus)
    g = rep.graphique
    if g and g.type == "barres_horizontales" and len(g.series) == 1 and g.series[0].points:
        y = pdf.get_y() + 6
        place = (pdf.h - 26) - (5 + h_source + 5 + h_citation) - y - 6 - 2 - 4.5 - 6
        n = min(BARRES_MAX, len(g.series[0].points), int(place // 6))
        if n >= 2:
            pdf.set_y(_barres(pdf, g, y, largeur, n))

    pdf.ln(5)
    y0 = pdf.get_y()
    y1 = y0 + h_source
    pdf.set_fill_color(*COTON)
    pdf.rect(20, y0, largeur, y1 - y0, style="F")
    pdf.set_y(y0 + 5)
    pdf.set_x(26)
    pdf.set_font("PoppinsSB", "", 10)
    pdf.set_text_color(*BAOBAB)
    pdf.cell(0, 5, "Source officielle", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Poppins", "", 9.5)
    pdf.set_text_color(*ENCRE)
    for ligne in lignes:
        pdf.set_x(26)
        pdf.multi_cell(largeur - 12, 5, _texte(ligne), new_x="LMARGIN", new_y="NEXT")

    # Citation (EF-35)
    pdf.set_y(y1 + 5)
    pdf.set_font("PoppinsSB", "", 8)
    pdf.set_text_color(*FEUILLE)
    pdf.cell(0, 5, "CITER CE CHIFFRE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Poppins", "", 9.5)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 5, _texte(rep.citation), new_x="LMARGIN", new_y="NEXT")

    # Pied : URL, licence, page
    pdf.set_draw_color(*LIN)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.h - 22, pdf.w - 20, pdf.h - 22)
    pdf.set_y(pdf.h - 19)
    pdf.set_font("Poppins", "", 8.5)
    pdf.set_text_color(*ARDOISE)
    pdf.cell(largeur * 0.55, 5, _texte(rep.url.replace("https://", "").replace("http://", "")))
    pdf.cell(largeur * 0.45, 5, _texte(f"Export Gëstukaay {LICENCE_EXPORT} · page 1/1"), align="R")
    return bytes(pdf.output())
