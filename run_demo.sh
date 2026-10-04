#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf '%s\n' 'Create the Python environment first; see README.md.' >&2
  exit 1
fi
if [ ! -f frontend/dist/index.html ]; then
  printf '%s\n' 'Build the frontend first: cd frontend && npm ci && npm run build' >&2
  exit 1
fi
# Use the downloaded fine-tuned model; explicitly select baseline if desired.
export COMPLAINTIQ_BACKEND="${COMPLAINTIQ_BACKEND:-slm}"
if [ "$COMPLAINTIQ_BACKEND" = slm ]; then
  export COMPLAINTIQ_MODEL_PATH="${COMPLAINTIQ_MODEL_PATH:-$PWD/models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf}"
  export COMPLAINTIQ_MODEL_URL="${COMPLAINTIQ_MODEL_URL:-http://127.0.0.1:8504}"
  export COMPLAINTIQ_EVALUATION_PATH="${COMPLAINTIQ_EVALUATION_PATH:-$PWD/artifacts/finetuned_evaluation.json}"
fi
exec .venv/bin/python -m uvicorn complaintiq.api:app --host 127.0.0.1 --port 8501 --no-access-log "$@"
