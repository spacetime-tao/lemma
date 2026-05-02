# Lean 4 + Mathlib + stub workspace (bake .lake for offline `lake build` in validator sandboxes).
# Build from repo root: docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y curl git ca-certificates jq && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-lc"]
RUN curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | bash -s -- -y
ENV PATH="/root/.elan/bin:${PATH}"

WORKDIR /opt/lemma-stub
COPY lemma/lean/template/ /opt/lemma-stub/
RUN cd /opt/lemma-stub && lake exe cache get && lake build Challenge Solution Submission

WORKDIR /work
# Default: interactive shell; validator overrides command.
CMD ["bash", "-lc", "echo 'lemma lean-sandbox image ready'; bash"]
