# Runtime image for lemma miner/validator.
#
# Lean verification uses the Python Docker SDK against a mounted host Docker
# socket. Do not install the full Docker engine here; it is large and the daemon
# belongs on the host.
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY lemma ./lemma
COPY tools ./tools
RUN pip install --no-cache-dir .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["lemma"]
CMD ["validator", "start"]
