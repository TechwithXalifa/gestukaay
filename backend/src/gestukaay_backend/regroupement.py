"""Questions non résolues regroupées par thème (back-office, V1.1).

Le tableau de bord liste les questions refusées une par une : « chômage des jeunes à Dakar » et « taux de
chômage des jeunes à Kolda » y font deux lignes. Ici, elles se regroupent par leurs mots utiles (zones, années,
mots outils retirés), le thème le plus fréquent d'abord. Pour chaque thème, les indicateurs du catalogue qui
contiennent ces mots : s'il y en a, le chiffre existe et la question a été mal comprise (lexique, #23) ; sinon,
il manque au socle (suggestion d'indicateur).

Regroupement simple et explicable, sans modèle : similarité de Jaccard entre ensembles de mots, au-dessus d'un
seuil, par rapport à la première question du groupe. Rien n'est envoyé hors du serveur.
"""

from __future__ import annotations

import re
from collections import Counter
from functools import cache

from gestukaay_socle.zones import normaliser, zones

SEUIL = 0.5
EXEMPLES = 5
VIDES = frozenset(
    ["les", "des", "une", "est", "quel", "quelle", "quels", "quelles", "combien", "comment", "pourquoi", "dans", "pour", "par", "sur", "avec", "aux", "ont", "sont", "fait", "faire", "donne", "donner", "moi", "nous", "vous", "leur", "leurs", "cette", "ces", "son", "ses", "sur", "entre", "plus", "moins", "tres", "taux", "nombre", "niveau", "part", "pourcentage", "chiffre", "chiffres", "statistique", "statistiques", "donnee", "donnees", "region", "regions", "departement", "ville", "senegal", "pays", "national", "annee", "annees", "mois", "dernier", "derniere", "actuel", "actuelle", "aujourd", "hui", "svp", "merci", "bonjour", "stp"]
)


@cache
def _lieux() -> frozenset[str]:
    """Les mots des noms de zones (« saint », « louis », « kolda ») : retirés, la zone ne fait pas le thème."""
    noms = set()
    for z in zones().values():
        for nom in (z.libelle_fr, z.libelle_wo, *z.variantes):
            noms.update(normaliser(nom).split())
    return frozenset(noms)


def _mots(question: str) -> list[tuple[str, str]]:
    """(forme normalisée, forme écrite) des mots utiles : trois lettres au moins, ni chiffre, ni lieu, ni mot outil.
    Un pluriel en -s se ramène au singulier (« jeunes » et « jeune » se rejoignent)."""
    sortie = []
    for brut in re.findall(r"[\w'’-]+", question.lower()):
        forme = brut.strip("'’-")
        norm = normaliser(forme).replace(" ", "")
        if norm in _lieux():  # avant le pluriel : « thies » est Thiès, pas un pluriel
            continue
        if len(norm) > 4 and norm.endswith("s"):
            norm = norm[:-1]
        if len(norm) < 3 or norm.isdigit() or norm in VIDES:
            continue
        sortie.append((norm, forme))
    return sortie


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def regrouper(lignes: list[dict], seuil: float = SEUIL) -> list[dict]:
    """lignes : {question, langue, motif, recu_le, reponse_id}. Groupes du plus fréquent au moins fréquent :
    thème (les mots les plus fréquents), occurrences, langues, motifs, exemples distincts, dernière date."""
    groupes: list[dict] = []
    for lg in sorted(lignes, key=lambda x: x["recu_le"]):
        mots = _mots(lg["question"])
        ensemble = frozenset(n for n, _ in mots)
        if ensemble:
            cible = max(groupes, key=lambda g: _jaccard(ensemble, g["graine"]), default=None)
        else:  # aucun mot utile (« quel est le taux ? ») : toutes ensemble, dans « autres questions »
            cible = next((g for g in groupes if not g["graine"]), None)
        if cible is None or (ensemble and _jaccard(ensemble, cible["graine"]) < seuil):
            cible = {"graine": ensemble, "lignes": [], "mots": Counter(), "formes": {}}
            groupes.append(cible)
        cible["lignes"].append(lg)
        cible["mots"].update(list(dict.fromkeys(n for n, _ in mots)))  # à égalité, l'ordre de la question
        for n, f in mots:
            cible["formes"].setdefault(n, Counter())[f] += 1

    sortie = []
    for g in groupes:
        principaux = [n for n, _ in g["mots"].most_common(3)]
        distinctes: dict[str, dict] = {}
        for lg in reversed(g["lignes"]):  # les plus récentes d'abord
            distinctes.setdefault(" ".join(lg["question"].lower().split()), lg)
        sortie.append({
            "theme": " · ".join(g["formes"][n].most_common(1)[0][0] for n in principaux) or "autres questions",
            "mots": principaux,
            "occurrences": len(g["lignes"]),
            "langues": dict(Counter(lg["langue"] for lg in g["lignes"])),
            "motifs": dict(Counter(lg["motif"] or "inconnu" for lg in g["lignes"])),
            "exemples": [{"question": lg["question"], "reponse_id": lg["reponse_id"], "recu_le": lg["recu_le"]}
                         for lg in list(distinctes.values())[:EXEMPLES]],
            "derniere": max(lg["recu_le"] for lg in g["lignes"]),
        })
    return sorted(sortie, key=lambda g: (-g["occurrences"], g["theme"]))
