"""Метрика для lab_results.

Алгоритм:
  1. Канонизируем имена в pred и в gt через SynonymsIndex (учитывается unit).
     Если для GT задан analyte_canonical вручную — используем его, иначе
     канонизируем `test_name`. Алиасы из GT добавляются в матчинг-индекс GT.
  2. На set-уровне канонических имён считаем matched / FP / FN.
  3. Для matched пар оцениваем value/unit/flag.

Value-сравнение: numeric tolerance 5%, иначе string match. Точные дробные
значения важны в медицине, но 5% покрывает округления (например, 4.5 vs 4.51).
"""

from __future__ import annotations

import re
from typing import Optional

from benchmarks.document_analysis.src.schema import LabResult, LabResultGT
from benchmarks.document_analysis.src.synonyms import SynonymsIndex

from .types import LabResultMatch, LabResultsScore

VALUE_TOLERANCE = 0.05


def _canonical_or_fallback(name: str, unit: Optional[str], idx: SynonymsIndex) -> str:
    c = idx.canonicalize(name, unit)
    if c:
        return c
    return (name or "").strip().lower()


def _numeric(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    m = re.search(r"-?\d+[.,]?\d*", str(v).replace(",", "."))
    if not m:
        return None
    try:
        return float(m.group().replace(",", "."))
    except ValueError:
        return None


def _values_match(pred: Optional[str], gt: Optional[str]) -> bool:
    if pred is None and gt is None:
        return True
    if pred is None or gt is None:
        return False
    p_num, g_num = _numeric(pred), _numeric(gt)
    if p_num is not None and g_num is not None:
        if g_num == 0:
            return abs(p_num) <= VALUE_TOLERANCE
        return abs(p_num - g_num) / abs(g_num) <= VALUE_TOLERANCE
    return str(pred).strip() == str(gt).strip()


_SUPERSCRIPT_TO_ASCII = str.maketrans({
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
})


def _normalize_unit(u: Optional[str]) -> str:
    """Канонизировать запись единицы.

    Цель: «×10⁹/л», «10^9/л», «10*9/л», «х10^9/л» — один и тот же unit.
    Алгоритм:
      1. lower + strip + удалить все пробелы
      2. Юникод-суперскрипты (⁰¹²³⁴⁵⁶⁷⁸⁹) → ASCII, разделитель степени `^`
      3. `*` между цифрами → `^` (10*9 → 10^9)
      4. Удалить умножающий префикс/связку `×`, латинскую `x`, русскую `х`
    """
    if not u:
        return ""
    s = u.strip().lower()
    s = re.sub(r"(?<=\d)([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: "^" + m.group(0).translate(_SUPERSCRIPT_TO_ASCII), s)
    s = re.sub(r"(\d)\*(\d)", r"\1^\2", s)
    s = re.sub(r"[×xх](?=\d)", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def _units_match(pred: Optional[str], gt: Optional[str]) -> bool:
    if not pred and not gt:
        return True
    if not pred or not gt:
        return False
    return _normalize_unit(pred) == _normalize_unit(gt)


def _flag_match(pred_flag, gt_flag) -> bool:
    p = pred_flag.value if pred_flag is not None else None
    g = gt_flag.value if gt_flag is not None else None
    return p == g


def score_lab_results(
    pred: list[LabResult],
    gt: list[LabResultGT],
    synonyms: SynonymsIndex,
) -> LabResultsScore:
    pred_by_canon: dict[str, LabResult] = {}
    for p in pred:
        c = _canonical_or_fallback(p.test_name, p.unit, synonyms)
        pred_by_canon.setdefault(c, p)

    gt_by_canon: dict[str, LabResultGT] = {}
    for g in gt:
        c = g.analyte_canonical or _canonical_or_fallback(g.test_name, g.unit, synonyms)
        gt_by_canon.setdefault(c, g)
        # Алиасы: чтобы prediction, использующий синоним, который не в нашей БД,
        # всё равно матчился — добавим алиасы в gt-индекс как доп. ключи.
        for alias in g.aliases:
            alias_canon = _canonical_or_fallback(alias, g.unit, synonyms)
            gt_by_canon.setdefault(alias_canon, g)

    matched = set(pred_by_canon) & set(gt_by_canon)

    details: list[LabResultMatch] = []
    n_value_ok = n_unit_ok = n_flag_ok = 0

    for canon in matched:
        p = pred_by_canon[canon]
        g = gt_by_canon[canon]
        vm = _values_match(p.value, g.value)
        um = _units_match(p.unit, g.unit)
        fm = _flag_match(p.flag, g.flag)
        details.append(LabResultMatch(
            canonical=canon, pred_name=p.test_name, gt_name=g.test_name,
            matched=True, value_match=vm, unit_match=um, flag_match=fm,
        ))
        n_value_ok += int(vm)
        n_unit_ok += int(um)
        n_flag_ok += int(fm)

    for canon in set(pred_by_canon) - matched:
        details.append(LabResultMatch(
            canonical=canon, pred_name=pred_by_canon[canon].test_name, matched=False,
        ))
    for canon in set(gt_by_canon) - matched:
        details.append(LabResultMatch(
            canonical=canon, gt_name=gt_by_canon[canon].test_name, matched=False,
        ))

    # Для счёта n_gt используем gt-список (а не индекс — он расширен алиасами).
    # Дубли по канонике в исходном gt-списке тоже схлопываем.
    distinct_gt = {g.analyte_canonical or _canonical_or_fallback(g.test_name, g.unit, synonyms) for g in gt}

    n_pred = len(pred_by_canon)
    n_gt = len(distinct_gt)
    m = len(matched & distinct_gt)  # совпадения только по основным каноникам gt

    precision = m / n_pred if n_pred else (1.0 if n_gt == 0 else 0.0)
    recall = m / n_gt if n_gt else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    matched_n = len(matched)
    return LabResultsScore(
        n_pred=n_pred, n_gt=n_gt, matched=m,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        value_accuracy=round(n_value_ok / matched_n, 4) if matched_n else 1.0,
        unit_accuracy=round(n_unit_ok / matched_n, 4) if matched_n else 1.0,
        flag_accuracy=round(n_flag_ok / matched_n, 4) if matched_n else 1.0,
        details=details,
    )
