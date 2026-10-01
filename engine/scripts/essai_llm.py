"""Essai RÉEL de la chaîne LLM configurée dans .env (issue #9). Coûte quelques
fractions de centime : à lancer à la main, jamais en CI.

    uv run python engine/scripts/essai_llm.py            # chaque maillon, puis la chaîne
    uv run python engine/scripts/essai_llm.py --chaine   # la chaîne seulement

Pose une question simple et vérifie : JSON valide, délai, latence, coût.
N'affiche jamais les clés.
"""

from __future__ import annotations

import os
import sys
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
    """Lecteur minimal de .env (CLE=valeur), sans écraser l'environnement existant."""
    if not fichier.exists():
        sys.exit(f"{fichier} introuvable : copier .env.example en .env et le remplir.")
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, _, valeur = ligne.partition("=")
            os.environ.setdefault(cle.strip(), valeur.split(" #")[0].strip())


def essayer(titre: str, client: ClientLLM) -> bool:
    print(f"\n== {titre}")
    try:
        obj, appel = client.structurer(SYSTEME, QUESTION, Reponse)
    except EchecLLM as e:
        appel, obj = e.appel, None
    for t in appel.tentatives:
        print(f"   {t.maillon:<10} {t.fournisseur:<18} {t.modele:<28} {t.statut:<12} {t.latence_ms:>5} ms  {t.detail[:80]}")
    if obj is None:
        print("   ÉCHEC : aucun maillon n'a répondu")
        return False
    cout = f"{appel.cout_usd * 100:.4f} centime(s) $" if appel.cout_usd is not None else "coût inconnu (prix non configurés)"
    print(f"   → {obj.model_dump()}  | {appel.jetons_entree} + {appel.jetons_sortie} jetons | {cout}")
    return True


def main() -> int:
    charger_env(RACINE / ".env")
    chaine = lire_chaine()
    ok = True
    if "--chaine" not in sys.argv:
        for m in chaine:
            if m.fournisseur != "regles":
                ok &= essayer(f"maillon « {m.nom} » seul", ClientLLM([m]))
    ok &= essayer("chaîne complète", ClientLLM(chaine))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
