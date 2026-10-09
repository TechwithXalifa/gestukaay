#!/usr/bin/env sh
# Vérifie un déploiement Docker Compose de bout en bout (DEPLOIEMENT.md, étape 8) :
#   1. l'API répond ; 2. le site répond ; 3. une question écrite reçoit le chiffre officiel ;
#   4. avec le profil « voix » : une réponse en wolof est dite par Oolel, puis retranscrite par M-Kiriku.
#   ./scripts/verifier_deploiement.sh
set -u
API=${API:-http://localhost:8000}
SITE=${SITE:-http://localhost:3000}
echecs=0
ok() { echo "  OK    $1"; }
ko() { echo "  ÉCHEC $1"; echecs=$((echecs + 1)); }
cd "$(dirname "$0")/.."

echo "1. API ($API)"
if curl -fsS -m 10 "$API/health" | grep -q '"ok"'; then ok "santé de l'API"; else ko "l'API ne répond pas (docker compose ps, docker compose logs api)"; fi

echo "2. Site ($SITE)"
if curl -fsS -m 20 "$SITE" | grep -q "Gëstukaay"; then ok "page d'accueil"; else ko "le site ne répond pas (docker compose logs web)"; fi

echo "3. Question écrite : « Combien d'habitants à Thiès en 2023 ? »"
reponse=$(curl -fsS -m 60 -X POST "$API/v1/ask" -H 'Content-Type: application/json' \
  -d '{"question": "Combien d'"'"'habitants à Thiès en 2023 ?"}' || true)
if echo "$reponse" | grep -qE '"valeur":2463677(\.0)?[,}]'; then
  ok "2 463 677 habitants (RGPH-5, ANSD)"
elif echo "$reponse" | grep -q '"issue":"exacte"'; then
  ko "réponse exacte, mais pas le chiffre attendu : le moteur réel et le socle sont-ils en place ? (GESTUKAAY_MOTEUR=reel, ./scripts/recuperer_socle.sh)"
else
  ko "pas de réponse chiffrée : GESTUKAAY_MOTEUR=reel dans .env ? socle téléchargé ?"
fi

echo "4. Voix en wolof (profil « voix », GPU)"
if ! docker compose ps --services --status running 2>/dev/null | grep -q '^synthese$'; then
  echo "  --    services de voix non démarrés (COMPOSE_PROFILES=voix dans .env, GPU NVIDIA) : étape sautée"
else
  docker compose exec -T api python - <<'PY'
import time
from gestukaay_contracts.models import AskRequest
from gestukaay_engine.moteur import MoteurReel

m = MoteurReel()
rep = m.repondre(AskRequest(question="Ñata nit ñoo dëkk Cees ?"))
t0 = time.perf_counter()
note = m.parler(rep)
if note is None or note.voix != "oolel":
    raise SystemExit("  ÉCHEC synthèse : pas de note d'Oolel (docker compose logs synthese)")
print(f"  OK    synthèse Oolel : {note.duree_s:.1f} s d'audio en {time.perf_counter() - t0:.1f} s")
t0 = time.perf_counter()
texte = m.transcrire(note.opus, "ogg", "wo").transcription
if not texte:
    raise SystemExit("  ÉCHEC transcription : texte vide (docker compose logs transcription)")
print(f"  OK    transcription M-Kiriku en {time.perf_counter() - t0:.1f} s : « {texte} »")
PY
  [ $? -eq 0 ] || echecs=$((echecs + 1))
fi

echo
if [ "$echecs" -eq 0 ]; then echo "Déploiement vérifié."; else echo "$echecs vérification(s) en échec."; exit 1; fi
