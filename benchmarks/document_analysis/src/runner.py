"""Runner: запуск prod extraction-pipeline с подменой LLM.

`BenchmarkAIService` наследует `AIService` и переопределяет:
  * `self.model` — slug модели из `models.yaml`
  * `_call_openrouter()` — чтобы прокинуть temperature из конфига
    (в prod она захардкожена 0.1).

Всё остальное — промпты, парсинг ответа, обработка PDF/изображений —
наследуется как есть, чтобы бенчмарк меряет именно то, что в проде.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai_service import AIService

from .schema import DocMetadata, LabResult, Prediction


class BenchmarkAIService(AIService):
    def __init__(self, model_id: str, openrouter_slug: str, temperature: float = 0.1):
        super().__init__()
        self._benchmark_model_id = model_id
        self.model = openrouter_slug
        self._benchmark_temperature = temperature

    async def _call_openrouter(self, messages: list) -> dict:
        """Копия prod-метода с одним отличием: temperature из конфига бенчмарка.

        max_tokens берём из настроек (как в проде) — иначе крупные многостраничные
        отчёты обрезаются и бенчмарк перестаёт мерить реальное поведение.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.OPENROUTER_MAX_TOKENS,
            "temperature": self._benchmark_temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MedHistory-Benchmark",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()


def compute_prompt_versions(ai: AIService) -> dict[str, str]:
    """SHA-16 хеши текущих промптов prod-pipeline — для версионирования прогонов."""
    return {
        "metadata_prompt": _sha16(ai._build_extraction_prompt()),
        "lab_prompt": _sha16(ai._build_labs_extraction_prompt()),
    }


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def run_one_document(
    ai: BenchmarkAIService,
    doc_path: Path,
    doc_id: str,
) -> Prediction:
    """Прогон полного pipeline на одном документе. Никогда не кидает исключение.

    AIService.analyze_document() сам ловит ошибки и возвращает default-метадату
    с document_type="неизвестно" — это сигнал, что extraction провалился.
    Записываем эту строку в `Prediction.error`.

    Lab extraction вызываем только если документ классифицирован как
    "Результаты анализа" — так же, как prod document_service.
    """
    file_bytes = doc_path.read_bytes()
    file_ext = doc_path.suffix.lstrip(".").lower()

    metadata, _usage = await ai.analyze_document(file_bytes, file_ext, doc_path.name)

    error: str | None = None
    if metadata.document_type == "неизвестно":
        error = metadata.summary or "extraction failed"

    lab_results: list[LabResult] = []
    if metadata.document_type == "Результаты анализа":
        try:
            labs_data = await ai.extract_lab_results(file_bytes, file_ext, doc_path.name)
            lab_results = [
                LabResult.model_validate(_clean_lab_item(item))
                for item in labs_data.get("lab_results", [])
                if item.get("test_name") and item.get("value") is not None
            ]
        except Exception as e:
            error = f"{error} | lab_extraction_failed: {e}" if error else f"lab_extraction_failed: {e}"

    return Prediction(
        doc_id=doc_id,
        metadata=DocMetadata(
            document_type=metadata.document_type,
            document_subtype=metadata.document_subtype,
            research_area=metadata.research_area,
            specialties=metadata.specialties or [],
            document_date=metadata.document_date.isoformat() if metadata.document_date else None,
            patient_name=metadata.patient_name,
            medical_facility=metadata.medical_facility,
            document_language=metadata.document_language,
            confidence=metadata.confidence,
        ),
        summary=metadata.summary,
        lab_results=lab_results,
        error=error,
    )


def _clean_lab_item(item: dict[str, Any]) -> dict[str, Any]:
    """Привести значения к строкам — pydantic LabResult ожидает str."""
    return {
        "test_name": str(item.get("test_name", "")),
        "value": str(item.get("value", "")),
        "unit": item.get("unit"),
        "reference_range": item.get("reference_range"),
        "flag": item.get("flag"),
    }
