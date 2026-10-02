"""Inventaire des indicateurs du socle (issue #3, décision 0005).

    uv run python socle/scripts/inventaire_indicateurs.py

Lit $GESTUKAAY_SOCLE_BRUT/{catalogue,observations}.csv (défaut :
../socle_opendata_par_themes) et le jeu de test, puis écrit :
  - socle/referentiels/indicateurs.csv : un indicateur par ligne
    (jeu × valeur « Indicateur » × unité) ;
  - socle/rapports/indicateurs.md : comptes par domaine, couverture des
    100 questions, anomalies.

Relançable : les colonnes remplies à la main (libellé FR corrigé, wolof,
vérification, note) sont reprises du fichier existant, jamais écrasées.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from gestukaay_socle.indicateurs import (
    COLONNES,
    FICHIER,
    MANUELLES,
    codes,
    dimensions_indicateur,
    domaines,
    est_dimension_indicateur,
    libelle,
    nom_du_jeu,
    valeur_indicateur,
)
from gestukaay_socle.zones import niveau_de_colonne, normaliser, resoudre, zones

RACINE = Path(__file__).resolve().parents[2]
SOCLE = Path(os.environ.get("GESTUKAAY_SOCLE_BRUT", RACINE.parent / "socle_opendata_par_themes"))
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
RAPPORT = RACINE / "socle" / "rapports" / "indicateurs.md"
NIVEAUX = ("pays", "region", "departement", "academie")


@dataclass
class Cumul:
    """Ce que l'on sait d'un indicateur après lecture de ses valeurs."""

    nb: int = 0
    variantes: Counter = field(default_factory=Counter)  # graphies de la valeur « Indicateur »
    debut: tuple[str, str] = ("9999", "")  # (période brute, fréquence)
    fin: tuple[str, str] = ("", "")
    frequences: Counter = field(default_factory=Counter)
    echelles: set = field(default_factory=set)
    dims: set = field(default_factory=set)  # clés hors « Indicateur »
    niveaux_col: dict = field(default_factory=lambda: defaultdict(set))  # colonne -> niveaux
    niveaux_portail: set = field(default_factory=set)  # d'après region_id


def periode(p: str, freq: str) -> str:
    """Période du portail -> format du jeu de test : 2023, 2026-03, 2023-T2, 2024-05-17."""
    if freq == "M":
        return p[:7]
    if freq == "Q":
        return f"{p[:4]}-T{(int(p[5:7]) - 1) // 3 + 1}"
    if freq == "D":
        return p[:10]
    return p[:4]


def lire_catalogue() -> dict[str, dict]:
    with open(SOCLE / "catalogue.csv", encoding="utf-8-sig", newline="") as f:
        return {r["dataset_id"]: r for r in csv.DictReader(f)}


def lire_observations():
    """(jeu, valeur Indicateur normalisée, unité) -> Cumul ; clé de la dimension Indicateur
    par jeu ; libellés rattachables par (jeu, colonne), pour juger les colonnes géographiques.

    La valeur « Indicateur » est normalisée (casse, accents) : le portail écrit parfois le
    même indicateur de deux façons dans un jeu (« Effectif » / « effectif »). Les graphies
    sont gardées pour l'extraction."""
    csv.field_size_limit(sys.maxsize)
    cumuls: dict[tuple[str, str, str], Cumul] = defaultdict(Cumul)
    cle_indic: dict[str, str] = {}
    geo: dict[tuple[str, str], set] = defaultdict(set)
    with open(SOCLE / "observations.csv", encoding="utf-8-sig", newline="") as f:
        for ligne in csv.DictReader(f):
            if not ligne["valeur"]:
                continue
            ds = ligne["dataset_id"]
            try:
                dims = json.loads(ligne["desagregation_json"] or "{}")
            except ValueError:
                dims = {}
            cles = dimensions_indicateur(dims)
            if cles:
                cle_indic[ds] = "+".join(cles)
            valeur = valeur_indicateur(dims)
            c = cumuls[(ds, normaliser(valeur), ligne["unite"].strip())]
            c.nb += 1
            c.variantes[valeur] += 1
            p, fq = ligne["periode"], ligne["frequence"]
            c.debut, c.fin = min(c.debut, (p, fq)), max(c.fin, (p, fq))
            c.frequences[fq] += 1
            c.echelles.add(ligne["echelle"])
            rid = ligne["region_id"] or ""
            if rid == "SN":
                c.niveaux_portail.add("pays")
            elif len(rid) == 5 and rid.startswith("SN-"):
                c.niveaux_portail.add("region")
            for k, v in dims.items():
                if k in cles:
                    continue
                c.dims.add(k)
                if isinstance(v, str) and (code := resoudre(v, niveau_de_colonne(k))):
                    geo[(ds, k)].add(v)
                    c.niveaux_col[k].add(zones()[code].niveau)
    return cumuls, cle_indic, geo


def lire_jeu_de_test() -> list[dict]:
    with open(JEU, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def rattacher_questions(questions, identites) -> dict[tuple, list[str]]:
    """Identité d'indicateur -> questions du jeu qui l'utilisent (dataset_id + filtres + unité)."""
    par_jeu = defaultdict(list)
    for i in identites:
        par_jeu[i[0]].append(i)
    out = defaultdict(list)
    for q in questions:
        if not q["dataset_id"]:
            continue
        filtres = json.loads(q["filtres"] or "{}")
        v = valeur_indicateur(filtres)
        cand = [i for i in par_jeu[q["dataset_id"]] if not v or i[1] == normaliser(v)]
        # plusieurs unités pour le même indicateur : celle de la question, si elle est donnée
        meme_unite = [i for i in cand if q["unite"] and normaliser(i[2]) == normaliser(q["unite"])]
        for i in meme_unite or cand:
            out[i].append(q["id"])
    return out


def lire_existant() -> dict[str, dict]:
    if not FICHIER.exists():
        return {}
    with FICHIER.open(encoding="utf-8") as f:
        return {r["code"]: r for r in csv.DictReader(f, delimiter=";")}


def departager(lignes) -> None:
    """Deux indicateurs ne doivent pas porter le même libellé (catalogue, compréhension).
    Les libellés générés en double reçoivent le nom du jeu, puis l'unité, puis la période.
    Un libellé écrit à la main n'est jamais modifié."""
    etapes = (
        (lambda r: r["dataset_id"], lambda r: f" — {nom_du_jeu(r['jeu'])}"),
        (lambda r: r["unite"], lambda r: f" ({r['unite'] or 'sans unité'})"),
        (lambda r: (r["periode_debut"], r["periode_fin"]), lambda r: f" ({r['periode_debut']}–{r['periode_fin']})"),
    )
    for distinguer, suffixe in etapes:
        groupes = defaultdict(list)
        for r in lignes:
            groupes[normaliser(r["libelle_fr"])].append(r)
        for g in groupes.values():
            if len(g) > 1 and len({distinguer(r) for r in g}) > 1:
                for r in g:
                    if r["_auto"] and suffixe(r).strip(" —()") not in r["libelle_fr"]:
                        r["libelle_fr"] += suffixe(r)


def construire(catalogue, cumuls, cle_indic, geo, questions):
    doms = domaines()
    inconnus = sorted({catalogue[ds]["theme"] for ds, _, _ in cumuls} - doms.keys())
    if inconnus:
        sys.exit(f"Thèmes absents de domaines.csv : {inconnus}")
    geo_cols = {k for k, v in geo.items() if len(v) >= 3}  # même règle que couverture_zones
    les_codes = codes(list(cumuls))
    usages = rattacher_questions(questions, cumuls)
    existant = lire_existant()
    lignes = []
    for i, c in cumuls.items():
        ds, _, unite = i
        valeur = c.variantes.most_common(1)[0][0]  # graphie la plus fréquente
        cat = catalogue[ds]
        dom = doms[cat["theme"]]
        niveaux = set(c.niveaux_portail)
        for col, nivs in c.niveaux_col.items():
            if (ds, col) in geo_cols:
                niveaux |= nivs
        qs = sorted(set(usages.get(i, [])))
        code = les_codes[i]
        ligne = {
            "code": code, "dataset_id": ds, "libelle_fr": libelle(cat["nom"], valeur, mesure_seule=bool(valeur) and not
                                                          est_dimension_indicateur(cle_indic[ds].split("+")[0])),
            "libelle_wo": "", "statut_wo": "", "unite": unite, "unite_affichee": "", "domaine": dom.domaine,
            "priorite": "P1" if qs else "P2" if dom.questions_types else "P3",
            "verification": "a_verifier" if dom.domaine else "ecarte",
            "questions_test": "|".join(qs), "producteur": cat["producteur"],
            "niveaux_zone": "|".join(n for n in NIVEAUX if n in niveaux),
            "desagregations": "|".join(sorted(k for k in c.dims if (ds, k) not in geo_cols)),
            "frequence": "|".join(f for f, _ in c.frequences.most_common()),
            "periode_debut": periode(*c.debut), "periode_fin": periode(*c.fin),
            "nb_valeurs": str(c.nb), "dimension_indicateur": cle_indic.get(ds, "") if valeur else "",
            "valeur_portail": "|".join(sorted(c.variantes)) if valeur else "", "jeu": cat["nom"],
            "note": "" if dom.domaine else dom.note,
        }
        ligne["_auto"] = code not in existant or not existant[code]["libelle_fr"]
        if code in existant:  # le travail fait à la main est conservé
            ligne.update({k: existant[code].get(k, "") for k in MANUELLES if existant[code].get(k)})
        lignes.append(ligne)
    departager(lignes)
    ordre = {d.domaine: n for n, d in enumerate(sorted(doms.values(), key=lambda d: (not d.questions_types, d.domaine)))}
    lignes.sort(key=lambda r: (r["priorite"], ordre.get(r["domaine"], 99), r["dataset_id"], r["code"]))
    perdus = sorted(set(existant) - {r["code"] for r in lignes})
    return lignes, perdus


def ecrire(lignes) -> None:
    with FICHIER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def rapport(lignes, questions, cumuls, perdus) -> list[str]:
    par_code = {r["code"]: r for r in lignes}
    par_question = defaultdict(list)
    for r in lignes:
        for q in filter(None, r["questions_test"].split("|")):
            par_question[q].append(r["code"])
    retenus = [r for r in lignes if r["verification"] != "ecarte"]

    L = ["# Inventaire des indicateurs", "",
         (f"Socle : `{SOCLE.name}/` · référentiel : `socle/referentiels/indicateurs.csv` · "
          "règle : un indicateur = jeu × valeur « Indicateur » × unité (décision 0005)."), "",
         "## Résumé", "", "| | Nombre |", "|---|---|",
         f"| Indicateurs retenus | {len(retenus)} |",
         f"| Jeux du portail | {len({r['dataset_id'] for r in retenus})} |",
         f"| Domaines | {len({r['domaine'] for r in retenus})} |"]
    for p, titre in (("P1", "jeu de test"), ("P2", "domaines des questions types"), ("P3", "autres")):
        L.append(f"| Priorité {p} ({titre}) | {sum(r['priorite'] == p for r in retenus)} |")
    L += [f"| Vérifiés à la main | {sum(r['verification'] == 'verifie' for r in retenus)} |",
          f"| Avec un libellé wolof | {sum(bool(r['libelle_wo']) for r in retenus)} |",
          f"| Écartés | {len(lignes) - len(retenus)} |", ""]
    if perdus:
        L += [(f"**Attention** : {len(perdus)} code(s) du référentiel précédent ont disparu du socle "
              f"(travail manuel perdu ?) : {', '.join(perdus[:20])}"), ""]

    L += ["## Par domaine", "", "| Domaine | Indicateurs | Jeux | P1 | P2 | P3 | Régionaux |",
          "|---|---|---|---|---|---|---|"]
    par_dom = defaultdict(list)
    for r in retenus:
        par_dom[r["domaine"]].append(r)
    for d, rs in sorted(par_dom.items(), key=lambda x: -len(x[1])):
        cpt = Counter(r["priorite"] for r in rs)
        reg = sum("region" in r["niveaux_zone"] or "departement" in r["niveaux_zone"] for r in rs)
        L.append(f"| {d} | {len(rs)} | {len({r['dataset_id'] for r in rs})} | {cpt['P1']} | {cpt['P2']} "
                 f"| {cpt['P3']} | {reg} |")

    L += ["", "## Couverture du jeu de test", "",
          ("Chaque question à issue exacte ou approchée doit trouver son indicateur ; les refus sont hors "
          "périmètre par construction."), "",
          "| Question | Issue | Indicateur(s) | Libellé |", "|---|---|---|---|"]
    manquantes = []
    for q in questions:
        cs = par_question.get(q["id"], [])
        if q["issue_attendue"] == "aucune":
            L.append(f"| {q['id']} | aucune | hors périmètre ({q['motif']}) | |")
            continue
        if not cs:
            manquantes.append(q["id"])
        L.append(f"| {q['id']} | {q['issue_attendue']} | {', '.join(f'`{c}`' for c in cs) or '**aucun**'} "
                 f"| {'; '.join(par_code[c]['libelle_fr'] for c in cs)} |")
    L += ["", f"Questions sans indicateur : {', '.join(manquantes) or 'aucune'}.", ""]

    # --- anomalies -------------------------------------------------------
    L += ["## Anomalies à connaître", "", "### Indicateurs publiés en plusieurs unités (séparés)", "",
          "Même jeu et même valeur « Indicateur », unités différentes : chaque unité est un indicateur.", "",
          "| Jeu | Indicateurs concernés | Unités |", "|---|---|---|"]
    unites = defaultdict(set)
    for ds, v, u in cumuls:
        unites[(ds, v)].add(u)
    multi = Counter(ds for (ds, _), us in unites.items() if len({u for u in us if u}) > 1)
    for ds, n in multi.most_common():
        us = sorted({u for (d, _), s in unites.items() if d == ds for u in s if u})
        apercu = " · ".join(us[:4]) + (f" · … ({len(us)} unités)" if len(us) > 4 else "")
        L.append(f"| `{ds}` | {n} | {apercu} |")

    graphies = [(i, c) for i, c in cumuls.items() if len(c.variantes) > 1]
    L += ["", "### Même indicateur écrit de plusieurs façons (fusionnés)", "",
          (f"{len(graphies)} indicateurs ({len({i[0] for i, _ in graphies})} jeux) apparaissent sous plusieurs "
          "graphies dans leur jeu (casse, accents). Ils sont fusionnés ; `valeur_portail` les garde toutes "
          "pour l'extraction. Exemples :"), ""]
    L += [f"- `{i[0]}` : {' / '.join(f'« {v} »' for v in sorted(c.variantes))}" for i, c in graphies[:8]]
    L += ["", "### Unités suspectes", "",
          ("Libellé d'unité incrémenté ligne à ligne (« prix constants de 1999 », « de 2000 »…) : "
          "à corriger à l'extraction (#4)."), ""]
    suspects = defaultdict(set)
    for ds, _, u in cumuls:
        if m := re.search(r"prix constants de (\d{4})", u):
            suspects[ds].add(m.group(1))
    lignes_s = [f"- `{ds}` : {len(a)} années de base ({min(a)} à {max(a)})" for ds, a in sorted(suspects.items())
                if len(a) > 1]
    L += (lignes_s or ["Aucune."]) + [""]

    sans_unite = [r for r in retenus if not r["unite"]]
    L += ["### Indicateurs sans unité", "",
          (f"{len(sans_unite)} indicateurs ({len({r['dataset_id'] for r in sans_unite})} jeux) n'ont pas d'unité "
          "sur le portail. Souvent elle est dans le libellé (« … (%) ») : à compléter à la vérification."), ""]
    melanges = sum(len(c.echelles) > 1 for c in cumuls.values())
    hors_un = Counter(e for c in cumuls.values() for e in c.echelles if e not in ("", "1"))
    L += ["### Échelle", "",
          (f"{sum(1 for c in cumuls.values() if c.echelles - {'', '1'})} indicateurs ont une échelle différente "
          f"de 1 ({', '.join(f'{e} : {n}' for e, n in hors_un.most_common())}) ; {melanges} en mélangent "
          "plusieurs. Le sens exact de `echelle` (valeur à multiplier ou unité déjà en millions) est à "
          "établir à l'extraction (#4)."), ""]
    sans_zone = [r for r in retenus if not r["niveaux_zone"]]
    L += ["### Sans zone", "",
          (f"{len(sans_zone)} indicateurs n'ont ni colonne géographique ni code région du portail. "
          "Ils sont en général nationaux, mais pas toujours (les prix de `feujxob` sont relevés dans "
          "l'agglomération de Dakar) : la zone est fixée jeu par jeu à la vérification."), ""]
    if ecartes := [r for r in lignes if r["verification"] == "ecarte"]:
        L += ["### Écartés", ""] + [f"- `{ds}` : {n} indicateurs — {note}" for (ds, note), n in
                                    Counter((r["dataset_id"], r["note"]) for r in ecartes).items()] + [""]
    RAPPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    return manquantes


def main() -> int:
    if not (SOCLE / "observations.csv").exists():
        sys.exit(f"{SOCLE}/observations.csv introuvable : définir GESTUKAAY_SOCLE_BRUT.")
    questions = lire_jeu_de_test()
    cumuls, cle_indic, geo = lire_observations()
    lignes, perdus = construire(lire_catalogue(), cumuls, cle_indic, geo, questions)
    ecrire(lignes)
    manquantes = rapport(lignes, questions, cumuls, perdus)
    print(f"{len(lignes)} indicateurs -> {FICHIER.relative_to(RACINE)}")
    print(f"Rapport : {RAPPORT.relative_to(RACINE)}")
    if manquantes:
        print(f"Questions sans indicateur : {', '.join(manquantes)}")
    return 1 if manquantes else 0


if __name__ == "__main__":
    sys.exit(main())
