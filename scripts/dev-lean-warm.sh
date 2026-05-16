#!/usr/bin/env bash
# Stable Lean cache + long-lived Docker worker for fast local verify (docker exec).
# Defaults LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR to <repo>/.lemma-lean-cache when unset.
#
# Usage:
#   bash scripts/dev-lean-warm.sh
#   bash scripts/dev-lean-warm.sh --update-dotenv          # also append LEMMA_LEAN_DOCKER_WORKER to .env
#   bash scripts/dev-lean-warm.sh --bootstrap-dotenv       # append cache dir to .env if missing
#   bash scripts/dev-lean-warm.sh --bootstrap-dotenv --update-dotenv
#
# See docs/validator.md (Fast Docker verify).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOOTSTRAP_DOTENV=0
FORWARD=()
for a in "$@"; do
  if [[ "$a" == "--bootstrap-dotenv" ]]; then
    BOOTSTRAP_DOTENV=1
  else
    FORWARD+=("$a")
  fi
done

if [[ -z "${LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR:-}" ]]; then
  export LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR="${ROOT}/.lemma-lean-cache"
fi
mkdir -p "${LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR}"

ENV_FILE="${ROOT}/.env"
if [[ "${BOOTSTRAP_DOTENV}" -eq 1 ]] && [[ -f "${ENV_FILE}" ]]; then
  if ! grep -qE '^[[:space:]]*LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=' "${ENV_FILE}"; then
    {
      echo ""
      echo "# Added by scripts/dev-lean-warm.sh --bootstrap-dotenv"
      echo "LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=${LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR}"
    } >>"${ENV_FILE}"
    echo "Appended LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR to ${ENV_FILE}"
  else
    echo "Note: ${ENV_FILE} already sets LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR — not overwriting."
  fi
fi

echo "Using workspace cache: ${LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR}"
exec "${ROOT}/scripts/start_lean_docker_worker.sh" "${FORWARD[@]}"
