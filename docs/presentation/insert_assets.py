#!/usr/bin/env python3
"""Insert built assets into FSP_NIKITA_DRAFT.pptx.

Uses add_picture at template coordinates — PicturePlaceholder.insert_picture
was shifting/breaking positions on this LCT template.
Run after fill_slides_7_11.py.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_DRAFT.pptx"
ASSETS = ROOT / "assets"

# Geoscan / template slot (EMU) — full height; branded panel is designed to meet the divider.
S8_PHOTO = (0, 335_267, 6_456_363, 2_971_784)
# Slide 9: MUST be square — non-square (1.88×1.70) squashed circular portraits into ovals.
# Card ~2.40″ wide; names sit at y≈3.96″ → max square ≈2.00″ with inset.
S9_PHOTO_SIZE = (2.00, 2.00)  # inches, square
S9_PHOTO_TOP_INSET = 0.18  # inches from card top
S9_NAME_GAP = 0.08  # inches below photo before name box


def delete_picture_placeholders(slide) -> int:
    n = 0
    for sh in list(slide.shapes):
        try:
            if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                sh._element.getparent().remove(sh._element)
                n += 1
        except Exception:
            continue
    return n


def main() -> None:
    slide8 = ASSETS / "slide8_visual.png"
    # Same order as Geoscan cards / slide-8 panel: Тимофей · Данила · Никита
    portraits = [
        ASSETS / "portrait_timofey.png",
        ASSETS / "portrait_danila.png",
        ASSETS / "portrait_nikita.png",
    ]
    for p in [slide8, *portraits]:
        if not p.exists():
            raise SystemExit(f"missing {p} — run build_assets.py first")

    prs = Presentation(str(PPTX))

    s8 = prs.slides[7]
    print(f"slide8 removed placeholders: {delete_picture_placeholders(s8)}")
    # Also remove previously add_picture-d images sitting in the photo slot
    for sh in list(s8.shapes):
        try:
            if sh.shape_type == 13 and sh.left is not None and int(sh.left) < 1_000_000:  # PICTURE
                sh._element.getparent().remove(sh._element)
        except Exception:
            pass
    left, top, w, h = S8_PHOTO
    s8.shapes.add_picture(str(slide8), left, top, width=w, height=h)
    print("slide8: slide8_visual (stand)")

    s9 = prs.slides[8]
    print(f"slide9 removed placeholders: {delete_picture_placeholders(s9)}")
    for sh in list(s9.shapes):
        try:
            if sh.shape_type == 13:  # PICTURE
                sh._element.getparent().remove(sh._element)
        except Exception:
            pass
    cards = []
    for sh in s9.shapes:
        name = getattr(sh, "name", "") or ""
        # h>2.5″ (not 4.37″): after card-hug to roles, cards are ~4.45″ and must still match
        if "Скругленный прямоугольник" in name and sh.width > 2_000_000 and sh.height > 2_500_000:
            cards.append(sh)
    cards.sort(key=lambda s: s.left)
    if len(cards) < 3:
        raise SystemExit(f"slide9: expected 3 cards after fill, got {len(cards)}")
    EMU = 914400
    pw, ph = S9_PHOTO_SIZE
    if abs(pw - ph) > 1e-6:
        raise SystemExit(f"S9_PHOTO_SIZE must be square to avoid squash, got {pw}×{ph}")
    photo_bottoms = []
    for card, path in zip(cards[:3], portraits):
        side = min(pw, ph)
        # Cap to card width with 0.12″ side pad
        max_side = (card.width / EMU) - 0.24
        side = min(side, max_side)
        w = h = int(side * EMU)
        left = int(card.left + (card.width - w) / 2)
        top = int(card.top + S9_PHOTO_TOP_INSET * EMU)
        s9.shapes.add_picture(str(path), left, top, width=w, height=h)
        photo_bottoms.append(top + h)
        print(f"slide9: {path.name} square {side:.2f}\" @ L={left} (centered, no squash)")

    # Push name/role boxes below larger photos so they don't collide
    name_texts = {"Тимофей Розов", "Данила Бессмертный", "Никита Холод"}
    names = sorted(
        [sh for sh in s9.shapes if sh.has_text_frame and sh.text_frame.text.strip() in name_texts],
        key=lambda s: s.left,
    )
    roles = sorted(
        [
            sh
            for sh in s9.shapes
            if sh.has_text_frame
            and any(
                sh.text_frame.text.strip().startswith(p)
                for p in ("Тест и подбор", "Тимлид", "UI и сценарии")
            )
        ],
        key=lambda s: s.left,
    )
    for i, nm in enumerate(names[:3]):
        want_top = int(photo_bottoms[i] + S9_NAME_GAP * EMU)
        nm.top = want_top
        if i < len(roles):
            roles[i].top = want_top + nm.height
        print(f"slide9: name[{i}] top→{want_top / EMU:.2f}\"")

    prs.save(str(PPTX))
    print(f"saved {PPTX}")

    # Binding gate — do not skip after insert
    import subprocess
    import sys

    rc = subprocess.call([sys.executable, str(ROOT / "gate_check.py")])
    if rc != 0:
        raise SystemExit("gate_check failed after insert — fix before claiming ready")
    rc2 = subprocess.call([sys.executable, str(ROOT / "full_audit.py")])
    if rc2 != 0:
        raise SystemExit("full_audit failed after insert — fix before claiming ready")


if __name__ == "__main__":
    main()
