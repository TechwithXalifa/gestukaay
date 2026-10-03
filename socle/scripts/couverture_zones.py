"""Rapport de couverture du référentiel des zones sur le socle réel (issue #2).

    uv run python socle/scripts/couverture_zones.py

Lit $GESTUKAAY_SOCLE_BRUT/observations.csv (défaut : ../socle_opendata_par_themes)
et écrit socle/rapports/couverture_zones.md : pour chaque colonne géographique,
quels libellés sont rattachés à un code, lesquels sont écartés et pourquoi.

Une colonne est jugée géographique JEU PAR JEU : dans un jeu donné, elle l'est
dès que 3 de ses libellés distincts sont rattachables. (La même colonne
« regions » contient 15 régions dans un jeu et 700 arrondissements dans un
autre : un critère global la ferait ignorer partout.) Les couples (jeu,
colonne) avec 1 ou 2 libellés rattachables sont listés pour vérification.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from gestukaay_socle.zones import niveau_de_colonne, normaliser, resoudre, zones

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
SORTIE = RACINE / "socle" / "rapports" / "couverture_zones.md"

ECARTES = {"total", "totaux", "all", "ensemble", "ensemble national", "communes"}
# Arrondissements et communes, toutes abréviations du portail (Arrond, ARD., ARDT, COOMUNE…)
INFRA = re.compile(
    r"^(arrondissement|arrond|ardt|ard|ca|commune|coomune|cmc|cr|communaute rurale|ville de|quartier) "
)
# Regroupements qui ne sont pas des zones administratives : points cardinaux, pôles,
# couples de régions, zones agricoles, régions dans leurs limites d'une année passée.
NON_ADMIN = re.compile(
    r"^zone |^(nord|sud|est|ouest|centre)( |$)| et |^pole |"
    r"^(notto diosmone palmarain|gorom lampsar|saint louis matam)$| (19|20)\d\d$"
)

STATUT_ECARTE = "écarté : total ambigu, traité jeu par jeu (#4)"
STATUT_INFRA = "infra-départemental : hors référentiel (décision #2)"
STATUT_NON_ADMIN = "regroupement non administratif ou historique : hors référentiel"
STATUT_NON = "**non rattaché**"


def statut(val: str, cle: str) -> str | None:
    """None si rattaché, sinon la raison."""
    if resoudre(val, niveau_de_colonne(cle)):
        return None
    n = normaliser(val)
    if n in ECARTES:
        return STATUT_ECARTE
    if INFRA.match(n):
        return STATUT_INFRA
    if NON_ADMIN.search(n):
        return STATUT_NON_ADMIN
    return STATUT_NON


def lire():
    """(jeu, colonne) -> Counter(libellé), compteurs globaux, contrôle des codes portail."""
    csv.field_size_limit(2**31 - 1)  # sys.maxsize déborde sous Windows (long C sur 32 bits)
    libelles: dict[tuple[str, str], Counter] = defaultdict(Counter)
    portail: Counter = Counter()
    desaccords: Counter = Counter()
    non_vides = 0
    with open(SOCLE / "observations.csv", encoding="utf-8-sig", newline="") as f:
        for ligne in csv.DictReader(f):
            if not ligne["valeur"]:
                continue
            non_vides += 1
            rid = ligne["region_id"] or ""
            portail["sans code" if not rid else "SN" if rid.startswith("SN") else "étranger"] += 1
            try:
                dims = json.loads(ligne["desagregation_json"] or "{}")
            except ValueError:
                continue
            for cle, val in dims.items():
                if not isinstance(val, str):
                    continue
                libelles[(ligne["dataset_id"], cle)][val] += 1
                # code région du portail (fiable) contre notre rattachement
                if len(rid) == 5 and rid.startswith("SN-"):
                    code = resoudre(val, niveau_de_colonne(cle))
                    if code and zones()[code].niveau == "region" and code != rid:
                        desaccords[(cle, val, rid, code)] += 1
    return libelles, portail, desaccords, non_vides


def classer(libelles):
    geo: dict[str, Counter] = defaultdict(Counter)  # colonne -> libellés (jeux géo seulement)
    jeux: dict[str, set] = defaultdict(set)
    proches = []
    for (ds, cle), compte in libelles.items():
        ok = sum(1 for v in compte if resoudre(v, niveau_de_colonne(cle)))
        if ok >= 3:
            geo[cle].update(compte)
            jeux[cle].add(ds)
        elif ok >= 1:
            proches.append((ds, cle, ok, len(compte), [v for v in compte if resoudre(v)][:3]))
    return geo, jeux, proches


def rapport(libelles, portail, desaccords, non_vides):
    geo, jeux, proches = classer(libelles)
    par_statut: Counter = Counter()
    par_niveau: Counter = Counter()
    blocs = []
    for cle in sorted(geo, key=lambda k: -sum(geo[k].values())):
        compte, niv = geo[cle], niveau_de_colonne(cle)
        manquants: dict[str, list] = defaultdict(list)
        for val, n in compte.most_common():
            s = statut(val, cle)
            if s is None:
                par_niveau[zones()[resoudre(val, niv)].niveau] += n
                par_statut["rattaché"] += n
            else:
                par_statut[s] += n
                manquants[s].append((val, n))
        titre = (f"### `{cle}` — {len(compte)} libellés, {sum(compte.values())} valeurs, "
                 f"{len(jeux[cle])} jeux" + (f" · niveau imposé : {niv}" if niv else ""))
        blocs += [titre, ""]
        if not manquants:
            blocs += ["Tous les libellés sont rattachés.", ""]
            continue
        blocs += ["| Libellé | Valeurs | Statut |", "|---|---|---|"]
        for s in (STATUT_NON, STATUT_ECARTE, STATUT_NON_ADMIN):
            blocs += [f"| {v} | {n} | {s} |" for v, n in manquants.get(s, [])]
        infra = manquants.get(STATUT_INFRA, [])
        if infra:
            exemples = ", ".join(v for v, _ in infra[:4])
            blocs.append(f"| *{len(infra)} libellés* (ex. {exemples}) | {sum(n for _, n in infra)}"
                         f" | {STATUT_INFRA} |")
        blocs.append("")

    tot = sum(par_statut.values())
    rat = par_statut["rattaché"]
    L = ["# Couverture du référentiel des zones", "",
         (f"Socle : `{SOCLE.name}/observations.csv` · référentiel : `socle/referentiels/zones.csv`"
          " (1 pays, 14 régions, 46 départements, 16 académies)."), "",
         "## Résumé", "", "| | Valeurs |", "|---|---|",
         f"| Valeurs non vides du socle | {non_vides} |",
         f"| Valeurs portant un libellé géographique | {tot} |",
         f"| → rattachées à une zone | {rat} ({100 * rat / tot:.2f} %) |",
         (f"|   dont pays / régions / départements / académies | {par_niveau['pays']}"
          f" / {par_niveau['region']} / {par_niveau['departement']} / {par_niveau['academie']} |"),
         f"| → infra-départementales, hors référentiel (décision #2) | {par_statut[STATUT_INFRA]} |",
         f"| → regroupements non administratifs ou historiques | {par_statut[STATUT_NON_ADMIN]} |",
         f"| → écartées volontairement (Total, ALL…) | {par_statut[STATUT_ECARTE]} |",
         f"| → **non rattachées** | **{par_statut[STATUT_NON]}** |", "",
         "Codes du portail (`region_id`) sur les valeurs non vides : "
         + ", ".join(f"{k} {v}" for k, v in portail.most_common()) + ".", "",
         "## Contrôle : codes région du portail contre notre rattachement", ""]
    if desaccords:
        L += ["| Colonne | Libellé | Code portail | Notre code | Valeurs |", "|---|---|---|---|---|"]
        L += [f"| {c} | {v} | {p} | {g} | {n} |" for (c, v, p, g), n in desaccords.most_common(30)]
    else:
        L.append("Aucun désaccord.")
    L += ["", f"## Colonnes géographiques ({len(geo)})", ""] + blocs
    L += ["## Colonnes avec 1 ou 2 libellés rattachables (non comptées, à vérifier)", "",
          "| Jeu | Colonne | Rattachables / distincts | Exemples rattachés |", "|---|---|---|---|"]
    L += [f"| {ds} | `{c}` | {ok} / {n} | {', '.join(ex)} |" for ds, c, ok, n, ex in sorted(proches)]
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
    return tot, rat, par_statut


def main() -> None:
    if not (SOCLE / "observations.csv").exists():
        sys.exit(f"{SOCLE}/observations.csv introuvable : définir GESTUKAAY_SOCLE_BRUT.")
    tot, rat, par_statut = rapport(*lire())
    print(f"{tot} valeurs géographiques : {rat} rattachées ({100 * rat / tot:.2f} %), "
          f"{par_statut[STATUT_INFRA]} infra-départementales, {par_statut[STATUT_ECARTE]} écartées, "
          f"{par_statut[STATUT_NON]} non rattachées")
    print(f"Rapport : {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
