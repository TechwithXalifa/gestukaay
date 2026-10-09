#!/usr/bin/env sh
# Télécharge le socle officiel (release GitHub « socle-2026.10.0 », 15 Mo), vérifie son empreinte et celles de
# son MANIFEST, puis l'extrait dans socle_gestukaay/ (chemin lu par docker-compose.yml). Relançable.
#   ./scripts/recuperer_socle.sh
set -eu
VERSION="2026.10.0"
SHA256="db4ac1118d00d62c98e11bb7e5c049d8be3f0da2a974d31a759bd247cb29cde2"
DEPOT="TechwithXalifa/gestukaay"
ARCHIVE="socle-$VERSION.zip"
CIBLE="socle_gestukaay"

cd "$(dirname "$0")/.."
if [ -f "$CIBLE/$VERSION/VERSION" ]; then
  echo "Socle $VERSION déjà présent dans $CIBLE/$VERSION."
  exit 0
fi
somme() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
echo "Téléchargement du socle ${VERSION}…"
if ! curl -fsSL -o "$tmp/$ARCHIVE" "https://github.com/$DEPOT/releases/download/socle-$VERSION/$ARCHIVE"; then
  # dépôt privé : la CLI GitHub (gh auth login) a les droits
  command -v gh >/dev/null || { echo "Téléchargement impossible (dépôt privé ?) : installer gh et lancer gh auth login." >&2; exit 1; }
  gh release download "socle-$VERSION" --repo "$DEPOT" --pattern "$ARCHIVE" --dir "$tmp"
fi
[ "$(somme "$tmp/$ARCHIVE")" = "$SHA256" ] || { echo "Empreinte de l'archive incorrecte : fichier abîmé." >&2; exit 1; }

mkdir -p "$CIBLE"
python3 - "$tmp/$ARCHIVE" "$CIBLE" "$VERSION" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
archive, cible, version = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
zipfile.ZipFile(archive).extractall(cible)
dossier = cible / version
for nom, attendu in json.loads((dossier / "MANIFEST.json").read_text())["fichiers"].items():
    h = hashlib.sha256((dossier / nom).read_bytes()).hexdigest()
    if h != attendu:
        sys.exit(f"{nom} : empreinte différente du MANIFEST")
print(f"Socle {version} prêt dans {dossier} (empreintes vérifiées).")
PY
