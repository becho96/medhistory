"""
Analyte resolver: proposes a canonical mapping for lab analytes that the exact
dictionary lookup missed, and queues the proposal for human review.

Pipeline for one unmapped (test_name, unit):
  1. Embed the name and retrieve top-k nearest canonicals (in-memory kNN over the
     canonical+synonym label set, embedded via the e5 sidecar).
  2. Ask a cheap LLM arbiter to decide, given the unit and the candidate shortlist:
     map to one candidate, or create a new canonical.
  3. Upsert the proposal into analyte_mapping_queue (status='pending').

Nothing is written to analyte_synonyms here — approval happens in db-viewer.

The reference index is held in memory (≈500 short labels); it is rebuilt lazily
and can be invalidated when the dictionary changes.
"""
import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.embeddings_client import embed_passages, embed_query, EmbeddingsError
from app.services.analyte_normalization_service_db import analyte_normalization_service_db

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Общий анализ крови",
    "Биохимия крови",
    "Липидный профиль",
    "Гормоны",
    "Витамины и микроэлементы",
    "Маркеры воспаления",
    "Общий анализ мочи",
    "Другие анализы",
]


@dataclass
class RefLabel:
    label: str
    canonical: str
    std_unit: str
    category: str
    vector: List[float]


@dataclass
class Candidate:
    canonical: str
    score: float
    std_unit: str
    category: str


class AnalyteResolver:
    def __init__(self) -> None:
        self._refs: List[RefLabel] = []
        self._loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def invalidate(self) -> None:
        self._loaded = False
        self._refs = []

    async def ensure_loaded(self, db: AsyncSession) -> None:
        """Build the in-memory reference index from the normalization dictionary."""
        if self._loaded:
            return
        if not analyte_normalization_service_db.is_loaded:
            await analyte_normalization_service_db.load_from_db(db, force=True)

        # Distinct labels -> canonical (canonical names + every synonym string).
        svc = analyte_normalization_service_db
        label_to_canon: Dict[str, str] = {}
        for canonical in svc._analytes.keys():
            label_to_canon.setdefault(canonical.strip().lower(), canonical)
        for (syn_lower, _unit_lower), (canonical, _coef) in svc._synonym_unit_index.items():
            label_to_canon.setdefault(syn_lower, canonical)

        labels = list(label_to_canon.keys())
        if not labels:
            self._refs = []
            self._loaded = True
            return

        vectors = await embed_passages(labels)
        refs: List[RefLabel] = []
        for label, vector in zip(labels, vectors):
            canonical = label_to_canon[label]
            analyte = svc.get_analyte(canonical)
            refs.append(RefLabel(
                label=label,
                canonical=canonical,
                std_unit=analyte.standard_unit if analyte else "",
                category=analyte.category_name if analyte else "Другие анализы",
                vector=vector,
            ))
        self._refs = refs
        self._loaded = True
        logger.info(f"🧭 Analyte resolver ref index ready: {len(refs)} labels")

    def knn(self, query_vec: List[float], k: int = 6) -> List[Candidate]:
        """Top-k canonicals by cosine similarity (vectors are L2-normalized → dot)."""
        scored: List[Tuple[float, RefLabel]] = [
            (sum(a * b for a, b in zip(query_vec, ref.vector)), ref)
            for ref in self._refs
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        seen: set = set()
        out: List[Candidate] = []
        for score, ref in scored:
            if ref.canonical in seen:
                continue
            seen.add(ref.canonical)
            out.append(Candidate(ref.canonical, round(score, 3), ref.std_unit, ref.category))
            if len(out) >= k:
                break
        return out

    async def _adjudicate(
        self, name: str, unit: str, candidates: List[Candidate]
    ) -> Dict[str, Any]:
        """LLM arbiter: decide map-to-candidate vs create-new. Returns proposal dict."""
        cand_lines = "\n".join(
            f"  - {c.canonical} [ед: {c.std_unit}] (кат: {c.category}, sim {c.score})"
            for c in candidates
        )
        system = (
            "Ты — медицинский лаборант, ведёшь справочник анализов. Дана лабораторная "
            "позиция (название+единица) и список КАНДИДАТОВ из справочника, найденных "
            "нечётким поиском (многие кандидаты нерелевантны — это лишь подсказки). "
            "Реши: это ТОТ ЖЕ биомаркер, что один из кандидатов, или НОВЫЙ анализ.\n"
            "Правила:\n"
            "- Один и тот же аналит в разных единицах — ОДИН биомаркер (map).\n"
            "- Процентная и абсолютная версии (% vs 10*9/л) — РАЗНЫЕ биомаркеры. Учитывай единицу.\n"
            "- Совпадение только по общему слову ('общий','кислота','гемоглобин') без совпадения "
            "сути — это НЕ тот же аналит.\n"
            "- Если верного кандидата нет — action='create' с чистым каноническим названием, "
            "категорией из списка и стандартной единицей.\n"
            'Ответ СТРОГО JSON: {"action":"map|create","target":"<точное имя кандидата или null>",'
            '"new_name":"<или null>","new_category":"<или null>","new_std_unit":"<или null>",'
            '"confidence":0..1,"reason":"<кратко>"}'
        )
        user = (
            f"Позиция: {name!r}, единица: {unit or '(нет)'!r}\n"
            f"Кандидаты:\n{cand_lines}\n\n"
            f"Категории для create: {', '.join(CATEGORIES)}"
        )
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-Title": "MedHistory",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(settings.OPENROUTER_BASE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        if "```" in content:
            part = content.split("```", 2)[1]
            content = part[4:].strip() if part.startswith("json") else part.strip()
        return json.loads(content)

    async def resolve(self, db: AsyncSession, name: str, unit: str) -> Dict[str, Any]:
        """Full resolve for one (name, unit): candidates + LLM proposal."""
        await self.ensure_loaded(db)
        query_vec = await embed_query(name)
        candidates = self.knn(query_vec, k=6)
        verdict = await self._adjudicate(name, unit, candidates)
        action = verdict.get("action")
        if action not in ("map", "create"):
            action = "uncertain"
        return {
            "candidates": [c.__dict__ for c in candidates],
            "action": action,
            "target": verdict.get("target"),
            "new_name": verdict.get("new_name"),
            "new_category": verdict.get("new_category"),
            "new_std_unit": verdict.get("new_std_unit"),
            "confidence": verdict.get("confidence"),
            "reason": verdict.get("reason"),
        }


analyte_resolver = AnalyteResolver()
