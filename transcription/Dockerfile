# Transcription des notes vocales : M-Kiriku (0026), sur GPU NVIDIA. Contexte de construction : racine du dépôt.
# Torch 2.11 avec CUDA 12.6 : pilote NVIDIA 535 ou plus récent (la roue PyPI par défaut, en CUDA 13, demande 580).
# Versions : celles du service qui tourne sur le Mac de l'équipe (09/10), épinglées.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUTF8=1 PYTHONUNBUFFERED=1 HF_HOME=/modeles
RUN uv pip install --system --no-cache --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cu126 \
      "torch==2.11.0+cu126" "transformers==4.57.6" "av==19.0.1" "numpy==2.5.3" \
      "fastapi==0.142.2" "uvicorn==0.54.0" "python-multipart==0.0.32"

COPY transcription/serveur.py serveur.py
EXPOSE 8100
# Le modèle est chargé avant d'écouter : /ping répond une fois prêt (healthcheck du compose)
CMD ["python", "serveur.py", "--hote", "0.0.0.0", "--port", "8100"]
