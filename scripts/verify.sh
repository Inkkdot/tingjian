#!/usr/bin/env bash
# Full DoD sequence. Run from Git Bash / WSL: bash scripts/verify.sh
# Each step is teed to artifacts/verify/<step>.log; a failure stops the run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -x .venv/Scripts/python.exe ]]; then
  PY=".venv/Scripts/python.exe"
elif [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="python"
fi

LOGDIR="artifacts/verify"
mkdir -p "$LOGDIR"

run() {
  local name="$1"
  shift
  echo "== $name"
  "$@" 2>&1 | tee "$LOGDIR/$name.log"
}

run db_probe "$PY" scripts/db_probe.py
run verify_m0 "$PY" scripts/verify_m0.py
run unit "$PY" -m pytest tests/unit -q
run integration "$PY" -m pytest tests/integration -q
run eval "$PY" scripts/eval_run.py --output artifacts/metrics.json
run web_build bash -c "cd apps/web && npm run build"

echo "all checks passed; logs in $LOGDIR"
