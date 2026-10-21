#!/usr/bin/env python3
"""Gates for free slides 12–14 (outside locked 7–11). Exit 0 = GATE OUTSIDE PASS.

Catches:
- wrong shape / empty picture placeholder
- type ramp / VT / Invite EN / custom bullets
- overflow
- SG-density-ref: short copy in tall body boxes (пустыня)
- SG-aspect / bad demo shot: picture blob aspect ≪ slot, tiny width, or phone-stand assets
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_DRAFT.pptx"
EMU = 914400.0

OUTSIDE = (12, 13, 14)
ALLOWED_PT = {11.0, 12.0, 13.0, 15.0, 16.0, 20.0, 22.0}
FILL_MAX = 1.55
# Slide 13: text past white panel = dark-on-purple (illegible) — tight overflow
FILL_MAX_BY_SLIDE = {13: 1.05}
# Anti-desert: estimated text height must cover at least this fraction of the box
DENSITY_MIN_FILL = {
    12: 0.48,
    14: 0.48,
}
DENSITY_MIN_CHARS = {
    12: 520,
    14: 420,
}
# Slide 13 is a real 5×2 table (header + 4 proof rows) — not freeform two columns
S13_TABLE_MIN_ROWS = 5
S13_TABLE_MIN_COLS = 2
S13_TABLE_MIN_CHARS = 280

# Picture must roughly match slot aspect (stretch of phone into tall panel = FAIL)
ASPECT_TOL = 0.28  # |a_img - a_slot| / a_slot
MIN_PIC_WIDTH_PX = 1000
# Phone-stand screenshots are ~0.36 — never OK in ~0.89 tall slot
BANNED_NAME_SUBSTR = ("demo_stand_",)

EXPECTED = {
    12: {"title": "Заголовок 27", "body": "Объект 28"},
    13: {"title": "Заголовок 1", "body": "Объект 2"},
    14: {"title": "Заголовок 2", "body": "Текст 6", "picture": True},
}

FORBIDDEN = (
    "НАЗВАНИЕ",
    "Имя Фамилия",
    "Образец текста",
    "дописать",
    "Вставка рисунка",
    "Вставка таблицы",
)

FORBIDDEN_BODY_HOST = {
    13: "Скругленный прямоугольник 3",
}


def _shape(slide, name: str):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    return None


def estimate_need_h_in(text: str, width_in: float, pt: float = 13.0) -> float:
    avg_char_w = 0.52 * pt / 72.0
    cpl = max(8, int(width_in / avg_char_w))
    lines = 0.0
    for para in text.split("\n"):
        if not para.strip():
            # blank lines still eat vertical space on the slide (anti-desert)
            lines += 0.55
            continue
        lines += max(1, (len(para) + cpl - 1) // cpl)
    return lines * (pt / 72.0) * 1.15


def first_run_pt(shape) -> float | None:
    if not shape.has_text_frame:
        return None
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            if run.text.strip() and run.font.size is not None:
                return float(run.font.size.pt)
    return None


def _picture_blob_size(shape) -> tuple[int, int] | None:
    try:
        blob = shape.image.blob
    except Exception:
        return None
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(blob))
        return im.size
    except Exception:
        return None


def check_slide14_picture(slide, fails: list[str]) -> None:
    pics = []
    for sh in slide.shapes:
        try:
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE and sh.left is not None and int(sh.left) > 5_000_000:
                pics.append(sh)
            if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                fails.append("s14 SG-placeholder empty picture slot (Вставка рисунка)")
        except Exception:
            continue
    if not pics:
        fails.append("s14 SG-placeholder no picture in right slot")
        return

    pic = max(pics, key=lambda s: s.width * s.height)
    slot_w = pic.width / EMU
    slot_h = pic.height / EMU
    if slot_h <= 0:
        fails.append("s14 picture slot height 0")
        return
    slot_aspect = slot_w / slot_h

    size = _picture_blob_size(pic)
    if size is None:
        fails.append("s14 cannot read picture blob")
        return
    iw, ih = size
    if ih <= 0:
        fails.append("s14 picture blob height 0")
        return
    img_aspect = iw / ih

    rel = abs(img_aspect - slot_aspect) / slot_aspect
    if rel > ASPECT_TOL:
        fails.append(
            f"s14 SG-aspect bad demo shot: img={img_aspect:.3f} slot={slot_aspect:.3f} "
            f"rel_err={rel:.2f} (phone/stand stretch into tall panel)"
        )
    if iw < MIN_PIC_WIDTH_PX:
        fails.append(
            f"s14 SG-aspect soft/tiny source width={iw}px < {MIN_PIC_WIDTH_PX} "
            f"(use desktop cover crop, not stand_* )"
        )

    # Filename hint from zip relationships (best-effort)
    try:
        # shape.image.filename sometimes available
        fname = getattr(pic.image, "filename", "") or ""
        low = fname.lower()
        for bad in BANNED_NAME_SUBSTR:
            if bad in low:
                fails.append(f"s14 banned asset name «{fname}» ({bad}*)")
    except Exception:
        pass


def check_density(sn: int, body, fails: list[str]) -> None:
    if body is None or not body.has_text_frame:
        return
    text = body.text_frame.text.strip()
    min_chars = DENSITY_MIN_CHARS.get(sn, 360)
    if len(text) < min_chars:
        fails.append(
            f"s{sn} SG-density-ref body chars={len(text)} < {min_chars} (пустыня)"
        )
    pt = first_run_pt(body) or 13.0
    w_in = body.width / EMU
    h_in = body.height / EMU
    if h_in <= 0:
        return
    need = estimate_need_h_in(text, w_in, pt)
    fill = need / h_in
    min_fill = DENSITY_MIN_FILL.get(sn, 0.38)
    if fill < min_fill:
        fails.append(
            f"s{sn} SG-density-ref fill={fill:.2f} < {min_fill:.2f} "
            f"(need={need:.2f}\" / have={h_in:.2f}\") — уплотните текст, не кегль"
        )
    # Too many blank gaps = visual desert even if chars look ok
    if "\n\n\n" in text.replace("\r\n", "\n"):
        fails.append(f"s{sn} SG-density-ref too many blank gaps (\\n\\n\\n)")


def main() -> int:
    if not PPTX.exists():
        print(f"FAIL missing {PPTX}")
        return 1

    fails: list[str] = []
    prs = Presentation(str(PPTX))

    for sn in OUTSIDE:
        slide = prs.slides[sn - 1]
        exp = EXPECTED[sn]
        title = _shape(slide, exp["title"])
        body = _shape(slide, exp["body"])
        if title is None or not title.has_text_frame or not title.text_frame.text.strip():
            fails.append(f"s{sn} EMPTY_TITLE ({exp['title']})")
        if sn != 13:
            if body is None or not body.has_text_frame or len(body.text_frame.text.strip()) < 40:
                fails.append(f"s{sn} EMPTY_OR_SPARSE_BODY ({exp['body']})")

        bad_host = FORBIDDEN_BODY_HOST.get(sn)
        if bad_host:
            host = _shape(slide, bad_host)
            if host and host.has_text_frame and len(host.text_frame.text.strip()) > 20:
                fails.append(
                    f"s{sn} SG-placeholder body on decorative «{bad_host}» "
                    f"(use content placeholder «{exp['body']}»)"
                )

        if exp.get("picture"):
            check_slide14_picture(slide, fails)

        for sh in slide.shapes:
            if getattr(sh, "has_table", False):
                # table cells checked for forbidden / VT below via cell text
                for row in sh.table.rows:
                    for cell in row.cells:
                        t = cell.text_frame.text if cell.text_frame else ""
                        if "\x0b" in t or "\v" in t:
                            fails.append(f"s{sn} SG-vt soft-break in table")
                        for bad in FORBIDDEN:
                            if bad in t:
                                fails.append(f"s{sn} SG-placeholder «{bad}» in table")
                continue
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text
            if "номер" in (sh.name or "").lower():
                continue
            if "\x0b" in t or "\v" in t:
                fails.append(f"s{sn} SG-vt soft-break in {sh.name}")
            if "Invite" in t:
                fails.append(f"s{sn} SG-copy-ru «Invite» in {sh.name}")
            for bad in FORBIDDEN:
                if bad in t:
                    fails.append(f"s{sn} SG-placeholder «{bad}» in {sh.name}")
            if t.lstrip().startswith("•") or "\n•" in t:
                fails.append(f"s{sn} SG-repetition custom «•» in {sh.name}")
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    if not run.text.strip() or run.font.size is None:
                        continue
                    pt = round(float(run.font.size.pt), 1)
                    if pt not in ALLOWED_PT:
                        fails.append(f"s{sn} SG-type-ramp {sh.name} pt={pt}")

        if sn != 13 and body and body.has_text_frame and body.text_frame.text.strip():
            pt = first_run_pt(body) or 13.0
            w_in = body.width / EMU
            h_in = body.height / EMU
            need = estimate_need_h_in(body.text_frame.text, w_in, pt)
            fill_max = FILL_MAX_BY_SLIDE.get(sn, FILL_MAX)
            if need > h_in * fill_max:
                fails.append(
                    f"s{sn} SG-overflow {body.name} need={need:.2f}\" have={h_in:.2f}\" "
                    f"ratio={need/h_in:.2f} (max {fill_max})"
                )
            check_density(sn, body, fails)

        if sn == 13:
            tables = [sh for sh in slide.shapes if getattr(sh, "has_table", False)]
            if not tables:
                fails.append("s13 SG-table missing — expected 5×2 proof table")
            else:
                tbl = max(tables, key=lambda s: s.width * s.height)
                nrows = len(tbl.table.rows)
                ncols = len(tbl.table.columns)
                if nrows < S13_TABLE_MIN_ROWS or ncols < S13_TABLE_MIN_COLS:
                    fails.append(
                        f"s13 SG-table size {nrows}x{ncols} "
                        f"< {S13_TABLE_MIN_ROWS}x{S13_TABLE_MIN_COLS}"
                    )
                chars = 0
                for row in tbl.table.rows:
                    for cell in row.cells:
                        chars += len((cell.text_frame.text or "").strip())
                if chars < S13_TABLE_MIN_CHARS:
                    fails.append(
                        f"s13 SG-table chars={chars} < {S13_TABLE_MIN_CHARS}"
                    )
                # Freeform sidebar must be gone (was crooked two-column layout)
                names = {getattr(sh, "name", "") for sh in slide.shapes}
                if "Шпаргалка 13" in names or "Шпаргалка тело 13" in names:
                    fails.append("s13 leftover freeform «Шпаргалка» — use table only")

    if fails:
        seen: set[str] = set()
        uniq = []
        for f in fails:
            if f not in seen:
                seen.add(f)
                uniq.append(f)
        print("GATE OUTSIDE FAIL")
        for f in uniq:
            print(" -", f)
        return 1

    print("GATE OUTSIDE PASS")
    print(
        f" checked slides {list(OUTSIDE)} "
        f"density/aspect/type/overflow/vt/placeholder in {PPTX.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
