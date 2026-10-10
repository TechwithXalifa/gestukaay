"""Télécharge les modèles de voix dans le cache Hugging Face ($HF_HOME, volume « modeles » du compose).

    docker compose run --rm modeles

M-Kiriku est en accès contrôlé : accepter ses conditions sur https://huggingface.co/AIHubSN/M-Kiriku-ASR
(gratuit, immédiat), puis mettre un jeton de lecture dans HF_TOKEN (.env). Oolel-Voices est public.
Une fois les modèles dans le volume, la voix fonctionne sans Internet."""

import os
import sys

from huggingface_hub import hf_hub_download, snapshot_download
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

TRANSCRIPTION = os.environ.get("TRANSCRIPTION_MODELE", "AIHubSN/M-Kiriku-ASR")

try:
    print(f"1/3 transcription : {TRANSCRIPTION} (environ 6 Go)…", flush=True)
    snapshot_download(TRANSCRIPTION)
except (GatedRepoError, RepositoryNotFoundError):
    sys.exit(f"Accès refusé à {TRANSCRIPTION} : accepter ses conditions sur https://huggingface.co/{TRANSCRIPTION}, "
             "puis mettre un jeton de lecture dans HF_TOKEN (.env).")
print("2/3 voix de réponse : soynade-research/Oolel-Voices (environ 7 Go)…", flush=True)
snapshot_download("soynade-research/Oolel-Voices")
print("3/3 voix de référence de la démo d'Oolel…", flush=True)
hf_hub_download("soynade-research/Oolel-Voices-Demo", "8_1_c.wav", repo_type="space")
print("Modèles prêts.", flush=True)
