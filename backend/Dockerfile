# API Gëstukaay. Contexte de construction : racine du dépôt (voir docker-compose.yml).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUTF8=1

# Dépendances d'abord (couche mise en cache tant que uv.lock ne change pas)
COPY pyproject.toml uv.lock ./
COPY contracts/pyproject.toml contracts/pyproject.toml
COPY engine/pyproject.toml engine/pyproject.toml
COPY socle/pyproject.toml socle/pyproject.toml
COPY backend/pyproject.toml backend/pyproject.toml
COPY canaux/pyproject.toml canaux/pyproject.toml
RUN uv sync --locked --no-dev --no-install-workspace --package gestukaay-backend --package gestukaay-canaux

# Code (le faux moteur lit contracts/examples/)
COPY contracts contracts
COPY engine engine
COPY socle socle
COPY backend backend
# Canaux WhatsApp et Telegram (0025) : sans eux, les webhooks répondent 404
COPY canaux canaux
RUN uv sync --locked --no-dev --package gestukaay-backend --package gestukaay-canaux \
 && .venv/bin/python -c "import gestukaay_canaux.whatsapp, gestukaay_canaux.telegram"

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "gestukaay_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
