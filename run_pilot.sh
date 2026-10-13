#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf '%s\n' 'Create the Python environment first; see README.md.' >&2
  exit 1
fi
exec .venv/bin/python scripts/launch_pilot.py
