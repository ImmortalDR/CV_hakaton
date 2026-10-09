#!/usr/bin/env python3
"""Fill LCT slides 7–11 by cloning Geoscan geometry + type ramp on the same template.

Source of truth: Downloads/ЛЦТ2026_Geoscan_презентация.pptx slides 2–5
(= our slides 8–11). Absolute box tops/heights and pt sizes — not «content-fit».
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Pt

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "template_source.pptx"
OUT = ROOT / "FSP_NIKITA_DRAFT.pptx"

TEAM_NAME_SHORT = "НТ АЛЬЯНС"
SLIDE_TITLE = f"КОМАНДА «{TEAM_NAME_SHORT}»"
LAYOUT_TITLE_REPLACEMENTS = (
    ("КОМАНДА «НАЗВАНИЕ»", SLIDE_TITLE),
    ("КОМАНДА «Нанотехнологический альянс»", SLIDE_TITLE),
    ("НАЗВАНИЕ КОМАНДЫ", TEAM_NAME_SHORT),
)

BODY_RGB = RGBColor(0x2A, 0x27, 0x33)
TITLE_RGB = RGBColor(0xFF, 0xFF, 0xFF)
LABEL_RGB = RGBColor(0x6B, 0x2D, 0x8B)
EMU = 914400

# Geoscan type ramp (proven on this template)
PT_TITLE = 22
PT_LABEL = 16
PT_BODY = 13
PT_TEAM = 12
PT_NAME = 15
PT_ROLE = 11
PT_PANEL = 20

# Density matched to Geoscan on the same template boxes (chars ≈ their slide 2/5).
# Anti-pattern we already hit: short copy in huge slots → «пустыня»; stuffing tiny pt → overlap.

# Gate body keys («Тест навыков» / «Грейд из теста») + length ≈ Geoscan slide2 (~290 / ~251).
# Density gate wants ≥240/220 chars; stock Geoscan h=0.97″ overflowed → raise boxes (see BOX).
ESSENCE = (
    "Тест навыков → подтверждённый грейд. Приглашение с вилкой ₽ до переписки.\n"
    "Из профиля, теста и статусов подбора (подтверждено / нет / не проверено) "
    "работодатель видит основания, не «красивое резюме»; контакты — только после "
    "принятия и только этой компании.\n"
    "Стенд: https://85-137-26-131.sslip.io"
)

UNIQUENESS = (
    "Грейд из теста, не из резюме. В подборе статусы честные: подтверждено / нет / "
    "не проверено — «не проверено» не выдаём за полный матч.\n"
    "Без боевого ФСП путь жив. Вилка ₽ в приглашении; согласие отделяет интерес "
    "от контактов. Жюри видит: основание грейда и кто получает контакты."
)

TEAM_ABOUT = (
    "Участники: 3 человека\n"
    "Состав: Розов · Бессмертный · Холод\n"
    "Роли: тест и подбор · сервер и стенд · UI кабинетов\n"
    "Telegram: @l_tyrosine · @TylerDDDDDDD · @Nikita_Khol0d\n"
    "Стенд: https://85-137-26-131.sslip.io"
)

# Same left→right order as Geoscan panel + their cards (Тимофей · Данила · Никита)
TEAM = [
    ("Тимофей Розов", "Тест и подбор\n@l_tyrosine\nМетодики и статусы"),
    ("Данила Бессмертный", "Тимлид / сервер\n@TylerDDDDDDD\nДатасет и стенд"),
    ("Никита Холод", "UI и сценарии\n@Nikita_Khol0d\nКабинеты / HR"),
]

# Slide 10 bands are short — keep each body ≤ ~Geoscan length so it fits under next label.
HISTORY = (
    "«Нанотехнологический альянс» собрался под ФСП ЛЦТ 2026: один — сервер и стенд, "
    "второй — UI кабинетов, третий — тест и подбор. Роли не смешиваем — так быстрее "
    "доводим сквозной путь до живого стенда. Три человека — три зоны ответственности, "
    "без «все делают всё»."
)

INSPIRED = (
    "Нужно связать доказанный навык, честный грейд и согласие на контакт в один путь. "
    "Ошибку «почти» глазами не увидеть — её показывает статус. Сначала навыки и вилка ₽, "
    "потом переписка. Выбрали задачу, где честность статуса важнее «красивой витрины»."
)

HARDSHIPS = (
    "Главный вызов — честно жить в титуле «агрегатор», когда продукт — обратный найм.\n"
    "Второй — демо без боевого ФСП и почты: путь жив, «не проверено» ≠ полный матч, "
    "мок ФСП озвучен как граница MVP. Не маскируем дыру под «полный контур»."
)

TECH = (
    "Стек. React + FastAPI + PostgreSQL — кабинет HR и кандидата на одном стенде.\n"
    "Грейд. Считается на сервере из теста, не из резюме; UI только показывает факт.\n"
    "Подбор. Статусы: подтверждено / нет / не проверено — без подмены «почти».\n"
    "Приглашение. Вилка ₽ в тексте; контакты только после принятия этой компанией.\n"
    "Проверено. Живой стенд: поиск → приглашение → согласие → контакты у своего HR.\n"
    "Стенд. https://85-137-26-131.sslip.io"
)

PEOPLE = (
    "Путь. Тест → доказательства → предложение с вилкой → контакты после согласия.\n"
    "Контроль. Контакты открыты только пригласившей компании, не всему рынку.\n"
    "Честность. Без ФСП путь жив; ФСП ≠ грейд; «не проверено» ≠ полный матч.\n"
    "Выгода заказчику. Меньше ложных матчей и переписок «вслепую»; вилка ₽ сразу в тексте.\n"
    "Дальше. Боевой ФСП, почта, проверка на реальных работодателях и кандидатах."
)

# Geoscan two-line labels (hard paragraphs, not U+000B — gate forbids soft-break)
S10_LABEL_LINES = {
    "Почему вы": (
        "Почему вы выбрали именно эту задачу",
        "из предложенных на хакатоне?",
    ),
    "С какими": (
        "С какими основными сложностями или вызовами",
        "вы столкнулись и как их преодолели?",
    ),
}

LABEL_PREFIXES = (
    "Краткое описание",
    "Уникальность",
    "О команде",
    "Краткая история",
    "Почему вы",
    "С какими",
    "Техническая суть",
    "Маркетинговая суть",
    "Почему это выгодно",
)

GEOSCAN_CARD_LEFTS_IN = (2.52, 5.47, 8.42)

# Absolute boxes from Geoscan (inches) — do not invent
BOX = {
    # slide 8 — raised heights vs Geoscan 0.97″ so density-ref copy fits without clip
    "s8_essence": (7.45, 2.80, 5.41, 1.80),
    # Keep unique above footer (~6.90″): top≈5.20 → h≤1.55
    "s8_unique": (7.48, 5.20, 5.41, 1.55),
    # Hug team copy (~5 lines) — stock 2.62″ left a white foot under Telegram
    "s8_team": (0.37, 4.25, 6.16, 1.55),
    # slide 10
    "s10_history": (0.58, 1.75, 4.84, 1.02),
    "s10_inspired": (0.58, 3.75, 5.41, 1.18),
    "s10_hardships": (0.58, 5.62, 8.00, 1.15),
    # slide 11 — body height after hug (cards shrunk in fill_slide11)
    "s11_tech": (0.64, 2.10, 5.39, 3.10),
    "s11_people": (7.12, 2.10, 5.42, 3.10),
}


def i2e(inches: float) -> int:
    return int(inches * EMU)


def place_box(shape, left: float, top: float, width: float, height: float) -> None:
    shape.left = i2e(left)
    shape.top = i2e(top)
    shape.width = i2e(width)
    shape.height = i2e(height)


def iter_shapes(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from iter_shapes(sh.shapes)


def _strip_bullets(paragraph) -> None:
    from pptx.oxml.ns import qn
    from lxml import etree

    pPr = paragraph._p.get_or_add_pPr()
    for child in list(pPr):
        if child.tag.endswith(("buFont", "buChar", "buAutoNum", "buBlip", "buNone", "buClr")):
            pPr.remove(child)
    etree.SubElement(pPr, qn("a:buNone"))


def _apply_fill_height(shape, lines: list[str], size_pt: float) -> None:
    """Spread paragraphs through tall box; no low gap cap (16pt left white feet)."""
    tf = shape.text_frame
    if len(lines) < 2:
        return
    box_h_pt = (shape.height / EMU) * 72.0
    line_h_pt = size_pt * 1.25
    used = 0.0
    w_in = max(shape.width / EMU, 1.0)
    cpl = max(8, int(w_in / (0.52 * size_pt / 72.0)))
    for line in lines:
        if not line.strip():
            used += line_h_pt * 0.4
        else:
            used += line_h_pt * max(1, (len(line) + cpl - 1) // cpl)
    remain = max(0.0, box_h_pt * 0.97 - used)
    gap = remain / (len(lines) - 1)
    for p in tf.paragraphs[:-1]:
        p.space_after = Pt(max(2.0, gap))
    if tf.paragraphs:
        tf.paragraphs[-1].space_after = Pt(0)


def set_text(
    shape,
    text: str,
    *,
    force_pt: float,
    rgb: RGBColor | None = None,
    bold: bool | None = None,
    fill_height: bool = False,
) -> None:
    tf = shape.text_frame
    lines = text.split("\n")
    font_name = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        font_name = tf.paragraphs[0].runs[0].font.name
    color = rgb if rgb is not None else BODY_RGB
    size = Pt(force_pt)
    tf.clear()
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _strip_bullets(p)
        run = p.add_run()
        run.text = line
        if font_name:
            run.font.name = font_name
        run.font.size = size
        if bold is not None:
            run.font.bold = bold
        run.font.color.rgb = color
    if fill_height:
        _apply_fill_height(shape, lines, force_pt)


def set_tech_people(shape, text: str, *, fill_height: bool = True) -> None:
    """Geoscan style: first word of each line bold, rest regular, 13pt."""
    tf = shape.text_frame
    font_name = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        font_name = tf.paragraphs[0].runs[0].font.name
    lines = text.split("\n")
    tf.clear()
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _strip_bullets(p)
        if ". " in line:
            head, rest = line.split(". ", 1)
            r1 = p.add_run()
            r1.text = head + ". "
            r1.font.size = Pt(PT_BODY)
            r1.font.bold = True
            r1.font.color.rgb = BODY_RGB
            if font_name:
                r1.font.name = font_name
            r2 = p.add_run()
            r2.text = rest
            r2.font.size = Pt(PT_BODY)
            r2.font.bold = False
            r2.font.color.rgb = BODY_RGB
            if font_name:
                r2.font.name = font_name
        else:
            r = p.add_run()
            r.text = line
            r.font.size = Pt(PT_BODY)
            r.font.color.rgb = BODY_RGB
            if font_name:
                r.font.name = font_name
    if fill_height:
        _apply_fill_height(shape, lines, float(PT_BODY))


def find_text(slide, predicate):
    for sh in iter_shapes(slide.shapes):
        if sh.has_text_frame and predicate(sh.text_frame.text.strip()):
            return sh
    return None


def delete_shape(shape) -> None:
    el = shape._element
    el.getparent().remove(el)


def paint_section_labels(slide) -> list[str]:
    done = []
    for sh in iter_shapes(slide.shapes):
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        if not any(t.startswith(p) for p in LABEL_PREFIXES):
            continue
        # Geoscan renamed marketing label
        if t.startswith("Маркетинговая суть"):
            t = "Почему это выгодно заказчику"
        set_text(sh, t, force_pt=PT_LABEL if not t.startswith("Техническая") and not t.startswith("Почему это") else PT_PANEL, rgb=LABEL_RGB, bold=True)
        if t.startswith("Техническая") or t.startswith("Почему это"):
            set_text(sh, t, force_pt=PT_PANEL, rgb=LABEL_RGB, bold=True)
        done.append(f"label:{t[:28]}")
    return done


def _slide_has_pink_title_pill(slide) -> bool:
    for sh in slide.shapes:
        name = getattr(sh, "name", "") or ""
        if "Скругленный прямоугольник" not in name:
            continue
        try:
            if sh.top < i2e(1.2) and sh.left < i2e(5.0) and sh.height < i2e(1.0):
                return True
        except Exception:
            continue
    return False


def _widen_pink_title_pill(slide, title: str) -> None:
    """Pink chrome was ~3.4–4.3″ — long titles clipped visually; widen to fit glyphs."""
    # ~0.14″ per glyph at 20pt bold + padding
    need = max(4.8, min(9.5, 0.55 + len(title) * 0.145))
    for sh in slide.shapes:
        name = getattr(sh, "name", "") or ""
        if "Скругленный прямоугольник" not in name:
            continue
        try:
            if sh.top < i2e(1.2) and sh.left < i2e(5.0) and sh.height < i2e(1.0):
                sh.width = i2e(need)
                sh.height = i2e(0.72)
                _strip_shape_line(sh)
        except Exception:
            continue


def fill_title_placeholder(slide, title: str = SLIDE_TITLE, pt: float = PT_TITLE) -> bool:
    on_pink = _slide_has_pink_title_pill(slide)
    color = TITLE_RGB if on_pink else BODY_RGB
    # Geoscan: pink pill titles are 20pt; slide 8 white field title is 22pt
    use_pt = 20 if on_pink else pt
    for sh in slide.shapes:
        try:
            if not sh.is_placeholder:
                continue
            if sh.placeholder_format.type != PP_PLACEHOLDER.TITLE:
                continue
            cur = sh.text_frame.text.strip() if sh.has_text_frame else ""
            if cur and "КОРОТКО" in cur:
                return False
            if on_pink:
                _widen_pink_title_pill(slide, title)
                # Keep title box inside the widened pill
                sh.top = i2e(0.48)
                sh.height = i2e(0.46)
            else:
                # Hug title box — tall placeholder draws a huge dashed selection frame on capture
                sh.height = i2e(0.55)
            set_text(sh, title, force_pt=use_pt, rgb=color, bold=True)
            return True
        except Exception:
            continue
    return False


def scrub_vertical_tabs(slide) -> int:
    from pptx.oxml.ns import qn

    n = 0
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        for p in sh.text_frame.paragraphs:
            el = p._p
            if not el.findall(qn("a:br")) and "\x0b" not in (p.text or ""):
                continue
            parts = []
            for r in el.findall(qn("a:r")):
                t_el = r.find(qn("a:t"))
                if t_el is not None and t_el.text:
                    parts.append(t_el.text)
            cleaned = " ".join(" ".join(parts).split())
            for child in list(el):
                if child.tag in (qn("a:r"), qn("a:br")):
                    el.remove(child)
            run = p.add_run()
            run.text = cleaned
            n += 1
    return n


def redistribute_slide9(slide) -> list[str]:
    cards = []
    for sh in slide.shapes:
        name = getattr(sh, "name", "") or ""
        if "Скругленный прямоугольник" in name and sh.width > i2e(2.0) and sh.height > i2e(4.0):
            cards.append(sh)
    cards.sort(key=lambda s: s.left)
    if len(cards) != 3:
        return [f"spread_skip_cards={len(cards)}"]

    new_lefts = [i2e(x) for x in GEOSCAN_CARD_LEFTS_IN]
    old_lefts = [c.left for c in cards]
    title_bar_top = i2e(1.2)
    moved = 0
    for sh in list(slide.shapes):
        try:
            left, top = sh.left, sh.top
        except Exception:
            continue
        name = getattr(sh, "name", "") or ""
        if "Номер слайда" in name:
            continue
        if top < title_bar_top and sh.height < i2e(1.0):
            continue
        if left > i2e(11.5):
            continue
        nearest = min(range(3), key=lambda i: abs(left - old_lefts[i]))
        if abs(left - old_lefts[nearest]) > i2e(1.4) and sh not in cards:
            if not (
                old_lefts[nearest] - i2e(0.1)
                <= left
                <= old_lefts[nearest] + cards[0].width + i2e(0.1)
            ):
                continue
        delta = new_lefts[nearest] - old_lefts[nearest]
        if delta:
            sh.left = int(left + delta)
            moved += 1

    names = sorted(
        [sh for sh in slide.shapes if sh.has_text_frame and any(n.split()[0] in sh.text_frame.text for n, _ in TEAM)],
        key=lambda s: s.left,
    )
    # Prefer exact full-name shapes after fill
    names = sorted(
        [sh for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip() in {n for n, _ in TEAM}],
        key=lambda s: s.left,
    )
    roles = sorted(
        [
            sh
            for sh in slide.shapes
            if sh.has_text_frame
            and any(sh.text_frame.text.strip().startswith(r.split("\n")[0]) for _, r in TEAM)
        ],
        key=lambda s: s.left,
    )
    for i, card in enumerate(cards):
        if i >= len(names) or i >= len(roles):
            break
        nm, rl = names[i], roles[i]
        # Geoscan absolute name/role boxes relative to card
        nm.left = int(card.left + i2e(0.19))
        nm.width = i2e(1.88)
        nm.top = i2e(3.96)
        nm.height = i2e(0.69)
        rl.left = nm.left
        rl.width = i2e(2.07)
        rl.top = i2e(4.65)
        # 3 role lines need ~0.95″; stock 1.78″ left a white foot in each card
        rl.height = i2e(0.95)
    # Hug white cards to role bottoms. Keep h≥4.4″ so insert_assets still finds cards.
    cards = sorted(
        [
            sh
            for sh in slide.shapes
            if "Скругленный прямоугольник" in (getattr(sh, "name", "") or "")
            and sh.width > 2.0 * EMU
            and sh.height > 3.0 * EMU
        ],
        key=lambda s: s.left,
    )
    for card in cards[:3]:
        role_bottom = i2e(4.65) + i2e(0.95)
        want = role_bottom + i2e(0.22) - card.top
        card.height = max(want, i2e(4.45))
    return [f"cluster3 moved={moved}"]


def fill_slide8(slide) -> list[str]:
    done = []
    if fill_title_placeholder(slide, pt=PT_TITLE):
        done.append("title")

    done.extend(paint_section_labels(slide))
    lab_e = find_text(slide, lambda t: t.startswith("Краткое описание"))
    lab_u = find_text(slide, lambda t: t.startswith("Уникальность"))
    lab_t = find_text(slide, lambda t: t.startswith("О команде"))
    # Stock label boxes are ~0.73″ tall for one line → geometry nest into body. Hug to glyphs.
    for lab in (lab_e, lab_u, lab_t):
        if lab is not None:
            lab.height = i2e(0.36)

    body_e = find_text(
        slide,
        lambda t: t.startswith("Тест навыков")
        or "вилкой" in t
        or t.startswith("В чем")
        or t.startswith("В чём"),
    )
    body_u = find_text(
        slide,
        lambda t: "Грейд из теста" in t or "sslip.io" in t or "уникальным" in t.lower(),
    )
    body_t = find_text(slide, lambda t: t.startswith("Участники:") or t.startswith("Капитан:"))

    CONTENT_GAP = 0.08
    if body_e and lab_e:
        top = max(BOX["s8_essence"][1], _label_content_bottom_in(lab_e) + CONTENT_GAP)
        _, _, w, h = BOX["s8_essence"]
        place_box(body_e, BOX["s8_essence"][0], top, w, h)
        set_text(body_e, ESSENCE, force_pt=PT_BODY)
        done.append(f"essence@y={top:.2f}")
    if body_u and lab_u:
        top = max(BOX["s8_unique"][1], _label_content_bottom_in(lab_u) + CONTENT_GAP)
        _, _, w, h = BOX["s8_unique"]
        place_box(body_u, BOX["s8_unique"][0], top, w, h)
        set_text(body_u, UNIQUENESS, force_pt=PT_BODY)
        done.append(f"unique@y={top:.2f}")
    if body_t and lab_t:
        top = max(BOX["s8_team"][1], _label_content_bottom_in(lab_t) + CONTENT_GAP)
        _, _, w, h = BOX["s8_team"]
        place_box(body_t, BOX["s8_team"][0], top, w, h)
        set_text(body_t, TEAM_ABOUT, force_pt=PT_TEAM, bold=True)
        done.append(f"team@y={top:.2f}")

    return done


def fill_slide9(slide) -> list[str]:
    done = []
    if fill_title_placeholder(slide):
        done.append("title")
    names, roles = [], []
    for sh in list(iter_shapes(slide.shapes)):
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        first = t.split()[0] if t.split() else ""
        if t == "Имя Фамилия" or t in {n for n, _ in TEAM} or first in {"Данила", "Никита", "Тимофей"}:
            if t == "Имя Фамилия" or any(t == n or t.startswith(n.split()[0]) for n, _ in TEAM):
                names.append(sh)
        elif t.startswith("Роль в команде") or any(t.startswith(r.split("\n")[0]) for _, r in TEAM):
            roles.append(sh)
    names = sorted(names, key=lambda s: s.left)[:3]
    roles = sorted(roles, key=lambda s: s.left)[:3]
    if len(names) < 3 or len(roles) < 3:
        names, roles = [], []
        for sh in list(iter_shapes(slide.shapes)):
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text.strip()
            if t == "Имя Фамилия":
                names.append(sh)
            elif t.startswith("Роль в команде"):
                roles.append(sh)
        names = sorted(names, key=lambda s: s.left)[:3]
        roles = sorted(roles, key=lambda s: s.left)[:3]
    if len(names) < 3 or len(roles) < 3:
        raise SystemExit(f"slide9: need 3 names+roles, got {len(names)}/{len(roles)}")

    for i, (name, role) in enumerate(TEAM):
        set_text(names[i], name, force_pt=PT_NAME, bold=True)
        set_text(roles[i], role, force_pt=PT_ROLE)
        done.append(f"card{i}")

    for sh in list(slide.shapes):
        try:
            left = sh.left
        except Exception:
            continue
        if left < 7_000_000:
            continue
        if sh.has_text_frame and sh.text_frame.text.strip() in {"9", "10", "11"}:
            continue
        name = getattr(sh, "name", "")
        if "Номер слайда" in name:
            continue
        try:
            delete_shape(sh)
            done.append(f"del:{name or left}")
        except Exception:
            pass

    done.extend(redistribute_slide9(slide))
    return done


def _set_twoline_label(shape, line1: str, line2: str) -> None:
    """Geoscan label height without U+000B (gate forbids soft-break)."""
    tf = shape.text_frame
    font_name = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        font_name = tf.paragraphs[0].runs[0].font.name
    tf.clear()
    for i, line in enumerate((line1, line2)):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _strip_bullets(p)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(PT_LABEL)
        run.font.bold = True
        run.font.color.rgb = LABEL_RGB
        if font_name:
            run.font.name = font_name


def _label_content_bottom_in(lab) -> float:
    """Where label glyphs end. Multi-line labels: never above shape bottom (PPT leading)."""
    text = lab.text_frame.text.strip()
    pt = PT_LABEL
    for p in lab.text_frame.paragraphs:
        for r in p.runs:
            if r.text.strip() and r.font.size is not None:
                pt = float(r.font.size.pt)
                break
    w_in = lab.width / EMU
    char_w = 0.62 * pt / 72.0
    cpl = max(8, int(w_in / char_w))
    lines = 0
    for para in text.split("\n"):
        if not para.strip():
            continue
        lines += max(1, (len(para) + cpl - 1) // cpl)
    # PPT line spacing is looser than 1.15 — use 1.35 for labels
    need = lines * (pt / 72.0) * 1.35
    content = lab.top / EMU + max(need, pt / 72.0 * 1.35)
    shape_b = (lab.top + lab.height) / EMU
    # Tall empty one-line label boxes (slide 8): keep content estimate (not shape bottom).
    # Multi-line labels fill their box — body must clear shape bottom.
    if lines >= 2:
        return max(content, shape_b)
    return content


def fill_slide10(slide) -> list[str]:
    done = []
    if fill_title_placeholder(slide):
        done.append("title")
    vt = scrub_vertical_tabs(slide)
    if vt:
        done.append(f"scrub_vt={vt}")

    # Paint other labels first; then force Geoscan two-line splits (paint would flatten them)
    done.extend(paint_section_labels(slide))
    for sh in list(iter_shapes(slide.shapes)):
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        for prefix, lines in S10_LABEL_LINES.items():
            if t.startswith(prefix):
                _set_twoline_label(sh, lines[0], lines[1])
                # Geoscan label box heights for wrapped titles
                if prefix == "Почему вы":
                    place_box(sh, 0.58, 3.17, 6.16, 0.58)
                elif prefix == "С какими":
                    place_box(sh, 0.58, 5.00, 7.04, 0.69)
                done.append(f"label2:{prefix}")
                break

    lab_h = find_text(slide, lambda t: t.startswith("Краткая история"))
    lab_i = find_text(slide, lambda t: t.startswith("Почему вы"))
    lab_x = find_text(slide, lambda t: t.startswith("С какими"))
    # Ensure history label is one line wide enough / short enough
    if lab_h:
        place_box(lab_h, 0.58, 1.40, 5.50, 0.39)  # wider than Geoscan 3.27 → no wrap
        set_text(lab_h, "Краткая история команды:", force_pt=PT_LABEL, rgb=LABEL_RGB, bold=True)

    # Place bodies BELOW label content (+0.08"), capped by next label top — no content overlap
    CONTENT_GAP = 0.08
    bodies = (
        (
            lambda t: t.startswith("Расскажите, как")
            or t.startswith("Собрались")
            or "альянс» собрался" in t
            or t.startswith("«Нанотехнологический"),
            HISTORY,
            lab_h,
            (lab_i.top / EMU) if lab_i else 3.05,
            7.60,  # was 4.84 — right third was empty desert
            "history",
        ),
        (
            lambda t: t.startswith("Что вас вдохновило")
            or t.startswith("Сначала навыки")
            or t.startswith("Нужно связать")
            or "Вилка" in t,
            INSPIRED,
            lab_i,
            (lab_x.top / EMU) if lab_x else 4.90,
            7.60,  # was 5.41 — fill to numbers column
            "inspired",
        ),
        (
            lambda t: t.startswith("Расскажите о самых")
            or "агрегатор" in t
            or t.startswith("Главный вызов")
            or t.startswith("В титуле"),
            HARDSHIPS,
            lab_x,
            6.85,
            8.20,
            "hardships",
        ),
    )
    for pred, text, lab, barrier_top, width_in, tag in bodies:
        sh = find_text(slide, pred)
        if not sh or not lab:
            continue
        top = _label_content_bottom_in(lab) + CONTENT_GAP
        height = max(0.55, barrier_top - top - CONTENT_GAP)
        # Fit copy into band: if estimate overflows, cut sentences until it fits
        fitted = text
        char_w = 0.52 * PT_BODY / 72.0
        cpl = max(8, int(width_in / char_w))
        while fitted:
            lines = 0
            for para in fitted.split("\n"):
                if not para.strip():
                    continue
                lines += max(1, (len(para) + cpl - 1) // cpl)
            need = lines * (PT_BODY / 72.0) * 1.15
            if need <= height + 1e-6:
                break
            # drop last sentence
            parts = fitted.replace("\n", " ").split(". ")
            if len(parts) <= 1:
                fitted = fitted[: max(40, int(len(fitted) * 0.75))].rstrip(" .,;:") + "."
                break
            fitted = ". ".join(parts[:-1]).rstrip(".") + "."
        place_box(sh, 0.58, top, width_in, height)
        set_text(sh, fitted, force_pt=PT_BODY)
        done.append(f"{tag}@y={top:.2f}h={height:.2f}")

    return done


def fill_slide11(slide) -> list[str]:
    done = []
    tech = find_text(
        slide,
        lambda t: "техническая составляющая" in t.lower()
        or t.startswith("Стек.")
        or "React" in t
        or (t.startswith("Опишите") and "техн" in t.lower()),
    )
    people = find_text(
        slide,
        lambda t: "дальнейшему применению" in t.lower()
        or t.startswith("Путь.")
        or t.startswith("Тест →")
        or "доказательства" in t
        or "Безопасность прежде" in t,
    )
    if tech:
        place_box(tech, *BOX["s11_tech"])
        set_tech_people(tech, TECH, fill_height=True)
        done.append("tech")
    if people:
        place_box(people, *BOX["s11_people"])
        set_tech_people(people, PEOPLE, fill_height=True)
        done.append("people")
    # Hug the two white cards to body bottoms — stock 5.46″ left half-empty columns
    cards = sorted(
        [
            sh
            for sh in slide.shapes
            if "Скругленный прямоугольник" in (getattr(sh, "name", "") or "")
            and sh.width > 4.0 * EMU
            and sh.height > 3.0 * EMU
        ],
        key=lambda s: s.left,
    )
    bodies = [b for b in (tech, people) if b is not None]
    for card, body in zip(cards[:2], bodies):
        card.height = (body.top + body.height + i2e(0.22)) - card.top
        done.append(f"card_hug={card.height/EMU:.2f}")
    done.extend(paint_section_labels(slide))
    return done


def patch_team_title_in_layouts(pptx_path: Path) -> int:
    import zipfile

    tmp = pptx_path.with_suffix(".pptx.tmp")
    n = 0
    with zipfile.ZipFile(pptx_path, "r") as zin, zipfile.ZipFile(
        tmp, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            if info.filename.startswith("ppt/slideLayouts/") and info.filename.endswith(".xml"):
                text = raw.decode("utf-8")
                for old, new in LAYOUT_TITLE_REPLACEMENTS:
                    c = text.count(old)
                    if c:
                        text = text.replace(old, new)
                        n += c
                raw = text.encode("utf-8")
            zout.writestr(info, raw)
    tmp.replace(pptx_path)
    return n


def _strip_shape_line(shape) -> None:
    """Remove stroke — thin scheme lines read as a dashed frame on capture."""
    from pptx.oxml.ns import qn

    spPr = shape._element.spPr
    if spPr is None:
        return
    ln = spPr.find(qn("a:ln"))
    if ln is not None:
        spPr.remove(ln)


def fill_slide7(slide) -> list[str]:
    """Title slide: real «НТ АЛЬЯНС» in placeholder (layout ghost + border looked like a dashed box)."""
    done = []
    # Remove off-slide decorative frame entirely (stroke read as dashed box around team name)
    for sh in list(slide.shapes):
        name = getattr(sh, "name", "") or ""
        if "Скругленный прямоугольник" in name and sh.top < i2e(0.5):
            sh._element.getparent().remove(sh._element)
            done.append(f"removed:{name}")
            continue
        _strip_shape_line(sh)
    # Prefer named title placeholder
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        name = getattr(sh, "name", "") or ""
        if "Заголовок" in name:
            place_box(sh, 0.35, 4.10, 6.40, 0.95)
            set_text(sh, TEAM_NAME_SHORT, force_pt=PT_PANEL, rgb=TITLE_RGB, bold=True)
            _strip_shape_line(sh)
            done.append("title:НТ АЛЬЯНС")
            break
    body = None
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        name = getattr(sh, "name", "") or ""
        if name.startswith("Текст"):
            body = sh
            break
    if body is None:
        body = find_text(
            slide,
            lambda t: "платформа" in t.lower() or "агрегатор" in t.lower() or "верифицир" in t.lower(),
        )
    if body:
        # No U+000B soft-breaks — gate forbids VT
        copy = (
            "Цифровая платформа-агрегатор ИТ-вакансий\n"
            "с верифицированным профилем достижений\n"
            "участника Федерации спортивного программирования (ФСП)"
        )
        place_box(body, 0.35, 5.15, 9.40, 1.10)
        set_text(body, copy, force_pt=PT_BODY, rgb=TITLE_RGB)
        done.append("body")
    return done


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    prs = Presentation(str(SRC))
    s7, s8, s9, s10, s11 = (prs.slides[i] for i in range(6, 11))
    r7 = fill_slide7(s7)
    r8 = fill_slide8(s8)
    r9 = fill_slide9(s9)
    r10 = fill_slide10(s10)
    r11 = fill_slide11(s11)
    prs.save(str(OUT))
    n_title = patch_team_title_in_layouts(OUT)
    print(f"saved {OUT}")
    print(f"  layout title patches: {n_title}")
    print(f"  Geoscan ramp: title={PT_TITLE} label={PT_LABEL} body={PT_BODY} name={PT_NAME} role={PT_ROLE}")
    print(f"  7:{r7}")
    print(f"  8:{r8}")
    print(f"  9:{r9}")
    print(f" 10:{r10}")
    print(f" 11:{r11}")


if __name__ == "__main__":
    main()
