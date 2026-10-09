#!/usr/bin/env bash
# Capture slides from Microsoft PowerPoint ONLY.
# Forbidden: LibreOffice / soffice / Impress PDF as proof.
#
# Focus: this script ACTIVATES PowerPoint (steals keyboard/mouse focus).
# Do not run while the human is typing elsewhere — or set CAPTURE_NO_ACTIVATE=1
# to skip `activate` (may fail if PPT is fully backgrounded).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Override with CAPTURE_PPTX=…/FSP_NIKITA_SUBMISSION.pptx for the file we ship.
PPTX="${CAPTURE_PPTX:-$ROOT/FSP_NIKITA_DRAFT.pptx}"
OUT="$ROOT/preview_frames"
START="${1:-8}"
END="${2:-11}"
PREFIX="${3:-ppt_verify}"
REQUIRE_NAME_SUBSTR="${CAPTURE_REQUIRE_NAME:-}"

mkdir -p "$OUT"
echo "capture file: $PPTX"
# Always reload from disk — PPT keeps stale in-memory copy after python-pptx saves
ACTIVATE_CMD="activate"
if [[ "${CAPTURE_NO_ACTIVATE:-}" == "1" ]]; then
  ACTIVATE_CMD=""
  echo "CAPTURE_NO_ACTIVATE=1 — not bringing PowerPoint to front"
fi

osascript <<EOF
tell application "Microsoft PowerPoint"
  $ACTIVATE_CMD
  try
    close every presentation saving no
  end try
  delay 0.8
  open POSIX file "$PPTX"
  delay 1.5
end tell
EOF

ACTIVE_NAME=$(osascript -e 'tell application "Microsoft PowerPoint" to return name of active presentation')
echo "active presentation: $ACTIVE_NAME"
if [[ -n "$REQUIRE_NAME_SUBSTR" && "$ACTIVE_NAME" != *"$REQUIRE_NAME_SUBSTR"* ]]; then
  echo "FAIL: expected name containing '$REQUIRE_NAME_SUBSTR', got '$ACTIVE_NAME'" >&2
  exit 1
fi
BASE_OPEN=$(basename "$PPTX")
if [[ "$ACTIVE_NAME" != *"$BASE_OPEN"* && "$ACTIVE_NAME" != *"${BASE_OPEN%.*}"* ]]; then
  echo "FAIL: opened '$ACTIVE_NAME' but asked for '$BASE_OPEN'" >&2
  exit 1
fi

get_win() {
  swift -e '
import Cocoa
let opts = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
if let info = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] {
  for w in info {
    let owner = w[kCGWindowOwnerName as String] as? String ?? ""
    let bounds = w[kCGWindowBounds as String] as? [String: Any]
    let width = (bounds?["Width"] as? NSNumber)?.doubleValue ?? 0
    let wnum = w[kCGWindowNumber as String] as? Int ?? 0
    if owner == "Microsoft PowerPoint" && width > 800 {
      print(wnum); break
    }
  }
}
'
}

for n in $(seq "$START" "$END"); do
  CUR=""
  for attempt in 1 2 3; do
    osascript <<EOF
tell application "Microsoft PowerPoint"
  $ACTIVATE_CMD
  set theView to view of document window 1 of active presentation
  go to slide theView number $n
  -- Select the slide itself (not a shape) — shape selection draws a dashed frame in captures
  try
    select slide $n of active presentation
  end try
end tell
tell application "System Events"
  if exists process "Microsoft PowerPoint" then
    tell process "Microsoft PowerPoint"
      key code 53 -- Escape clears residual shape handles
    end tell
  end if
end tell
EOF
    sleep 1.0
    CUR=$(osascript <<'EOF'
tell application "Microsoft PowerPoint"
  try
    return slide index of slide range of selection of document window 1 of active presentation
  on error
    return "?"
  end try
end tell
EOF
)
    if [[ "$CUR" == "$n" ]]; then
      break
    fi
    echo "retry go-to slide $n (got $CUR, attempt $attempt)"
  done
  if [[ "$CUR" != "$n" ]]; then
    echo "FAIL: asked slide $n but PowerPoint is on $CUR — not writing lying frame" >&2
    exit 1
  fi
  WIN="$(get_win)"
  if [[ -z "$WIN" ]]; then
    echo "FAIL: no PowerPoint window id (TCC / window hidden?)" >&2
    exit 1
  fi
  DEST="$OUT/${PREFIX}_slide_${n}.png"
  /usr/sbin/screencapture -x -l "$WIN" "$DEST"
  BYTES=$(wc -c < "$DEST" | tr -d ' ')
  echo "PPT channel: slide=$n confirmed=$CUR win=$WIN bytes=$BYTES → $DEST"
  if [[ "$BYTES" -lt 100000 ]]; then
    echo "FAIL: capture too small" >&2
    exit 1
  fi
done

echo "done — Microsoft PowerPoint only (no LibreOffice)"
