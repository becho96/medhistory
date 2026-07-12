"""Body-text builders for demo documents.

Each builder returns the full plain-text content of one document (Russian),
including a compact metadata header so the AI extractor gets
facility/date/patient/doctor even from a handwritten image. The file
generators add visual styling (letterhead / handwriting) on top of this text.

Kept deliberately close to how real Russian clinic paperwork reads so that
the production Gemini pipeline classifies type, extracts lab tables and
picks up doctor referrals as `orders`.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def _meta(clinic: str, doc_date: str, patient: str, doctor: Optional[str],
          extra: Optional[Sequence[tuple[str, str]]] = None) -> list[str]:
    lines = [
        clinic,
        "",
        f"Дата: {fmt_date(doc_date)}",
        f"Пациент: {patient}",
    ]
    if doctor:
        lines.append(f"Врач: {doctor}")
    for key, value in extra or []:
        lines.append(f"{key}: {value}")
    return lines


def appointment(*, clinic: str, doc_date: str, patient: str, doctor: str,
                specialty_label: str, complaint: str, anamnesis: str,
                exam: str, diagnosis: str, icd: Optional[str] = None,
                treatment: Optional[Iterable[str]] = None,
                referrals: Optional[Iterable[str]] = None) -> tuple[str, str]:
    """Return (title, body) for a doctor's appointment / conclusion."""
    title = f"Приём — {specialty_label}"
    lines = _meta(clinic, doc_date, patient, doctor,
                  extra=[("Специальность", specialty_label)])
    lines += [
        "",
        f"КОНСУЛЬТАЦИЯ: {specialty_label}",
        "",
        f"Жалобы: {complaint}",
        f"Анамнез: {anamnesis}",
        f"Объективно: {exam}",
        "",
        f"Диагноз: {diagnosis}" + (f" (МКБ-10: {icd})" if icd else ""),
    ]
    if treatment:
        lines += ["", "Назначено лечение:"]
        lines += [f"— {item}" for item in treatment]
    if referrals:
        lines += ["", "Рекомендовано (направления):"]
        lines += [f"— {item}" for item in referrals]
    lines += ["", f"Подпись врача: {doctor}"]
    return title, "\n".join(lines)


def lab(*, clinic: str, doc_date: str, patient: str, doctor: Optional[str],
        panel: str, rows: Sequence[tuple[str, str, str, str]],
        conclusion: Optional[str] = None) -> tuple[str, str, list]:
    """Return (title, body, rows) for a lab result.

    rows: sequence of (test_name, value, unit, reference_range). The structured
    rows are returned as-is so the seed driver can inject deterministic
    `lab_results` into MongoDB (independent of AI re-reading).
    """
    title = f"Анализ — {panel}"
    lines = _meta(clinic, doc_date, patient, doctor,
                  extra=[("Исследование", panel)])
    lines += ["", f"РЕЗУЛЬТАТЫ: {panel}", ""]
    lines.append(f"{'Показатель':<34}{'Результат':<14}{'Ед.':<10}Референс")
    lines.append("-" * 78)
    for name, value, unit, ref in rows:
        lines.append(f"{name:<34}{value:<14}{unit:<10}{ref}")
    if conclusion:
        lines += ["", f"Заключение: {conclusion}"]
    return title, "\n".join(lines), [list(r) for r in rows]


def imaging(*, clinic: str, doc_date: str, patient: str, doctor: str,
            modality: str, area: str, protocol: str,
            conclusion: str, referrals: Optional[Iterable[str]] = None
            ) -> tuple[str, str]:
    """Return (title, body) for an instrumental study (УЗИ/МРТ/КТ/Рентген)."""
    title = f"{modality} — {area}"
    lines = _meta(clinic, doc_date, patient, doctor,
                  extra=[("Исследование", f"{modality} ({area})")])
    lines += [
        "",
        f"ПРОТОКОЛ ИССЛЕДОВАНИЯ: {modality}, {area}",
        "",
        protocol,
        "",
        f"Заключение: {conclusion}",
    ]
    if referrals:
        lines += ["", "Рекомендовано:"]
        lines += [f"— {item}" for item in referrals]
    lines += ["", f"Врач: {doctor}"]
    return title, "\n".join(lines)


def functional(*, clinic: str, doc_date: str, patient: str, doctor: str,
               study: str, protocol: str, conclusion: str) -> tuple[str, str]:
    """Return (title, body) for functional diagnostics (ЭКГ/ФГДС/спирометрия…)."""
    title = study
    lines = _meta(clinic, doc_date, patient, doctor,
                  extra=[("Исследование", study)])
    lines += [
        "",
        f"ПРОТОКОЛ: {study}",
        "",
        protocol,
        "",
        f"Заключение: {conclusion}",
        "",
        f"Врач функциональной диагностики: {doctor}",
    ]
    return title, "\n".join(lines)


def certificate(*, clinic: str, doc_date: str, patient: str,
                doctor: Optional[str], kind: str, text: str) -> tuple[str, str]:
    """Return (title, body) for a misc document (справка/сертификат/эпикриз)."""
    title = kind
    lines = _meta(clinic, doc_date, patient, doctor)
    lines += ["", kind.upper(), "", text]
    if doctor:
        lines += ["", f"Врач: {doctor}"]
    return title, "\n".join(lines)
