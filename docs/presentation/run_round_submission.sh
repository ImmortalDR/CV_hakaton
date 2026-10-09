#!/usr/bin/env bash
# Ship ritual: draft gates → fill solution → export SUBMISSION → gate SUBMISSION → PPT frames 1–16.
# Exit ≠0 = not ready to give jury the file.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
PY="$REPO/.venv-pptx/bin/python"
cd "$REPO"

echo "=== draft gates 7–11 ==="
"$PY" docs/presentation/gate_check.py
"$PY" docs/presentation/full_audit.py
echo "=== draft gates 12–14 ==="
"$PY" docs/presentation/gate_check_outside.py
echo "=== draft gates solution 15+ ==="
"$PY" docs/presentation/gate_check_solution.py
echo "=== export SUBMISSION (delete junk) ==="
"$PY" docs/presentation/export_submission_deck.py
echo "=== gate SUBMISSION file ==="
"$PY" docs/presentation/gate_check_submission.py
echo "=== capture SUBMISSION in PowerPoint ==="
# CRITICAL: capture_ppt_frames defaults to DRAFT — must override or jury frames are lies.
export CAPTURE_PPTX="$ROOT/FSP_NIKITA_SUBMISSION.pptx"
export CAPTURE_REQUIRE_NAME="SUBMISSION"
N=$("$PY" -c "from pptx import Presentation; print(len(Presentation('$ROOT/FSP_NIKITA_SUBMISSION.pptx').slides))")
bash docs/presentation/capture_ppt_frames.sh 1 "$N" sub_final
echo "=== ROUND SUBMISSION OK — $N slides, frames sub_final_slide_*.png ==="
echo "FILE: $ROOT/FSP_NIKITA_SUBMISSION.pptx"
