"""Pydantic-типы для оценок. Вынесены отдельно, чтобы не было циклических импортов
между metadata.py / lab_results.py / aggregate.py."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MetadataFieldScore(BaseModel):
    field: str
    pred: Optional[str] = None
    expected: Optional[str] = None
    match: bool
    score: float
    method: str  # "exact" | "fuzzy" | "set_f1" | "missing"


class MetadataScore(BaseModel):
    fields: list[MetadataFieldScore] = Field(default_factory=list)
    overall: float


class LabResultMatch(BaseModel):
    canonical: str
    pred_name: Optional[str] = None
    gt_name: Optional[str] = None
    matched: bool
    value_match: Optional[bool] = None
    unit_match: Optional[bool] = None
    flag_match: Optional[bool] = None


class LabResultsScore(BaseModel):
    n_pred: int
    n_gt: int
    matched: int
    precision: float
    recall: float
    f1: float
    value_accuracy: float
    unit_accuracy: float
    flag_accuracy: float
    details: list[LabResultMatch] = Field(default_factory=list)


class SummaryScore(BaseModel):
    """Оценка summary от LLM-as-judge.

    Все шкалы — целые 0..5 (как просит judge), normalized — 0..1.
    `per_fact_coverage` — соответствует порядку `gt.summary_key_facts`.
    """

    factuality: int  # факты в summary не противоречат эталону
    completeness: int  # доля ключевых фактов раскрыта
    hallucination_freedom: int  # нет выдумок
    per_fact_coverage: list[bool] = Field(default_factory=list)
    comment: Optional[str] = None
    normalized: float  # 0..1 — усреднённая по 3 шкалам
    judge_model: str
    from_cache: bool = False


class DocumentScore(BaseModel):
    doc_id: str
    metadata: MetadataScore
    lab_results: Optional[LabResultsScore] = None
    summary: Optional[SummaryScore] = None
    overall: float


class FormatBreakdown(BaseModel):
    format: str
    n_documents: int
    overall_mean: float


class RunAggregate(BaseModel):
    """Сводные метрики по всему прогону. Средние считаются только по тем
    документам, у которых соответствующая под-метрика присутствует."""

    n_documents: int
    n_successful: int  # без ошибок pipeline
    n_failed: int

    overall_mean: float
    metadata_mean: float
    lab_f1_mean: Optional[float] = None
    lab_value_acc_mean: Optional[float] = None
    lab_unit_acc_mean: Optional[float] = None
    lab_flag_acc_mean: Optional[float] = None
    summary_mean: Optional[float] = None

    by_format: list[FormatBreakdown] = Field(default_factory=list)
