"""Essai RÉEL de la chaîne LLM configurée dans .env (issue #9). Coûte quelques
fractions de centime : à lancer à la main, jamais en CI.

    uv run python engine/scripts/essai_llm.py                    # chaque maillon, puis la chaîne
    uv run python engine/scripts/essai_llm.py --chaine           # la chaîne seulement
    uv run python engine/scripts/essai_llm.py --repetitions 10   # latence : médiane, p95, max
    uv run python engine/scripts/essai_llm.py -n 10 --delai 30   # latence RÉELLE, sans couper à 2 s

Pose une question simple et vérifie : JSON valide, délai, latence, coût.
N'affiche jamais les clés.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from gestukaay_engine.llm import ClientLLM, EchecLLM, lire_chaine
from pydantic import BaseModel, ConfigDict, Field

RACINE = Path(__file__).resolve().parents[2]


class Reponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    region: str = Field(description="nom de la région")
    code_iso: str = Field(description="code ISO 3166-2, ex. SN-DK")
    confiance: float = Field(ge=0, le=1)


SYSTEME = "Tu identifies la région du Sénégal dont parle l'utilisateur."
QUESTION = "Ñata nit ñoo dëkk Cees ?"


def charger_env(fichier: Path) -> None:
    """Lecteur minimal de .env (CLE=valeur), sans écraser l'environnement existant.
    Comme les outils .env usuels, la DERNIÈRE définition d'une variable l'emporte ;
    les doublons sont signalés (source d'erreur fréquente)."""
    if not fichier.exists():
        sys.exit(f"{fichier} introuvable : copier .env.example en .env et le remplir.")
    valeurs: dict[str, str] = {}
    lignes: dict[str, list[int]] = {}
    for n, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, _, valeur = ligne.partition("=")
            valeurs[cle.strip()] = valeur.split(" #")[0].strip()
            lignes.setdefault(cle.strip(), []).append(n)
    for cle, ns in lignes.items():
        if len(ns) > 1:
            print(f"ATTENTION : {cle} est défini {len(ns)} fois dans .env (lignes {ns}) ; "
                  f"la ligne {ns[-1]} est utilisée.")
    for cle, valeur in valeurs.items():
        os.environ.setdefault(cle, valeur)


def essayer(titre: str, client: ClientLLM) -> bool:
    print(f"\n== {titre}")
    try:
        obj, appel = client.structurer(SYSTEME, QUESTION, Reponse)
    except EchecLLM as e:
        appel, obj = e.appel, None
    for t in appel.tentatives:
        print(f"   {t.maillon:<10} {t.fournisseur:<18} {t.modele:<32} {t.statut:<12} {t.latence_ms:>5} ms  {t.detail[:80]}")
    if obj is None:
        print("   ÉCHEC : aucun maillon n'a répondu")
        return False
    cout = f"{appel.cout_usd * 100:.4f} centime(s) $" if appel.cout_usd is not None else "coût inconnu (prix non configurés)"
    print(f"   → {obj.model_dump()}  | {appel.jetons_entree} + {appel.jetons_sortie} jetons | {cout}")
    return True


def mesurer(titre: str, client: ClientLLM, n: int, seuil_ms: int) -> bool:
    """n appels : taux de réussite, latence médiane / p95 / max, coût moyen."""
    print(f"\n== {titre} — {n} appels")
    latences, statuts, couts, reussites = [], Counter(), [], 0
    for i in range(n):
        try:
            _, appel = client.structurer(SYSTEME, QUESTION, Reponse)
            reussites += 1
            if appel.cout_usd is not None:
                couts.append(appel.cout_usd)
        except EchecLLM as e:
            appel = e.appel
        latences.append(appel.latence_ms)
        statuts.update(t.statut for t in appel.tentatives)
        print(f"   {i + 1:>2}. {appel.latence_ms:>5} ms  {' → '.join(f'{t.maillon}:{t.statut}' for t in appel.tentatives)}",
              flush=True)
        for t in appel.tentatives:  # le pourquoi des échecs (hors maillons non configurés)
            if t.statut not in ("ok", "indisponible"):
                print(f"         {t.maillon} : {t.detail[:110]}")
    ordre = sorted(latences)
    p95 = ordre[min(len(ordre) - 1, round(0.95 * (len(ordre) - 1)))]
    sous = sum(1 for x in latences if x <= seuil_ms)
    print(f"   réussites {reussites}/{n} | médiane {statistics.median(latences):.0f} ms | p95 {p95} ms | "
          f"max {ordre[-1]} ms | sous {seuil_ms} ms : {sous}/{n}")
    print(f"   statuts : {dict(statuts)}" + (f" | coût moyen {statistics.mean(couts) * 100:.4f} centime(s) $"
                                             if couts else " | coût inconnu (prix non configurés)"))
    return reussites == n


def main() -> int:
    p = argparse.ArgumentParser(description="Essai réel de la chaîne LLM du .env")
    p.add_argument("--chaine", action="store_true", help="tester la chaîne seulement")
    p.add_argument("-n", "--repetitions", type=int, default=1, help="nombre d'appels par essai")
    p.add_argument("--delai", type=float, help="remplace le délai de chaque maillon (s), ex. 30 "
                   "pour mesurer la latence réelle sans couper")
    args = p.parse_args()

    charger_env(RACINE / ".env")
    chaine = lire_chaine()
    seuil_ms = round(min(m.delai_s for m in chaine) * 1000)
    if args.delai:
        chaine = [replace(m, delai_s=args.delai) for m in chaine]
        print(f"Délai porté à {args.delai} s pour mesurer la latence réelle (le seuil affiché reste {seuil_ms} ms).")

    def lancer(titre: str, client: ClientLLM) -> bool:
        if args.repetitions > 1:
            return mesurer(titre, client, args.repetitions, seuil_ms)
        return essayer(titre, client)

    ok = True
    if not args.chaine:
        for m in chaine:
            if m.fournisseur != "regles":
                ok &= lancer(f"maillon « {m.nom} » seul", ClientLLM([m]))
    ok &= lancer("chaîne complète", ClientLLM(chaine))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
