"""Exports d'une réponse exacte : CSV (EF-34) et PDF A4 d'une page (EF-33), fiche statistique officielle.

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


# ---- PDF : fiche statistique officielle (charte v2, décision 0036) ------------------------------------
#
# Une page A4 pensée pour l'impression, pas une copie de la page web : bandeau sombre et frise de la
# marque ; titre = l'indicateur (la question n'est qu'un rappel) ; chiffre clé à côté d'une fiche
# technique ; lecture ; mise en perspective (barres) ; source et citation en deux colonnes ; pied.
# Polices de la charte, auto-hébergées (OFL) : Unbounded (titres, chiffre), Bricolage Grotesque
# (texte), Space Mono (repères, sources).

SOMBRE, FOND, CARTE = (23, 17, 11), (246, 240, 227), (255, 253, 248)
ENCRE, ENCRE_DOUCE, LIGNE = (28, 20, 13), (107, 93, 76), (227, 215, 192)
SUR_SOMBRE, SUR_SOMBRE_DOUX = (246, 240, 227), (191, 176, 154)
BAOBAB, BAOBAB_50, OR, OR_CLAIR, LATERITE = (29, 68, 72), (225, 235, 232), (217, 149, 46), (226, 189, 107), (164, 71, 43)
EXACTE, PROJECTION, PROJECTION_50 = (15, 110, 86), (90, 74, 140), (233, 228, 243)
DATA_NEUTRE = (213, 199, 173)
BARRES_MAX = 8  # comme la page réponse

MARGE = 18.0
POLICES = Path(__file__).parent / "polices"  # licence OFL : voir les fichiers OFL-*.txt

_MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
         "novembre", "décembre")


def _texte(t: str) -> str:
    """Tout caractère passe (’, «, ñ, ë, ŋ). L'espace fine insécable (U+202F), absente d'Unbounded et de
    Space Mono, devient l'insécable ordinaire, visuellement identique."""
    return t.replace(chr(0x202F), chr(0xA0))


def _date(d) -> str:
    return f"{'1er' if d.day == 1 else d.day} {_MOIS[d.month - 1]} {d.year}"


def _polices(pdf) -> None:
    pdf.add_font("Unbounded", "", POLICES / "Unbounded-SemiBold.ttf")
    pdf.add_font("Unbounded", "B", POLICES / "Unbounded-Bold.ttf")
    pdf.add_font("Bricolage", "", POLICES / "BricolageGrotesque-Regular.ttf")
    pdf.add_font("Bricolage", "B", POLICES / "BricolageGrotesque-Bold.ttf")
    pdf.add_font("BricolageSB", "", POLICES / "BricolageGrotesque-SemiBold.ttf")
    pdf.add_font("Mono", "", POLICES / "SpaceMono-Regular.ttf")
    pdf.add_font("Mono", "B", POLICES / "SpaceMono-Bold.ttf")


# Logo baobab : même tracé que le SVG de la charte (viewBox 33 × 43)
_TRONC = [((16, 20.7), (16, 36.4)), ((16, 36.4), (10.8, 40.8)), ((16, 36.4), (21.3, 40.8))]
_BRANCHES = [(2.9, 12), (10.5, 4.2), (18.2, 2.1), (25.8, 5.3), (30.2, 14.1)]


def _baobab(pdf, x: float, y: float, hauteur: float, couleur=BAOBAB) -> None:
    k = hauteur / 43
    pdf.set_draw_color(*couleur)
    pdf.set_fill_color(*couleur)
    pdf.set_line_width(2.2 * k)
    for (x1, y1), (x2, y2) in _TRONC + [((16, 20.7), b) for b in _BRANCHES]:
        pdf.line(x + x1 * k, y + y1 * k, x + x2 * k, y + y2 * k)
    for bx, by in _BRANCHES:
        r = 2.3 * k
        pdf.ellipse(x + bx * k - r, y + by * k - r, 2 * r, 2 * r, style="F")


def _frise(pdf, y: float, cote: float) -> None:
    """La frise de la marque (décision 0036 §3), en tuiles carrées sur toute la largeur de la page."""
    x, i = 0.0, 0
    while x < pdf.w:
        c, k = i % 6, cote / 28
        fond = (BAOBAB, FOND, LATERITE, OR, ENCRE, FOND)[c]
        pdf.set_fill_color(*fond)
        pdf.rect(x, y, cote, cote, style="F")
        if c == 0:  # demi-disque : un disque crème posé sur le bas
            pdf.set_fill_color(*FOND)
            pdf.ellipse(x + 4 * k, y + 12 * k, 20 * k, 20 * k, style="F")
            pdf.set_fill_color(*BAOBAB)
            pdf.rect(x, y + cote, cote, 6 * k, style="F")  # recouvert par la suite de la page (fond blanc)
        elif c == 1:  # point d'or
            pdf.set_fill_color(*OR)
            pdf.ellipse(x + 7 * k, y + 7 * k, 14 * k, 14 * k, style="F")
        elif c == 2:  # histogramme
            pdf.set_fill_color(*FOND)
            for bx, hb in ((5, 8), (12, 13), (19, 18)):
                pdf.rect(x + bx * k, y + (24 - hb) * k, 4 * k, hb * k, style="F")
        elif c == 3:  # quart de disque sombre
            pdf.set_fill_color(*ENCRE)
            pdf.polygon([(x, y + cote), (x, y), (x + cote, y + cote)], style="F")
        elif c == 4:  # trait et nœud
            pdf.set_draw_color(*FOND)
            pdf.set_line_width(2.5 * k)
            pdf.line(x + 6 * k, y + 23 * k, x + 19 * k, y + 10 * k)
            pdf.set_fill_color(*OR_CLAIR)
            pdf.ellipse(x + 16.8 * k, y + 5.8 * k, 6.4 * k, 6.4 * k, style="F")
        else:  # deux barres
            pdf.set_fill_color(*BAOBAB)
            pdf.rect(x + 5 * k, y + 9 * k, 18 * k, 4 * k, style="F")
            pdf.rect(x + 5 * k, y + 16 * k, 11 * k, 4 * k, style="F")
        x += cote
        i += 1


def _sceau(pdf, x: float, y: float, d: float, couleur, projection: bool = False) -> None:
    """Pastille : coche claire pour un chiffre publié (même idée que le sceau du site), courbe montante
    pour une projection ou une estimation, qui n'est jamais présentée comme une valeur certifiée."""
    pdf.set_fill_color(*couleur)
    pdf.ellipse(x, y, d, d, style="F")
    pdf.set_draw_color(*CARTE)
    pdf.set_line_width(d * 0.12)
    if projection:
        pdf.line(x + d * 0.24, y + d * 0.66, x + d * 0.44, y + d * 0.46)
        pdf.line(x + d * 0.44, y + d * 0.46, x + d * 0.56, y + d * 0.58)
        pdf.line(x + d * 0.56, y + d * 0.58, x + d * 0.76, y + d * 0.36)
    else:
        pdf.line(x + d * 0.28, y + d * 0.52, x + d * 0.44, y + d * 0.68)
        pdf.line(x + d * 0.44, y + d * 0.68, x + d * 0.74, y + d * 0.34)


def _intitule(pdf, x: float, y: float, texte: str, couleur=ENCRE_DOUCE) -> None:
    """Petit repère en capitales, Space Mono espacé (rubriques de la fiche)."""
    pdf.set_xy(x, y)
    pdf.set_font("Mono", "B", 6.8)
    pdf.set_text_color(*couleur)
    pdf.set_char_spacing(0.9)
    pdf.cell(0, 4, _texte(texte.upper()))
    pdf.set_char_spacing(0)


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
    return texte.replace(",", chr(0xA0)).replace(".", ",")


def _lignes(pdf, largeur: float, texte: str) -> int:
    return len(pdf.multi_cell(largeur, 4, _texte(texte), dry_run=True, output="LINES", align="L"))


def _barres(pdf, g, y: float, largeur: float, n: int) -> float:
    """Mise en perspective : barres horizontales, n au plus, la zone demandée toujours visible et en
    baobab. Rend le y de fin."""
    points = list(g.series[0].points)  # ordre du moteur (classement possible, #14)
    visibles = points[:n]
    for p in points[n:]:
        if p.mise_en_evidence:
            visibles[-1] = p
    maxi = max((p.y for p in points), default=0) or 1
    pdf.set_xy(MARGE, y)
    pdf.set_font("BricolageSB", "", 9)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 4.6, _texte(g.titre), align="L", new_x="LMARGIN", new_y="NEXT")
    y = pdf.get_y() + 2.5
    col, valeur = 40.0, 26.0
    x_axe, piste = MARGE + col + 3, largeur - col - 3 - valeur
    pas = 6.2
    pdf.set_draw_color(*LIGNE)
    pdf.set_line_width(0.25)
    pdf.line(x_axe, y - 0.5, x_axe, y + len(visibles) * pas)
    for i, p in enumerate(visibles):
        yb = y + i * pas
        fort = p.mise_en_evidence
        pdf.set_font("BricolageSB" if fort else "Bricolage", "", 8.3)
        pdf.set_text_color(*(ENCRE if fort else ENCRE_DOUCE))
        pdf.set_xy(MARGE, yb)
        pdf.cell(col, pas, _texte(p.x), align="R")
        w = max(p.y / maxi * piste, 0.6)
        pdf.set_fill_color(*(BAOBAB if fort else DATA_NEUTRE))
        pdf.rect(x_axe, yb + 1.4, w, pas - 2.8, style="F", round_corners=("TOP_RIGHT", "BOTTOM_RIGHT"),
                 corner_radius=0.8)
        pdf.set_xy(x_axe + w + 1.8, yb)
        pdf.set_font("Mono", "B" if fort else "", 7.6)
        pdf.set_text_color(*(ENCRE if fort else ENCRE_DOUCE))
        pdf.cell(valeur, pas, _texte(_nombre(p.y)))
    y += len(visibles) * pas + 2
    pdf.set_xy(MARGE, y)
    pdf.set_font("Mono", "", 6.6)
    pdf.set_text_color(*ENCRE_DOUCE)
    pdf.cell(largeur, 3.6, _texte(g.pied))
    return y + 3.6


def vers_pdf(rep: ReponseExacte, genere_le: datetime | None = None) -> bytes:
    from fpdf import FPDF  # chargé à la demande : seul le PDF en a besoin

    genere_le = genere_le or datetime.now(UTC)  # heure du Sénégal = UTC
    pdf = FPDF(format="A4", unit="mm")
    _polices(pdf)
    pdf.set_auto_page_break(False)
    pdf.set_margins(MARGE, MARGE, MARGE)
    pdf.add_page()
    largeur = pdf.w - 2 * MARGE
    r0 = rep.resultats[0]
    sources = list({r.source.url: r.source for r in rep.resultats}.values())

    # ---- Bandeau sombre et frise --------------------------------------------------------------
    pdf.set_fill_color(*SOMBRE)
    pdf.rect(0, 0, pdf.w, 30, style="F")
    _baobab(pdf, MARGE, 8.2, 13.5, SUR_SOMBRE)
    pdf.set_xy(MARGE + 11, 8.6)
    pdf.set_font("Unbounded", "B", 16)
    pdf.set_text_color(*SUR_SOMBRE)
    pdf.cell(80, 8, _texte("Gëstukaay"))
    _intitule(pdf, MARGE + 11.2, 17.8, "Fiche statistique officielle", OR_CLAIR)
    pdf.set_font("Mono", "", 7)
    pdf.set_text_color(*SUR_SOMBRE_DOUX)
    pdf.set_xy(pdf.w - MARGE - 70, 9.5)
    pdf.cell(70, 4, _texte(f"Réf. {rep.id}"), align="R")
    pdf.set_xy(pdf.w - MARGE - 70, 14)
    pdf.cell(70, 4, _texte(f"Éditée le {_date(genere_le)} à {genere_le:%H:%M} (GMT)"), align="R")
    pdf.set_xy(pdf.w - MARGE - 70, 18.5)
    pdf.cell(70, 4, _texte("Données : ANSD et producteurs officiels"), align="R")
    _frise(pdf, 30, 5)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 35, pdf.w, 2, style="F")

    # ---- Titre : l'indicateur, puis la zone et la période ---------------------------------------
    y = 43
    _intitule(pdf, MARGE, y, "Indicateur")
    pdf.set_xy(MARGE, y + 5)
    pdf.set_font("Unbounded", "", 15.5)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 7.2, _texte(r0.indicateur.libelle), align="L", new_x="LMARGIN", new_y="NEXT")
    zones_txt = " et ".join(dict.fromkeys(r.zone.libelle for r in rep.resultats))
    sous = f"{zones_txt} · {r0.periode.libelle}"
    if rep.periode_par_defaut:
        sous += " · dernière donnée publiée"
    pdf.set_font("Bricolage", "", 10.5)
    pdf.set_text_color(*ENCRE_DOUCE)
    pdf.multi_cell(largeur, 5.4, _texte(sous), align="L", new_x="LMARGIN", new_y="NEXT")

    # Statut : certifié, ou projection / estimation toujours étiquetée (décision 0002), jusque dans l'export
    y = pdf.get_y() + 3
    autre = next((r for r in rep.resultats if r.nature in ("projection", "estimation")), None)
    if autre:
        etiquette = "Projection" if autre.nature == "projection" else "Estimation"
        statut = f"{etiquette} : ce n'est pas une valeur observée"
        if autre.base_projection:
            statut += f". Base : {autre.base_projection}"
        couleur, fond = PROJECTION, PROJECTION_50
    else:
        statut, couleur, fond = "Correspondance exacte · chiffre publié, retrouvé tel quel", EXACTE, CARTE
    pdf.set_font("BricolageSB", "", 8.6)
    w_statut = min(pdf.get_string_width(_texte(statut)) + 13, largeur)
    pdf.set_fill_color(*fond)
    pdf.set_draw_color(*LIGNE)
    pdf.set_line_width(0.25)
    pdf.rect(MARGE, y, w_statut, 7, style="DF", round_corners=True, corner_radius=3.5)
    _sceau(pdf, MARGE + 2.4, y + 1.6, 3.8, couleur, projection=bool(autre))
    pdf.set_xy(MARGE + 7.6, y)
    pdf.set_text_color(*ENCRE)
    pdf.cell(w_statut - 9, 7, _texte(statut))

    # ---- Chiffre clé et fiche technique ---------------------------------------------------------
    y += 12
    g_larg = largeur * 0.58
    d_x, d_larg = MARGE + g_larg + 6, largeur - g_larg - 6
    lignes_fiche = [
        ("Zone", zones_txt),
        ("Période", r0.periode.libelle),
        ("Producteur", " · ".join(dict.fromkeys(s.producteur for s in sources))),
        ("Opération", " · ".join(dict.fromkeys(s.operation or s.titre for s in sources))),
        ("Publiée le", " · ".join(dict.fromkeys(_date(s.date_publication) for s in sources))),
        ("Nature", "Projection" if autre and autre.nature == "projection" else
         "Estimation" if autre else "Valeur observée"),
    ]
    pdf.set_font("Bricolage", "", 8.6)
    c_larg = (d_larg - 8 - 4) / 2  # fiche technique sur deux colonnes
    rangs = [lignes_fiche[k:k + 2] for k in range(0, len(lignes_fiche), 2)]
    h_rangs = [3.6 + 4.2 * max(_lignes(pdf, c_larg, v) for _, v in rang) + 2.2 for rang in rangs]
    h_fiche = 10.5 + sum(h_rangs) + 1.5
    plusieurs = len(rep.resultats) > 1
    tailles = [(24 if plusieurs else 30) if len(r.valeur_affichee) <= 11 else (18 if plusieurs else 22)
               for r in rep.resultats]
    hauteurs = [(5 if plusieurs else 0) + t * 0.45 + (5 if plusieurs else 0) for t in tailles]
    contenu = sum(hauteurs)
    h_chiffres = 10 + contenu + 6
    h_bloc = max(h_fiche, h_chiffres)
    # gauche : le ou les chiffres, sur fond crème
    pdf.set_fill_color(*FOND)
    pdf.rect(MARGE, y, g_larg, h_bloc, style="F", round_corners=True, corner_radius=3)
    pdf.set_fill_color(*OR)
    pdf.rect(MARGE, y + 6, 1.4, h_bloc - 12, style="F")
    if autre:
        nom = "Projection officielle" if autre.nature == "projection" else "Estimation officielle"
        nom = nom.replace("officielle", "officielles").replace("ion ", "ions ") if plusieurs else nom
    else:
        nom = "Chiffres officiels" if plusieurs else "Chiffre officiel"
    _intitule(pdf, MARGE + 7, y + 6, nom)
    yy = y + 10 + max(0.0, (h_bloc - 10 - contenu) / 2)  # centré dans le bloc
    for r, taille in zip(rep.resultats, tailles, strict=True):
        if plusieurs:
            pdf.set_xy(MARGE + 7, yy)
            pdf.set_font("BricolageSB", "", 9)
            pdf.set_text_color(*ENCRE_DOUCE)
            pdf.cell(g_larg - 14, 4.5, _texte(f"{r.zone.libelle} · {r.periode.libelle}"))
            yy += 5
        pdf.set_xy(MARGE + 7, yy)
        pdf.set_font("Unbounded", "B", taille)
        pdf.set_text_color(*BAOBAB)
        pdf.cell(pdf.get_string_width(_texte(r.valeur_affichee)) + 2.5, taille * 0.45, _texte(r.valeur_affichee))
        pdf.set_font("Bricolage", "", 11)
        pdf.set_text_color(*ENCRE_DOUCE)
        pdf.cell(0, taille * 0.45 + 2, _texte(r.unite or ""))
        yy += taille * 0.45 + (5 if plusieurs else 0)
    # droite : fiche technique
    pdf.set_fill_color(*CARTE)
    pdf.set_draw_color(*LIGNE)
    pdf.rect(d_x, y, d_larg, h_bloc, style="DF", round_corners=True, corner_radius=3)
    _intitule(pdf, d_x + 4, y + 4.5, "Fiche technique")
    yy = y + 10.5
    for rang, h_rang in zip(rangs, h_rangs, strict=True):
        for j, (etiquette, valeur) in enumerate(rang):
            cx_f = d_x + 4 + j * (c_larg + 4)
            pdf.set_xy(cx_f, yy)
            pdf.set_font("Mono", "", 6.4)
            pdf.set_text_color(*ENCRE_DOUCE)
            pdf.cell(c_larg, 3.4, _texte(etiquette.upper()))
            pdf.set_xy(cx_f, yy + 3.6)
            pdf.set_font("Bricolage", "", 8.6)
            pdf.set_text_color(*ENCRE)
            pdf.multi_cell(c_larg, 4.2, _texte(valeur), align="L")
        yy += h_rang

    # ---- Lecture --------------------------------------------------------------------------------
    y += h_bloc + 7
    _intitule(pdf, MARGE, y, "Lecture")
    pdf.set_xy(MARGE, y + 5)
    pdf.set_font("Bricolage", "", 10.4)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(largeur, 5.3, _texte(rep.explication), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Mono", "", 6.8)
    pdf.set_text_color(*ENCRE_DOUCE)
    pdf.multi_cell(largeur, 3.8, _texte(f"Question posée à Gëstukaay : « {rep.question} »"), align="L", new_x="LMARGIN",
                   new_y="NEXT")
    y_lecture = pdf.get_y()

    # ---- Bas de page : source et citation, mesurés d'abord (place restante pour le graphique) --------
    col = (largeur - 6) / 2
    src = []
    for s in sources:
        src += [s.titre, s.libelle, s.url]
    if rep.note_perimetre:
        src.append(f"Périmètre : {rep.note_perimetre}")
    src.append(mention_licence_donnees(sources))
    pdf.set_font("Bricolage", "", 8.2)
    h_src = 11 + sum(4 * _lignes(pdf, col - 9, t) for t in src) + 3
    pdf.set_font("Mono", "", 7.2)
    h_cit = 11 + 3.9 * _lignes(pdf, col - 11, rep.citation) + 3
    h_bas = max(h_src, h_cit)
    y_pied = pdf.h - 16
    y_bas = y_pied - 6 - h_bas  # au plus bas ; remonté sous le contenu s'il reste de la place
    y_fin = y_lecture

    # ---- Mise en perspective (EF-26) : autant de barres que la page unique le permet ----------------
    g = rep.graphique
    if g and g.type == "barres_horizontales" and len(g.series) == 1 and g.series[0].points:
        y = y_lecture + 6
        place = y_bas - 6 - (y + 5 + 4.6 + 2.5 + 2 + 3.6)
        n = min(BARRES_MAX, len(g.series[0].points), int(place // 6.2))
        if n >= 2:
            _intitule(pdf, MARGE, y, "Mise en perspective")
            y_fin = _barres(pdf, g, y + 5, largeur, n)
    y_bas = min(y_bas, y_fin + 9)

    # Source et méthode
    pdf.set_fill_color(*FOND)
    pdf.rect(MARGE, y_bas, col, h_bas, style="F", round_corners=True, corner_radius=3)
    _intitule(pdf, MARGE + 5, y_bas + 4.5, "Source et méthode", BAOBAB)
    pdf.set_xy(MARGE + 5, y_bas + 10)
    for i, t in enumerate(src):
        pdf.set_x(MARGE + 5)
        pdf.set_font("BricolageSB" if i == 0 else "Bricolage", "", 8.2)
        pdf.set_text_color(*(ENCRE if i < 2 else ENCRE_DOUCE))
        pdf.multi_cell(col - 9, 4, _texte(t), align="L", new_x="LMARGIN", new_y="NEXT")
    # Citer ce chiffre (EF-35)
    cx = MARGE + col + 6
    pdf.set_fill_color(*CARTE)
    pdf.set_draw_color(*LIGNE)
    pdf.rect(cx, y_bas, col, h_bas, style="DF", round_corners=True, corner_radius=3)
    pdf.set_fill_color(*OR)
    pdf.rect(cx, y_bas + 5, 1.4, h_bas - 10, style="F")
    _intitule(pdf, cx + 6, y_bas + 4.5, "Citer ce chiffre", BAOBAB)
    pdf.set_xy(cx + 6, y_bas + 10)
    pdf.set_font("Mono", "", 7.2)
    pdf.set_text_color(*ENCRE)
    pdf.multi_cell(col - 11, 3.9, _texte(rep.citation), align="L", new_x="LMARGIN", new_y="NEXT")

    # ---- Pied -------------------------------------------------------------------------------------
    pdf.set_draw_color(*LIGNE)
    pdf.set_line_width(0.3)
    pdf.line(MARGE, y_pied, pdf.w - MARGE, y_pied)
    _baobab(pdf, MARGE, y_pied + 2.6, 4.2)
    pdf.set_xy(MARGE + 4.5, y_pied + 2.3)
    pdf.set_font("Mono", "", 6.8)
    pdf.set_text_color(*ENCRE_DOUCE)
    pdf.cell(largeur * 0.5, 4.5, _texte(rep.url.replace("https://", "").replace("http://", "")))
    pdf.set_xy(MARGE + largeur * 0.5, y_pied + 2.3)
    pdf.cell(largeur * 0.5, 4.5, _texte(f"Export Gëstukaay {LICENCE_EXPORT} · page 1/1"), align="R")
    return bytes(pdf.output())
