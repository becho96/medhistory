"""Pydantic-схемы бенчмарка первичного анализа документов."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class DocFormat(str, Enum):
    pdf_text = "pdf_text"
    pdf_scan = "pdf_scan"
    image_lab_printed = "image_lab_printed"
    photo_handwritten = "photo_handwritten"
    photo_printed = "photo_printed"
    docx = "docx"
    other = "other"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class FlagValue(str, Enum):
    L = "L"
    N = "N"
    H = "H"
    A = "A"


class DocumentTags(BaseModel):
    document_type: str
    format: DocFormat
    specialty: Optional[str] = None
    difficulty: Difficulty = Difficulty.medium


class LabResult(BaseModel):
    """Зеркало того, что pipeline возвращает в `extracted_data.lab_results`."""

    test_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: Optional[FlagValue] = None


class LabResultGT(LabResult):
    """Расширение для ground truth: канонизированное имя и алиасы для матчинга."""

    analyte_canonical: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)


class DocMetadata(BaseModel):
    """Метаданные документа — отражают то, что extraction pipeline возвращает.

    `document_date` — строка в ISO 8601 (YYYY-MM-DD), как сейчас сохраняется
    в PostgreSQL.
    """

    document_type: str
    document_subtype: Optional[str] = None
    research_area: Optional[str] = None
    specialties: list[str] = Field(default_factory=list)
    document_date: Optional[str] = None
    patient_name: Optional[str] = None
    medical_facility: Optional[str] = None
    document_language: Optional[str] = None
    confidence: Optional[float] = None


class GroundTruth(BaseModel):
    doc_id: str
    source_file: str
    source_sha256: str
    tags: DocumentTags
    metadata: DocMetadata
    summary_reference: str
    summary_key_facts: list[str] = Field(default_factory=list)
    lab_results: list[LabResultGT] = Field(default_factory=list)
    notes: Optional[str] = None


class Prediction(BaseModel):
    """Результат одного прогона extraction-pipeline на одном документе."""

    doc_id: str
    metadata: Optional[DocMetadata] = None
    summary: Optional[str] = None
    lab_results: list[LabResult] = Field(default_factory=list)
    raw_response: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ExtractionModelConfig(BaseModel):
    id: str
    openrouter_slug: str
    temperature: float = 0.1
    notes: Optional[str] = None


class JudgeConfig(BaseModel):
    id: str
    openrouter_slug: str
    temperature: float = 0.0
    notes: Optional[str] = None


class ModelsRegistry(BaseModel):
    extraction_models: list[ExtractionModelConfig]
    judge: JudgeConfig

    def find_extraction_model(self, model_id: str) -> ExtractionModelConfig:
        for m in self.extraction_models:
            if m.id == model_id:
                return m
        raise ValueError(
            f"Модель '{model_id}' не найдена в models.yaml. "
            f"Доступные: {[m.id for m in self.extraction_models]}"
        )


class DatasetDocumentEntry(BaseModel):
    id: str
    file: str
    sha256: str
    format: DocFormat
    tags: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class DatasetManifest(BaseModel):
    version: int
    created_at: str
    status: str = "in_progress"
    description: str
    changes_from_previous: str
    categories: dict[str, dict[str, Any]] = Field(default_factory=dict)
    documents: list[DatasetDocumentEntry] = Field(default_factory=list)


class RunMeta(BaseModel):
    """Метаданные одного прогона. Сохраняется в runs/<...>/run_meta.json."""

    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    dataset_version: int
    model: ExtractionModelConfig
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    git_commit: Optional[str] = None
    total_documents: int = 0
    successful: int = 0
    failed: int = 0


def load_models_registry(path: Path) -> ModelsRegistry:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ModelsRegistry.model_validate(data)


def load_manifest(path: Path) -> DatasetManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DatasetManifest.model_validate(data)


def load_ground_truth(path: Path) -> GroundTruth:
    return GroundTruth.model_validate_json(path.read_text(encoding="utf-8"))


def dump_json(obj: BaseModel, path: Path) -> None:
    path.write_text(
        json.dumps(obj.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
