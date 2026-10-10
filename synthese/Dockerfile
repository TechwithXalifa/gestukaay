# Voix de réponse en wolof : Oolel-Voices (0029, licence AGPL-3.0, utilisé tel quel), sur GPU NVIDIA.
# Contexte de construction : racine du dépôt. Torch 2.11 avec CUDA 12.6 : pilote NVIDIA 535 ou plus récent.
# Versions : celles du service qui tourne sur le Mac de l'équipe (09/10), épinglées.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
# Délai réseau de uv relevé (30 s par défaut) : les paquets CUDA font jusqu'à 700 Mo (build du 09/10)
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUTF8=1 PYTHONUNBUFFERED=1 HF_HOME=/modeles UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cu126 \
      "torch==2.11.0+cu126" "torchaudio==2.11.0+cu126" "transformers==4.46.3" "diffusers==0.29.0" \
      "conformer==0.3.2" "librosa==1.0.0" "s3tokenizer==0.3.0" "safetensors==0.8.0" "huggingface_hub==0.36.2" \
      "omegaconf==2.3.1" "einops==0.8.2" "scipy==1.18.1" "numpy==2.5.3" "fastapi==0.142.2" "uvicorn==0.54.0"

COPY synthese/serveur.py serveur.py
# Téléchargement des modèles (service « modeles » du compose) : M-Kiriku (jeton HF_TOKEN, conditions acceptées
# sur Hugging Face), Oolel-Voices et la voix de référence de sa démo, dans le volume /modeles
COPY scripts/telecharger_modeles.py telecharger_modeles.py
EXPOSE 8200
CMD ["python", "serveur.py", "--hote", "0.0.0.0", "--port", "8200"]
