#!/usr/bin/env bash
# Example: upload the validator JSONL somewhere **once per UTC day** (not built into Lemma).
#
# Schedule with cron at **00:00 UTC**, e.g.:
#   0 0 * * * LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/train.jsonl \
#     TRAINING_EXPORT_UPLOAD_DEST=s3://my-bucket/lemma/$(date -u +\%F).jsonl \
#     /path/to/lemma/scripts/training_export_upload_example.sh
#
# Customize the middle — common patterns:
#   aws s3 cp "$SRC" "$DST"
#   rclone copyto "$SRC" "remote:lemma/$(date -u +%F).jsonl"
#   gh release upload ...   (after creating a release)
#
set -euo pipefail

SRC="${LEMMA_TRAINING_EXPORT_JSONL:?}"
DST="${TRAINING_EXPORT_UPLOAD_DEST:?}"

if [[ ! -f "$SRC" ]]; then
  echo "skip: no file yet at $SRC" >&2
  exit 0
fi

case "${TRAINING_EXPORT_UPLOAD_BACKEND:-aws}" in
  aws)
    aws s3 cp "$SRC" "$DST"
    ;;
  rclone)
    rclone copyto "$SRC" "$DST"
    ;;
  *)
    echo "unknown TRAINING_EXPORT_UPLOAD_BACKEND=$TRAINING_EXPORT_UPLOAD_BACKEND (use aws|rclone)" >&2
    exit 1
    ;;
esac
