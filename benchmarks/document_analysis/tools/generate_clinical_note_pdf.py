"""Рендерит нарративную клиническую заметку (например, из MedSyn) в PDF.

Имитирует визуально приём врача: шапка с лабораторией/клиникой, ФИО пациента,
дата, тело заметки, подпись врача. Все данные — синтетические, передаются
аргументами командной строки.

Запуск:
    python tools/generate_clinical_note_pdf.py \\
        --text /tmp/note.txt \\
        --out /tmp/doc_002.pdf \\
        --facility "ГБУЗ Поликлиника №5" \\
        --patient "Кузнецов К.К." \\
        --date "12.03.2026" \\
        --doctor "Соколова М.Н." \\
        --specialty "Неврология"
"""

import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _register_cyrillic_font() -> str:
    candidates = [
        ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"),
        ("DejaVuSans", "/Library/Fonts/DejaVuSans.ttf"),
        ("HelveticaNeue", "/System/Library/Fonts/HelveticaNeue.ttc"),
    ]
    for name, path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return "Helvetica"


def build(args: argparse.Namespace) -> None:
    font = _register_cyrillic_font()
    text = Path(args.text).read_text(encoding="utf-8").strip()

    doc = SimpleDocTemplate(
        args.out, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    base = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=base["Title"], fontName=font, fontSize=13, spaceAfter=6)
    h = ParagraphStyle("h", parent=base["Normal"], fontName=font, fontSize=11, spaceAfter=4)
    body = ParagraphStyle("b", parent=base["Normal"], fontName=font, fontSize=10, leading=14, spaceAfter=6)

    elems = [
        Paragraph(args.facility, title),
        Paragraph(f"Врач: {args.doctor} ({args.specialty})", h),
        Paragraph(f"Пациент: {args.patient}", h),
        Paragraph(f"Дата приёма: {args.date}", h),
        Spacer(1, 10),
        Paragraph("<b>Запись приёма врача</b>", h),
        Spacer(1, 4),
    ]
    for para in text.split("\n\n"):
        para = para.strip()
        if para:
            elems.append(Paragraph(para, body))
    elems.append(Spacer(1, 14))
    elems.append(Paragraph(f"Подпись врача: {args.doctor}", body))

    doc.build(elems)
    print(f"✅ {args.out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True, help="Файл с телом заметки (UTF-8)")
    p.add_argument("--out", required=True, help="Куда положить PDF")
    p.add_argument("--facility", default="ГБУЗ Поликлиника №5")
    p.add_argument("--patient", default="Кузнецов К.К.")
    p.add_argument("--date", default="14.05.2026")
    p.add_argument("--doctor", default="Соколова М.Н.")
    p.add_argument("--specialty", default="Терапия")
    build(p.parse_args())


if __name__ == "__main__":
    main()
