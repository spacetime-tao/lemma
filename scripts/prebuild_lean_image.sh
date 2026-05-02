#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REV="$(grep -E '^\s*rev\s*=' lemma/lean/template/lakefile.toml | head -1 | sed -E 's/.*"(.*)".*/\1/')"
SHORT="${REV:0:8}"
TAG_LOCAL="lemma/lean-sandbox:mathlib-${SHORT}"
docker build -f compose/lean.Dockerfile -t "${TAG_LOCAL}" .
docker tag "${TAG_LOCAL}" lemma/lean-sandbox:latest
echo "Built ${TAG_LOCAL} and tagged lemma/lean-sandbox:latest"
