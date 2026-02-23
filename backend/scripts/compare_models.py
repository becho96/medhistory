#!/usr/bin/env python3
"""
Сравнение моделей OpenRouter на одних и тех же медицинских документах.

Использует идентичные промпты и параметры из backend/app/services/ai_service.py.
API-ключ берётся из .env.local в корне проекта.

Запуск из корня проекта:
  python3 backend/scripts/compare_models.py

Опции:
  --models    Список моделей через запятую (по умолчанию: claude-3.5-sonnet, gemini-2.5-flash, и др.)
  --docs      Пути к файлам (glob или пути). По умолчанию: test_model/*.pdf, test_model/*.jpg, test_model/*.png
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO

# Project root (where .env.local lives)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_LOCAL = PROJECT_ROOT / ".env.local"
TEST_MODEL_DIR = PROJECT_ROOT / "test_model"

if ENV_LOCAL.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_LOCAL, override=True)

# Add backend to path for PyPDF2 if needed (we use it directly)
# Dependencies: httpx, PyPDF2, python-dotenv - all in backend requirements
import httpx
import PyPDF2

# ---------------------------------------------------------------------------
# Prompts and logic - exact copy from app/services/ai_service.py
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """Проанализируй этот медицинский документ и извлеки следующую информацию в формате JSON.

# ОБЯЗАТЕЛЬНАЯ СТРУКТУРА JSON:

{
  "document_type": "ОБЯЗАТЕЛЬНО - один из 5 типов",
  "document_subtype": "условно обязательно",
  "research_area": "только для инструментальных исследований",
  "specialties": ["массив специальностей"],
  "document_date": "YYYY-MM-DD",
  "patient_name": "Фамилия И.О.",
  "medical_facility": "название учреждения",
  "document_language": "ru|en",
  "confidence": 0.95,
  "summary": "краткое содержание"
}

# ТИПЫ ДОКУМЕНТОВ (выбери ОДИН из 5):

1. "Прием врача" - амбулаторный прием, консультация, медицинское заключение врача
2. "Результаты анализа" - лабораторные анализы любого типа
3. "Инструментальное исследование" - УЗИ, МРТ, КТ, рентген, маммография
4. "Функциональная диагностика" - ЭКГ, ЭЭГ, холтер, спирометрия, ФГДС, колоноскопия
5. "Другое" - если не подходит ни под одну категорию

# ПРАВИЛА ЗАПОЛНЕНИЯ ПО ТИПАМ:

## "Прием врача":
- specialties: ["Кардиология", "Терапия"] - ОБЯЗАТЕЛЬНО массив (минимум 1)
- document_subtype: null
- research_area: null

Справочник специальностей: Терапия, Кардиология, Неврология, Гастроэнтерология, Эндокринология, Урология, Оториноларингология (ЛОР), Офтальмология, Травматология и ортопедия, Дерматология, Инфекционные болезни, Ревматология, Пульмонология, Нефрология, Онкология, Хирургия, Акушерство и гинекология, Педиатрия, Психиатрия, Другая специальность

## "Результаты анализа":
- document_subtype: "Общий анализ крови" - ОБЯЗАТЕЛЬНО
- specialties: null
- research_area: null

Подтипы: Общий анализ крови, Биохимический анализ крови, Общий анализ мочи, Анализ кала, Бактериологический анализ, Серологический анализ, Гистологическое исследование, Цитологическое исследование, Иммунологический анализ, Гормональный анализ, Генетический анализ, Другой анализ

## "Инструментальное исследование":
- document_subtype: "УЗИ" - ОБЯЗАТЕЛЬНО
- research_area: "Брюшная полость" - рекомендуется
- specialties: null

Подтипы: УЗИ, МРТ, КТ, Рентген, Маммография, Флюорография, Ангиография, Другое исследование

Области для УЗИ: Брюшная полость, Щитовидная железа, Молочные железы, Органы малого таза, Сердце (ЭхоКГ), Сосуды, Суставы, Мягкие ткани, Другая область

Области для МРТ/КТ: Головной мозг, Позвоночник, Брюшная полость, Грудная клетка, Суставы, Мягкие ткани, Сосуды, Другая область

Области для Рентген: Грудная клетка, Позвоночник, Суставы, Кости конечностей, Черепа, Другая область

## "Функциональная диагностика":
- document_subtype: "ЭКГ (электрокардиография)" - ОБЯЗАТЕЛЬНО
- specialties: null
- research_area: null

Подтипы: ЭКГ (электрокардиография), ЭЭГ (электроэнцефалография), Холтер-мониторирование, Суточный мониторинг АД, Спирометрия, Велоэргометрия, ФГДС (фиброгастродуоденоскопия), Колоноскопия, Бронхоскопия, Другая функциональная диагностика

## "Другое":
- Все дополнительные параметры опциональны
- confidence должна быть низкой (<0.5)

# ОБЩИЕ ПРАВИЛА:

1. document_type - ВСЕГДА ОБЯЗАТЕЛЬНО, используй точное название из списка выше
2. Дата документа - это дата процедуры/приема, НЕ дата печати
3. Формат ФИО: "Иванов И.И." (с точками)
4. Специальности (specialties) - СУЩЕСТВИТЕЛЬНЫЕ: "Кардиология", а НЕ "Кардиолог"
5. Если информация не найдена - используй null
6. confidence (0.0-1.0) - твоя уверенность в классификации
7. document_language - код языка ("ru", "en")

# ВАЖНО:
- Отвечай ТОЛЬКО валидным JSON
- Без дополнительного текста
- Проверь, что структура соответствует типу документа"""

LABS_EXTRACTION_PROMPT = """Определи, есть ли в документе результаты лабораторных анализов. Если да, извлеки их в JSON по стандартизованной схеме.

Стандартизованный формат:
{
  "lab_results": [
    {
      "test_name": "название анализа (например: гемоглобин, глюкоза)",
      "value": "числовое значение как строка",
      "unit": "единицы измерения (например: г/л, ммоль/л, %)",
      "reference_range": "референсный диапазон как строка (например: 120-160)",
      "flag": "L|N|H|A"  // L ниже нормы, N норма, H выше нормы, A абнормально/критично
    }
  ]
}

Правила:
- Если анализов нет, верни {"lab_results": []}
- test_name на русском языке, как в документе, но без лишнего шума
- value оставляй строкой, не округляй
- ВАЖНО: unit должен точно соответствовать единицам измерения из документа
  * Если указаны проценты (%), обязательно указывай "%" в unit
  * Если указаны абсолютные значения (например, 10*9/л, х10^9/л, г/л), указывай их точно как в документе
  * Разные единицы измерения одного анализа (например, процентные и абсолютные) - это РАЗНЫЕ биомаркеры
  * Не смешивай единицы: если в документе "Лимфоциты 42%" и "Лимфоциты 2.5 10*9/л", это две отдельные записи
- Если единиц нет, используй null
- Если референс нет, используй null
- Определи flag исходя из референсного диапазона, если он указан
- Отвечай ТОЛЬКО валидным JSON

Примеры правильного извлечения:
- "Лимфоциты 42%" → {"test_name": "Лимфоциты", "value": "42", "unit": "%", ...}
- "Лимфоциты 2.5 10*9/л" → {"test_name": "Лимфоциты", "value": "2.5", "unit": "10*9/л", ...}
- "Гемоглобин 145 г/л" → {"test_name": "Гемоглобин", "value": "145", "unit": "г/л", ...}
- "Гемоглобин 14.5 г/дл" → {"test_name": "Гемоглобин", "value": "14.5", "unit": "г/дл", ...}
"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from PDF file - same as ai_service._extract_text_from_pdf"""
    try:
        pdf_file = BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        raise ValueError(f"Не удалось извлечь текст из PDF: {str(e)}")


async def call_openrouter(
    api_key: str,
    model: str,
    messages: list,
    base_url: str = "https://openrouter.ai/api/v1/chat/completions",
) -> dict:
    """OpenRouter API call - same params as ai_service._call_openrouter"""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "MedHistory",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def extract_usage(response_data: dict) -> dict | None:
    usage = response_data.get("usage")
    if not usage:
        return None
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def parse_classification_response(response_data: dict) -> dict:
    """Parse classification JSON from response - returns dict (not DocumentMetadata)"""
    content = response_data["choices"][0]["message"]["content"]
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def parse_labs_response(response_data: dict) -> dict:
    """Parse lab_results from response - same as ai_service._parse_labs_response"""
    try:
        content = response_data["choices"][0]["message"]["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)
        lab_results = data.get("lab_results") or []
        normalized = []
        for item in lab_results:
            normalized.append({
                "test_name": item.get("test_name"),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "reference_range": item.get("reference_range"),
                "flag": item.get("flag"),
            })
        return {"lab_results": normalized, "usage": extract_usage(response_data)}
    except Exception:
        return {"lab_results": [], "usage": None}


async def process_document(
    api_key: str,
    model: str,
    doc_path: Path,
    base_url: str,
) -> dict:
    """Process one document with one model: classification + lab extraction if applicable."""
    result = {
        "document": doc_path.name,
        "model": model,
        "classification": None,
        "lab_results_count": 0,
        "lab_results_sample": [],
        "usage": None,
        "usage_labs": None,
        "duration_sec": 0.0,
        "error": None,
    }
    start = time.perf_counter()

    try:
        file_bytes = doc_path.read_bytes()
        file_ext = doc_path.suffix.lstrip(".").lower()

        if file_ext == "pdf":
            text_content = extract_text_from_pdf(file_bytes)
            if not text_content or len(text_content.strip()) < 50:
                raise ValueError("PDF содержит слишком мало текста или это отсканированное изображение")

            # 1. Classification
            messages = [
                {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\nТекст медицинского документа:\n\n{text_content}"}
            ]
        elif file_ext in ("jpg", "jpeg", "png"):
            import base64
            file_base64 = base64.b64encode(file_bytes).decode("utf-8")
            mime_type = "image/jpeg" if file_ext in ("jpg", "jpeg") else "image/png"
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{file_base64}"}},
                    ],
                }
            ]
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        resp = await call_openrouter(api_key, model, messages, base_url)
        result["classification"] = parse_classification_response(resp)
        result["usage"] = extract_usage(resp)

        doc_type = result["classification"].get("document_type", "")

        # 2. Lab extraction if "Результаты анализа"
        if doc_type == "Результаты анализа":
            if file_ext == "pdf":
                lab_messages = [
                    {"role": "user", "content": f"{LABS_EXTRACTION_PROMPT}\n\nТекст медицинского документа:\n\n{text_content}"}
                ]
            else:
                import base64
                file_base64 = base64.b64encode(file_bytes).decode("utf-8")
                mime_type = "image/jpeg" if file_ext in ("jpg", "jpeg") else "image/png"
                lab_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": LABS_EXTRACTION_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{file_base64}"}},
                        ],
                    }
                ]
            lab_resp = await call_openrouter(api_key, model, lab_messages, base_url)
            labs_data = parse_labs_response(lab_resp)
            result["lab_results_count"] = len(labs_data.get("lab_results", []) or [])
            result["lab_results_sample"] = (labs_data.get("lab_results") or [])[:5]
            result["usage_labs"] = labs_data.get("usage")

    except Exception as e:
        result["error"] = str(e)

    result["duration_sec"] = round(time.perf_counter() - start, 2)
    return result


def collect_document_paths(doc_args: list[str] | None) -> list[Path]:
    """Collect document paths from args or default test_model glob."""
    if doc_args:
        paths = []
        for arg in doc_args:
            p = Path(arg)
            if p.exists():
                if p.is_file():
                    paths.append(p)
                else:
                    paths.extend(p.glob("*.pdf"))
                    paths.extend(p.glob("*.jpg"))
                    paths.extend(p.glob("*.jpeg"))
                    paths.extend(p.glob("*.png"))
            else:
                # Try glob from project root
                for m in PROJECT_ROOT.glob(arg):
                    if m.is_file():
                        paths.append(m)
        return sorted(set(paths))

    if not TEST_MODEL_DIR.exists():
        return []
    paths = []
    for ext in ("*.pdf", "*.jpg", "*.jpeg", "*.png"):
        paths.extend(TEST_MODEL_DIR.glob(ext))
    return sorted(set(paths))


def print_report(results: list[dict], models: list[str], documents: list[str]):
    """Print console comparison table."""
    print("\n" + "=" * 100)
    print("СРАВНЕНИЕ МОДЕЛЕЙ")
    print("=" * 100)

    # Table: document x model (type | subtype | labs)
    col_w = 24
    header = "Документ".ljust(35)[:35] + " | " + " | ".join(m.ljust(col_w)[:col_w] for m in models)
    print("\n" + header)
    print("-" * len(header))

    for doc in documents:
        row_parts = [doc[:33].ljust(35) if len(doc) > 33 else doc.ljust(35)]
        for model in models:
            r = next((x for x in results if x["document"] == doc and x["model"] == model), None)
            if not r:
                cell = "-"
            elif r.get("error"):
                cell = f"ERR: {r['error'][:15]}..."
            else:
                ct = r.get("classification") or {}
                dt = (ct.get("document_type") or "?")[:10]
                ds = (ct.get("document_subtype") or "-")[:8]
                lc = r.get("lab_results_count", 0)
                cell = f"{dt}|{ds}|L{lc}"
            row_parts.append(cell.ljust(col_w)[:col_w])
        print(" | ".join(row_parts))

    # Summary by model
    print("\n" + "-" * 60)
    print("Сводка по моделям:")
    for model in models:
        model_results = [r for r in results if r["model"] == model]
        ok = sum(1 for r in model_results if not r.get("error"))
        total = len(model_results)
        avg_dur = sum(r["duration_sec"] for r in model_results) / total if total else 0
        total_tokens = 0
        for r in model_results:
            if r.get("usage"):
                total_tokens += (r["usage"].get("total_tokens") or 0) + (r.get("usage_labs") or {}).get("total_tokens", 0)
        avg_tok = total_tokens / total if total else 0
        print(f"  {model}: success={ok}/{total}, avg_duration={avg_dur:.1f}s, avg_tokens={avg_tok:.0f}")


async def main():
    parser = argparse.ArgumentParser(description="Compare OpenRouter models on medical documents")
    parser.add_argument(
        "--models",
        type=str,
        default="anthropic/claude-3.5-sonnet,google/gemini-2.5-flash,google/gemini-2.5-flash-lite,google/gemini-2.5-pro,google/gemini-2.0-flash-001",
        help="Comma-separated model IDs",
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        default=None,
        help="Document paths or globs (default: test_model/*.pdf, *.jpg, *.png)",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set. Create .env.local with OPENROUTER_API_KEY=sk-or-v1-...")
        sys.exit(1)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    doc_paths = collect_document_paths(args.docs)

    if not doc_paths:
        print(f"ERROR: No documents found. Add PDF/jpg/png to {TEST_MODEL_DIR} or pass --docs")
        sys.exit(1)

    documents = [p.name for p in doc_paths]
    base_url = "https://openrouter.ai/api/v1/chat/completions"

    print(f"Models: {models}")
    print(f"Documents: {documents}")
    print()

    results = []
    total_jobs = len(doc_paths) * len(models)
    done = 0
    for doc_path in doc_paths:
        for model in models:
            done += 1
            print(f"[{done}/{total_jobs}] {doc_path.name} @ {model}...", end=" ", flush=True)
            r = await process_document(api_key, model, doc_path, base_url)
            results.append(r)
            if r.get("error"):
                print(f"ERROR: {r['error'][:50]}")
            else:
                print(f"OK ({r['duration_sec']}s)")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "documents": documents,
        "models": models,
        "results": results,
        "summary": {},
    }

    by_model = {}
    for model in models:
        mr = [r for r in results if r["model"] == model]
        ok = sum(1 for r in mr if not r.get("error"))
        by_model[model] = {
            "success_rate": ok / len(mr) if mr else 0,
            "avg_tokens": sum(
                (r.get("usage") or {}).get("total_tokens", 0) + (r.get("usage_labs") or {}).get("total_tokens", 0)
                for r in mr
            ) / len(mr) if mr else 0,
            "avg_duration": sum(r["duration_sec"] for r in mr) / len(mr) if mr else 0,
        }
    report["summary"]["by_model"] = by_model

    print_report(results, models, documents)

    out_file = SCRIPT_DIR / f"compare_models_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nFull report saved to: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
