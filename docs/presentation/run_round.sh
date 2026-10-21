#!/usr/bin/env bash
# One fix→check round for slides 7–11. Exit ≠0 = not ready.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
PY="$REPO/.venv-pptx/bin/python"
cd "$REPO"
echo "=== fill ==="
"$PY" docs/presentation/fill_slides_7_11.py
echo "=== insert (+gate+audit) ==="
"$PY" docs/presentation/insert_assets.py
echo "=== capture PPT 8–11 ==="
bash docs/presentation/capture_ppt_frames.sh 8 11
echo "=== ROUND OK — open preview_frames/ppt_verify_slide_*.png ==="
