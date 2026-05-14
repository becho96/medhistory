"""Индекс синонимов имён анализов.

Источник — таблицы `analyte_standards` + `analyte_synonyms` (см. backend/migrations/005).
Кэшируется в `.cache/synonyms.json`, чтобы прогон метрик не требовал поднятой БД.

Уникальный ключ в `analyte_synonyms` — (synonym_lower, unit_lower), так что одно
и то же название может быть привязано к РАЗНЫМ canonical в зависимости от unit
(пример: "Лимфоциты" в "%" и в "10^9/л" — два разных биомаркера).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class SynonymsIndex:
    def __init__(
        self,
        primary: dict[tuple[str, str], str],
        fallback: dict[str, list[str]],
    ):
        self._primary = primary
        self._fallback = fallback

    def canonicalize(self, name: str, unit: Optional[str] = None) -> Optional[str]:
        """Найти canonical_name. Если по (name, unit) точно — возвращаем.
        Если только по name и вариант один — возвращаем. Иначе None.
        """
        if not name:
            return None
        key_name = name.strip().lower()
        key_unit = (unit or "").strip().lower()

        if key_unit:
            r = self._primary.get((key_name, key_unit))
            if r:
                return r
            # запасной вариант: synonym есть с unit_lower=""
            r = self._primary.get((key_name, ""))
            if r:
                return r

        candidates = self._fallback.get(key_name, [])
        unique = list(dict.fromkeys(candidates))  # сохранить порядок
        if len(unique) == 1:
            return unique[0]
        return None

    def size(self) -> dict[str, int]:
        return {
            "primary_pairs": len(self._primary),
            "unique_synonyms": len(self._fallback),
        }


def fetch_index_from_db(dsn: str) -> dict:
    """Запрос в Postgres → плоская структура для JSON-кэша.

    Формат:
        {
          "pairs": [{"synonym": "...", "unit": "...", "canonical": "..."}, ...],
          "stats": {"rows": N, "unique_synonyms": M, "canonicals": K}
        }
    """
    import psycopg

    query = """
        SELECT s.synonym_lower, COALESCE(s.unit_lower, ''), std.canonical_name
        FROM analyte_synonyms s
        JOIN analyte_standards std ON s.analyte_id = std.id
        WHERE std.is_active = true
    """
    pairs: list[dict[str, str]] = []
    canonicals: set[str] = set()
    synonyms: set[str] = set()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            for synonym_lower, unit_lower, canonical_name in cur:
                pairs.append({
                    "synonym": synonym_lower,
                    "unit": unit_lower,
                    "canonical": canonical_name,
                })
                canonicals.add(canonical_name)
                synonyms.add(synonym_lower)

    return {
        "pairs": pairs,
        "stats": {
            "rows": len(pairs),
            "unique_synonyms": len(synonyms),
            "canonicals": len(canonicals),
        },
    }


def save_cache(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(cache_path: Path) -> SynonymsIndex:
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Кэш синонимов не найден: {cache_path}.\n"
            f"Запустите: DATABASE_URL=... python -m benchmarks.document_analysis.src.cli sync-synonyms"
        )
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return _build_index(data["pairs"])


def _build_index(pairs: list[dict[str, str]]) -> SynonymsIndex:
    primary: dict[tuple[str, str], str] = {}
    fallback: dict[str, list[str]] = {}
    for p in pairs:
        key = (p["synonym"], p["unit"])
        # Если коллизия (одна и та же пара → разные canonical) — берём первую.
        primary.setdefault(key, p["canonical"])
        fallback.setdefault(p["synonym"], []).append(p["canonical"])
    return SynonymsIndex(primary, fallback)
