#!/usr/bin/env python3
"""Full banal-mistake audit for LCT slides 7–11. Exit 0 = clean enough for gate+eye."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_DRAFT.pptx"
EMU = 914400.0

FORBIDDEN = (
    "НАЗВАНИЕ",
    "Имя Фамилия",
    "Образец текста",
    "дописать",
    "не используется",
    "Роль в команде",
    "В чем суть",
    "В чём суть",
    "Капитан: ФИО",
)


def main() -> int:
    if not PPTX.exists():
        print("FAIL missing pptx")
        return 1

    issues: list[str] = []
    prs = Presentation(str(PPTX))

    # gate_check first
    rc = subprocess.call([sys.executable, str(ROOT / "gate_check.py")])
    if rc != 0:
        issues.append("gate_check.py FAIL")

    with zipfile.ZipFile(PPTX) as z:
        for name in z.namelist():
            if not name.startswith("ppt/slides/slide") or name.endswith(".rels"):
                continue
            # map to human index via presentation order later — scan all, filter by content
            blob = "\n".join(
                re.findall(r"<a:t[^>]*>([^<]*)</a:t>", z.read(name).decode("utf-8", "replace"))
            )

    for human_n in (8, 9, 10, 11):
        slide = prs.slides[human_n - 1]
        for sh in slide.shapes:
            if not getattr(sh, "has_text_frame", False):
                continue
            t = sh.text_frame.text
            for bad in FORBIDDEN:
                if bad in t:
                    issues.append(f"s{human_n} PLACEHOLDER «{bad}»")
            if "\x0b" in t or "\v" in t:
                issues.append(f"s{human_n} VT soft-break «{t.strip()[:40]}»")
            try:
                if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.TITLE:
                    if human_n in (8, 9, 10):
                        if not t.strip():
                            issues.append(f"s{human_n} EMPTY_TITLE")
                        on_pink = False
                        for other in slide.shapes:
                            oname = getattr(other, "name", "") or ""
                            if "Скругленный прямоугольник" not in oname:
                                continue
                            try:
                                if (
                                    other.top < 1.2 * EMU
                                    and other.left < 5.0 * EMU
                                    and other.height < 1.0 * EMU
                                ):
                                    on_pink = True
                                    break
                            except Exception:
                                continue
                        for p in sh.text_frame.paragraphs:
                            for r in p.runs:
                                if not r.text.strip():
                                    continue
                                c = None
                                try:
                                    c = r.font.color.rgb
                                except Exception:
                                    pass
                                if c is None:
                                    issues.append(f"s{human_n} TITLE no color")
                                else:
                                    R = int(str(c)[0:2], 16)
                                    G = int(str(c)[2:4], 16)
                                    B = int(str(c)[4:6], 16)
                                    lum = R + G + B
                                    if on_pink and lum < 500:
                                        issues.append(f"s{human_n} TITLE dark {c} on pink")
                                    if (not on_pink) and lum > 500:
                                        issues.append(f"s{human_n} TITLE light {c} on white")
            except Exception:
                pass

        blob = "\n".join(
            sh.text_frame.text for sh in slide.shapes if getattr(sh, "has_text_frame", False)
        )
        if human_n in (8, 10) and re.search(r"\bInvite\b|\binvite\b", blob):
            issues.append(f"s{human_n} EN Invite")

        # Content overlaps: body×body always; label×body via content-bottom (gate_check)
        # Do NOT ignore label×body — that hid real collisions. Tall empty label *shapes* OK.
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from gate_check import (  # noqa: WPS433 — same folder scripts
            PROXIMITY_PAIRS,
            label_content_bottom_emu,
            PROX_CONTENT_GAP_MIN,
            find_shape_with,
        )

        for slide_n, lab_pref, body_key in PROXIMITY_PAIRS:
            if slide_n != human_n:
                continue
            lab = find_shape_with(slide, lambda t, p=lab_pref: t.startswith(p))
            body = find_shape_with(slide, lambda t, k=body_key: k in t)
            if not lab or not body:
                continue
            gap = (body.top - label_content_bottom_emu(lab)) / EMU
            if gap < PROX_CONTENT_GAP_MIN - 1e-6:
                issues.append(
                    f"s{human_n} CONTENT-OVERLAP gap={gap:.2f}\" «{lab_pref}»×body"
                )

        texts = []
        for sh in slide.shapes:
            if not getattr(sh, "has_text_frame", False):
                continue
            t = sh.text_frame.text.strip()
            if len(t) < 10 or t.isdigit():
                continue
            # skip section labels — handled above via content-gap
            if any(
                t.startswith(p)
                for p in (
                    "Краткое описание",
                    "Уникальность",
                    "О команде",
                    "Краткая история",
                    "Почему вы",
                    "С какими",
                    "Техническая суть",
                    "Маркетинговая суть",
                    "Почему это выгодно",
                    "КОМАНДА",
                    "КОРОТКО",
                )
            ):
                continue
            try:
                box = (sh.left / EMU, sh.top / EMU, sh.width / EMU, sh.height / EMU)
            except Exception:
                continue
            texts.append((box, t))
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                a, ta = texts[i]
                b, tb = texts[j]
                ax, ay, aw, ah = a
                bx, by, bw, bh = b
                ix1, iy1 = max(ax, bx), max(ay, by)
                ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
                if ix2 > ix1 and iy2 > iy1:
                    area = (ix2 - ix1) * (iy2 - iy1)
                    if area >= 0.15:
                        issues.append(f"s{human_n} OVERLAP {area:.2f} «{ta[:40]}»×«{tb[:40]}»")

        pics = sum(1 for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE)
        if human_n == 8 and pics < 1:
            issues.append("s8 no picture")
        if human_n == 9 and pics < 3:
            issues.append(f"s9 pics={pics}")

    # asset presence (Geoscan brand panel is intentionally dark purple)
    try:
        from PIL import Image

        im = Image.open(ROOT / "assets" / "slide8_visual.png").convert("RGB")
        if im.size[0] < 800 or im.size[1] < 400:
            issues.append(f"slide8_visual too small {im.size}")
        small = im.resize((64, 32))
        px = list(small.getdata())
        mean = sum(p[0] + p[1] + p[2] for p in px) / (len(px) * 3)
        var = sum((p[0] + p[1] + p[2] - mean) ** 2 for p in px) / len(px)
        if var < 80:
            issues.append(f"slide8_visual flat/blank var={var:.0f}")
    except Exception as e:
        issues.append(f"slide8_visual inspect fail: {e}")

    if issues:
        print("FULL AUDIT FAIL")
        for i in issues:
            print(" -", i)
        return 1

    print("FULL AUDIT PASS")
    print(" checked: gate + placeholders + title contrast + VT + Invite + overlap + photos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
