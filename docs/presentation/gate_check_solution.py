#!/usr/bin/env python3
"""Gates for solution-structure slides (15–20, 25, 19, 26). Exit 0 = GATE SOLUTION PASS."""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_DRAFT.pptx"

# Only slides we still ship from the solution block (others dropped from SUBMISSION)
SOLUTION = (16, 25)
ALLOWED_PT = {11.0, 12.0, 13.0, 15.0, 16.0, 20.0, 22.0}
PLACEHOLDERS = (
    "Заголовок слайда",
    "Текст слайда",
    "Заголовок",
    "Описание",
    "• Описание",
)


def main() -> int:
    fails: list[str] = []
    prs = Presentation(str(PPTX))
    for sn in SOLUTION:
        slide = prs.slides[sn - 1]
        blob: list[str] = []
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text.strip()
            name = getattr(sh, "name", "") or ""
            if not t:
                if name.startswith(("Текст", "Заголовок")) and "Номер" not in name:
                    if "Скругленный" in name:
                        continue
                    fails.append(f"s{sn} empty «{name}»")
                continue
            blob.append(t)
            for bad in PLACEHOLDERS:
                if t == bad or t.startswith("Образец"):
                    fails.append(f"s{sn} placeholder «{t[:40]}»")
            if "\x0b" in t:
                fails.append(f"s{sn} VT soft-break")
            if name.startswith("Скругленный") and t.strip().isdigit():
                continue
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.text.strip() and r.font.size is not None:
                        pt = float(r.font.size.pt)
                        if pt not in ALLOWED_PT:
                            fails.append(f"s{sn} type-ramp {pt}pt «{t[:30]}»")
        joined = "\n".join(blob)
        if len(joined) < 80:
            fails.append(f"s{sn} too sparse ({len(joined)} chars)")
    if fails:
        print("GATE SOLUTION FAIL")
        for f in fails[:40]:
            print(" -", f)
        return 1
    print("GATE SOLUTION PASS")
    print(f" checked slides {list(SOLUTION)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
