"""Render manifest entries into real files (text-layer PDF / handwritten JPG).

PDFs get a text layer (extractable by PyPDF2), monospace body so lab tables
stay aligned, and a per-clinic letterhead font for visual variety. Handwritten
entries are rasterised to JPG with a Cyrillic handwriting font on a paper-like
background, so they go through the Gemini vision transcription path.

Run:  python -m scripts.demo_seed.generate_files
Output: backend/scripts/demo_seed/out/<slug>_<date>.<ext>  (+ index.json)
"""
from __future__ import annotations

import json
import os
import random
import re
import textwrap
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

from .manifest import build_manifest  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONTS = os.path.join(HERE, "fonts")
SYS = "/System/Library/Fonts/Supplemental"

# --- font registration (PDF) -------------------------------------------------
_PDF_FONTS = {
    "mono": os.path.join(SYS, "Courier New.ttf"),
    "arial": os.path.join(SYS, "Arial.ttf"),
    "arialB": os.path.join(SYS, "Arial Bold.ttf"),
    "georgiaB": os.path.join(SYS, "Georgia Bold.ttf"),
    "timesB": os.path.join(SYS, "Times New Roman Bold.ttf"),
}
for _name, _path in _PDF_FONTS.items():
    pdfmetrics.registerFont(TTFont(_name, _path))

# per-clinic letterhead theme: (heading font, RGB accent)
_CLINIC_THEME = {
    "СМ-Клиника": ("arialB", (0, 90, 160)),
    "Медси": ("georgiaB", (200, 30, 60)),
    "Клиника К+31": ("timesB", (30, 40, 60)),
    "Городская поликлиника № 180": ("arialB", (40, 110, 60)),
    "Лаборатория ИНВИТРО": ("arialB", (150, 30, 90)),
    "Лаборатория Гемотест": ("arialB", (210, 70, 20)),
    "Лаборатория Хеликс": ("georgiaB", (0, 120, 130)),
    "Центр диагностики МРТ-Эксперт": ("timesB", (20, 60, 120)),
    "Детская клиника «Фэнтези»": ("arialB", (230, 120, 20)),
}
_DEFAULT_THEME = ("arialB", (40, 40, 40))

# --- fonts for handwriting (image) ------------------------------------------
_HAND_FONT = os.path.join(FONTS, "MarckScript-Regular.ttf")
_HAND_FONT2 = os.path.join(FONTS, "BadScript-Regular.ttf")
_PRINT_FONT = os.path.join(SYS, "Arial Bold.ttf")


def _slug(text: str) -> str:
    text = text.replace(" ", "_")
    text = re.sub(r"[^0-9A-Za-zА-Яа-яЁё_\-]", "", text)
    return text[:60].strip("_")


def _wrap_line(line: str, width: int) -> list[str]:
    # Preserve preformatted (table) lines: those with runs of 2+ spaces.
    if "  " in line.strip() or set(line) <= set(" -"):
        return [line]
    if len(line) <= width:
        return [line]
    return textwrap.wrap(line, width=width, break_long_words=False,
                         break_on_hyphens=False) or [""]


# =============================================================================
# PDF
# =============================================================================
def render_pdf(doc: dict[str, Any], path: str) -> None:
    width, height = A4
    c = canvas.Canvas(path, pagesize=A4)
    margin = 48
    heading_font, accent = _CLINIC_THEME.get(doc["clinic"], _DEFAULT_THEME)

    body_size, leading = 8.6, 11.4
    max_chars = 94
    x = margin

    def draw_letterhead(y: float) -> float:
        c.setFillColorRGB(*[v / 255 for v in accent])
        c.setFont(heading_font, 15)
        c.drawString(x, y, doc["clinic"])
        y -= 16
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.setFont("arial", 7.5)
        c.drawString(x, y, "г. Москва  ·  Медицинский центр  ·  Лицензия № ЛО-77-01-0" +
                     str(10000 + hash(doc["clinic"]) % 8999))
        y -= 8
        c.setStrokeColorRGB(*[v / 255 for v in accent])
        c.setLineWidth(1.2)
        c.line(x, y, width - margin, y)
        c.setFillColorRGB(0, 0, 0)
        return y - 18

    def draw_footer() -> None:
        c.setFillColorRGB(0.55, 0.55, 0.55)
        c.setFont("arial", 6.8)
        c.drawString(x, 26, "Электронный медицинский документ. Сформирован информационной системой клиники.")

    y = draw_letterhead(height - margin)
    c.setFont("mono", body_size)
    c.setFillColorRGB(0.05, 0.05, 0.05)

    # skip the first body line (clinic) — already in the letterhead
    body_lines = doc["body"].split("\n")
    if body_lines and body_lines[0].strip() == doc["clinic"].strip():
        body_lines = body_lines[1:]

    for raw in body_lines:
        for line in _wrap_line(raw, max_chars):
            if y < 48:
                draw_footer()
                c.showPage()
                y = draw_letterhead(height - margin)
                c.setFont("mono", body_size)
                c.setFillColorRGB(0.05, 0.05, 0.05)
            c.drawString(x, y, line)
            y -= leading
    draw_footer()
    c.showPage()
    c.save()


# =============================================================================
# Handwriting image
# =============================================================================
def _paper_background(w: int, h: int, rnd: random.Random) -> Image.Image:
    base = (252, 250, 244)
    img = Image.new("RGB", (w, h), base)
    px = img.load()
    # subtle paper noise
    for _ in range(int(w * h * 0.015)):
        xx = rnd.randint(0, w - 1)
        yy = rnd.randint(0, h - 1)
        d = rnd.randint(-6, 4)
        r, g, b = px[xx, yy]
        px[xx, yy] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return img


def render_image(doc: dict[str, Any], path: str) -> None:
    rnd = random.Random(doc["code"])
    W, H = 1000, 1414
    img = _paper_background(W, H, rnd)
    draw = ImageDraw.Draw(img)

    margin = 70
    # printed letterhead band (form filled by hand)
    head_font = ImageFont.truetype(_PRINT_FONT, 30)
    sub_font = ImageFont.truetype(_PRINT_FONT, 15)
    accent = _CLINIC_THEME.get(doc["clinic"], _DEFAULT_THEME)[1]
    draw.text((margin, 46), doc["clinic"], font=head_font, fill=accent)
    draw.text((margin, 84), "г. Москва   ·   амбулаторная карта", font=sub_font, fill=(110, 110, 110))
    draw.line((margin, 112, W - margin, 112), fill=accent, width=3)

    # faint ruled lines
    for yy in range(150, H - 60, 46):
        draw.line((margin, yy, W - margin, yy), fill=(225, 222, 210), width=1)

    ink = rnd.choice([(24, 32, 84), (20, 24, 40), (28, 40, 96)])
    hand = ImageFont.truetype(_HAND_FONT, 33)
    hand_alt = ImageFont.truetype(_HAND_FONT2, 33)
    max_w = W - 2 * margin

    def wrap(text: str) -> list[str]:
        words = text.split(" ")
        out, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if draw.textlength(trial, font=hand) <= max_w:
                cur = trial
            else:
                if cur:
                    out.append(cur)
                cur = wd
        if cur:
            out.append(cur)
        return out or [""]

    # skip clinic line (already printed)
    body_lines = doc["body"].split("\n")
    if body_lines and body_lines[0].strip() == doc["clinic"].strip():
        body_lines = body_lines[1:]

    y = 150
    line_h = 46
    for raw in body_lines:
        raw = raw.rstrip()
        if not raw:
            y += int(line_h * 0.5)
            continue
        for seg in wrap(raw):
            f = hand if rnd.random() > 0.25 else hand_alt
            jitter_x = rnd.randint(-3, 4)
            jitter_y = rnd.randint(-3, 3)
            draw.text((margin + jitter_x, y + jitter_y), seg, font=f, fill=ink)
            y += line_h
            if y > H - 80:
                break
        if y > H - 80:
            break

    # slight rotation to mimic a scan
    img = img.rotate(rnd.uniform(-1.2, 1.2), expand=False, fillcolor=(252, 250, 244))
    img.save(path, "JPEG", quality=82)


# =============================================================================
# driver
# =============================================================================
def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))

    manifest = build_manifest()
    index = []
    seen: set[str] = set()
    for doc in manifest:
        ext = "jpg" if doc["format"] == "image" else "pdf"
        fname = f"{_slug(doc['title'])}_{doc['date']}.{ext}"
        if fname in seen:
            fname = f"{_slug(doc['title'])}_{doc['date']}_{doc['code']}.{ext}"
        seen.add(fname)
        path = os.path.join(OUT, fname)

        if doc["format"] == "image":
            render_image(doc, path)
        else:
            render_pdf(doc, path)

        entry = {k: doc[k] for k in (
            "code", "profile", "date", "document_type", "document_subtype",
            "research_area", "specialties", "clinic", "doctor", "title",
            "body", "format", "handwritten", "orders", "lab_rows")}
        entry["filename"] = fname
        index.append(entry)

    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)

    n_pdf = sum(1 for d in manifest if d["format"] == "pdf")
    n_img = sum(1 for d in manifest if d["format"] == "image")
    print(f"Generated {len(manifest)} files -> {OUT}")
    print(f"  PDF: {n_pdf} | JPG(handwritten): {n_img}")
    print(f"  index.json written ({len(index)} entries)")


if __name__ == "__main__":
    main()
