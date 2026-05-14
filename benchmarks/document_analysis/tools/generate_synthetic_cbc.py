"""Сгенерировать синтетический PDF общего анализа крови.

Запуск:
    cd benchmarks/document_analysis
    source venv/bin/activate
    pip install reportlab  # если ещё не установлен
    python tools/generate_synthetic_cbc.py /tmp/synth_cbc.pdf
"""

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib import colors


def _register_cyrillic_font() -> str:
    """Найти системный TTF с кириллицей. На macOS это обычно ArialUnicode."""
    candidates = [
        ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"),
        ("DejaVuSans", "/Library/Fonts/DejaVuSans.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("HelveticaNeue", "/System/Library/Fonts/HelveticaNeue.ttc"),
    ]
    for name, path in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    # Fallback — встроенный, кириллицу может не отрисовать корректно.
    return "Helvetica"


def build_pdf(out_path: Path) -> None:
    font = _register_cyrillic_font()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontName=font, fontSize=14, spaceAfter=8)
    header_style = ParagraphStyle("header", parent=styles["Normal"], fontName=font, fontSize=11, spaceAfter=4)
    body_style = ParagraphStyle("body", parent=styles["Normal"], fontName=font, fontSize=10, spaceAfter=4)

    elems = [
        Paragraph("ООО «ЛабТест»", title_style),
        Paragraph("Лаборатория клинической диагностики", body_style),
        Paragraph("г. Москва, ул. Примерная, д. 1", body_style),
        Spacer(1, 8),
        Paragraph("<b>ОБЩИЙ АНАЛИЗ КРОВИ</b>", title_style),
        Paragraph("Пациент: Петров П.П.", header_style),
        Paragraph("Дата взятия материала: 14.05.2026", header_style),
        Paragraph("Возраст: 35 лет, пол: мужской", header_style),
        Spacer(1, 8),
    ]

    data = [
        ["Показатель",    "Значение", "Ед. изм.", "Норма"],
        ["Гемоглобин",    "145",      "г/л",      "130-160"],
        ["Эритроциты",    "4.8",      "10^12/л",  "4.0-5.5"],
        ["Гематокрит",    "42",       "%",        "39-49"],
        ["Лейкоциты",     "6.2",      "10^9/л",   "4.0-9.0"],
        ["Тромбоциты",    "250",      "10^9/л",   "180-320"],
        ["СОЭ",           "8",        "мм/ч",     "2-15"],
    ]
    tbl = Table(data, colWidths=[60 * mm, 30 * mm, 30 * mm, 35 * mm])
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), font, 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), font, 10, ),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elems.append(tbl)
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("<b>Заключение:</b> все показатели в пределах референсных значений.", body_style))
    elems.append(Spacer(1, 16))
    elems.append(Paragraph("Врач лабораторной диагностики: Иванова А.А.", body_style))

    doc.build(elems)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synth_cbc.pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(target)
    print(f"✅ {target}")
