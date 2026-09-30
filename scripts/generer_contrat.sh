#!/usr/bin/env bash
# Régénère le schéma JSON et les types TypeScript depuis contracts/src/.../models.py.
# À lancer après toute modification du contrat, puis committer contracts/generated/.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python -m gestukaay_contracts.export
for s in ask_request ask_response confirm_request feedback_request problem; do
  npx --yes json-schema-to-typescript@15 --no-additionalProperties --bannerComment \
    "/* GÉNÉRÉ depuis contracts/src/gestukaay_contracts/models.py — ne pas modifier à la main. */" \
    -i "contracts/generated/$s.schema.json" -o "contracts/generated/$s.d.ts"
done
echo "OK — pensez à committer contracts/generated/"
