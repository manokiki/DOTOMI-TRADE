# DOTOMI-TRADE — Image Docker pour l'API (et, optionnellement, le scheduler
# autonome via docker/Dockerfile.scheduler).
#
# Image légère basée sur python:3.12-slim. Multi-étapes non nécessaire ici :
# pas de compilation lourde, les dépendances sont toutes des wheels prêtes.

FROM python:3.12-slim

WORKDIR /app

# Dépendances système minimales : aucune lib native requise par
# pandas/numpy/pandas-ta dans les versions utilisées ici (wheels manylinux),
# mais curl est utile pour le HEALTHCHECK ci-dessous.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Utilisateur non-root par principe de robustesse/sécurité — un process qui
# tourne 24h/24 ne devrait jamais avoir plus de privilèges que nécessaire.
RUN useradd --create-home --shell /bin/bash dotomi \
    && chown -R dotomi:dotomi /app
USER dotomi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
