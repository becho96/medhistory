"""Render backend API payloads into Telegram-ready HTML text."""
import html

TG_MESSAGE_LIMIT = 3900  # safe margin under Telegram's 4096-char limit

FLAG_EMOJI = {"N": "✅", "H": "🔺", "L": "🔻", "A": "⚠️"}
STATUS_LABEL = {
    "pending": "⏳ в очереди",
    "processing": "⏳ обрабатывается",
    "completed": "✅ обработан",
    "failed": "❌ ошибка обработки",
}


def esc(value) -> str:
    """HTML-escape a value for safe insertion into an HTML-parsed message."""
    return html.escape(str(value)) if value not in (None, "") else ""


def clip(text: str, limit: int = TG_MESSAGE_LIMIT) -> str:
    """Trim text to Telegram's message length budget."""
    return text if len(text) <= limit else text[:limit] + "…"


def _short_date(value) -> str:
    return str(value)[:10] if value else ""


def document_label(doc: dict) -> str:
    """Short one-line label for a document list button."""
    date = _short_date(doc.get("document_date") or doc.get("created_at"))
    dtype = doc.get("document_type") or "Документ"
    label = f"{date} · {dtype}" if date else dtype
    return label[:62]


def document_card(doc: dict) -> str:
    """Full document view: metadata plus AI summary."""
    title = doc.get("document_type") or doc.get("original_filename") or "Документ"
    lines = [f"📄 <b>{esc(title)}</b>"]
    if doc.get("document_subtype"):
        lines.append(esc(doc["document_subtype"]))
    if doc.get("document_date"):
        lines.append(f"📅 Дата: {esc(_short_date(doc['document_date']))}")
    if doc.get("medical_facility"):
        lines.append(f"🏥 {esc(doc['medical_facility'])}")
    if doc.get("specialty"):
        lines.append(f"🩺 {esc(doc['specialty'])}")
    status = STATUS_LABEL.get(doc.get("processing_status"), doc.get("processing_status"))
    lines.append(f"Статус: {esc(status)}")
    if doc.get("summary"):
        lines.append(f"\n<b>Кратко:</b>\n{esc(doc['summary'])}")
    return clip("\n".join(lines))


def abnormal_section(lab_results: list) -> str:
    """List lab results flagged H/L/A. Empty string when nothing is flagged."""
    flagged = [r for r in lab_results if (r.get("flag") or "N").upper() in ("H", "L", "A")]
    if not flagged:
        return ""
    lines = ["", "⚠️ <b>Показатели вне нормы:</b>"]
    for r in flagged:
        flag = (r.get("flag") or "").upper()
        emoji = FLAG_EMOJI.get(flag, "•")
        ref = esc(r.get("reference_range"))
        ref_part = f" (норма: {ref})" if ref else ""
        lines.append(
            f"{emoji} {esc(r.get('test_name'))}: "
            f"<b>{esc(r.get('value'))} {esc(r.get('unit'))}</b>{ref_part}"
        )
    return clip("\n".join(lines))


def timeseries_text(data: dict) -> str:
    """Render an analyte time series as a textual trend."""
    unit = esc(data.get("standard_unit") or "")
    header = f"📊 <b>{esc(data.get('analyte'))}</b>" + (f" ({unit})" if unit else "")
    lines = [header]
    ref_min, ref_max = data.get("reference_min"), data.get("reference_max")
    if ref_min is not None and ref_max is not None:
        lines.append(f"Норма: {esc(ref_min)}–{esc(ref_max)}")

    points = data.get("points") or []
    if not points:
        lines.append("\nПо этому показателю пока нет данных.")
        return "\n".join(lines)

    lines.append("")
    shown = points[-15:]
    for p in shown:
        emoji = FLAG_EMOJI.get((p.get("flag") or "").upper(), "▫️")
        date = esc(_short_date(p.get("date")) or "—")
        lines.append(f"{emoji} {date}: <b>{esc(p.get('value_num'))}</b>")
    if len(points) > len(shown):
        lines.append(f"\n…показаны последние {len(shown)} из {len(points)} измерений.")
    return clip("\n".join(lines))


def subscription_text(sub: dict) -> str:
    """Render the user's subscription status."""
    tier = sub.get("tier", "free")
    if tier == "pro":
        lines = ["⭐ <b>Тариф: Pro</b>"]
        if sub.get("pro_expires_at"):
            lines.append(f"Действует до: {esc(_short_date(sub['pro_expires_at']))}")
    else:
        lines = ["🆓 <b>Тариф: Free</b>"]

    limit = sub.get("limit")
    if limit is not None:
        lines.append(
            f"Загрузки документов: {esc(sub.get('used'))}/{esc(limit)} "
            f"(осталось {esc(sub.get('remaining'))})"
        )
    if tier != "pro":
        lines.append(
            "\n<b>Pro</b> снимает лимит на документы, открывает семейные "
            "профили и расширенную аналитику."
        )
    return "\n".join(lines)
