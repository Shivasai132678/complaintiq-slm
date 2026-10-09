#!/bin/sh
# Copy the SLM Project for the Windows PC, leaving out Mac-only, regenerable or unneeded files.
#
#   sh pc_kit/mac_prep/make_pc_bundle.sh DEST          full bundle: works offline on the PC
#   sh pc_kit/mac_prep/make_pc_bundle.sh --lite DEST   small bundle: the PC downloads the model,
#        Python packages, installers and llama.cpp itself (needs internet; SHA-256 checked)
#   add --zip to also write DEST.zip
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LITE=0; ZIP=0
while [ $# -gt 1 ]; do
  case "$1" in --lite) LITE=1 ;; --zip) ZIP=1 ;; *) echo "unknown option $1"; exit 1 ;; esac
  shift
done
DEST="${1:?Usage: make_pc_bundle.sh [--lite] [--zip] DESTINATION_FOLDER}"
mkdir -p "$DEST"
# Refresh the frontend build that the app serves (Node is not needed on the PC for the app).
if [ -d "$ROOT/frontend/node_modules" ]; then (cd "$ROOT/frontend" && npm run build >/dev/null); fi
set -- \
  --exclude '.venv/' --exclude 'frontend/node_modules/' --exclude 'frontend/coverage/' \
  --exclude '*.tsbuildinfo' --exclude '__pycache__/' \
  --exclude '.mypy_cache/' --exclude '.pytest_cache/' --exclude '.ruff_cache/' \
  --exclude '.coverage' --exclude 'htmlcov/' --exclude '.DS_Store' --exclude '._*' \
  --exclude 'data/cfpb_raw/' --exclude 'data/*.worker.lock' --exclude 'data/backups/' \
  --exclude 'models/qwen2.5-1.5b/' --exclude 'upstream/' --exclude '.agents/' --exclude '.kilo/' \
  --exclude 'logs/' --exclude 'pc_kit/results/*/' --exclude 'pc_kit/.venv/'
if [ "$LITE" = 1 ]; then
  set -- "$@" --exclude 'pc_kit/model/' --exclude 'pc_kit/wheels/' --exclude 'pc_kit/wheels_app/' \
    --exclude 'pc_kit/installers/' --exclude 'pc_kit/tools/llama-bin/' --exclude 'models/*.gguf'
fi
rsync -rt --delete "$@" "$ROOT/" "$DEST/"
echo "Copied to $DEST ($(du -sh "$DEST" | cut -f1))."
if [ "$ZIP" = 1 ]; then
  (cd "$(dirname "$DEST")" && rm -f "$(basename "$DEST").zip" && zip -r -q -1 "$(basename "$DEST").zip" "$(basename "$DEST")")
  echo "Zip: $DEST.zip ($(du -sh "$DEST.zip" | cut -f1))"
fi
echo "On the PC: unzip/copy to C:\\SLMProject and double-click RUN_ALL.bat."
