#!/bin/sh
set -eu
cd "$(dirname "$0")"
COMPLAINTIQ_GGUF="${COMPLAINTIQ_MODEL_PATH:-$PWD/models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf}"
if [ ! -f "$COMPLAINTIQ_GGUF" ]; then
  printf '%s\n' "Model missing: $COMPLAINTIQ_GGUF" >&2
  exit 1
fi
exec llama-server -m "$COMPLAINTIQ_GGUF" -c 2048 -ngl 99 -t 4 -b 256 -ub 128 --parallel 1 --host 127.0.0.1 --port 8504 --jinja --reasoning off
