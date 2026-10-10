"""Menu à boutons de WhatsApp et Telegram : naviguer sans savoir formuler une question.

« menu » (ou « thèmes », « /themes ») ouvre les thèmes ; un thème donne des questions qui marchent ; une question
touchée part au moteur comme si elle avait été écrite. « région » (ou « /region ») ouvre les 14 régions, par pages
de 7 (une liste WhatsApp a 10 lignes au plus) ; une région donne ses questions types.

Questions vérifiées sur le moteur réel (réponse exacte le 10/10). Textes en français : les questions en wolof et
les titres des menus en wolof sont à écrire par KBD (décision 0009 ; colonne « wo » de textes.csv).
Identifiants des boutons courts (Telegram : 64 octets au plus) : « menu-t3 », « menu-q3-1 », « menu-r-SN-KD »…
"""

from __future__ import annotations

from dataclasses import dataclass

PREFIXE = "menu-"
PAR_PAGE = 7

THEMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Population", ("Combien d'habitants à Thiès ?", "Quel est le taux d'urbanisation au Sénégal ?",
                    "Combien d'enfants par femme au Sénégal ?")),
    ("Emploi", ("Quel est le taux de chômage au Sénégal ?", "Chômage à Dakar et à Thiès en 2024")),
    ("Prix", ("Combien coûte le kilo de riz brisé au détail ?", "Quel est l'indice des prix à la consommation ?")),
    ("Éducation", ("Quel est le taux de scolarisation à Dakar ?",)),
    ("Santé", ("Quelle proportion des enfants sont complètement vaccinés à Kolda ?",
               "Quelle est la mortalité des enfants de moins de 5 ans au Sénégal ?")),
    ("Pauvreté", ("Quel est le taux de pauvreté à Kolda ?", "Quel est l'indice de Gini au Sénégal ?")),
    ("Énergie et eau", ("Quel est le taux d'électrification au Sénégal ?",
                        "Quelle est la part des ménages avec un robinet dans le logement ?")),
    ("Économie", ("Quel est le PIB du Sénégal ?",)),
)
QUESTIONS_REGION = ("Combien d'habitants à {r} ?", "Quel est le taux de pauvreté à {r} ?",
                    "Quel est le taux de chômage à {r} ?", "Quel est le taux de scolarisation à {r} ?")


@dataclass(frozen=True)
class Bouton:
    id: str
    libelle: str


@dataclass(frozen=True)
class Menu:
    titre: str  # clé de textes.csv
    boutons: tuple[Bouton, ...]
    complement: str = ""  # nom du thème ou de la région, ajouté au titre


# Les 14 régions du référentiel des zones (socle/referentiels/zones.csv, décision 0003), par ordre alphabétique
REGIONS = (
    ("SN-DK", "Dakar"), ("SN-DB", "Diourbel"), ("SN-FK", "Fatick"), ("SN-KA", "Kaffrine"), ("SN-KL", "Kaolack"),
    ("SN-KE", "Kédougou"), ("SN-KD", "Kolda"), ("SN-LG", "Louga"), ("SN-MT", "Matam"), ("SN-SL", "Saint-Louis"),
    ("SN-SE", "Sédhiou"), ("SN-TC", "Tambacounda"), ("SN-TH", "Thiès"), ("SN-ZG", "Ziguinchor"),
)


def regions() -> list[tuple[str, str]]:
    return list(REGIONS)


def themes() -> Menu:
    return Menu("menu_themes", tuple(Bouton(f"{PREFIXE}t{i}", nom) for i, (nom, _) in enumerate(THEMES)))


def liste_regions(page: int = 0) -> Menu:
    toutes = regions()
    morceau = toutes[page * PAR_PAGE:(page + 1) * PAR_PAGE]
    boutons = [Bouton(f"{PREFIXE}r-{code}", nom) for code, nom in morceau]
    if (page + 1) * PAR_PAGE < len(toutes):
        boutons.append(Bouton(f"{PREFIXE}rp{page + 1}", "Autres régions →"))
    elif page > 0:
        boutons.append(Bouton(f"{PREFIXE}rp0", "← Premières régions"))
    return Menu("menu_regions", tuple(boutons))


def reagir(ident: str) -> Menu | str | None:
    """Ce que donne un bouton touché : un menu à envoyer, une question à poser, ou None (bouton inconnu)."""
    cle = ident.removeprefix(PREFIXE)
    try:
        if cle.startswith("q"):  # question d'un thème : « q3-1 »
            t, q = (int(x) for x in cle[1:].split("-"))
            return THEMES[t][1][q]
        if cle.startswith("t"):  # un thème : ses questions
            t = int(cle[1:])
            nom, questions = THEMES[t]
            return Menu("menu_questions", tuple(Bouton(f"{PREFIXE}q{t}-{i}", q) for i, q in enumerate(questions)), nom)
        if cle.startswith("rp"):  # page de régions
            return liste_regions(int(cle[2:]))
        if cle.startswith("rq-"):  # question d'une région : « rq-SN-KD-2 »
            code, i = cle[3:].rsplit("-", 1)
            return QUESTIONS_REGION[int(i)].format(r=dict(regions())[code])
        if cle.startswith("r-"):  # une région : ses questions
            code = cle[2:]
            nom = dict(regions())[code]
            return Menu("menu_questions", tuple(Bouton(f"{PREFIXE}rq-{code}-{i}", q.format(r=nom))
                                                for i, q in enumerate(QUESTIONS_REGION)), nom)
    except (ValueError, IndexError, KeyError):
        return None
    return None
