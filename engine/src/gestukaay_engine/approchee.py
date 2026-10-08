"""Correspondance approchée : transformer une demande sans valeur exacte en choix vérifiés (issue #12).

Principes non négociables :
  1. Zéro chiffre inventé : chaque choix proposé est résolu et vérifié par
     resolution.resoudre(socle, req) à l'avance. S'il ne donne aucune valeur,
     il n'est pas proposé.
  2. Aucune valeur numérique n'est affichée dans la réponse approchée (EF-06).
  3. Le cahier impose strictement 2 à 3 choix (min_length=2, max_length=3).
  4. Ordre de repli pour atteindre 2 à 3 choix :
     (a) zone parente, puis niveau au-dessus (département -> région -> Sénégal) ;
     (b) sinon la même zone à une autre période publiée ;
     (c) s'il ne reste qu'une option réelle vérifiée : repli sur ReponseAucune
         (hors_socle) avec cette option en suggestion.
  5. Reformulation : sans jargon (« les zones pour lesquelles l'ANSD publie ce chiffre »),
     une phrase, vouvoiement, se termine par « Est-ce ce que vous cherchez ? ».
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from gestukaay_contracts.models import (
    Choix,
    Periode,
    RefIndicateur,
    RequeteStructuree,
    Suggestion,
)
from gestukaay_socle.indicateurs import indicateurs
from gestukaay_socle.zones import normaliser, zones

from .resolution import Introuvable, Resolution, est_total, libelle_periode, resoudre
from .socle import Socle

REFERENTIELS = Path(__file__).resolve().parents[3] / "socle" / "referentiels"


@dataclass(frozen=True)
class Rattachement:
    type: str  # lieu | modalite
    terme: str
    propositions: tuple[str, ...]
    preuve: str


@cache
def rattachements() -> dict[str, Rattachement]:
    """Référentiel déclaratif des rattachements (socle/referentiels/rattachements.csv)."""
    f = REFERENTIELS / "rattachements.csv"
    if not f.exists():
        return {}
    with f.open(encoding="utf-8") as fh:
        declares = {
            normaliser(r["terme"]): Rattachement(
                type=r["type"],
                terme=r["terme"],
                propositions=tuple(p.strip() for p in r["propositions"].split("|") if p.strip()),
                preuve=r["preuve"],
            )
            for r in csv.DictReader(fh, delimiter=";")
        }
    return _villes_chefs_lieux() | declares  # une ligne déclarée prime


def _villes_chefs_lieux() -> dict[str, Rattachement]:
    """« la ville de Dakar » : le département du même nom, puis la région (recette du 08/10 : seules Thiès,
    Kaolack et Kolda étaient déclarées ; « ville de Dakar » finissait en « cette donnée n'existe pas »)."""
    out: dict[str, Rattachement] = {}
    for z in zones().values():
        if z.niveau not in ("region", "departement"):
            continue
        region = z if z.niveau == "region" else zones().get(z.parent or "")
        if region is None or normaliser(z.libelle_fr) != normaliser(region.libelle_fr):
            continue  # seul le département chef-lieu porte le nom de la ville
        dep = next((d.code for d in zones().values() if d.niveau == "departement" and d.parent == region.code
                    and normaliser(d.libelle_fr) == normaliser(region.libelle_fr)), None)
        cle = f"ville de {normaliser(region.libelle_fr)}"
        out[cle] = Rattachement("lieu", cle, tuple(c for c in (dep, region.code) if c),
                                "Commune chef-lieu du département et de la région du même nom (référentiel des zones)")
    return out


@dataclass(frozen=True)
class Approchee:
    reformulation: str
    choix: list[Choix]


@dataclass(frozen=True)
class RepliAucune:
    motif: Literal["hors_socle", "projection", "incomprehension"]
    message: str
    suggestions: list[Suggestion]


# Une approchée n'affiche aucun chiffre hors années (EF-06, volet (d) de l'invariant) : le « 5 » du sigle
# serait lu comme une valeur. Forme écrite pour ce seul sigle (#116, choix KBD), pas de règle générale.
SIGLES_SANS_CHIFFRE = {"RGPH-5": "recensement de 2023"}


def _nom_indicateur(code: str | None, langue: str = "fr") -> str:
    if not code:
        return "Cet indicateur"
    ind = indicateurs().get(code)
    if not ind:
        return code
    nom = ind.libelle_fr
    for sigle, forme in SIGLES_SANS_CHIFFRE.items():
        nom = nom.replace(sigle, forme)
    return nom


def _nom_zone(code: str, langue: str = "fr") -> str:
    z = zones().get(code)
    if not z:
        return code
    if z.niveau == "academie":
        return f"Inspection d'académie de {z.libelle_fr}" if not normaliser(
            z.libelle_fr).startswith(("academie", "ia")) else z.libelle_fr
    if z.niveau == "region":
        return f"Région de {z.libelle_fr}"
    if z.niveau == "departement":
        return f"Département de {z.libelle_fr}"
    return z.libelle_fr


_ARTICLES = (("Région de ", "la région de "), ("Département de ", "le département de "),
             ("Inspection d'académie de ", "l'inspection d'académie de "))


def _dans_la_phrase(nom: str) -> str:
    """« pour Département de Pikine » -> « pour le département de Pikine » (les listes de choix gardent la
    majuscule) ; « Sénégal » -> « le Sénégal » ; un lieu cité (« Touba ») reste tel quel."""
    for tete, article in _ARTICLES:
        if nom.startswith(tete):
            return article + nom[len(tete):]
    return "le Sénégal" if nom == "Sénégal" else nom


def _portee(requete: RequeteStructuree, langue: str = "fr") -> str:
    """Ce que le choix donnera, selon l'intention (US-03 : savoir ce qu'on va lire avant de confirmer)."""
    if requete.intention == "classement":  # même règle que la résolution : académies si publié ainsi
        ind = indicateurs().get(requete.indicateur or "")
        return ", par académie" if ind and "academie" in ind.niveaux_zone else ", par région"
    noms = [_nom_zone(z, langue) for z in requete.zones] or [_nom_zone("SN", langue)]
    return f" ({' et '.join(noms)})"


def _periode_texte(p: Periode) -> str:
    if p.type == "derniere" or not p.valeur:
        return "dernière période publiée"
    return libelle_periode(p.valeur)


def _lieu_cite(lieu: str) -> str:
    """« ville de Thiès » -> « la ville de Thiès » (#116) ; « Touba » inchangé."""
    if normaliser(lieu).startswith("ville "):
        tete, _, nom = lieu.partition(" de ")
        return f"la {tete} de {nom[:1].upper()}{nom[1:]}" if nom else f"la {lieu}"
    return lieu


def modalite_citee(requete: RequeteStructuree, question: str) -> Rattachement | None:
    """Modalité ambiguë de rattachements.csv citée dans la question (« voitures »), pour l'indicateur compris.

    None si l'utilisateur a déjà précisé la catégorie (dimension des propositions déjà fixée).
    """
    if not requete.indicateur:
        return None
    q_norm = normaliser(question)
    desag = requete.desagregation or {}
    for terme_cle, rat in rattachements().items():
        if rat.type != "modalite":
            continue
        if not (terme_cle in q_norm or (terme_cle == "voitures" and ("voiture" in q_norm or "woto" in q_norm))):
            continue
        props = [p.split(":", 1) for p in rat.propositions if ":" in p]
        if not any(requete.indicateur.startswith(jeu) for jeu, _ in props):
            continue
        dims = {a.split("=", 1)[0] for _, a in props}
        if dims & set(desag) and not any(_est_le_terme(v, terme_cle) for v in desag.values()):
            return None  # catégorie déjà précisée (« véhicules particuliers »)
        return rat
    return None


# Catégorie dite dans la question, parmi les propositions de rattachements.csv : pas de choix à proposer
_CATEGORIES_DITES = {"VPP": re.compile(r"\b(particuliers?|particulieres?|vpp)\b")}


def categorie_dite(requete: RequeteStructuree, question: str) -> RequeteStructuree | None:
    """« Combien de véhicules particuliers à Kolda ? » servait le parc TOTAL (9 317 au lieu de 5 000) :
    « véhicules » ne déclenche pas le choix des « voitures » et rien ne fixait la catégorie. Dite, elle est
    imposée ; sinon None."""
    if not requete.indicateur:
        return None
    q = normaliser(question)
    for rat in rattachements().values():
        if rat.type != "modalite":
            continue
        for prop in rat.propositions:
            jeu, _, assign = prop.partition(":")
            dim, _, val = assign.partition("=")
            motif = _CATEGORIES_DITES.get(val)
            if motif and requete.indicateur.startswith(jeu) and motif.search(q):
                return requete.model_copy(update={"desagregation": {**(requete.desagregation or {}), dim: val}})
    return None


def _est_le_terme(valeur: str, terme_cle: str) -> bool:
    """Le terme ambigu lui-même (« voitures ») n'est pas une catégorie publiée : il ne filtre rien."""
    v = normaliser(str(valeur))
    return v == terme_cle or v.rstrip("s") == terme_cle.rstrip("s")


def _verifier_choix(socle: Socle, req: RequeteStructuree, libelle: str,
                    choix_id: str) -> Choix | None:
    res = resoudre(socle, req)
    # publié, mais une catégorie reste à choisir (le cycle pour une académie) : valable, le cycle se demande
    # après le choix, en deux temps (KBD, 08/10 : « Combien d'écoles à Kolda ? » finissait en refus)
    ambigu = isinstance(res, Introuvable) and res.raison == "desagregation_ambigue"
    if ambigu or (isinstance(res, Resolution) and res.resultats):
        req_validee = req.model_copy(update={"confiance": 1.0})
        return Choix(id=choix_id, libelle=libelle, requete=req_validee)
    return None


def _distance_periode(p_cible: str, p_obs: str) -> float:
    """Distance temporelle entre deux périodes pour retenir les plus proches."""
    an_cible = int(p_cible[:4]) if p_cible[:4].isdigit() else 2024
    an_obs = int(p_obs[:4]) if p_obs[:4].isdigit() else 2024
    return abs(an_cible - an_obs)


def proposer_approchee(
    socle: Socle,
    requete: RequeteStructuree,
    introuvable: Introuvable | None,
    question: str = "",
    langue: str = "fr",
    lieux_inconnus: list[str] | None = None,
) -> Approchee | RepliAucune | None:
    """Génère une réponse approchée vérifiée (2 à 3 choix) ou bascule en refus (repli c)."""
    if not requete.indicateur:
        return None

    code_ind = requete.indicateur
    ind_obj = indicateurs().get(code_ind)
    q_norm = normaliser(question)
    candidats_choix: list[tuple[RequeteStructuree, str]] = []
    reformulation = ""
    nom_lieu_concerne = ""

    # -----------------------------------------------------------------------
    # Cas 1 : Modalité ambiguë déclarée dans rattachements.csv (ex. « voitures »)
    # -----------------------------------------------------------------------
    termes_modalite = {k: v for k, v in rattachements().items() if v.type == "modalite"}
    for terme_cle, rat in termes_modalite.items():
        if terme_cle in q_norm or (terme_cle == "voitures" and ("voiture" in q_norm or "woto" in q_norm)):
            for prop in rat.propositions:
                if ":" in prop:
                    jeu_prefix, assign = prop.split(":", 1)
                    if not code_ind.startswith(jeu_prefix):
                        continue
                else:
                    assign = prop
                if "=" in assign:
                    dim, val = assign.split("=", 1)
                    # « produit = voitures » (LLM) ferait échouer chaque choix : on le retire (#116)
                    desag = {k: v for k, v in (requete.desagregation or {}).items()
                             if not _est_le_terme(v, terme_cle)}
                    desag[dim] = val
                    req_c = requete.model_copy(update={"desagregation": desag})
                    nom = "Ensemble du parc de véhicules" if val.upper() == "TOTAL" else \
                        f"Véhicules particuliers ({val})"
                    lib = f"{nom}{_portee(requete, langue)}"
                    candidats_choix.append((req_c, lib))
            if candidats_choix:
                reformulation = (
                    "Veuillez préciser la catégorie souhaitée pour le nombre de voitures. "
                    "Est-ce ce que vous cherchez ?"
                )
                break

    # -----------------------------------------------------------------------
    # Cas 2 : Dimension ambiguë avec plusieurs modalités (introuvable.choix)
    # -----------------------------------------------------------------------
    if not candidats_choix and introuvable and introuvable.choix:
        dim, modalites = next(iter(introuvable.choix.items()))
        # Critère déterministe :
        # 1. Nommées dans la question
        # 2. Plus fréquentes dans le jeu
        # 3. Total exclu
        mods_utiles = [m for m in modalites if not est_total(m)]

        def _score_mod(m: str) -> tuple[int, int]:
            mention = 1 if normaliser(m) in q_norm else 0
            freq = sum(1 for o in socle.observations(code_ind) if o.dims().get(dim) == m)
            return (-mention, -freq)

        mods_utiles.sort(key=_score_mod)
        for m in mods_utiles[:5]:
            desag = dict(requete.desagregation or {})
            desag[dim] = m
            req_c = requete.model_copy(update={"desagregation": desag})
            z_code = requete.zones[0] if requete.zones else "SN"
            lib = f"{m} ({_nom_zone(z_code, langue)})"
            candidats_choix.append((req_c, lib))
        reformulation = (
            "Veuillez préciser la catégorie souhaitée parmi celles pour lesquelles l'ANSD publie ce chiffre. "
            "Est-ce ce que vous cherchez ?"
        )

    # -----------------------------------------------------------------------
    # Cas 3 : Lieu inconnu / hors référentiel (Touba, ville de Thiès...)
    # -----------------------------------------------------------------------
    if not candidats_choix and lieux_inconnus:
        lieu_brut = lieux_inconnus[0]
        nom_lieu_concerne = _lieu_cite(lieu_brut)
        lieu_norm = normaliser(lieu_brut)
        rat = rattachements().get(lieu_norm)
        if rat and rat.type == "lieu":
            # Ordre de repli (a) de la 0015 : après les zones déclarées, les niveaux au-dessus.
            # La population (RGPH-5) n'est publiée que par région : Touba -> Diourbel, puis Sénégal.
            zones_cand = list(rat.propositions)
            cur = zones().get(zones_cand[-1]) if zones_cand else None
            while cur and cur.parent:
                zones_cand.append(cur.parent)
                cur = zones().get(cur.parent)
            for z_cand in dict.fromkeys(zones_cand):  # sans doublon, quel que soit l'ordre déclaré
                req_c = requete.model_copy(update={"zones": [z_cand]})
                p_txt = _periode_texte(requete.periode)
                lib = f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(z_cand, langue)} ({p_txt})"
                candidats_choix.append((req_c, lib))
            reformulation = (
                f"Ce chiffre n'est pas publié pour {_lieu_cite(lieu_brut)} ; "
                "voici les zones pour lesquelles l'ANSD publie ce chiffre. Est-ce ce que vous cherchez ?"
            )

    # -----------------------------------------------------------------------
    # Cas 4 : Zone non couverte (niveau hiérarchique ou multi-académies)
    # -----------------------------------------------------------------------
    if not candidats_choix and introuvable and introuvable.raison == "zone_non_couverte":
        z_demandee = requete.zones[0] if requete.zones else "SN"
        z_obj = zones().get(z_demandee)
        nom_lieu_concerne = _nom_zone(z_demandee, langue)
        est_academique = "academie" in (ind_obj.niveaux_zone if ind_obj else ())

        # 4a. Multi-académies (ex. Dakar pour ervtjfc si indicateur académique)
        academies_couvrantes = [
            z for z in zones().values()
            if z.niveau == "academie" and z.parent == z_demandee
        ] if est_academique else []

        if academies_couvrantes:
            academies_couvrantes.sort(key=lambda a: a.code)
            for a in academies_couvrantes:
                req_c = requete.model_copy(update={"zones": [a.code]})
                p_txt = _periode_texte(requete.periode)
                lib = f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(a.code, langue)} ({p_txt})"
                candidats_choix.append((req_c, lib))
            reformulation = (
                f"Les statistiques scolaires de la région de {z_obj.libelle_fr if z_obj else z_demandee} "
                "sont publiées par inspection d'académie. Est-ce ce que vous cherchez ?"
            )
        else:
            # 4b. Ordre de repli (a) : zone parente, puis niveau au-dessus (département -> région -> Sénégal)
            parents = []
            cur = z_obj
            while cur and cur.parent:
                parents.append(cur.parent)
                cur = zones().get(cur.parent)

            for pz in parents:
                req_c = requete.model_copy(update={"zones": [pz]})
                p_txt = _periode_texte(requete.periode)
                lib = f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(pz, langue)} ({p_txt})"
                candidats_choix.append((req_c, lib))

            reformulation = (
                f"Ce chiffre n'est pas publié pour {_dans_la_phrase(_nom_zone(z_demandee, langue))} ; "
                "voici les zones pour lesquelles l'ANSD publie ce chiffre. Est-ce ce que vous cherchez ?"
            )

    # -----------------------------------------------------------------------
    # Cas 5 : Période absente (ex. 2023 pour jcvcajc, 2026 pour dwibrlf)
    # -----------------------------------------------------------------------
    if not candidats_choix and introuvable and introuvable.raison == "periode_absente":
        p_demandee = requete.periode.valeur or "2024"
        z_code = requete.zones[0] if requete.zones else "SN"
        nom_lieu_concerne = _nom_zone(z_code, langue)

        # Récupérer toutes les périodes publiées pour cet indicateur et cette zone
        periodes_publiees = sorted(
            {o.periode for o in socle.observations(code_ind) if o.zone == z_code},
            key=lambda p: (_distance_periode(p_demandee, p), p),
        )
        for p in periodes_publiees[:4]:
            req_c = requete.model_copy(update={"periode": Periode(type="annee", valeur=p)})
            lib = f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(z_code, langue)} en {libelle_periode(p)}"
            candidats_choix.append((req_c, lib))

        reformulation = (
            f"Ce chiffre n'a pas été publié pour l'année {p_demandee} ; "
            "voici les années les plus proches pour lesquelles l'ANSD publie ce chiffre. "
            "Est-ce ce que vous cherchez ?"
        )

    # -----------------------------------------------------------------------
    # Cas 6 : précision citée non publiée pour cette zone (« pauvreté rurale à Kaffrine », recette du 08/10 :
    # refus « cette donnée n'existe pas ») -> la zone sans la précision, puis le Sénégal avec la précision
    # -----------------------------------------------------------------------
    if not candidats_choix and introuvable and introuvable.raison == "desagregation_absente" and requete.desagregation:
        z_code = requete.zones[0] if requete.zones else "SN"
        nom_lieu_concerne = _nom_zone(z_code, langue)
        precision = ", ".join(requete.desagregation.values())
        candidats_choix.append((requete.model_copy(update={"desagregation": None}),
                                f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(z_code, langue)}"))
        if z_code != "SN":
            candidats_choix.append((requete.model_copy(update={"zones": ["SN"]}),
                                    f"{_nom_indicateur(code_ind, langue)} ({precision}) - {_nom_zone('SN', langue)}"))
        reformulation = (
            f"Ce chiffre n'est pas publié ({precision}) pour {nom_lieu_concerne} ; "
            "voici les chiffres les plus proches que l'ANSD publie. Est-ce ce que vous cherchez ?"
        )

    # -----------------------------------------------------------------------
    # Vérification stricte de chaque choix par resolution.resoudre
    # -----------------------------------------------------------------------
    choix_valides: list[Choix] = []
    vus: set[tuple[str, str, str]] = set()

    for req_cand, libelle in candidats_choix:
        ch = _verifier_choix(socle, req_cand, libelle, str(len(choix_valides) + 1))
        if ch:
            z_cle = ch.requete.zones[0] if ch.requete.zones else "SN"
            p_cle = ch.requete.periode.valeur or "derniere"
            d_cle = str(ch.requete.desagregation)
            if (z_cle, p_cle, d_cle) not in vus:
                vus.add((z_cle, p_cle, d_cle))
                choix_valides.append(ch)
        if len(choix_valides) == 3:
            break

    # -----------------------------------------------------------------------
    # Ordre de repli (b) : si 1 seul choix obtenu sur zone parente,
    # proposer la même zone parente à une autre période publiée
    # -----------------------------------------------------------------------
    if len(choix_valides) == 1 and introuvable and introuvable.raison == "zone_non_couverte":
        pz = choix_valides[0].requete.zones[0] if choix_valides[0].requete.zones else "SN"
        periodes_autres = sorted(
            {o.periode for o in socle.observations(code_ind) if o.zone == pz},
            reverse=True,
        )
        p_actuelle = choix_valides[0].requete.periode.valeur or (
            periodes_autres[0] if periodes_autres else ""
        )
        for pa in periodes_autres:
            if pa != p_actuelle:
                req_b = choix_valides[0].requete.model_copy(
                    update={"periode": Periode(type="annee", valeur=pa)}
                )
                lib_b = f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(pz, langue)} en {libelle_periode(pa)}"
                ch_b = _verifier_choix(socle, req_b, lib_b, "2")
                if ch_b:
                    ch1_mis_a_jour = Choix(
                        id="1",
                        libelle=(f"{_nom_indicateur(code_ind, langue)} - {_nom_zone(pz, langue)} "
                                 f"en {libelle_periode(p_actuelle)}"),
                        requete=choix_valides[0].requete,
                    )
                    choix_valides = [ch1_mis_a_jour, ch_b]
                    break

    # -----------------------------------------------------------------------
    # Arbitrage final (2 à 3 choix -> Approchee, 1 seul -> Repli c Refus)
    # -----------------------------------------------------------------------
    if len(choix_valides) >= 2:
        return Approchee(reformulation=reformulation, choix=choix_valides[:3])

    if len(choix_valides) == 1:
        # Cas (c) : une seule option réelle -> réponse aucune (hors socle) en suggestion
        lieu_nom = nom_lieu_concerne or (
            _nom_zone(requete.zones[0], langue) if requete.zones else "cette zone"
        )
        ref_ind = RefIndicateur(code=code_ind, libelle=_nom_indicateur(code_ind, langue))
        sugg = Suggestion(indicateur=ref_ind, question_suggeree=choix_valides[0].libelle)
        msg = f"Cette statistique n'est pas disponible pour {_dans_la_phrase(lieu_nom)}."
        return RepliAucune(motif="hors_socle", message=msg, suggestions=[sugg])

    # 0 choix valide -> Refus hors socle complet
    lieu_nom = nom_lieu_concerne or (
        _nom_zone(requete.zones[0], langue) if requete.zones else "cette zone"
    )
    msg = f"Cette donnée n'est pas publiée par l'ANSD pour {_dans_la_phrase(lieu_nom)}."
    return RepliAucune(motif="hors_socle", message=msg, suggestions=[])
