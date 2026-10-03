"""Extraction du socle brut vers le schéma du cahier (10.3) : issue #4.

Une ligne par valeur publiée :
    indicateur | zone | période | désagrégation | valeur | unité | source

Décisions (#4) :
  - valeurs gardées telles que publiées, sans recalcul. La colonne `echelle`
    du portail n'est PAS un multiplicateur : les valeurs sont déjà en unités
    pleines (4 023 500 000 000 FCFA, echelle 10⁹ = « affiché en milliards ») ;
  - zone : colonne géographique du jeu (même règle que la couverture des
    zones : au moins 3 zones distinctes rattachées). « Total » / « Ensemble »
    dans cette colonne = Sénégal seulement si elle couvre les 14 régions ;
    sinon rejeté (total ambigu) ;
  - jeu sans colonne géographique : code région du portail s'il y en a un,
    sinon l'exception déclarée dans `zones_par_jeu.csv` (feujxob = Dakar),
    sinon Sénégal, marqué `zone_presumee` (à confirmer à la vérification) ;
  - rien ne disparaît sans trace : chaque valeur écartée va dans les rejets
    avec son motif ; chaque valeur gardée remonte à sa ligne d'origine ;
  - les corrections (Thiès permuté, unités incrémentées…) viennent après,
    en #6 : ici on extrait fidèlement ce que publie le portail.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .indicateurs import REFERENTIELS, Indicateur, dimensions_indicateur, valeur_indicateur
from .zones import motif_non_rattache, niveau_de_colonne, normaliser, resoudre, zones

FICHIER_ZONES_PAR_JEU = REFERENTIELS / "zones_par_jeu.csv"

COLONNES_OBSERVATIONS = (
    "observation_id", "indicateur", "zone", "zone_presumee", "periode", "desagregation", "valeur",
    "unite", "echelle", "source_id", "nature", "ligne_origine",
)
COLONNES_REJETS = ("ligne_origine", "dataset_id", "indicateur", "motif", "detail")
COLONNES_SOURCES = (
    "source_id", "producteur", "organisme", "titre", "date_publication", "derniere_maj", "licence",
    "url", "url_producteur",
)

# Une zone plus fine l'emporte : « région = Dakar, département = Pikine » -> Pikine
_RANG = {"pays": 0, "region": 1, "departement": 2, "academie": 2}


def periode(p: str, freq: str) -> str:
    """Période du portail -> 2023, 2026-03, 2023-T2, 2024-05-17."""
    if freq == "M":
        return p[:7]
    if freq == "Q":
        return f"{p[:4]}-T{(int(p[5:7]) - 1) // 3 + 1}"
    if freq == "D":
        return p[:10]
    return p[:4]


def observation_id(dataset_id: str, periode_brute: str, dims: dict, unite: str) -> str:
    """Empreinte stable d'une valeur : ne dépend que de ce que publie le portail."""
    cle = "|".join((dataset_id, periode_brute, json.dumps(dims, ensure_ascii=False, sort_keys=True), unite))
    return hashlib.sha1(cle.encode()).hexdigest()[:16]


def zones_par_jeu() -> dict[str, str]:
    """Zone déclarée d'un jeu sans colonne géographique : autre que le Sénégal (feujxob = Dakar),
    ou Sénégal confirmé à la vérification (la valeur n'est alors plus « présumée »)."""
    with FICHIER_ZONES_PAR_JEU.open(encoding="utf-8") as f:
        return {r["dataset_id"]: r["zone"] for r in csv.DictReader(f, delimiter=";")}


def colonnes_geo(lignes: Iterable[dict]) -> dict[str, dict[str, bool]]:
    """Jeu -> {colonne géographique: couvre les 14 régions ?}. Une colonne est
    géographique DANS UN JEU dès que 3 zones distinctes y sont rattachées."""
    vus: dict[tuple[str, str], set] = defaultdict(set)
    for ligne in lignes:
        if not ligne["valeur"]:
            continue
        for col, v in json.loads(ligne["desagregation_json"] or "{}").items():
            if isinstance(v, str) and (code := resoudre(v, niveau_de_colonne(col))):
                vus[(ligne["dataset_id"], col)].add(code)
    z = zones()
    out: dict[str, dict[str, bool]] = defaultdict(dict)
    for (ds, col), codes in vus.items():
        if len(codes) >= 3:
            out[ds][col] = sum(z[c].niveau == "region" for c in codes) == 14
    return dict(out)


def zone_de_ligne(dims: dict, geo: dict[str, bool], region_id: str,
                  exception: str | None) -> tuple[str | None, bool, str]:
    """(code de zone ou None, zone présumée ?, motif du rejet)."""
    if exception:
        return exception, False, ""
    if not geo:  # jeu sans colonne géographique
        if region_id in zones():
            return region_id, False, ""
        return "SN", True, ""
    trouves, totaux, motifs = [], [], []
    for col, national in geo.items():
        v = dims.get(col)
        if not isinstance(v, str):
            continue
        if code := resoudre(v, niveau_de_colonne(col)):
            trouves.append(code)
        elif (m := motif_non_rattache(v)) == "total":
            totaux.append(national)
        else:
            motifs.append(f"{m} : {v}")
    if motifs:  # plus fin que le référentiel (arrondissement…) ou inconnu
        return None, False, motifs[0]
    if trouves:
        rang = max(_RANG[zones()[c].niveau] for c in trouves)
        fins = {c for c in trouves if _RANG[zones()[c].niveau] == rang}
        if len(fins) > 1:
            return None, False, f"zones contradictoires : {', '.join(sorted(fins))}"
        return fins.pop(), False, ""
    if totaux:
        return ("SN", False, "") if any(totaux) else (None, False, "total ambigu (colonne non nationale)")
    if region_id in zones():
        return region_id, False, ""
    return None, False, "sans zone"


def index_indicateurs(indicateurs: dict[str, Indicateur]) -> dict[tuple[str, str, str], Indicateur]:
    """(jeu, valeur « Indicateur » normalisée, unité) -> indicateur du référentiel."""
    out = {}
    for x in indicateurs.values():
        for v in x.valeur_portail.split("|") if x.valeur_portail else [""]:
            out[(x.dataset_id, normaliser(v), x.unite)] = x
    return out


@dataclass
class Resultat:
    observations: list[tuple]
    rejets: list[tuple]
    stats: Counter


def extraire(lignes: Iterable[tuple[int, dict]], geo: dict[str, dict[str, bool]],
             index: dict[tuple[str, str, str], Indicateur], exceptions: dict[str, str]) -> Resultat:
    """lignes : (numéro de ligne dans observations.csv, ligne du portail)."""
    stats: Counter = Counter()
    rejets: list[tuple] = []
    par_cle: dict[tuple, list[tuple]] = defaultdict(list)
    for n, ligne in lignes:
        if not ligne["valeur"]:
            continue
        stats["valeurs lues"] += 1
        ds = ligne["dataset_id"]
        dims = json.loads(ligne["desagregation_json"] or "{}")
        cles = dimensions_indicateur(dims)
        valeur_ind = valeur_indicateur(dims)
        unite = ligne["unite"].strip()
        ind = index.get((ds, normaliser(valeur_ind), unite))
        if ind is None or ind.verification == "ecarte":
            motif = "indicateur absent du référentiel" if ind is None else "indicateur écarté"
            rejets.append((n, ds, ind.code if ind else "", motif, valeur_ind))
            continue
        geo_ds = geo.get(ds, {})
        zone, presumee, motif = zone_de_ligne(dims, geo_ds, ligne["region_id"] or "", exceptions.get(ds))
        if zone is None:
            rejets.append((n, ds, ind.code, motif.split(" : ")[0], motif))
            continue
        desag = {k: v for k, v in dims.items() if k not in cles and k not in geo_ds}
        desag_json = json.dumps(desag, ensure_ascii=False, sort_keys=True)
        per = periode(ligne["periode"], ligne["frequence"])
        par_cle[(ind.code, zone, per, desag_json)].append((
            observation_id(ds, ligne["periode"], dims, unite), ind.code, zone, "oui" if presumee else "",
            per, desag_json, ligne["valeur"], unite, ligne["echelle"], ds, "", n,
        ))

    observations = []
    for (code, zone, per, _), groupe in par_cle.items():
        if len({float(o[6]) for o in groupe}) == 1:  # doublons identiques : une seule valeur
            observations.append(groupe[0])
            stats["doublons identiques fusionnés"] += len(groupe) - 1
        else:  # deux valeurs pour la même clé : #6 tranchera
            for o in groupe:
                rejets.append((o[11], o[9], code, "doublon conflictuel",
                               f"{zone} {per} : " + " / ".join(sorted({x[6] for x in groupe}))))
    observations.sort(key=lambda o: (o[1], o[2], o[4], o[5]))
    rejets.sort(key=lambda r: r[0])
    stats["valeurs extraites"] = len(observations)
    stats["valeurs rejetées"] = len(rejets)
    return Resultat(observations, rejets, stats)
