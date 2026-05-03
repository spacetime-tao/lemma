#!/usr/bin/env bash
# Long-lived Lean sandbox container for fast `docker exec` verify (see docs/validator.md).
# Reads LEAN_SANDBOX_IMAGE, LEMMA_LEAN_DOCKER_WORKER, LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR from env / .env.
#
# Usage:
#   ./scripts/start_lean_docker_worker.sh
#   ./scripts/start_lean_docker_worker.sh --update-dotenv   # append LEMMA_LEAN_DOCKER_WORKER to .env if missing
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPDATE_DOTENV=0
for a in "$@"; do
  if [[ "$a" == "--update-dotenv" ]]; then UPDATE_DOTENV=1; fi
done
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

IMAGE="${LEAN_SANDBOX_IMAGE:-lemma/lean-sandbox:latest}"
NAME="${LEMMA_LEAN_DOCKER_WORKER:-lemma-lean-worker}"
CACHE="${LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR:-}"
MOUNT="${LEMMA_LEAN_DOCKER_WORKER_MOUNT:-/lemma-workspace}"
NET="${LEAN_SANDBOX_NETWORK:-none}"

if [[ -z "${CACHE}" ]]; then
  echo "error: set LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR to the host path mounted at ${MOUNT} in the worker."
  echo "  Example: export LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=/var/lib/lemma-lean-cache"
  exit 1
fi

docker rm -f "${NAME}" >/dev/null 2>&1 || true
# Docker Desktop (macOS): :delegated speeds container writes on bind mounts; ignored on Linux.
if [[ "$(uname -s)" == "Darwin" ]]; then
  VOLARG=(-v "${CACHE}:${MOUNT}:delegated")
else
  VOLARG=(-v "${CACHE}:${MOUNT}:rw")
fi
docker run -d --name "${NAME}" --restart unless-stopped \
  --network "${NET}" \
  "${VOLARG[@]}" \
  "${IMAGE}" sleep infinity

echo "Started worker container: ${NAME}"
echo "  image=${IMAGE}  mount  ${CACHE} -> ${MOUNT}  network=${NET}"

ENV_FILE="${ROOT}/.env"
if [[ "${UPDATE_DOTENV}" -eq 1 ]] && [[ -f "${ENV_FILE}" ]]; then
  if ! grep -qE '^[[:space:]]*LEMMA_LEAN_DOCKER_WORKER=' "${ENV_FILE}"; then
    {
      echo ""
      echo "# Added by scripts/start_lean_docker_worker.sh --update-dotenv"
      echo "LEMMA_LEAN_DOCKER_WORKER=${NAME}"
    } >>"${ENV_FILE}"
    echo "Appended LEMMA_LEAN_DOCKER_WORKER=${NAME} to ${ENV_FILE}"
  else
    echo "Note: ${ENV_FILE} already sets LEMMA_LEAN_DOCKER_WORKER — ensure it matches container name ${NAME}"
  fi
else
  echo "Add to .env (Lemma loads this via LemmaSettings; shell export is not enough):"
  echo "  LEMMA_LEAN_DOCKER_WORKER=${NAME}"
  echo "Or re-run: ./scripts/start_lean_docker_worker.sh --update-dotenv"
fi
