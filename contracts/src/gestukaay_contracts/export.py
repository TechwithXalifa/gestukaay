"""Génère contracts/generated/*.schema.json depuis les modèles Pydantic.

    uv run python -m gestukaay_contracts.export
puis, pour les types TypeScript du front :
    npx --yes json-schema-to-typescript@15 -i contracts/generated/ask_response.schema.json \
        -o contracts/generated/contract.ts
(voir scripts/generer_contrat.sh qui fait les deux).
"""

import json
from pathlib import Path

from pydantic import TypeAdapter

from .models import AskRequest, AskResponse, ConfirmRequest, FeedbackRequest, Problem

SORTIE = Path(__file__).resolve().parents[2] / "generated"

# Les requêtes sont décrites telles qu'on les ENVOIE (champs par défaut
# optionnels) ; les réponses telles qu'on les REÇOIT (tout est présent).
MODELES = {
    "ask_request": (AskRequest, "validation"),
    "ask_response": (AskResponse, "serialization"),
    "confirm_request": (ConfirmRequest, "validation"),
    "feedback_request": (FeedbackRequest, "validation"),
    "problem": (Problem, "serialization"),
}


def _sans_titres_de_champs(noeud):
    """Retire les « title » des propriétés : sinon json-schema-to-typescript
    crée un alias par champ (Code1, Libelle2...) illisible côté front."""
    if isinstance(noeud, dict):
        for prop in (noeud.get("properties") or {}).values():
            prop.pop("title", None)
        for v in noeud.values():
            _sans_titres_de_champs(v)
    elif isinstance(noeud, list):
        for v in noeud:
            _sans_titres_de_champs(v)
    return noeud


def schema_de(modele, mode) -> dict:
    return _sans_titres_de_champs(TypeAdapter(modele).json_schema(mode=mode))


def main() -> None:
    SORTIE.mkdir(exist_ok=True)
    for nom, (modele, mode) in MODELES.items():
        schema = schema_de(modele, mode)
        chemin = SORTIE / f"{nom}.schema.json"
        chemin.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(chemin.relative_to(SORTIE.parents[1]))


if __name__ == "__main__":
    main()
