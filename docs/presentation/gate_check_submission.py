#!/usr/bin/env python3
"""Gates for the FILE we ship: FSP_NIKITA_SUBMISSION.pptx. Exit 0 = GATE SUBMISSION PASS.

Catches: wrong slide count, template junk, empty placeholders, VT, sparse slides.
Does NOT replace PowerPoint eye check — still need sub_final_slide_*.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_SUBMISSION.pptx"
EXPECTED = 10
ALLOWED_PT = {11.0, 12.0, 13.0, 15.0, 16.0, 20.0, 22.0, 24.0}  # 24 = template step circles
TEMPLATE_LEAKS = (
    "Шаблон презентации",
    "ВВОДНЫЕ",
    "Привет, участник",
    "РЕКОМЕНДУЕМАЯ СТРУКТУРА",
    "Заголовок слайда",
    "Текст слайда",
    "ЛОГОТИПЫ ПОСТАНОВЩИКА",
    "ИКОНКИ",
    "Образец текста",
    "Имя Фамилия",
    "НАЗВАНИЕ",
)


def main() -> int:
    fails: list[str] = []
    if not PPTX.exists():
        print("GATE SUBMISSION FAIL — missing file")
        return 1
    prs = Presentation(str(PPTX))
    n = len(prs.slides)
    if n != EXPECTED:
        fails.append(f"slide count {n} ≠ {EXPECTED}")
    for i, slide in enumerate(prs.slides, 1):
        blob = []
        for sh in slide.shapes:
            if getattr(sh, "has_table", False):
                for row in sh.table.rows:
                    for cell in row.cells:
                        t = (cell.text_frame.text if cell.text_frame else "").strip()
                        if not t:
                            continue
                        blob.append(t)
                        for leak in TEMPLATE_LEAKS:
                            if leak in t:
                                fails.append(f"s{i} template leak «{leak}» in table")
                        if "\x0b" in t:
                            fails.append(f"s{i} VT soft-break in table")
                continue
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text.strip()
            if not t:
                continue
            blob.append(t)
            for leak in TEMPLATE_LEAKS:
                if leak in t:
                    fails.append(f"s{i} template leak «{leak}»")
            if "\x0b" in t and i > 1:
                # title case from organizer may keep VT — flag only content slides
                fails.append(f"s{i} VT soft-break")
            name = getattr(sh, "name", "") or ""
            if name.startswith("Скругленный") and t.strip().isdigit():
                continue
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.text.strip() and r.font.size is not None:
                        pt = float(r.font.size.pt)
                        if pt not in ALLOWED_PT:
                            fails.append(f"s{i} type {pt}pt")
        joined = "\n".join(blob)
        if len(joined) < 40:
            fails.append(f"s{i} sparse ({len(joined)} chars)")
        # Footer must match 1..N after trim (classic stupid error: leftover 14/25)
        for sh in slide.shapes:
            name = getattr(sh, "name", "") or ""
            if "Номер слайда" not in name or not sh.has_text_frame:
                continue
            num = sh.text_frame.text.strip()
            if num != str(i):
                fails.append(f"s{i} footer number «{num}» ≠ {i}")
            if "\x0b" in sh.text_frame.text:
                fails.append(f"s{i} VT in footer")
        for sh in slide.shapes:
            if sh.has_text_frame and "\x0b" in sh.text_frame.text:
                fails.append(f"s{i} VT soft-break in content")
    if fails:
        print("GATE SUBMISSION FAIL")
        for f in fails[:50]:
            print(" -", f)
        return 1
    print("GATE SUBMISSION PASS")
    print(f" file={PPTX.name} slides={n} no template leaks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
