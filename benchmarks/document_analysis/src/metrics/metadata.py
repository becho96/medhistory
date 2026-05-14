"""Метрика для метаданных документа.

По полям:
  * document_type / document_subtype / research_area / document_language — exact
  * document_date — exact (ISO YYYY-MM-DD)
  * patient_name / medical_facility — fuzzy (SequenceMatcher) с порогом 0.85
  * specialties — set-based F1

Поля с пустым GT (`expected is None` для одиночных, пустой list для specialties)
пропускаются в overall — иначе бенчмарк наказывал бы за корректный пропуск.
"""

from __future__ import annotations

import difflib
import re
from typing import Optional

from benchmarks.document_analysis.src.schema import DocMetadata

from .types import MetadataFieldScore, MetadataScore

FIELD_WEIGHTS: dict[str, float] = {
    "document_type": 1.0,
    "document_subtype": 0.6,
    "research_area": 0.4,
    "specialties": 0.6,
    "document_date": 0.4,
    "patient_name": 0.4,
    "medical_facility": 0.4,
    "document_language": 0.2,
}

FUZZY_THRESHOLD = 0.85


def _normalize_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.,;]", "", s)
    return s


def _is_empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)


def _score_exact(pred: Optional[str], gt: Optional[str]) -> tuple[bool, float, bool]:
    """Возвращает (match, score, gt_is_empty)."""
    if _is_empty(gt):
        return (True, 1.0, True)
    if _is_empty(pred):
        return (False, 0.0, False)
    eq = pred == gt
    return (eq, 1.0 if eq else 0.0, False)


def _score_fuzzy(pred: Optional[str], gt: Optional[str]) -> tuple[bool, float, bool]:
    if _is_empty(gt):
        return (True, 1.0, True)
    if _is_empty(pred):
        return (False, 0.0, False)
    n_pred, n_gt = _normalize_text(pred), _normalize_text(gt)
    if n_pred == n_gt:
        return (True, 1.0, False)
    ratio = difflib.SequenceMatcher(None, n_pred, n_gt).ratio()
    return (ratio >= FUZZY_THRESHOLD, round(ratio, 4), False)


def _score_set_f1(pred: list[str], gt: list[str]) -> tuple[bool, float, bool]:
    if _is_empty(gt):
        return (True, 1.0, True)
    pred_set = {_normalize_text(s) for s in (pred or []) if s}
    gt_set = {_normalize_text(s) for s in (gt or []) if s}
    if not pred_set:
        return (False, 0.0, False)
    tp = len(pred_set & gt_set)
    if tp == 0:
        return (False, 0.0, False)
    precision = tp / len(pred_set)
    recall = tp / len(gt_set)
    f1 = 2 * precision * recall / (precision + recall)
    return (f1 == 1.0, round(f1, 4), False)


def score_metadata(pred: Optional[DocMetadata], gt: DocMetadata) -> MetadataScore:
    fields: list[MetadataFieldScore] = []

    if pred is None:
        for f in FIELD_WEIGHTS:
            expected = getattr(gt, f, None)
            expected_str = ", ".join(expected) if isinstance(expected, list) else expected
            fields.append(MetadataFieldScore(
                field=f, pred=None, expected=expected_str or None,
                match=False, score=0.0, method="missing",
            ))
        return MetadataScore(fields=fields, overall=0.0)

    # exact fields
    for field in ("document_type", "document_subtype", "research_area", "document_language", "document_date"):
        p = getattr(pred, field, None)
        g = getattr(gt, field, None)
        match, sc, _gt_empty = _score_exact(p, g)
        fields.append(MetadataFieldScore(
            field=field, pred=p, expected=g, match=match, score=sc, method="exact",
        ))

    # fuzzy fields
    for field in ("patient_name", "medical_facility"):
        p = getattr(pred, field, None)
        g = getattr(gt, field, None)
        match, sc, _gt_empty = _score_fuzzy(p, g)
        fields.append(MetadataFieldScore(
            field=field, pred=p, expected=g, match=match, score=sc, method="fuzzy",
        ))

    # specialties
    match, sc, _gt_empty = _score_set_f1(pred.specialties or [], gt.specialties or [])
    fields.append(MetadataFieldScore(
        field="specialties",
        pred=", ".join(pred.specialties or []) or None,
        expected=", ".join(gt.specialties or []) or None,
        match=match, score=sc, method="set_f1",
    ))

    # weighted overall — учитываем только поля, где GT непустой
    total_w = 0.0
    sum_w = 0.0
    for f in fields:
        gt_val = getattr(gt, f.field, None)
        if _is_empty(gt_val):
            continue
        w = FIELD_WEIGHTS.get(f.field, 0.0)
        total_w += w
        sum_w += w * f.score
    overall = round(sum_w / total_w, 4) if total_w > 0 else 0.0
    return MetadataScore(fields=fields, overall=overall)
