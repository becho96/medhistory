"""LLM-as-judge для оценки качества summary.

Фиксированная модель-судья (по умолчанию Claude Opus 4.7 через OpenRouter,
конфиг — `judge` в models.yaml). Чтобы прогон метрик можно было повторять без
повторных платных вызовов, ответы судьи кэшируются на диск: ключ кэша —
sha256 от (pred_summary || gt_summary || gt_key_facts || judge_model).

Если pred_summary пустой (pipeline упал и не дал summary) — возвращается
нулевой результат без обращения к судье.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx

from benchmarks.document_analysis.src.schema import JudgeConfig

from .types import SummaryScore

JUDGE_PROMPT_TEMPLATE = """Ты — медицинский эксперт-ревьюер. Оцени КРАТКОЕ СОДЕРЖАНИЕ (summary),
сгенерированное AI для медицинского документа, относительно эталона.

# Эталонное summary (ground truth)
{gt_summary}

# Ключевые факты, которые ДОЛЖНЫ присутствовать в summary
{gt_key_facts}

# Оцениваемое summary
{pred_summary}

# Задача
Оцени по трём целочисленным шкалам 0..5:
- factuality            — насколько изложенные факты согласуются с эталоном (5 = полностью, 0 = противоречит)
- completeness          — какая доля КЛЮЧЕВЫХ фактов раскрыта (5 = все, 0 = ни одного)
- hallucination_freedom — насколько summary СВОБОДНО от выдумок (5 = ничего лишнего, 0 = много галлюцинаций)

Также верни массив `per_fact_coverage` той же длины и в том же порядке,
что и список ключевых фактов. Элемент — true, если факт упомянут в summary
(семантически, не дословно), иначе false.

# Формат ответа — СТРОГО валидный JSON, без markdown-обёрток
{{
  "factuality": 0..5,
  "completeness": 0..5,
  "hallucination_freedom": 0..5,
  "per_fact_coverage": [true|false, ...],
  "comment": "1-2 предложения с обоснованием"
}}
"""


def _cache_key(pred: str, gt: str, facts: list[str], judge_model: str) -> str:
    h = hashlib.sha256()
    h.update(pred.encode("utf-8"))
    h.update(b"|")
    h.update(gt.encode("utf-8"))
    h.update(b"|")
    h.update("".join(facts).encode("utf-8"))
    h.update(b"|")
    h.update(judge_model.encode("utf-8"))
    return h.hexdigest()


def _build_prompt(pred_summary: str, gt_summary: str, gt_key_facts: list[str]) -> str:
    facts_str = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(gt_key_facts)) or "(не задано)"
    return JUDGE_PROMPT_TEMPLATE.format(
        gt_summary=gt_summary.strip(),
        gt_key_facts=facts_str,
        pred_summary=pred_summary.strip(),
    )


def _parse_judge_response(content: str) -> dict:
    """Распарсить JSON-ответ; снять markdown-обёртку если есть."""
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif text.startswith("```"):
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(text)


def _empty_score(judge_model: str) -> SummaryScore:
    return SummaryScore(
        factuality=0,
        completeness=0,
        hallucination_freedom=0,
        per_fact_coverage=[],
        comment="pred_summary пуст или pipeline не дал ответа",
        normalized=0.0,
        judge_model=judge_model,
    )


async def score_summary(
    pred_summary: Optional[str],
    gt_summary: str,
    gt_key_facts: list[str],
    judge: JudgeConfig,
    cache_dir: Path,
    api_key: str,
    base_url: str,
) -> SummaryScore:
    if not pred_summary or not pred_summary.strip():
        return _empty_score(judge.openrouter_slug)

    key = _cache_key(pred_summary, gt_summary, gt_key_facts, judge.openrouter_slug)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{key}.json"

    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        cached["from_cache"] = True
        return SummaryScore.model_validate(cached)

    prompt = _build_prompt(pred_summary, gt_summary, gt_key_facts)
    payload = {
        "model": judge.openrouter_slug,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": judge.temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "MedHistory-Benchmark-Judge",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(base_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    parsed = _parse_judge_response(content)

    factuality = int(parsed["factuality"])
    completeness = int(parsed["completeness"])
    hallu = int(parsed["hallucination_freedom"])
    normalized = round((factuality + completeness + hallu) / 15, 4)

    score = SummaryScore(
        factuality=factuality,
        completeness=completeness,
        hallucination_freedom=hallu,
        per_fact_coverage=list(parsed.get("per_fact_coverage", [])),
        comment=parsed.get("comment"),
        normalized=normalized,
        judge_model=judge.openrouter_slug,
        from_cache=False,
    )

    cache_file.write_text(
        json.dumps(score.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return score


def env_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY не задан в окружении. Положите в .env.local."
        )
    return key


def env_base_url() -> str:
    return os.environ.get(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1/chat/completions",
    )
