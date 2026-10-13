#!/bin/sh
# Start the app with the built-in baseline classifier: no GGUF or llama.cpp needed.
# For the fine-tuned Qwen3 model use run_pilot.sh instead.
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
export COMPLAINTIQ_BACKEND=baseline
exec .venv/bin/python -m uvicorn complaintiq.api:app --host 127.0.0.1 --port 8501 --no-access-log "$@"
