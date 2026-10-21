#!/usr/bin/env bash
# Fix→check round for free slides 12–14. Does NOT rewrite locked 7–11.
# Exit ≠0 = not ready.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
PY="$REPO/.venv-pptx/bin/python"
cd "$REPO"
echo "=== fill outside 12–14 ==="
"$PY" docs/presentation/fill_slides_outside_7_11.py
echo "=== gate outside ==="
"$PY" docs/presentation/gate_check_outside.py
echo "=== gate locked 7–11 (must stay PASS) ==="
"$PY" docs/presentation/gate_check.py
echo "=== capture PPT 12–14 ==="
bash docs/presentation/capture_ppt_frames.sh 12 14 ppt_verify
echo "=== ROUND OUTSIDE OK — open preview_frames/ppt_verify_slide_{12,13,14}.png ==="
