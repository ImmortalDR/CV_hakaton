#!/usr/bin/env python3
"""Build presentation assets — never destroy Geoscan photos.

Lesson: pixel «matte» that treats dark pixels as background punches white holes
in hair and night shots. Use Geoscan circle PNGs as-is.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

PURPLE = (82, 9, 120)
DEEP = (36, 8, 58)
PINK = (196, 88, 168)
WHITE = (255, 255, 255)
SOFT = (236, 230, 245)
ROLE = (232, 160, 210)
# Sampled from Geoscan slide2 panel background
PANEL_PURPLE = (70, 18, 111)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _gradient(size: tuple[int, int], c0=DEEP, c1=PURPLE) -> Image.Image:
    w, h = size
    im = Image.new("RGB", (w, h), c0)
    px = im.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        for x in range(w):
            u = x / max(w - 1, 1)
            rr = int(r + (PINK[0] - r) * u * 0.12)
            gg = int(g + (PINK[1] - g) * u * 0.08)
            bb = int(b + (PINK[2] - b) * u * 0.15)
            px[x, y] = (rr, gg, bb)
    return im


def _nano_lattice(draw: ImageDraw.ImageDraw, w: int, h: int, step: int = 72) -> None:
    for y in range(0, h + step, step):
        for x in range(0, w + step, step):
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255, 28))
            if (x // step + y // step) % 2 == 0:
                draw.line((x, y, x + step // 2, y + step // 2), fill=(255, 255, 255, 18), width=1)


def make_logo() -> Path:
    s = 1024
    im = _gradient((s, s))
    overlay = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    _nano_lattice(d, s, s, 80)
    cx, cy, r = s // 2, int(s * 0.42), 280
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 220), width=6)
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 30)
        pts.append((cx + int(r * 0.7 * math.cos(a)), cy + int(r * 0.7 * math.sin(a))))
    d.line(pts + [pts[0]], fill=(*PINK, 230), width=5)
    for i in range(6):
        a = math.radians(60 * i - 30)
        x = cx + int(r * 0.4 * math.cos(a))
        y = cy + int(r * 0.4 * math.sin(a))
        d.line((cx, cy, x, y), fill=(255, 255, 255, 200), width=3)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(*PINK, 255))
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(255, 255, 255, 255))
    base = Image.alpha_composite(im.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(base)
    f1, f2 = _font(78, bold=True), _font(56, bold=True)
    for text, font, y in (("НАНОТЕХ", f1, 760), ("АЛЬЯНС", f2, 860)):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((s - tw) // 2, y), text, font=font, fill=WHITE)
    out = ASSETS / "logo_nano_alliance.png"
    base.convert("RGB").save(out, quality=95)
    return out


def make_portrait_fallback(letter: str, filename: str) -> Path:
    s = 1200
    im = _gradient((s, s), DEEP, PURPLE)
    draw = ImageDraw.Draw(im)
    f = _font(420, bold=True)
    bbox = draw.textbbox((0, 0), letter, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((s - tw) // 2, (s - th) // 2 - 40), letter, font=f, fill=WHITE)
    out = ASSETS / filename
    im.save(out, quality=95)
    return out


def ensure_geoscan_portraits() -> list[Path]:
    """Copy Geoscan circle PNGs verbatim — NO pixel matte (that punched white holes)."""
    # Prefer media extracted from Geoscan deck (exact slide-9 assets)
    extract = ASSETS / "_geoscan_extract"
    # Geoscan slide 3 order: Timofey, Danila, Nikita → we want Danila, Nikita, Timofey
    extract_map = {
        "portrait_danila.png": "slide3_pic2.png",  # Данила
        "portrait_nikita.png": "slide3_pic3.png",  # Никита
        "portrait_timofey.png": "slide3_pic1.png",  # Тимофей
    }
    src_dir = ASSETS / "from_geoscan"
    out: list[Path] = []
    for dest_name, extract_name in extract_map.items():
        dest = ASSETS / dest_name
        src_extract = extract / extract_name
        src_geo = src_dir / dest_name
        if src_extract.exists():
            shutil.copyfile(src_extract, dest)
            out.append(dest)
            print(f"  portrait {dest_name}: from Geoscan slide3 (clean)")
        elif src_geo.exists():
            shutil.copyfile(src_geo, dest)
            out.append(dest)
            print(f"  portrait {dest_name}: from from_geoscan (clean)")
        elif dest.exists() and dest.stat().st_size > 100_000:
            out.append(dest)
            print(f"  portrait {dest_name}: kept existing")
        else:
            out.append(make_portrait_fallback(dest_name.split("_")[1][0].upper(), dest_name))
            print(f"  portrait {dest_name}: FALLBACK monogram")
    return out


def _cover_rect(im: Image.Image, box: tuple[int, int, int, int], color=PANEL_PURPLE) -> None:
    ImageDraw.Draw(im).rectangle(box, fill=color)


def _center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: int,
    y: int,
    font: ImageFont.ImageFont,
    fill,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y), text, font=font, fill=fill)


def _paste_circle_portrait(
    base: Image.Image, portrait: Path, cx: int, cy: int, diameter: int
) -> None:
    """Paste circular Geoscan portrait centered at (cx,cy) — square resize + alpha mask."""
    por = Image.open(portrait).convert("RGBA")
    por = por.resize((diameter, diameter), Image.Resampling.LANCZOS)
    # Hard circular mask — kill any residual square fringe
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, diameter - 2, diameter - 2), fill=255)
    por.putalpha(Image.composite(por.split()[-1], mask, mask))
    x, y = cx - diameter // 2, cy - diameter // 2
    if base.mode != "RGBA":
        base_rgba = base.convert("RGBA")
        base_rgba.paste(por, (x, y), por)
        base.paste(base_rgba.convert(base.mode))
    else:
        base.paste(por, (x, y), por)


def make_slide8_visual(portraits: list[Path]) -> Path:
    """Clean FSP team panel — no overlapping circles, no backing band under faces.

    Built on solid PANEL_PURPLE (not a painted strip over Geoscan faces — that left
    a visible rectangle «form» behind the circles). Title kept from Geoscan chrome.
    """
    w, h = 1400, 640
    # Solid field — same purple as Geoscan panel (no mid-band rectangle)
    im = Image.new("RGBA", (w, h), (*PANEL_PURPLE, 255))
    draw = ImageDraw.Draw(im)
    # Draw title ourselves — Geoscan top-crop brought a dashed rule + clipped glyphs
    # y=48 — keep full glyphs below top edge (y=28 looked clipped when panel is cropped in slot)
    _center_text(draw, "НАНОТЕХНОЛОГИЧЕСКИЙ АЛЬЯНС", w // 2, 48, _font(36, bold=True), WHITE)
    _center_text(draw, "ФСП · ЛЦТ 2026 · Обратный найм", w // 2, 98, _font(22, bold=True), (255, 0, 83))

    # Three faces: diam 280, centers 300 apart → gap between rings = 20px (no overlap)
    centers = (300, 700, 1100)
    face_diam = 280
    face_cy = 310  # more air under title (was 270 → title kissed avatars)
    gap_ring = centers[1] - centers[0] - face_diam
    if gap_ring < 16:
        raise SystemExit(f"face rings would overlap: gap_ring={gap_ring}")

    names = ("Тимофей Розов", "Данила Бессмертный", "Никита Холод")
    roles = ("Тест", "Сервер", "UI")
    by_name = {p.name: p for p in portraits}
    ordered = [
        by_name.get("portrait_timofey.png") or portraits[2],
        by_name.get("portrait_danila.png") or portraits[0],
        by_name.get("portrait_nikita.png") or portraits[1],
    ]
    name_y = face_cy + face_diam // 2 + 20
    role_y = name_y + 34
    for cx, por, name, role in zip(centers, ordered, names, roles):
        _paste_circle_portrait(im, por, cx, face_cy, face_diam)
        _center_text(draw, name, cx, name_y, _font(22, bold=True), WHITE)
        _center_text(draw, role, cx, role_y, _font(20, bold=True), (255, 0, 83))

    # Thin magenta divider at bottom (Geoscan cue) — full width of panel only
    ImageDraw.Draw(im).rectangle((0, h - 8, w, h), fill=(255, 0, 83, 255))

    slot_w, slot_h = 2170, int(2170 * 3.25 / 7.06)
    fitted = im.convert("RGB").resize((slot_w, slot_h), Image.Resampling.LANCZOS)
    path = ASSETS / "slide8_visual.png"
    fitted.save(path, quality=95)
    print(
        f"  slide8_visual: clean field, diam={face_diam}, ring_gap={gap_ring}px, "
        f"out={slot_w}x{slot_h}"
    )
    return path


def make_wordmark() -> Path:
    w, h = 2200, 480
    im = _gradient((w, h))
    draw = ImageDraw.Draw(im)
    f1, f2 = _font(64, bold=True), _font(34)
    draw.text((80, 160), "Нанотехнологический альянс", font=f1, fill=WHITE)
    draw.text((80, 250), "ФСП · ЛЦТ 2026", font=f2, fill=SOFT)
    out = ASSETS / "wordmark_nano_alliance.png"
    im.save(out, quality=95)
    return out


def main() -> None:
    print("assets:")
    logo = make_logo()
    word = make_wordmark()
    portraits = ensure_geoscan_portraits()
    slide8 = make_slide8_visual(portraits)
    for p in [logo, word, *portraits, slide8]:
        print(f"  {p.name} {p.stat().st_size}")


if __name__ == "__main__":
    main()
