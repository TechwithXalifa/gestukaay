"""Exports d'une réponse exacte : CSV (EF-34) et PDF A4 d'une page (EF-33).

Les valeurs ne sont jamais recalculées ni reformatées : le CSV donne `valeur`
(brute) et le PDF affiche `valeur_affichee` (formatée par le moteur, 7.4).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from gestukaay_contracts.models import ReponseExacte

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
    return ("﻿" + sortie.getvalue()).encode("utf-8")


# ---- PDF -------------------------------------------------------------------

BAOBAB, FEUILLE, ARDOISE, ENCRE, LIN, COTON = (
    (29, 68, 72), (15, 110, 86), (92, 104, 103), (26, 26, 24), (228, 223, 213), (246, 242, 234),
)


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
    pdf.set_font("Poppins", "B", 18)
    pdf.set_text_color(*BAOBAB)
    pdf.cell(largeur / 2, 10, _texte("Gëstukaay"))
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
    pdf.ln(5)
    y0 = pdf.get_y()
    # Hauteur mesurée d'abord, pour dessiner le fond Coton sous le texte
    pdf.set_font("Poppins", "", 9.5)
    nb = sum(len(pdf.multi_cell(largeur - 12, 5, _texte(t), dry_run=True, output="LINES")) for t in lignes)
    y1 = y0 + 5 + 5 + nb * 5 + 4
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
    licences = ", ".join(sorted({s.licence for s in sources}))
    pdf.cell(largeur * 0.6, 5, _texte(rep.url.replace("https://", "").replace("http://", "")))
    pdf.cell(largeur * 0.4, 5, _texte(f"Licence {licences} · page 1/1"), align="R")
    return bytes(pdf.output())
