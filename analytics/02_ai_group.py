"""
Шаг 2: AI-группировка пар (test_name, unit) по анализам.

Читает pairs.json, отправляет список в Anthropic API.
LLM группирует пары в анализы, определяет canonical (самый частый в группе),
присваивает категорию и коэффициенты конвертации.

Вывод: analytics/groups_draft.json — РЕДАКТИРУЕМЫЙ источник правды для шага 03.
"""

import asyncio
import json
import os

import anthropic
import asyncpg

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PAIRS_PATH = "/analytics/pairs.json"
OUTPUT_PATH = "/analytics/groups_draft.json"

PG_DSN = (
    os.environ.get("DATABASE_URL", "")
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("+asyncpg", "")
    or "postgresql://medhistory_user:medhistory_local_pass@postgres:5432/medhistory"
)


# ── Загрузка категорий из PostgreSQL ──────────────────────────────────────────

async def fetch_categories(pg_dsn: str) -> list[str]:
    conn = await asyncpg.connect(pg_dsn)
    rows = await conn.fetch(
        "SELECT name FROM analyte_categories WHERE is_active = TRUE ORDER BY sort_order"
    )
    await conn.close()
    return [row["name"] for row in rows]


# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Ты эксперт по медицинским лабораторным анализам. Твоя задача — сгруппировать \
список пар (test_name, unit) из реальных лабораторных документов по анализам.

Правила:
1. Один анализ = одна группа. Разные варианты написания одного анализа (аббревиатура, \
   полное название, русский/английский) → одна группа.
2. Процентный (%) и абсолютный (10^9/л, тыс/мкл и т.п.) варианты одного показателя — \
   ВСЕГДА РАЗНЫЕ группы (например, "Лимфоциты (%)" и "Лимфоциты (абс)" — разные группы).
3. canonical_name: test_name пары с наибольшим count в группе.
4. standard_unit: unit пары с наибольшим count в группе (canonical).
5. is_canonical: true только у пары с наибольшим count (при равенстве — у первой).
6. coefficient: число, на которое нужно умножить значение синонима, \
   чтобы получить значение в standard_unit. \
   Если единицы совпадают — 1.0. \
   Примеры: г/дл → г/л: coefficient=10; мг/дл → ммоль/л (для холестерина): coefficient=0.0259.
7. category: одна из предоставленных категорий (точное совпадение названия).

Верни ТОЛЬКО валидный JSON-массив без комментариев и без markdown-обёртки:
[
  {
    "canonical_name": "...",
    "category": "...",
    "standard_unit": "...",
    "synonyms": [
      {"test_name": "...", "unit": "...", "count": N, "coefficient": 1.0, "is_canonical": true},
      {"test_name": "...", "unit": "...", "count": N, "coefficient": X.X}
    ]
  }
]
"""


def build_user_prompt(pairs: list[dict], categories: list[str]) -> str:
    categories_str = "\n".join(f"- {c}" for c in categories)
    pairs_str = "\n".join(
        f'{i+1}. test_name="{p["test_name"]}" | unit="{p["unit"]}" | count={p["count"]}'
        for i, p in enumerate(pairs)
    )
    return (
        f"Доступные категории:\n{categories_str}\n\n"
        f"Пары для группировки ({len(pairs)} штук):\n{pairs_str}"
    )


# ── AI-группировка ────────────────────────────────────────────────────────────

def call_anthropic(pairs: list[dict], categories: list[str]) -> list[dict]:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_prompt = build_user_prompt(pairs, categories)

    print(f"   Отправляю запрос в Anthropic API ({len(pairs)} пар, streaming)...")
    raw_parts = []
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
            print(".", end="", flush=True)
    print()  # newline after dots

    raw = "".join(raw_parts).strip()

    # Убираем markdown-обёртку если LLM всё же добавил
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    groups = json.loads(raw)
    print(f"   Получено {len(groups)} групп от LLM.")
    return groups


# ── Валидация ─────────────────────────────────────────────────────────────────

def validate_groups(groups: list[dict], pairs: list[dict], categories: list[str]) -> list[str]:
    """Базовые проверки структуры и охвата."""
    warnings = []
    known_categories = set(categories)

    # Собираем все синонимы из групп
    covered: set[tuple[str, str]] = set()
    for g in groups:
        if g.get("category") not in known_categories:
            warnings.append(f"Неизвестная категория: '{g.get('category')}' в группе '{g.get('canonical_name')}'")
        for s in g.get("synonyms", []):
            covered.add((s["test_name"], s["unit"]))

    # Проверяем, все ли исходные пары попали в группы
    for p in pairs:
        key = (p["test_name"], p["unit"])
        if key not in covered:
            warnings.append(f"Пара не попала ни в одну группу: test_name='{p['test_name']}' unit='{p['unit']}'")

    # Проверяем наличие is_canonical в каждой группе
    for g in groups:
        has_canonical = any(s.get("is_canonical") for s in g.get("synonyms", []))
        if not has_canonical:
            warnings.append(f"Нет is_canonical в группе '{g.get('canonical_name')}'")

    return warnings


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    print("📖 Читаю pairs.json...")
    with open(PAIRS_PATH, encoding="utf-8") as f:
        pairs = json.load(f)
    print(f"   Загружено {len(pairs)} пар.")

    print("🗃️  Загружаю категории из PostgreSQL...")
    categories = await fetch_categories(PG_DSN)
    print(f"   Категории: {categories}")

    print("🤖 Запрашиваю группировку у LLM...")
    groups = call_anthropic(pairs, categories)

    print("🔍 Валидирую результат...")
    warnings = validate_groups(groups, pairs, categories)
    if warnings:
        print(f"\n⚠️  Предупреждения ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("   ✅ Всё ок.")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

    total_synonyms = sum(len(g.get("synonyms", [])) for g in groups)
    print(f"\n✅ groups_draft.json сохранён: {len(groups)} групп, {total_synonyms} синонимов → {OUTPUT_PATH}")
    print("   📝 Отредактируй файл при необходимости, затем запускай 03_generate_sql.py")


if __name__ == "__main__":
    asyncio.run(main())
