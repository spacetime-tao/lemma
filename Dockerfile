# Runtime image for lemma miner/validator (Docker socket for Lean sandbox).
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends docker.io ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY lemma ./lemma
RUN pip install --no-cache-dir -e .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["lemma"]
CMD ["validator"]
